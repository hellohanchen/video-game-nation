#!/usr/bin/env python3

import os

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from app import MainPage
from repository.ts_giveaways import add_giveaway_access
from utils import has_giveaway_permissions
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

    await GIVEAWAY_SERVICE.load_from_guilds(GUILDS)
    refresh_entry.start()
    refresh_giveaways.start()


@bot.command(name='menu', help='Get video game nation portal menu')
async def menu(context):
    if not isinstance(context.channel, discord.channel.DMChannel):
        return

    await context.channel.send(WELCOME_MESSAGE, view=MainPage(GUILDS))


@bot.command(name='admin', help='[Admin] Give user admin access to a channel')
async def give_admin_access(context, username, guild_id, channel_id):
    if context.channel.id != ADMIN_CHANNEL_ID:
        return

    if not guild_id.isnumeric():
        await context.channel.send(f"Guild id needs to be snowflake id (bigint): {guild_id}")
        return
    guild_id = int(guild_id)
    if guild_id not in GUILDS:
        await context.channel.send(f"Guild not found: {guild_id}")
        return

    if not channel_id.isnumeric():
        await context.channel.send(f"Channel id needs to be snowflake id (bigint): {channel_id}")
        return

    guild = GUILDS[guild_id]['guild']
    member = discord.utils.find(lambda m: username == m.name, guild.members)
    if member is None:
        await context.channel.send(f"Discord user {username} not found in server {guild.name}.")
        return

    successful, err = add_giveaway_access(int(member.id), guild_id, int(channel_id))
    if successful:
        await context.channel.send("Giveaway access added.")
    else:
        await context.channel.send(f"Add giveaway access failed: {err}")


@bot.command(name='resync', help='[Admin] Resync bot access to guilds')
async def resync_guilds(context):
    if context.channel.id != ADMIN_CHANNEL_ID:
        return

    global GUILDS
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
