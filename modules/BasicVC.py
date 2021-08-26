from discord import message
import discord
from discord import Embed
from discord.ext import commands
from io import BytesIO
import os
from pathlib import Path


class BasicVC(commands.Cog):
    """ValorantCog"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='join', brief='Join a vc', description="Join a vc")
    async def join(self, context):
        if len(self.bot.voice_clients) > 0:
            await self.bot.voice_clients[0].move_to(context.message.author.voice.channel)
            return
        if context.message.author.voice:
            self.voice_player = await context.message.author.voice.channel.connect()
        else:
            await context.message.channel.send('You must be in a voice channel to use this command')
    
    @commands.command(name='leave', brief='Leave a vc', description="Leave a vc")
    async def leave(self, context):
        await self.bot.voice_clients[0].disconnect()

def setup(bot):
    bot.add_cog(BasicVC(bot))
