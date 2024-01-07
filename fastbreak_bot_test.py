#!/usr/bin/env python3

import os

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from service.fastbreak.lineup import LINEUP_SERVICE
from service.fastbreak.ranking import RANK_SERVICE
from service.fastbreak.views import MainPage

# config bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN_FASTBREAK')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='.', intents=intents)
FB_CHANNEL_NAMES = ["🎮-fantasy-test"]
ADMIN_CHANNEL_NAMES = ["💻-admin"]

FB_CHANNEL_MESSAGES = []

ADMIN_CHANNEL_IDS = []

PLAYERS_MESSAGE_IDS = {}


@bot.event
async def on_ready():
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.name in ADMIN_CHANNEL_NAMES:
                ADMIN_CHANNEL_IDS.append(channel.id)
            if channel.name in FB_CHANNEL_NAMES:
                view = MainPage(LINEUP_SERVICE, RANK_SERVICE)
                for emoji in guild.emojis:
                    if emoji.name == "vgn":
                        print(emoji)
                message = await channel.send("Ready to start daily NBA fantasy game?", view=view)
                FB_CHANNEL_MESSAGES.append(message)

    refresh_entry.start()


@tasks.loop(seconds=5)
async def refresh_entry():
    for message in FB_CHANNEL_MESSAGES:
        view = MainPage(LINEUP_SERVICE, RANK_SERVICE)
        await message.edit(content="Start your fastbreak here!", view=view)


# start the bot
bot.run(TOKEN)
