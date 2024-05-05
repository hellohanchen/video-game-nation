#!/usr/bin/env python3

import os

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from service.redemptionrun.lineup import RR_LINEUP_SERVICE
from service.redemptionrun.ranking import RR_RANKING_SERVICE
from service.redemptionrun.views import MainPage
from vgnlog.channel_logger import ADMIN_LOGGER

# config bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN_REDEMPTION_RUM')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='.rrtest.', intents=intents)
ADMIN_CHANNEL_ID = 1097055938441130004

RR_CHANNEL_IDS = ["🎮-fantasy-test"]
RR_CHANNEL_MESSAGES = []

WELCOME_MESSAGE = "**Welcome to the Redemption Run game!**\n"


@bot.event
async def on_ready():
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.type != discord.ChannelType.text:
                continue

            if channel.id == ADMIN_CHANNEL_ID:
                ADMIN_LOGGER.init("RRTest", channel)
                continue

            if channel.id in RR_CHANNEL_IDS:
                view = MainPage(RR_LINEUP_SERVICE, RR_RANKING_SERVICE)
                message = await channel.send(WELCOME_MESSAGE, view=view)
                RR_CHANNEL_MESSAGES.append(message)

    refresh_entry.start()


@tasks.loop(seconds=60)
async def refresh_entry():
    for message in RR_CHANNEL_MESSAGES:
        view = MainPage(RR_LINEUP_SERVICE, RR_RANKING_SERVICE)
        await message.edit(content=WELCOME_MESSAGE, view=view)

# start the bot
bot.run(TOKEN)
