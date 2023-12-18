#!/usr/bin/env python3

# trade_bot.py
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from provider.topshot import compare_moments
from provider.topshot import TS_SET_INFO
from utils import truncate_message

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN_TRADE')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='/', intents=intents)


def get_sorted_play_ids(plays):
    play_ids = list(plays.keys())

    play_ids.sort(key=lambda pid: plays[pid]['FullName'])

    return play_ids


def get_formatted_message(user1, user2, collection1, collection2, series_or_set):
    messages = []
    msg = ""
    new_msg = ""

    for set_id in collection1:
        if len(collection1[set_id]) == 0 and (set_id not in collection2 or len(collection2[set_id]) == 0):
            continue

        if series_or_set > 0:
            if set_id != series_or_set:
                continue
        elif series_or_set < 0:
            if TS_SET_INFO[set_id]['flowSeriesNumber'] != -series_or_set:
                continue

        new_msg += "🏀 ***{} (Series {}):***\n".format(
            TS_SET_INFO[set_id]['flowName'],
            TS_SET_INFO[set_id]['flowSeriesNumber']
        )

        msg, new_msg = truncate_message(messages, msg, new_msg, 1950)

        if len(collection1[set_id]) > 0:
            new_msg += "**{}** has **{}** needs:\n".format(user1, user2)

            plays = collection1[set_id]
            play_ids = get_sorted_play_ids(plays)

            for play_id in play_ids:
                if int(plays[play_id]['Count']) > 1:
                    new_msg += ":black_small_square: **{} ${} x{}** ".format(
                        plays[play_id]['FullName'],
                        plays[play_id]['LowAsk'],
                        plays[play_id]['Count']
                    )
                else:
                    new_msg += ":black_small_square: {} ${} x{} ".format(
                        plays[play_id]['FullName'],
                        plays[play_id]['LowAsk'],
                        plays[play_id]['Count']
                    )

                msg, new_msg = truncate_message(messages, msg, new_msg, 1950)

            new_msg += "\n"

        if set_id in collection2 and len(collection2[set_id]) > 0:
            new_msg += "**{}** has **{}** needs:\n".format(user2, user1)

            plays = collection2[set_id]
            play_ids = get_sorted_play_ids(plays)

            for play_id in play_ids:
                if int(plays[play_id]['Count']) > 1:
                    new_msg += ":black_small_square: **{} ${} x{}** ".format(
                        plays[play_id]['FullName'],
                        plays[play_id]['LowAsk'],
                        plays[play_id]['Count']
                    )
                else:
                    new_msg += ":black_small_square: {} ${} x{} ".format(
                        plays[play_id]['FullName'],
                        plays[play_id]['LowAsk'],
                        plays[play_id]['Count']
                    )

                msg, new_msg = truncate_message(messages, msg, new_msg, 1950)

            new_msg += "\n"

        new_msg += "\n"

    for set_id in collection2:
        if len(collection2[set_id]) == 0 or set_id in collection1:
            continue

        set_id = int(set_id)

        if TS_SET_INFO[set_id]['flowSeriesNumber'] != series_or_set:
            continue

        new_msg += "🏀 ***{} (Series {}):***\n".format(
            TS_SET_INFO[set_id]['flowName'],
            TS_SET_INFO[set_id]['flowSeriesNumber']
        )

        new_msg += "**{}** has **{}** needs:\n".format(user2, user1)

        msg, new_msg = truncate_message(messages, msg, new_msg, 1950)

        plays = collection2[set_id]
        play_ids = get_sorted_play_ids(plays)

        for play_id in play_ids:
            new_msg += ":black_small_square: {} ${} x{} ".format(
                plays[play_id]['FullName'],
                plays[play_id]['LowAsk'],
                plays[play_id]['Count'],
            )

            msg, new_msg = truncate_message(messages, msg, new_msg, 1950)

        new_msg += "\n\n"

    messages.append(msg)

    return messages


@bot.event
async def on_ready():
    for guild in bot.guilds:
        print(
            f'{bot.user} is connected to the following guild:\n'
            f'{guild.name}(id: {guild.id})'
        )


@bot.command(name='c', help='Compare the collection of 2 topshot users for given series/set \n'
                            '/c <username1> <username2> <S1/2/3/4 or set id (1~105)>')
@commands.cooldown(1, 30, commands.BucketType.user)
async def verify_user(context, user1, user2, series_or_set):
    if not isinstance(context.channel, discord.channel.DMChannel):
        return

    try:
        await context.channel.send("LOADING... Takes about 60s...")

        if series_or_set[0] in ['s', 'S']:
            series_or_set = -int(series_or_set[1:])
        else:
            series_or_set = int(series_or_set)

        c1, c2 = await compare_moments(user1, user2, series_or_set)
        messages = get_formatted_message(user1, user2, c1, c2, series_or_set)

        for message in messages:
            if len(message) > 0:
                await context.channel.send(message)

        await context.channel.send("COMPLETE!!! For questions/comments please contact MingDynastyVase#5527")

    except NameError as err:
        print(err)
        await context.channel.send("Not found. {}".format(err))
    except Exception as err:
        print(err)
        await context.channel.send("Failed to fetch collection")


@bot.command(name='sets', help='get all sets')
@commands.cooldown(1, 15, commands.BucketType.user)
async def verify_user(context):
    messages = []
    message = ""

    for set_id in TS_SET_INFO:
        new_message = f"**#{set_id}** {TS_SET_INFO[set_id]['flowName']} (S{TS_SET_INFO[set_id]['flowSeriesNumber']})\n"
        message, _ = truncate_message(messages, message, new_message, 1950)

    if len(message) > 0:
        messages.append(message)

    for message in messages:
        await context.channel.send(message)


@bot.event
async def on_command_error(context, error):
    if isinstance(error, commands.CommandOnCooldown):
        await context.channel.send("COOLING DOWN... retry after 30s")
    elif isinstance(error, commands.MissingRequiredArgument):
        await context.channel.send("Please provider username1, username2 and **a series number (1/2/3/4)**")
    else:
        raise error  # Here we raise other errors to ensure they aren't ignored


bot.run(TOKEN)
