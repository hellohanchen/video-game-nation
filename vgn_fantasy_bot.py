#!/usr/bin/env python3

import os
from datetime import datetime

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from service.fantasy import LINEUP_PROVIDER
from provider.nba_provider import NBA_PROVIDER
from repository.vgn_collections import upsert_collection as repo_upsert_collection
from repository.vgn_players import search_players_stats as repo_search_player
from repository.vgn_users import get_user, insert_user
from constants import TEAM_TRICODES, TZ_ET
from topshot.cadence.flow_collections import get_account_plays
from service.fantasy.ranking import RANK_PROVIDER
from topshot.graphql.get_address import get_flow_address
from utils import update_channel_messages

# config bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
# intents.message_content = True
intents.members = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='.', intents=intents)
LB_CHANNEL_NAMES = ["📊-leaderboard"]
GAMES_CHANNEL_NAMES = ["📅-games"]
PLAYERS_CHANNEL_NAMES = ["⛹-players"]
ADMIN_CHANNELS = ["💻-admin"]

LB_CHANNELS = []
GAMES_CHANNELS = []
PLAYERS_CHANNELS = []
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
            if channel.name in PLAYERS_CHANNEL_NAMES:
                PLAYERS_CHANNELS.append(channel)
            if channel.name in ADMIN_CHANNELS:
                ADMIN_CHANNEL_IDS.append(channel.id)

    update_scorebox.start()
    update_games.start()


############
# Collection (DM only)
############
@bot.command(name='collection', help="Update user's topshot collections info.")
async def upsert_collection(context):
    if not isinstance(context.channel, discord.channel.DMChannel):
        return

    vgn_user = get_user(context.message.author)

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
@bot.command(name='lineup', help="Check the current line up for user.")
async def check_lineup(context):
    if not isinstance(context.channel, discord.channel.DMChannel):
        return

    await context.message.channel.send(LINEUP_PROVIDER.check_lineup(context.author.id).formatted())


@bot.command(name='submit', help="Submit the current lineup.")
async def submit_lineup(context):
    if not isinstance(context.channel, discord.channel.DMChannel):
        return

    await context.message.channel.send(LINEUP_PROVIDER.check_lineup(context.author.id).submit())


@bot.command(name='add', help="Add a player to a lineup position.")
async def add_player(context, o_idx, pos):
    if not isinstance(context.channel, discord.channel.DMChannel):
        return

    if not o_idx.isdigit():
        await context.message.channel.send(
            "Provided player id {} is not positive integer.\n"
            "Please use **/player** or **/team <team_name>** to check player ids.".format(o_idx))
        return
    if pos.lower() not in ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']:
        await context.message.channel.send("Lineup position can only be one of [a|b|c|d|e|f|g|h].")
        return

    lineup = LINEUP_PROVIDER.check_lineup(context.author.id)
    if lineup is None:
        await context.message.channel.send("Fail to load lineup.")
        return

    messages = [lineup.add_player(int(o_idx), ord(pos.lower()) - 97), lineup.formatted()]

    for message in messages:
        await context.message.channel.send(message)


@bot.command(name='remove', help="Remove a player from lineup.")
async def remove_player(context, pos):
    if not isinstance(context.channel, discord.channel.DMChannel):
        return

    if pos.lower() not in ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']:
        await context.message.channel.send("Lineup position can only be one of [a|b|c|d|e|f|g|h].")
        return

    lineup = LINEUP_PROVIDER.check_lineup(context.author.id)
    if lineup is None:
        await context.message.channel.send("Fail to load lineup.")
        return

    messages = [lineup.remove_player(ord(pos.lower()) - 97), lineup.formatted()]

    for message in messages:
        await context.message.channel.send(message)


