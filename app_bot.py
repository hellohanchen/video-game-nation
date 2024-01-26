#!/usr/bin/env python3

import os

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from app import MainPage
from vgnlog.channel_logger import ADMIN_LOGGER
from service.giveaways.giveaway import GIVEAWAY_SERVICE

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

MAIN_CHANNELS = ["giveaway-admin"]
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
        for channel in guild.channels:
            if channel.type != discord.ChannelType.text:
                continue
            GUILDS[gid]['channels'][channel.id] = channel

            if channel.id == ADMIN_CHANNEL_ID:
                ADMIN_LOGGER.init("App", channel)
            if channel.name in MAIN_CHANNELS:
                view = MainPage(GUILDS)
                message = await channel.send(WELCOME_MESSAGE, view=view)
                MAIN_CHANNEL_MESSAGES.append(message)

    await GIVEAWAY_SERVICE.load_from_guilds(GUILDS)
    refresh_entry.start()
    refresh_giveaways.start()


@bot.command(name='menu', help='Get video game nation portal menu')
async def menu(context):
    if not isinstance(context.channel, discord.channel.DMChannel):
        return

    await context.channel.send(WELCOME_MESSAGE, view=MainPage(GUILDS))


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
