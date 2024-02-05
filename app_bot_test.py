#!/usr/bin/env python3

import os

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from app import MainPage
from repository.discord_roles import get_role_validations
from repository.ts_giveaways import add_giveaway_access
from service.giveaways.giveaway import GIVEAWAY_SERVICE
from utils import has_giveaway_permissions
from vgnlog.channel_logger import ADMIN_LOGGER

# config bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN_VGN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='.vgn.', intents=intents)
ADMIN_CHANNEL_ID = 1097055938441130004

MAIN_CHANNELS = ["🎮-fantasy-test"]
MAIN_CHANNEL_MESSAGES = []

GUILDS = {}

WELCOME_MESSAGE = "**Video Game Nation Discord Portal**\n\n" \
                  "Explore the Discord communities of NBA Topshot.\n" \
                  "Link your discord account with your Topshot collection.\n" \
                  "Play games with fans from all communities.\n" \
                  "Win moments and other prizes from activities."


@bot.event
async def on_ready():
    for guild in bot.guilds:
        gid = guild.id
        if guild.id not in GUILDS:
            GUILDS[gid] = {
                "guild": guild,
                "channels": {}
            }

        bot_member = guild.me
        for channel in guild.channels:
            if channel.type != discord.ChannelType.text:
                continue
            permissions = channel.permissions_for(bot_member)
            if not has_giveaway_permissions(permissions):
                continue

            GUILDS[gid]['channels'][channel.id] = channel

            if channel.id == ADMIN_CHANNEL_ID:
                ADMIN_LOGGER.init("App", channel)
            if channel.name in MAIN_CHANNELS:
                view = MainPage(GUILDS)
                message = await channel.send(WELCOME_MESSAGE, view=view)
                MAIN_CHANNEL_MESSAGES.append(message)

    validation_rules = get_role_validations(list(GUILDS.keys()))
    for gid in GUILDS:
        if gid in validation_rules:
            GUILDS[gid]['roles'] = validation_rules[gid]

    await GIVEAWAY_SERVICE.load_from_guilds(GUILDS)
    refresh_entry.start()
    refresh_giveaways.start()


@tasks.loop(seconds=120)
async def refresh_entry():
    for message in MAIN_CHANNEL_MESSAGES:
        view = MainPage(GUILDS)
        await message.edit(content=WELCOME_MESSAGE, view=view)


@tasks.loop(seconds=60)
async def refresh_giveaways():
    await GIVEAWAY_SERVICE.refresh()


# start the bot
bot.run(TOKEN)