@bot.command(name='swap', help="Swap players in the lineup.")
async def swap_players(context, pos1, pos2):
    if not isinstance(context.channel, discord.channel.DMChannel):
        return

    if pos1.lower() not in ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']:
        await context.message.channel.send("Lineup position can only be one of [a|b|c|d|e|f|g|h].")
        return
    if pos2.lower() not in ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']:
        await context.message.channel.send("Lineup position can only be one of [a|b|c|d|e|f|g|h].")
        return
    if pos1 == pos2:
        await context.message.channel.send("Two positions are the same.")
        return

    lineup = LINEUP_PROVIDER.check_lineup(context.author.id)
    if lineup is None:
        await context.message.channel.send("Fail to load lineup.")
        return

    messages = [
        lineup.swap_players(ord(pos1.lower()) - 97, ord(pos2.lower()) - 97),  # ord('a') = 97
        lineup.formatted()
    ]

    for message in messages:
        await context.message.channel.send(message)


############
# Player (DM only)
############
@bot.command(name='search', help="Search for a player by giving name.")
async def search_player(context, name):
    if not isinstance(context.channel, discord.channel.DMChannel):
        return

    players = repo_search_player(name, [('points_avg', 'DESC')])

    if players is None or len(players) == 0:
        await context.message.channel.send("Player {} not found.".format(name))
    else:
        user_id = context.author.id

        messages = LINEUP_PROVIDER.detailed_players(players, user_id)

        for message in messages:
            await context.message.channel.send(message)


@bot.command(name='player', help="List all players for the coming game date.")
async def all_players(context):
    if not isinstance(context.channel, discord.channel.DMChannel):
        return

    messages = LINEUP_PROVIDER.formatted_all_players()

    for message in messages:
        await context.message.channel.send(message)


@bot.command(name='team', help="List all players for the coming game date for a specific team.")
async def team_players(context, team):
    if not isinstance(context.channel, discord.channel.DMChannel):
        return

    messages = LINEUP_PROVIDER.formatted_team_players(TEAM_TRICODES[team.upper()])

    for message in messages:
        await context.message.channel.send(message)


############
# Score (DM only)
############
@bot.command(name='score', help="Get current score breakdown for a user")
async def get_score(context):
    if not isinstance(context.channel, discord.channel.DMChannel):
        return

    messages = RANK_PROVIDER.formatted_user_score(context.author.id)

    for message in messages:
        await context.message.channel.send(message)


############
# System
############
@bot.command(name='reload', help="[Admin] Reload game schedules, lineups and ranking")
async def reload(context):
    if context.channel.id not in ADMIN_CHANNEL_IDS:
        return

    NBA_PROVIDER.fresh_schedule()
    LINEUP_PROVIDER.reload()
    RANK_PROVIDER.reload()
    LB_MESSAGE_IDS.clear()


@bot.command(name='verify', help='[Admin] Insert a verified user record into db')
async def verify_user(context, username, topshot_username):
    if context.channel.id not in ADMIN_CHANNEL_IDS:
        return

    guild = discord.utils.find(lambda g: g.name == GUILD, bot.guilds)
    member = discord.utils.find(lambda m: username == "{}#{}".format(m.name, m.discriminator), guild.members)

    if member is None:
        await context.channel.send("Discord user {} not found.".format(username))

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


@tasks.loop(minutes=5)
async def update_scorebox():
    old_status = RANK_PROVIDER.status
    RANK_PROVIDER.update()
    new_status = RANK_PROVIDER.status

    if new_status != old_status and new_status == "PRE_GAME":
        messages = ["***Players for next game day {}:***".format(LINEUP_PROVIDER.coming_game_date)]
        messages.extend(LINEUP_PROVIDER.formatted_all_players())
        await update_channel_messages(messages, PLAYERS_CHANNELS, PLAYERS_MESSAGE_IDS)

    messages = RANK_PROVIDER.formatted_leaderboard(20)

    messages.append("ET: **{}** , UPDATE EVERY 5 MINS".format(datetime.now(TZ_ET).strftime("%H:%M:%S")))

    await update_channel_messages(messages, LB_CHANNELS, LB_MESSAGE_IDS)


@tasks.loop(minutes=2)
async def update_games():
    messages = [NBA_PROVIDER.get_scoreboard_message("VIDEO GAME NATION DAILY FANTASY"),
                "ET: **{}** , UPDATE EVERY 2 MINS".format(datetime.now(TZ_ET).strftime("%H:%M:%S"))]

    await update_channel_messages(messages, GAMES_CHANNELS, GAMES_MESSAGE_IDS)


# start the bot
bot.run(TOKEN)
