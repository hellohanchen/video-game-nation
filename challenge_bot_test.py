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
from provider.nba_provider import NBAProvider
from topshot.challenge.challenge import Challenge
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
        self.headline, self.challenges = load_challenges()

    def reload(self):
        self.headline, self.challenges = load_challenges()


def load_challenges():
    with open(os.path.join(
            pathlib.Path(__file__).parent.resolve(),
            'topshot/challenge/challenges/current.json'
    ), 'r') as json_file:
        loaded = json.load(json_file)
        return loaded['message'], [Challenge.build_from_dict(challenge) for challenge in loaded['challenges']]


CHALLENGE_PROVIDER = ChallengeProvider()
CHANNEL_NAMEs = ["⚡-fc-tracker"]
MESSAGE_CHANNELS = []
PREVIOUS_MESSAGE_IDS = {}

LOCK = threading.Lock()


@bot.event
async def on_ready():
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.name in CHANNEL_NAMEs:
                MESSAGE_CHANNELS.append(channel)

    get_current_challenge.start()


@tasks.loop(minutes=1)
async def get_current_challenge():
    LOCK.acquire()
    messages = [NBAProvider.get_scoreboard_message(CHALLENGE_PROVIDER.headline)]

    for challenge in CHALLENGE_PROVIDER.challenges:
        challenge_messages = challenge.get_formatted_messages()
        if challenge_messages:
            messages += challenge_messages

    messages.append("ET: **{}** , UPDATE EVERY MINUTE".format(datetime.now(TZ_ET).strftime("%m/%d/%Y, %H:%M:%S")))

    await update_channel_messages(messages, MESSAGE_CHANNELS, PREVIOUS_MESSAGE_IDS)
    LOCK.release()


async def purge_channel(channel):
    await channel.purge(limit=None)
    await channel.send("Loading new challenges ... ")
    if channel.id in PREVIOUS_MESSAGE_IDS:
        PREVIOUS_MESSAGE_IDS[channel.id] = []


@bot.command(name="testreload")
async def reload(ctx):
    LOCK.acquire()
    try:
        CHALLENGE_PROVIDER.reload()

        for channel in MESSAGE_CHANNELS:
            messages = [await channel.fetch_message(message_id) for message_id in PREVIOUS_MESSAGE_IDS[channel.id]]
            await channel.delete_messages(messages)
        PREVIOUS_MESSAGE_IDS.clear()
    except Exception as err:
        await ctx.channel.send(f'Failed: ${err}.')
        LOCK.release()
        return

    await ctx.channel.send("Reloaded")
    LOCK.release()


bot.run(TOKEN)
