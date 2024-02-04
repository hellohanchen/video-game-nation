#!/usr/bin/env python3
import json
import os
import pathlib
import threading
from datetime import datetime

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from constants import TZ_ET
from service.fastbreak.dynamic_lineup import DYNAMIC_LINEUP_SERVICE
from vgnlog.channel_logger import ADMIN_LOGGER
from provider.nba.nba_provider import NBAProvider, NBA_PROVIDER
from provider.topshot.challenge.challenge import Challenge
from service.fastbreak.views import MainPage
from utils import update_channel_messages

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN_CHALLENGE')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='/', intents=intents)


class ChallengeProvider:
    def __init__(self):
        self.headline = ""
        self.challenges = []
        self.reload()

    def reload(self):
        self.headline, self.challenges = load_challenges()


def load_challenges():
    with open(os.path.join(
            pathlib.Path(__file__).parent.resolve(),
            'provider/topshot/challenge/challenges/current.json'
    ), 'r') as json_file:
        loaded = json.load(json_file)
        return loaded['message'], [Challenge.build_from_dict(challenge) for challenge in loaded['challenges']]


CHALLENGE_PROVIDER = ChallengeProvider()
CHANNEL_NAMEs = ["⚡-fc-tracker"]
TS_CHANNEL_ID = 924447554480013343
ADMIN_CHANNEL_ID = 1097055938441130004

CHALLENGE_CHANNELS = []
CHALLENGE_MESSAGE_IDS = {}

FB_CHANNEL_MESSAGES = []


@bot.event
async def on_ready():
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.type != discord.ChannelType.text:
                continue

            if channel.id == TS_CHANNEL_ID:
                CHALLENGE_CHANNELS.append(channel)

                view = MainPage(DYNAMIC_LINEUP_SERVICE)
                message = await channel.send(f"Track your fastbreak here!", view=view)
                FB_CHANNEL_MESSAGES.append(message)
                continue

            if channel.id == ADMIN_CHANNEL_ID:
                ADMIN_LOGGER.init("Challenge", channel)
                continue

            if channel.name in CHANNEL_NAMEs:
                await purge_channel(channel)
                CHALLENGE_CHANNELS.append(channel)

                view = MainPage(DYNAMIC_LINEUP_SERVICE)
                message = await channel.send(f"Track your fastbreak here!", view=view)
                FB_CHANNEL_MESSAGES.append(message)

    update_fastbreak.start()
    update_challenges.start()


@tasks.loop(seconds=90)
async def update_challenges():
    messages = [NBAProvider.get_scoreboard_message(CHALLENGE_PROVIDER.headline)]

    for challenge in CHALLENGE_PROVIDER.challenges:
        challenge_messages = challenge.get_formatted_messages()
        if challenge_messages:
            messages += challenge_messages

    messages.append("ET: **{}** , UPDATE EVERY 90 SECONDS".format(datetime.now(TZ_ET).strftime("%m/%d/%Y, %H:%M:%S")))

    await update_channel_messages(messages, CHALLENGE_CHANNELS, CHALLENGE_MESSAGE_IDS)


async def purge_channel(channel):
    await channel.purge(limit=None)
    if channel.id in CHALLENGE_MESSAGE_IDS:
        CHALLENGE_MESSAGE_IDS[channel.id] = []


@bot.command(name="reload")
async def reload(ctx):
    try:
        NBA_PROVIDER.reload()
        CHALLENGE_PROVIDER.reload()
    except Exception as err:
        await ctx.channel.send(f'Failed: ${err}.')
        return

    await ctx.channel.send("Reloaded")


@tasks.loop(minutes=2)
async def update_fastbreak():
    await DYNAMIC_LINEUP_SERVICE.update()
    for message in FB_CHANNEL_MESSAGES:
        view = MainPage(DYNAMIC_LINEUP_SERVICE)
        await message.edit(content="Track your fastbreak here!", view=view)


bot.run(TOKEN)
