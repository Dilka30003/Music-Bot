from asyncio.queues import Queue
from discord import message
import discord
from discord import Embed
from discord.ext import commands
from discord.ext import tasks
from io import BytesIO
import os
from pathlib import Path
import yaml
import threading
import random

import youtube_dl
import asyncio
from youtubesearchpython import VideosSearch
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from discord_components import DiscordComponents, Button, ButtonStyle

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

with open('config.yaml') as f:
    localConfig = yaml.load(f, Loader=yaml.FullLoader)
    client_id = localConfig['spotify_client']
    client_secret = localConfig['spotify_secret']

scope = "playlist-read-collaborative"
#sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id, client_secret= client_secret, redirect_uri='http://localhost/', scope=scope))
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri="http://localhost/", scope=scope, open_browser=False, ))

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# Class for storing song data
class Song():
    def __init__(self, results):
        self.url = results['link']
        self.title = results['title']
        self.duration = results['duration']

class MusicControl(commands.Cog):
    """ValorantCog"""

    def __init__(self, bot):
        self.bot = bot
        self.task = self.queueHandler
        self.queue = []
        self.queueIndex = 0
        self.stopLoading = False
        self.context = None
        self.checkButtons.start()

    # Function to load tracks from a list of tracks
    def loadTracks(self, tracks):
        for rawSong in tracks:
            name = rawSong['track']['name']
            artist = rawSong['track']['artists'][0]['name']
            results = VideosSearch(name + ' ' + artist, limit = 1).result()['result'][0]
            song = Song(results)
            if self.stopLoading:
                self.stopLoading = False
                break
            self.queue.append(song)
            
    @commands.command(name='play', aliases=['p'])
    async def play(self, context, *, arg):

        controls = self.bot.get_cog('BasicVC')
        try:
            await controls.join(context)
        except:
            return

        # Check if the message contains a link to a spotify playlist
        if 'open.spotify.com/playlist/' in arg:
            playlist = sp.playlist(arg)

            name = playlist['tracks']['items'][0]['track']['name']
            results = VideosSearch(name, limit = 1).result()['result'][0]
            song = Song(results)
            self.queue.append(song)

            # If a playlist is specified, start loading in a seperate thread to stop the bot from hanging
            self.loadThread = threading.Thread(target=self.loadTracks, args=([playlist['tracks']['items'][1:]]), daemon=True).start()

            # If the loading task isn't running, start it
            if not self.task.is_running():
                await self.task.start(context)
            
            playlistLength = len(playlist['tracks']['items'])
            await context.send(f'Added {playlistLength} songs to queue')
        # If only a single song is specified, find it and add it to the queue
        else:
            results = VideosSearch(arg, limit = 1).result()['result'][0]
            song = Song(results)

            await context.send(f'Added \'{song.title}\' to queue')

            self.queue.append(song)


            if not self.task.is_running():
                self.task.start(context)

    @commands.command(name='stop')
    async def stop(self, context):
        self.stopLoading = True         # Stop loading songs from the loading thread
        context.voice_client.stop()
        self.queue = []
    
    @commands.command(name='clear')
    async def stop(self, context):
        self.stopLoading = True
        self.queue = []
        await context.message.add_reaction('\N{THUMBS UP SIGN}')
    
    # To skip, stop playing the current song and the play task will start the next song automatically
    @commands.command(name='skip', aliases=['n', 's'])
    async def skip(self, context):
        context.voice_client.stop()

    @commands.command(name='shuffle')
    async def shuffle(self, context):
        random.shuffle(self.queue)
        await context.message.add_reaction('\N{THUMBS UP SIGN}')
    
    # To jump, delete all the songs in the queue before the specified index and skip the current song
    @commands.command(name='jump')
    async def jump(self, context, id):
        try:
            id = int(id)
        except:
            context.send("Must supply a number")
        del self.queue[:id-1]
        context.voice_client.stop()
    
    @commands.command(name='remove')
    async def remove(self, context, id):
        try:
            id = int(id)
        except:
            context.send("Must supply a number")
        del self.queue[id-1]
        await context.message.add_reaction('\N{THUMBS UP SIGN}')
    
    @commands.command(name='swap')
    async def swap(self, context, id1, id2):
        try:
            id1 = int(id1)
            id2 = int(id2)
        except:
            context.send("Must supply a number")
        temp = self.queue[id1-1]
        self.queue[id1-1] = self.queue[id2-1]
        self.queue[id2-1] = temp
        await context.message.add_reaction('\N{THUMBS UP SIGN}')
    
    @commands.command(name='move')
    async def move(self, context, id1, id2):
        try:
            id1 = int(id1)
            id2 = int(id2)
        except:
            context.send("Must supply a number")
        song = self.queue.pop(id1-1)
        self.queue.insert(id2-1, song)
        await context.message.add_reaction('\N{THUMBS UP SIGN}')

    # Generates a human readable queue page based on the current page number
    async def generateQueue(self):
        index = self.queueIndex
        message = '```\n'
        for i in range(10*index, min(len(self.queue), 10*(index+1))):
            song:Song = self.queue[i]
            lineNumber = (str(i+1)+'.').ljust(3)
            line = f'{lineNumber} {song.title.ljust(100)} {song.duration}'
            message += line + '\n'
        message += '```'
        
        maxIndex = len(self.queue)//10

        buttons = []
        if index > 0:
            buttons.append(Button(style=ButtonStyle.blue, label="Previous Page", custom_id="btnPrev"))
        if index < maxIndex:
            buttons.append(Button(style=ButtonStyle.blue, label="Next Page", custom_id="btnNext"))
        
        return message, buttons

    # Output the current queue
    @commands.command(name='queue', aliases=['q'])
    async def queue(self, context):
        if len(self.queue) > 0:
            self.queueIndex = 0
            message, buttons = await self.generateQueue()

            if len(buttons) > 0:
                await context.send(content=message, components=[buttons])
            else:
                await context.send(content=message)
        else:
            await context.message.add_reaction('\N{NO ENTRY SIGN}')

            
    # handle buttons attached to messages
    @tasks.loop(seconds=0.5)
    async def checkButtons(self):
        interaction = await self.bot.wait_for("button_click")
        #await interaction.send(content="Button Clicked")
        if interaction.component.id == 'btnNext':
            self.queueIndex += 1
            message, buttons = await self.generateQueue()

            if len(buttons) > 0:
                await interaction.edit_origin(content=message, components=[buttons])
            else:
                await interaction.edit_origin(content=message)
        elif interaction.component.id == 'btnPrev':
            self.queueIndex -= 1
            message, buttons = await self.generateQueue()

            if len(buttons) > 0:
                await interaction.edit_origin(content=message, components=[buttons])
            else:
                await interaction.edit_origin(content=message)
        elif interaction.component.id == 'btnSkip':
            await self.skip(self.context)
            await interaction.edit_origin()

    # Loop that handles playing songs from the queue
    @tasks.loop(seconds=1)
    async def queueHandler(self, context):
        # If the bot isnt currently playing music, dequeue a song and start playing it
        if not context.voice_client.is_playing():
            if len(self.queue) < 1:
                self.task.cancel()
            else:
                song = self.queue.pop(0)
                url = song.url
                async with context.typing():
                    player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
                    context.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
                self.context = context
                await context.send(content=f'Now playing: {player.title}', components=[Button(style=ButtonStyle.blue, label="Skip", custom_id="btnSkip")])

def setup(bot):
    bot.add_cog(MusicControl(bot))
