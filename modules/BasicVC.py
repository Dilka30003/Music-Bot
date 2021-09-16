from discord import message
import discord
from discord import Embed
from discord.ext import commands
from io import BytesIO
import os
from pathlib import Path

from discord.ext.commands import context


class BasicVC(commands.Cog):
    """ValorantCog"""

    def __init__(self, bot):
        self.bot = bot
        self.context = None

    @commands.command(name='join', brief='Join a vc', description="Join a vc")
    async def join(self, context):
        self.context = context
        if len(self.bot.voice_clients) > 0:
            await context.voice_client.move_to(context.message.author.voice.channel)
            return
        if context.message.author.voice:
            self.voice_player = await context.message.author.voice.channel.connect()
        else:
            await context.message.channel.send('You must be in a voice channel to use this command')
            raise RuntimeError("User not in voice channel")
    
    @commands.command(name='leave', brief='Leave a vc', description="Leave a vc")
    async def leave(self, context):
        controls = self.bot.get_cog('MusicControl')
        await controls.stop(context)

        await context.voice_client.disconnect()
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel is not None and not member.bot:
            notBot = list(filter(None, [(x if not x.bot else None) for x in before.channel.members]))
            if len(notBot) == 0:
                controls = self.bot.get_cog('MusicControl')
                await controls.stop(self.context)
                await before.channel.guild.voice_client.disconnect()

def setup(bot):
    bot.add_cog(BasicVC(bot))
