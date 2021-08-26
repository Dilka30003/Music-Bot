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
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id, client_secret= client_secret, redirect_uri='http://localhost/', scope=scope))


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

    def loadTracks(self, tracks):
        for rawSong in tracks:
            name = rawSong['track']['name']
            results = VideosSearch(name, limit = 1).result()['result'][0]
            song = Song(results)
            self.queue.append(song)

    @commands.command(name='play', aliases=['p'])
    async def play(self, context, *, arg):

        controls = self.bot.get_cog('BasicVC')
        await controls.join(context)

        if 'open.spotify.com/playlist/' in arg:
            playlist = sp.playlist(arg)

            name = playlist['tracks']['items'][0]['track']['name']
            results = VideosSearch(name, limit = 1).result()['result'][0]
            song = Song(results)
            self.queue.append(song)

            threading.Thread(target=self.loadTracks, args=([playlist['tracks']['items'][1:]]), daemon=True).start()

            if not self.task.is_running():
                await self.task.start(context)
            
            playlistLength = len(playlist['tracks']['items'])
            await context.send(f'Added {playlistLength} songs to queue')

        else:
            results = VideosSearch(arg, limit = 1).result()['result'][0]
            song = Song(results)

            await context.send(f'Added \'{song.title}\' to queue')

            self.queue.append(song)


            if not self.task.is_running():
                self.task.start(context)

    @commands.command(name='stop', aliases=['clear'])
    async def stop(self, context, command = None):
        self.queue = []
        context.voice_client.stop()
    
    @commands.command(name='skip', aliases=['n', 's'])
    async def stop(self, context, command = None):
        context.voice_client.stop()

    @commands.command(name='shuffle')
    async def shuffle(self, context, command = None):
        random.shuffle(self.queue)
    
    @tasks.loop(seconds=0.5)
    async def queueHandler(self, context):
        if not context.voice_client.is_playing():
            if len(self.queue) < 1:
                self.task.cancel()
            else:
                song = self.queue.pop(0)
                url = song.url
                async with context.typing():
                    player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
                    context.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
                await context.send(f'Now playing: {player.title}')

def setup(bot):
    bot.add_cog(MusicControl(bot))
