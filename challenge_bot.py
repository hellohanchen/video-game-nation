#!/usr/bin/env python3
import json
import os
import pathlib
from datetime import datetime

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from constants import TZ_ET
from topshot.challenge.challenge import Challenge
from utils import get_scoreboard_message

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN_CHALLENGE')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='/', intents=intents)


def load_challenges():
    with open(os.path.join(
            pathlib.Path(__file__).parent.resolve(),
            'topshot/challenge/challenges/current.json'
    ), 'r') as json_file:
        loaded = json.load(json_file)
        return loaded['message'], [Challenge.build_from_dict(challenge) for challenge in loaded['challenges']]


START_MESSAGE, CHALLENGES = load_challenges()

CHANNEL_NAMEs = ["🤖-mdv-flash-challenge-bot", "⚡-fc-tracker"]
MESSAGE_CHANNELS = []
START = False
PREVIOUS_MESSAGE_IDS = {}


@bot.event
async def on_ready():
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.name in CHANNEL_NAMEs:
                await purge_channel(channel)
                MESSAGE_CHANNELS.append(channel)

    get_current_challenge.start()


@tasks.loop(minutes=2)
async def get_current_challenge():
    messages = [get_scoreboard_message(START_MESSAGE)]

    for challenge in CHALLENGES:
        challenge_messages = challenge.get_formatted_messages()
        if len(challenge_messages) > 0:
            messages.extend(challenge_messages)

    messages.append("ET: **{}** , UPDATE EVERY 2 MINS".format(datetime.now(TZ_ET).strftime("%H:%M:%S")))

    for channel in MESSAGE_CHANNELS:
        if channel.id not in PREVIOUS_MESSAGE_IDS:
            PREVIOUS_MESSAGE_IDS[channel.id] = []
        try:
            for i in range(0, min(len(messages), len(PREVIOUS_MESSAGE_IDS[channel.id]))):
                prev_message = await channel.fetch_message(PREVIOUS_MESSAGE_IDS[channel.id][i])
                await prev_message.edit(content=messages[i])

            for i in range(len(PREVIOUS_MESSAGE_IDS[channel.id]), len(messages)):
                new_message = await channel.send(messages[i])
                PREVIOUS_MESSAGE_IDS[channel.id].append(new_message.id)

            for i in range(len(messages), len(PREVIOUS_MESSAGE_IDS[channel.id])):
                prev_message = await channel.fetch_message(PREVIOUS_MESSAGE_IDS[channel.id][i])
                await prev_message.edit(content=".")

        except Exception as err:
            continue


@bot.command(name='track')
@commands.cooldown(1, 30, commands.BucketType.user)
async def track_challenge(context):
    messages = [get_scoreboard_message(START_MESSAGE)]

    for challenge in CHALLENGES:
        messages.extend(challenge.get_formatted_messages())

    messages.append("ET: **{}** , UPDATE EVERY MIN".format(datetime.now(TZ_ET).strftime("%H:%M:%S")))

    for message in messages:
        await context.channel.send(message)


@bot.command(name="purge")
async def purge(ctx):
    await purge_channel(ctx.channel)


async def purge_channel(channel):
    await channel.purge(limit=None)
    await channel.send("Purge this channel to track new challenge.")
    if channel.id in PREVIOUS_MESSAGE_IDS:
        PREVIOUS_MESSAGE_IDS[channel.id] = []


bot.run(TOKEN)
