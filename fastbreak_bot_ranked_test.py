#!/usr/bin/env python3

import os

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from service.fastbreak.lineup import LINEUP_SERVICE
from service.fastbreak.ranked.views import MainPage
from service.fastbreak.ranking import RANK_SERVICE

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

WELCOME_MESSAGE = "**Welcome to the B2B fastbreak contest!**\n" \
                  "Link TS account and submit your fastbreak lineup here to join the community contest.\n" \
                  "To be eligible to win rewards, please make sure use your own account and " \
                  "submit the same lineup matching the one submitted to Topshot Fastbreak.\n\n" \
                  "**Don't forget to enter our NBA Pick em game with Krause House DAO!**\n" \
                  "FREE to Enter! Daily Prizes! Make sure to join B2B for community specific prizes.\n" \
                  "➡ https://www.krausepicks.com/auth/signup?community=2"


@bot.event
async def on_ready():
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.type != discord.ChannelType.text:
                continue

            if channel.name in ADMIN_CHANNEL_NAMES:
                ADMIN_CHANNEL_IDS.append(channel.id)
            if channel.name in FB_CHANNEL_NAMES:
                view = MainPage(LINEUP_SERVICE, RANK_SERVICE)
                message = await channel.send(WELCOME_MESSAGE, view=view)
                FB_CHANNEL_MESSAGES.append(message)

    refresh_entry.start()


@tasks.loop(seconds=5)
async def refresh_entry():
    for message in FB_CHANNEL_MESSAGES:
        view = MainPage(LINEUP_SERVICE, RANK_SERVICE)
        await message.edit(content=WELCOME_MESSAGE, view=view)


# start the bot
bot.run(TOKEN)
