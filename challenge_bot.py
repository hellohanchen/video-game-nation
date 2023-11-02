#!/usr/bin/env python3
import json
import os
import pathlib
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
CHANNEL_NAMEs = ["🤖-mdv-flash-challenge-bot", "⚡-fc-tracker"]
MESSAGE_CHANNELS = []
PREVIOUS_MESSAGE_IDS = {}


@bot.event
async def on_ready():
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.name in CHANNEL_NAMEs:
                await purge_channel(channel)
                MESSAGE_CHANNELS.append(channel)

    get_current_challenge.start()


@tasks.loop(seconds=90)
async def get_current_challenge():
    messages = [NBAProvider.get_scoreboard_message(CHALLENGE_PROVIDER.headline)]

    for challenge in CHALLENGE_PROVIDER.challenges:
        challenge_messages = challenge.get_formatted_messages()
        if challenge_messages:
            messages += challenge_messages

    messages.append("ET: **{}** , UPDATE EVERY 90 SECONDS".format(datetime.now(TZ_ET).strftime("%m/%d/%Y, %H:%M:%S")))

    await update_channel_messages(messages, MESSAGE_CHANNELS, PREVIOUS_MESSAGE_IDS)


@bot.command(name="purge")
async def purge(ctx):
    await purge_channel(ctx.channel)


async def purge_channel(channel):
    await channel.purge(limit=None)
    await channel.send("Purge this channel to track new challenge.")
    if channel.id in PREVIOUS_MESSAGE_IDS:
        PREVIOUS_MESSAGE_IDS[channel.id] = []


@bot.command(name="reload")
async def reload(ctx):
    get_current_challenge.stop()
    try:
        CHALLENGE_PROVIDER.reload()

        for channel in MESSAGE_CHANNELS:
            await purge_channel(channel)
        PREVIOUS_MESSAGE_IDS.clear()
    except Exception as err:
        await ctx.channel.send(f'Failed: ${err}.')
        return

    get_current_challenge.start()
    await ctx.channel.send("Reloaded")


bot.run(TOKEN)
