#!/usr/bin/env python3

import os

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from provider.nba.nba_provider import NBA_PROVIDER
from service.fastbreak.lineup import LINEUP_SERVICE
from service.fastbreak.ranking import RANK_SERVICE
from service.fastbreak.views import MainPage

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
FB_CHANNEL_NAMES = ["⚡-fast-break"]
ADMIN_CHANNEL_NAMES = ["💻-admin"]

FB_CHANNEL_MESSAGES = []

ADMIN_CHANNEL_IDS = []

FB_EMOJI_ID = 1193465233054908416


@bot.event
async def on_ready():
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.type != discord.ChannelType.text:
                continue

            if channel.name in ADMIN_CHANNEL_NAMES:
                ADMIN_CHANNEL_IDS.append(channel.id)
            if channel.name in FB_CHANNEL_NAMES:
                emoji = guild.get_emoji(FB_EMOJI_ID)
                view = MainPage(LINEUP_SERVICE, RANK_SERVICE)
                if emoji is None:
                    message = await channel.send(f"Track your fastbreak here!", view=view)
                else:
                    message = await channel.send(f"Track your fastbreak here! {emoji}", view=view)
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
    RANK_SERVICE.update()


@tasks.loop(minutes=2)
async def refresh_entry():
    for message in FB_CHANNEL_MESSAGES:
        emoji = message.guild.get_emoji(FB_EMOJI_ID)
        view = MainPage(LINEUP_SERVICE, RANK_SERVICE)
        if emoji is None:
            await message.edit(content="Track your fastbreak here!", view=view)
        else:
            await message.edit(content=f"Track your fastbreak here! {emoji}", view=view)


# start the bot
bot.run(TOKEN)
