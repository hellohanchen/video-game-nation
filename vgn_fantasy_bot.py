# vgn_bot.py
import os
from datetime import datetime

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from awsmysql.collections_repo import upsert_collection as repo_upsert_collection
from awsmysql.players_repo import search_players_stats as repo_search_player
from awsmysql.users_repo import get_user
from constants import TEAM_TRICODES, TZ_ET
from nba.provider import NBA_PROVIDER
from topshot.cadence.flow_collections import get_account_plays
from topshot.fantasy.lineup import LINEUP_PROVIDER
from topshot.fantasy.ranking import RANK_PROVIDER

# config bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='/', intents=intents)
CHANNEL_NAMEs = ["📊-scorebox"]
MESSAGE_CHANNELS = []
PREVIOUS_MESSAGE_IDS = {}


@bot.event
async def on_ready():
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.name in CHANNEL_NAMEs:
                MESSAGE_CHANNELS.append(channel)

    update.start()


############
# Collection
############
@bot.command(name='collection', help="Update user's topshot collections info.")
async def upsert_collection(context):
    user = context.message.author
    vgn_user = get_user(user.id)

    if vgn_user is None:
        await context.channel.send("Account not found, contact admin for registration.")
        return

    try:
        plays = await get_account_plays(vgn_user[2])
    except:
        await context.channel.send("Failed to fetch collection, try again or contact admin.")
        return

    try:
        message = await repo_upsert_collection(vgn_user[0], plays)
    except:
        await context.channel.send("Failed to update database, try again or contact admin.")
        return

    await context.channel.send(message)


############
# Lineup
############
@bot.command(name='lineup', help="Check the current line up for user.")
async def check_lineup(context):
    await context.message.channel.send(LINEUP_PROVIDER.check_lineup(context.author.id).get_formatted())


@bot.command(name='submit', help="Submit the current lineup.")
async def submit_lineup(context):
    await context.message.channel.send(LINEUP_PROVIDER.check_lineup(context.author.id).submit())


@bot.command(name='add', help="Add a player to a lineup position.")
async def add_player(context, index, position):
    if not index.isdigit():
        await context.message.channel.send(
            "Provided player id {} is not positive integer.\n"
            "Please use **/player** or **/team <team_name>** to check player ids.".format(index))
        return
    if not position.isdigit() or int(position) < 1 or int(position) > 8:
        await context.message.channel.send("Lineup position can only be one of [1|2|3|4|5|6|7|8].")
        return

    lineup = LINEUP_PROVIDER.check_lineup(context.author.id)
    if lineup is None:
        await context.message.channel.send("Fail to load lineup.".format(position))
        return

    messages = [lineup.add_player(int(index), int(position)), lineup.get_formatted()]

    for message in messages:
        await context.message.channel.send(message)


@bot.command(name='remove', help="Remove a player from lineup.")
async def remove_player(context, pos):
    if not pos.isdigit() or int(pos) < 1 or int(pos) > 8:
        await context.message.channel.send("Lineup position can only be one of [1|2|3|4|5|6|7|8].")
        return

    lineup = LINEUP_PROVIDER.check_lineup(context.author.id)
    if lineup is None:
        await context.message.channel.send("Fail to load lineup.".format(pos))
        return

    messages = [lineup.remove_player(int(pos)), lineup.get_formatted()]

    for message in messages:
        await context.message.channel.send(message)


@bot.command(name='swap', help="Swap players in the lineup.")
async def swap_players(context, pos1, pos2):
    if not pos1.isdigit() or int(pos1) < 1 or int(pos1) > 8:
        await context.message.channel.send("Lineup position can only be one of [1|2|3|4|5|6|7|8].")
        return
    if not pos2.isdigit() or int(pos2) < 1 or int(pos2) > 8:
        await context.message.channel.send("Lineup position can only be one of [1|2|3|4|5|6|7|8].")
        return
    if pos1 == pos2:
        await context.message.channel.send("Two positions are the same.".format(pos2))
        return

    lineup = LINEUP_PROVIDER.check_lineup(context.author.id)
    if lineup is None:
        await context.message.channel.send("Fail to load lineup.".format(pos2))
        return

    messages = [lineup.swap_players(int(pos1), int(pos2)), lineup.get_formatted()]

    for message in messages:
        await context.message.channel.send(message)


############
# Player
############
@bot.command(name='search', help="Search for a player by giving name.")
async def search_player(context, name):
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
    messages = LINEUP_PROVIDER.formatted_all_players()

    for message in messages:
        await context.message.channel.send(message)


@bot.command(name='team', help="List all players for the coming game date for a specific team.")
async def team_players(context, team):
    messages = LINEUP_PROVIDER.formatted_team_players(TEAM_TRICODES[team.upper()])

    for message in messages:
        await context.message.channel.send(message)


############
# Ranking
############
@bot.command(name='rank', help="Get current leaderboard")
async def get_ranks(context):
    messages = RANK_PROVIDER.formatted_leaderboard(20)

    for message in messages:
        await context.message.channel.send(message)


@bot.command(name='score', help="Get current score breakdown for a user")
async def get_score(context):
    messages = RANK_PROVIDER.formatted_user_score(context.author.id)

    for message in messages:
        await context.message.channel.send(message)


############
# System
############
@bot.command(name='reload', help="Reload game schedules, lineups and ranking")
async def reload(context):
    NBA_PROVIDER.fresh_schedule()
    LINEUP_PROVIDER.reload()
    RANK_PROVIDER.reload()
    PREVIOUS_MESSAGE_IDS.clear()


@tasks.loop(minutes=5)
async def update():
    RANK_PROVIDER.update()

    messages = RANK_PROVIDER.formatted_leaderboard(20)

    messages.append("ET: **{}** , UPDATE EVERY 5 MINS".format(datetime.now(TZ_ET).strftime("%H:%M:%S")))

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


bot.run(TOKEN)
