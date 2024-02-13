#!/usr/bin/env python3

import os

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from constants import GameDateStatus
from provider.nba.nba_provider import NBA_PROVIDER
from service.fastbreak.dynamic_lineup import DYNAMIC_LINEUP_SERVICE
from service.fastbreak.ranked.views import RankedMainPage
from utils import get_the_past_week_with_offset
from vgnlog.channel_logger import ADMIN_LOGGER

# config bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN_FASTBREAK')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='.fb.', intents=intents)
ADMIN_CHANNEL_ID = 1097055938441130004

FB_CHANNEL_IDS = [1195804395309367469]
FB_CHANNEL_MESSAGES = []

WELCOME_MESSAGE = "**Welcome to the B2B fastbreak contest!**\n" \
                  "1️⃣ *Link TS account.*\n" \
                  "2️⃣ *Submit your fastbreak lineup.*\n" \
                  "- To be eligible to win prizes, please make sure to confirm your submission by providing a " \
                  "screenshot of your lineup in this channel that exactly matches your submission.\n" \
                  "3️⃣ *Watch NBA games LIVE with the community to help out with your late swaps, celebrate your W's*" \
                  ", and **WIN MORE GIVEAWAYS!**\n" \
                  "<:boards:1091858916335435837> <https://playback.tv/b2b>\n\n" \
                  "**Don't forget to enter NBA Pick em!**\n" \
                  "*FREE to Enter!*\n" \
                  "https://www.krausepicks.com/auth/signup?community=2"


REFRESH_COUNT = 0


@bot.event
async def on_ready():
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.type != discord.ChannelType.text:
                continue

            if channel.id == ADMIN_CHANNEL_ID:
                ADMIN_LOGGER.init("FBRanked", channel)
                continue

            if channel.id in FB_CHANNEL_IDS:
                view = RankedMainPage(DYNAMIC_LINEUP_SERVICE)
                message = await channel.send(WELCOME_MESSAGE, view=view)
                FB_CHANNEL_MESSAGES.append(message)

    update_stats.start()
    refresh_entry.start()


############
# Admin
############
@bot.command(name='reload', help="[Admin] Reload game schedules, lineups and ranking")
async def reload(context):
    if context.channel.id != ADMIN_CHANNEL_ID:
        return

    NBA_PROVIDER.reload()
    DYNAMIC_LINEUP_SERVICE.reload()

    await context.channel.send("reloaded")


############
# Routines
############
@tasks.loop(minutes=2)
async def update_stats():
    init_status = DYNAMIC_LINEUP_SERVICE.status
    init_date = DYNAMIC_LINEUP_SERVICE.current_game_date
    init_lb = DYNAMIC_LINEUP_SERVICE.formatted_leaderboard(20)
    await DYNAMIC_LINEUP_SERVICE.update()
    new_status = DYNAMIC_LINEUP_SERVICE.status

    if init_status == GameDateStatus.POST_GAME and new_status != init_status:
        dates = get_the_past_week_with_offset(init_date, 4)
        weekly_lb = DYNAMIC_LINEUP_SERVICE.formatted_weekly_leaderboard(dates, 20)

        for message in FB_CHANNEL_MESSAGES:
            await message.channel.send(init_lb)
            await message.channel.send(weekly_lb)


@tasks.loop(minutes=2)
async def refresh_entry():
    global REFRESH_COUNT, FB_CHANNEL_MESSAGES
    if DYNAMIC_LINEUP_SERVICE.status != GameDateStatus.IN_GAME:
        REFRESH_COUNT += 1

    if REFRESH_COUNT == 60:
        new_messages = []
        for old_message in FB_CHANNEL_MESSAGES:
            view = RankedMainPage(DYNAMIC_LINEUP_SERVICE)
            try:
                new_message = await old_message.channel.send(WELCOME_MESSAGE, view=view)
            except Exception as err:
                print(err)
                new_messages.append(old_message)
                continue

            new_messages.append(new_message)
            await old_message.delete()
        FB_CHANNEL_MESSAGES = new_messages
        REFRESH_COUNT = 0
    else:
        for message in FB_CHANNEL_MESSAGES:
            view = RankedMainPage(DYNAMIC_LINEUP_SERVICE)
            await message.edit(content=WELCOME_MESSAGE, view=view)


# start the bot
bot.run(TOKEN)
