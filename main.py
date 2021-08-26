#!/usr/bin/python3
import yaml
import os
from os import listdir
from os.path import isfile, join
from datetime import datetime, timedelta
import logging
from io import BytesIO

import discord
from discord import Embed
from discord.ext import commands
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType
import time

import asyncio
import threading

# Remove the old log file if it exists and start logging
try:
    os.remove('logs/bot.log')
except OSError:
    pass
logging.basicConfig(filename='logs/bot.log', level=logging.DEBUG)

# Open config files
with open('credentials.yaml') as f:
    credentials = yaml.load(f, Loader=yaml.FullLoader)
    logging.info('Loaded Credentials')
with open('config.yaml') as f:
    localConfig = yaml.load(f, Loader=yaml.FullLoader)
    logging.info('Loaded Local Config')

# Init Bot
TOKEN = credentials['token']

bot = commands.Bot(command_prefix=localConfig['command_prefix'])#, help_command=None)
logging.info('Created Bot')

if __name__ == '__main__':
    for extension in [f for f in listdir('modules') if isfile(join('modules', f))]:
        bot.load_extension('modules.' + extension[:-3])
        logging.info('Loaded ' + extension)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    logging.info('Successfully Logged In as ' + bot.user.name + '   ' + str(bot.user.id))
    DiscordComponents(bot, change_discord_methods=True)
    with open('version') as f:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f.read()))
    x = threading.Thread(target=background_task, daemon=True)
    x.start()
    
@bot.event
async def on_message(message):
    logging.debug('Recieved Message: ' + message.content)
    if message.author == bot.user:
        return
        
    await bot.process_commands(message)


# Background thread that runs once every 10 minutes
def background_task():
    while not bot.is_closed():
        pass

bot.run(TOKEN)