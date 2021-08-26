from asyncio.queues import Queue
from discord import message
import discord
from discord import Embed
from discord.ext import commands
from discord.ext import tasks
from io import BytesIO
import os
from pathlib import Path

import youtube_dl
import asyncio
from youtubesearchpython import VideosSearch

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




class MusicControl(commands.Cog):
    """ValorantCog"""

    def __init__(self, bot):
        self.bot = bot
        self.task = self.queueHandler
        self.queue = []

    @commands.command(name='play')
    async def play(self, context, *, arg):
        url = VideosSearch(arg, limit = 1).result()['result'][0]['link']


        controls = self.bot.get_cog('BasicVC')
        await controls.join(context)

        self.queue.append(url)
        if not self.task.is_running():
            self.task.start(context)

    @commands.command(name='stop')
    async def stop(self, context, command = None):
        self.queue = []
        context.voice_client.stop()
    
    @commands.command(name='skip')
    async def stop(self, context, command = None):
        context.voice_client.stop()
    
    @tasks.loop(seconds=1)
    async def queueHandler(self, context):
        if not context.voice_client.is_playing():
            if len(self.queue) < 1:
                self.task.cancel()
            else:
                url = self.queue.pop(0)
                async with context.typing():
                    player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
                    context.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
                await context.send(f'Now playing: {player.title}')

def setup(bot):
    bot.add_cog(MusicControl(bot))
