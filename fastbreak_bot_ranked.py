#!/usr/bin/env python3

import os

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from constants import GameDateStatus
from provider.nba.nba_provider import NBA_PROVIDER
from service.fastbreak.dynamic_lineup import DYNAMIC_LINEUP_SERVICE
from service.fastbreak.ranked.views import RankedMainPage
from utils import get_the_past_week_with_offset, truncate_message
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

FB_CHANNEL_IDS = [1195804395309367469, 887898106832769104]
B2B_GUILD_ID = 718491088142204998
INJURY_THREAD_IDS = [1207292397927800852]
B2B_GUILD: None | discord.Guild = None
FB_CHANNEL_MESSAGES = []
INJURY_THREADS = []

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
        if guild == B2B_GUILD_ID:
            global B2B_GUILD
            B2B_GUILD = guild
        for channel in guild.channels:
            if channel.type != discord.ChannelType.text:
                continue

            if channel.id == ADMIN_CHANNEL_ID:
                ADMIN_LOGGER.init("FBRanked", channel)
                continue

            if channel.id in FB_CHANNEL_IDS:
                for t in channel.threads:
                    if t.id in INJURY_THREAD_IDS:
                        INJURY_THREADS.append(t)
                view = RankedMainPage(DYNAMIC_LINEUP_SERVICE)
                message = await channel.send(WELCOME_MESSAGE, view=view)
                FB_CHANNEL_MESSAGES.append(message)

    update_stats.start()
    refresh_entry.start()
    injury_update.start()


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
        b2b_contest_dates = ['02/22/2024', '02/23/2024', '02/24/2024', '02/25/2024', '02/26/2024', '02/27/2024', '02/28/2024', '02/29/2024']
        if init_date in b2b_contest_dates:
            dates = b2b_contest_dates
        else:
            dates = get_the_past_week_with_offset(init_date, 4)
        winners, weekly_lb = DYNAMIC_LINEUP_SERVICE.formatted_weekly_leaderboard(dates, 20)

        for message in FB_CHANNEL_MESSAGES:
            await message.channel.send(init_lb)
            await message.channel.send(weekly_lb)

        if init_date == '02/29/2024' or len(dates) == 7:
            if B2B_GUILD is not None:
                winner_role = B2B_GUILD.get_role(1194158354608697465)
                if winner_role is None:
                    await ADMIN_LOGGER.warn("FBR:WinnerRole:not found")
                    return

                for user in winners:
                    member = B2B_GUILD.get_member(user['user_id'])
                    if member is not None:
                        await member.add_roles(winner_role)
            else:
                await ADMIN_LOGGER.warn("FBR:B2BGuild:not found")


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


@tasks.loop(minutes=5)
async def injury_update():
    global INJURY_THREADS
    injury_changes = NBA_PROVIDER.update_injury()
    injury_updates = ""
    messages = []
    for player_name in injury_changes:
        change = injury_changes[player_name]
        new_message = f"**{player_name}** updated from " \
                      f"**[{NBA_PROVIDER.format_injury(change['from'])}]** to " \
                      f"**[{NBA_PROVIDER.format_injury(change['to'])}]**\n"
        injury_updates, _ = truncate_message(messages, injury_updates, new_message, 1950)

    if injury_updates != "":
        messages.append(injury_updates)

    if len(messages) > 0:
        for thread in INJURY_THREADS:
            for msg in messages:
                await thread.send(msg)


# start the bot
bot.run(TOKEN)
