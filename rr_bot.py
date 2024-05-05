#!/usr/bin/env python3

import os
import time

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from constants import GameDateStatus
from service.redemptionrun.lineup import RR_LINEUP_SERVICE
from service.redemptionrun.ranking import RR_RANKING_SERVICE
from service.redemptionrun.views import MainPage
from vgnlog.channel_logger import ADMIN_LOGGER

# config bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN_REDEMPTION_RUN')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='.rr.', intents=intents)
ADMIN_CHANNEL_ID = 1097055938441130004

RR_CHANNEL_IDS = [1178938072562417714]
RR_CHANNEL_MESSAGES = []

REFRESH_COUNT = 0

WELCOME_MESSAGE = "**Welcome to the Redemption Run game!**\n"
STARTED = False


@bot.event
async def on_ready():
    global STARTED
    if STARTED:
        return

    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.type != discord.ChannelType.text:
                continue

            if channel.id == ADMIN_CHANNEL_ID:
                ADMIN_LOGGER.init("RR", channel)
                continue

            if channel.id in RR_CHANNEL_IDS:
                view = MainPage(RR_LINEUP_SERVICE, RR_RANKING_SERVICE)
                message = await channel.send(WELCOME_MESSAGE, view=view)
                RR_CHANNEL_MESSAGES.append(message)

    update_stats.start()
    refresh_entry.start()

    STARTED = True


@tasks.loop(minutes=2)
async def refresh_entry():
    global REFRESH_COUNT, RR_CHANNEL_MESSAGES
    REFRESH_COUNT += 1

    if REFRESH_COUNT == 60:
        new_messages = []
        for old_message in RR_CHANNEL_MESSAGES:
            view = MainPage(RR_LINEUP_SERVICE, RR_RANKING_SERVICE)
            try:
                new_message = await old_message.channel.send(WELCOME_MESSAGE, view=view)
            except Exception as err:
                await ADMIN_LOGGER.error(f"R:S:{err}")
                new_messages.append(old_message)
                continue

            new_messages.append(new_message)
            try:
                await old_message.delete()
            except Exception as err:
                await ADMIN_LOGGER.error(f"R:D:{err}")

        RR_CHANNEL_MESSAGES = new_messages
        REFRESH_COUNT = 0
    else:
        for i in range(0, len(RR_CHANNEL_MESSAGES)):
            message = RR_CHANNEL_MESSAGES[i]
            view = MainPage(RR_LINEUP_SERVICE, RR_RANKING_SERVICE)
            try:
                await message.edit(content=WELCOME_MESSAGE, view=view)
                continue
            except Exception as err:
                await ADMIN_LOGGER.error(f"R:E:{err}")

            try:
                await message.delete()
            except Exception as err:
                await ADMIN_LOGGER.error(f"R:D:{err}")

            try:
                new_message = await message.channel.send(content=WELCOME_MESSAGE, view=view)
                RR_CHANNEL_MESSAGES[i] = new_message
            except Exception as err:
                await ADMIN_LOGGER.error(f"R:S:{err}")

            time.sleep(0.2)


@tasks.loop(minutes=2)
async def update_stats():
    init_status = RR_RANKING_SERVICE.status
    init_lb = RR_RANKING_SERVICE.formatted_leaderboard(20)
    await RR_RANKING_SERVICE.update()
    new_status = RR_RANKING_SERVICE.status

    if init_status == GameDateStatus.POST_GAME and new_status != init_status:
        dates = RR_RANKING_SERVICE.get_previous_game_dates(RR_LINEUP_SERVICE.current_game_date)

        for message in RR_CHANNEL_MESSAGES:
            winners, weekly_lb = RR_RANKING_SERVICE.formatted_slate_leaderboard(dates, 20)
            await message.channel.send(init_lb)
            await message.channel.send(weekly_lb)

    global REFRESH_COUNT
    REFRESH_COUNT = 59


# start the bot
bot.run(TOKEN)
