# trade_bot.py
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from topshot.compare import compare_moments
from topshot.ts_info import TOPSHOT_SET_INFO

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN_TRADE')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='/', intents=intents)


def truncate_message(messages, msg, to_add, limit):
    if len(msg) + len(to_add) >= limit:
        messages.append(msg)
        return to_add, ""
    else:
        return msg + to_add, ""


def get_sorted_play_ids(set):
    play_ids = list(set.keys())

    play_ids.sort(reverse=True, key=lambda pid: set[pid]['LowAsk'])

    play_ids.sort(reverse=True, key=lambda pid: set[pid]['Count'])

    return play_ids


def get_formatted_message(user1, user2, collection1, collection2, series):
    messages = []
    message = ""
    new_message = ""

    for set_id_str in collection1:
        if len(collection1[set_id_str]) == 0 and (set_id_str not in collection2 or len(collection2[set_id_str]) == 0):
            continue

        set_id = int(set_id_str)

        if TOPSHOT_SET_INFO[set_id]['flowSeriesNumber'] != series:
            continue

        new_message += "***{} (Series {}):***\n".format(
            TOPSHOT_SET_INFO[set_id]['flowName'],
            TOPSHOT_SET_INFO[set_id]['flowSeriesNumber']
        )

        message, new_message = truncate_message(messages, message, new_message, 1950)

        if len(collection1[set_id_str]) > 0:
            new_message += "**{}** has **{}** needs:\n".format(user1, user2)

            plays = collection1[set_id_str]
            play_ids = get_sorted_play_ids(plays)

            for play_id in play_ids:
                new_message += "**□** {} ${} x{}  ".format(
                    plays[play_id]['FullName'],
                    plays[play_id]['LowAsk'],
                    plays[play_id]['Count'],
                )

                message, new_message = truncate_message(messages, message, new_message, 1950)

            new_message += "\n"

        if set_id_str in collection2 and len(collection2[set_id_str]) > 0:
            new_message += "**{}** has **{}** needs:\n".format(user2, user1)

            plays = collection2[set_id_str]
            play_ids = get_sorted_play_ids(plays)

            for play_id in play_ids:
                new_message += "**□** {} ${} x{}  ".format(
                    plays[play_id]['FullName'],
                    plays[play_id]['LowAsk'],
                    plays[play_id]['Count'],
                )

                message, new_message = truncate_message(messages, message, new_message, 1950)

            new_message += "\n"

        new_message += "\n"

    for set_id_str in collection2:
        if len(collection2[set_id_str]) == 0 or set_id_str in collection1:
            continue

        set_id = int(set_id_str)

        if TOPSHOT_SET_INFO[set_id]['flowSeriesNumber'] != series:
            continue

        new_message += "***{} (Series {}):***\n".format(
            TOPSHOT_SET_INFO[set_id]['flowName'],
            TOPSHOT_SET_INFO[set_id]['flowSeriesNumber']
        )

        new_message += "**{}** has **{}** needs:\n".format(user2, user1)

        message, new_message = truncate_message(messages, message, new_message, 1950)

        plays = collection2[set_id_str]
        play_ids = get_sorted_play_ids(plays)

        for play_id in play_ids:
            new_message += "**□** {} ${} x{}  ".format(
                plays[play_id]['FullName'],
                plays[play_id]['LowAsk'],
                plays[play_id]['Count'],
            )

            message, new_message = truncate_message(messages, message, new_message, 1950)

        new_message += "\n\n"

    messages.append(message)

    return messages


@bot.event
async def on_ready():
    for guild in bot.guilds:
        if guild.name == GUILD:
            break

    print(
        f'{bot.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )


@bot.command(name='c', help='Compare the collection of 2 topshot users for given series \n'
                            '/c <username1> <username2> <seriesNumber[1|2|3|4]>')
async def verify_user(context, user1, user2, series):
    try:
        c1, c2 = await compare_moments(user1, user2, int(series))

        messages = get_formatted_message(user1, user2, c1, c2, int(series))

        for message in messages:
            await context.channel.send(message)

        await context.channel.send("COMPLETE!!!")

    except NameError:
        await context.channel.send("User not found.")
    except Exception as err:
        await context.channel.send("Failed to fetch collection")


bot.run(TOKEN)
