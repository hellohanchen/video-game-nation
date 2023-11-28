#!/usr/bin/env python3

import os
from datetime import datetime

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from constants import TZ_ET
from discord_fantasy.views import MainPage
from provider.nba_provider import NBA_PROVIDER
from repository.vgn_collections import upsert_collection as repo_upsert_collection
from repository.vgn_users import get_user, insert_user
from service.fantasy import LINEUP_PROVIDER
from service.fantasy.ranking import RANK_PROVIDER
from topshot.cadence.flow_collections import get_account_plays
from topshot.graphql.get_address import get_flow_address
from utils import update_channel_messages, get_the_past_week, send_channel_messages

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
GAMES_CHANNEL_NAMES = ["📅-game-schedule"]
FANTASY_CHANNEL_NAMES = ["🎮-fantasy"]
ADMIN_CHANNEL_NAMES = ["💻-admin"]

LB_CHANNELS = []
GAMES_CHANNELS = []
FANTASY_CHANNEL_MESSAGES = []

ADMIN_CHANNEL_IDS = []

LB_MESSAGE_IDS = {}
GAMES_MESSAGE_IDS = {}
PLAYERS_MESSAGE_IDS = {}


VGN_EMOJI_ID = 1166225667952758815


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
                emoji = guild.get_emoji(VGN_EMOJI_ID)
                view = MainPage(LINEUP_PROVIDER, RANK_PROVIDER)
                if emoji is None:
                    message = await channel.send(f"Ready to start daily NBA fantasy game?", view=view)
                else:
                    message = await channel.send(f"Ready to start daily NBA fantasy game? {emoji}", view=view)
                FANTASY_CHANNEL_MESSAGES.append(message)

    update_leaderboard.start()
    update_games.start()
    refresh_entry.start()


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
# Admin
############
@bot.command(name='reload', help="[Admin] Reload game schedules, lineups and ranking")
async def reload(context):
    if context.channel.id not in ADMIN_CHANNEL_IDS:
        return

    NBA_PROVIDER.reload()
    LINEUP_PROVIDER.reload()
    RANK_PROVIDER.reload()
    LB_MESSAGE_IDS.clear()

    await context.channel.send("reloaded")


@bot.command(name='verify', help='[Admin] Insert a verified user record into db')
async def verify_user(context, username, topshot_username):
    if context.channel.id not in ADMIN_CHANNEL_IDS:
        return

    username = username.replace("~", " ")
    guild = discord.utils.find(lambda g: g.name == GUILD, bot.guilds)
    member = discord.utils.find(lambda m: username == m.name, guild.members)

    if member is None:
        await context.channel.send("Discord user {} not found.".format(username))
        return

    flow_address = await get_flow_address(topshot_username)

    if flow_address is not None:
        message = insert_user(member.id, topshot_username, flow_address)
        await context.channel.send(message)
        message = await load_and_upsert_collection(member.id, flow_address)
        await context.channel.send(message)
    else:
        await context.channel.send("Topshot user {} not found.".format(topshot_username))


@bot.command(name='find', help='Find the snowflake id of a user')
async def find_user_id(context, username):
    guild = discord.utils.find(lambda g: g.name == GUILD, bot.guilds)
    member = discord.utils.find(lambda m: username == "{}#{}".format(m.name, m.discriminator), guild.members)

    if member is None:
        await context.channel.send("User {} not found.".format(username))
    else:
        await context.channel.send(member.id)


############
# Commands
############
@bot.command(name='players', help="Get all players for the next game date")
async def get_players(context):
    if not isinstance(context.channel, discord.channel.DMChannel):
        return

    messages = LINEUP_PROVIDER.formatted_all_players

    for message in messages:
        await context.channel.send(message)



############
# Routines
############
@tasks.loop(minutes=5)
async def update_leaderboard():
    init_status = RANK_PROVIDER.status
    RANK_PROVIDER.update()
    new_status = RANK_PROVIDER.status

    global LB_MESSAGE_IDS
    if init_status == "POST_GAME" and new_status == "PRE_GAME":
        dates = get_the_past_week(RANK_PROVIDER.current_game_date)
        messages = RANK_PROVIDER.formatted_weekly_leaderboard(dates, 20)
        await send_channel_messages(messages, LB_CHANNELS)

        LB_MESSAGE_IDS.clear()
    else:
        messages = RANK_PROVIDER.formatted_leaderboard(20)
        messages.append("ET: **{}** , UPDATE EVERY 5 MINS".format(datetime.now(TZ_ET).strftime("%H:%M:%S")))

        await update_channel_messages(messages, LB_CHANNELS, LB_MESSAGE_IDS)


@tasks.loop(minutes=2)
async def update_games():
    messages = [NBA_PROVIDER.get_scoreboard_message("VIDEO GAME NATION DAILY FANTASY"),
                "ET: **{}** , UPDATE EVERY 2 MINS".format(datetime.now(TZ_ET).strftime("%H:%M:%S"))]

    await update_channel_messages(messages, GAMES_CHANNELS, GAMES_MESSAGE_IDS)


@tasks.loop(minutes=2)
async def refresh_entry():
    for message in FANTASY_CHANNEL_MESSAGES:
        emoji = message.guild.get_emoji(VGN_EMOJI_ID)
        view = MainPage(LINEUP_PROVIDER, RANK_PROVIDER)
        if emoji is None:
            await message.edit(content="Ready to start daily NBA fantasy game?", view=view)
        else:
            await message.edit(content=f"Ready to start daily NBA fantasy game? {emoji}", view=view)


# start the bot
bot.run(TOKEN)
