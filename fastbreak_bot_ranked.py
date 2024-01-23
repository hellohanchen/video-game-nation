#!/usr/bin/env python3

import os

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from provider.nba.nba_provider import NBA_PROVIDER
from provider.topshot.fb_provider import FB_PROVIDER
from service.fastbreak.lineup import LINEUP_SERVICE
from service.fastbreak.ranked.views import MainPage
from service.fastbreak.ranking import RANK_SERVICE
from utils import get_the_past_week_from_sunday, get_the_past_week_from_monday

# config bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN_FASTBREAK')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='.', intents=intents)
FB_CHANNEL_IDS = [1195804395309367469]
ADMIN_CHANNEL_NAMES = ["💻-admin"]

FB_CHANNEL_MESSAGES = []

ADMIN_CHANNEL_IDS = []

FB_EMOJI_ID = 1193465233054908416

WELCOME_MESSAGE = "**Welcome to the B2B fastbreak contest!**\n" \
                  "Link TS account and submit your fastbreak lineup here to join the community contest.\n" \
                  "To be eligible to win rewards, please make sure use your own account and " \
                  "submit the same lineup matching the one submitted to Topshot Fastbreak.\n\n" \
                  "**Don't forget to enter our NBA Pick em game with Krause House DAO!**\n" \
                  "FREE to Enter! Daily Prizes! Make sure to join B2B for community specific prizes.\n" \
                  "➡ https://www.krausepicks.com/auth/signup?community=2"


REFRESH_COUNT = 0


@bot.event
async def on_ready():
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.type != discord.ChannelType.text:
                continue

            if channel.name in ADMIN_CHANNEL_NAMES:
                ADMIN_CHANNEL_IDS.append(channel.id)
            if channel.id in FB_CHANNEL_IDS:
                view = MainPage(LINEUP_SERVICE, RANK_SERVICE)
                message = await channel.send(WELCOME_MESSAGE, view=view)
                FB_CHANNEL_MESSAGES.append(message)

    update_stats.start()
    refresh_entry.start()


############
# Admin
############
@bot.command(name='reload', help="[Admin] Reload game schedules, lineups and ranking")
async def reload(context):
    if context.channel.id not in ADMIN_CHANNEL_IDS:
        return

    NBA_PROVIDER.reload()
    LINEUP_SERVICE.reload()
    RANK_SERVICE.reload()

    await context.channel.send("reloaded")


############
# Routines
############
@tasks.loop(minutes=2)
async def update_stats():
    init_status = RANK_SERVICE.status
    daily_lb = RANK_SERVICE.formatted_leaderboard(20)
    RANK_SERVICE.update()
    new_status = RANK_SERVICE.status

    if init_status == "POST_GAME" and new_status == "PRE_GAME":
        dates = get_the_past_week_from_monday(RANK_SERVICE.current_game_date)
        dates = list(filter(lambda d: FB_PROVIDER.fb_info.get(d) is not None, dates))
        weekly_lb = RANK_SERVICE.formatted_weekly_leaderboard(dates, 20)

        for message in FB_CHANNEL_MESSAGES:
            await message.channel.send(daily_lb)
            await message.channel.send(weekly_lb)


@tasks.loop(minutes=2)
async def refresh_entry():
    global REFRESH_COUNT, FB_CHANNEL_MESSAGES
    if RANK_SERVICE.status != "IN_GAME":
        REFRESH_COUNT += 1

    if REFRESH_COUNT == 60:
        new_messages = []
        for old_message in FB_CHANNEL_MESSAGES:
            view = MainPage(LINEUP_SERVICE, RANK_SERVICE)
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
            view = MainPage(LINEUP_SERVICE, RANK_SERVICE)
            await message.edit(content=WELCOME_MESSAGE, view=view)


# start the bot
bot.run(TOKEN)
