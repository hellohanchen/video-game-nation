#!/usr/bin/env python3

import os

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from discord_fantasy.views import MainPage
from repository.vgn_collections import upsert_collection as repo_upsert_collection
from repository.vgn_users import get_user
from service.fantasy import LINEUP_PROVIDER
from service.fantasy.ranking import RANK_PROVIDER
from topshot.cadence.flow_collections import get_account_plays

# config bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='.', intents=intents)
LB_CHANNEL_NAMES = ["📊-leaderboard"]
GAMES_CHANNEL_NAMES = ["📅-games"]
FANTASY_CHANNEL_NAMES = ["🎮-fantasy"]
ADMIN_CHANNEL_NAMES = ["💻-admin"]

LB_CHANNELS = []
GAMES_CHANNELS = []
FANTASY_CHANNEL_MESSAGES = []

ADMIN_CHANNEL_IDS = []

LB_MESSAGE_IDS = {}
GAMES_MESSAGE_IDS = {}
PLAYERS_MESSAGE_IDS = {}


@bot.event
async def on_ready():
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.name in LB_CHANNEL_NAMES:
                LB_CHANNELS.append(channel)
            if channel.name in GAMES_CHANNEL_NAMES:
                GAMES_CHANNELS.append(channel)
            if channel.name in ADMIN_CHANNEL_NAMES:
                ADMIN_CHANNEL_IDS.append(channel.id)
            if channel.name in FANTASY_CHANNEL_NAMES:
                view = MainPage(LINEUP_PROVIDER, RANK_PROVIDER)
                message = await channel.send("Ready to start daily NBA fantasy game?", view=view)
                FANTASY_CHANNEL_MESSAGES.append(message)

    refresh_entry.start()


############
# Collection (DM only)
############
@bot.command(name='collection', help="Update user's topshot collections info.")
async def upsert_collection(context):
    if not isinstance(context.channel, discord.channel.DMChannel):
        return

    vgn_user = get_user(context.message.author.id)

    if vgn_user is None:
        await context.channel.send("Account not found, contact admin for registration.")
        return

    message = await load_and_upsert_collection(vgn_user[0], vgn_user[2])

    await context.channel.send(message)


async def load_and_upsert_collection(user_id, flow_address):
    try:
        plays = await get_account_plays(flow_address)
    except:
        return "Failed to fetch collection, try again or contact admin."

    try:
        return repo_upsert_collection(user_id, plays)
    except:
        return "Failed to update database, try again or contact admin."


############
# Lineup (DM only)
############
@tasks.loop(seconds=5)
async def refresh_entry():
    for message in FANTASY_CHANNEL_MESSAGES:
        view = MainPage(LINEUP_PROVIDER, RANK_PROVIDER)
        await message.edit(content="Ready to start daily NBA fantasy game?", view=view)


# start the bot
bot.run(TOKEN)
