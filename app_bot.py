#!/usr/bin/env python3

import os
import time

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from app import MainPage
from repository.discord_roles import get_role_verifications
from repository.ts_giveaways import add_giveaway_access
from service.exchange.listing import LISTING_SERVICE
from utils import has_giveaway_permissions
from vgnlog.channel_logger import ADMIN_LOGGER
from service.giveaway.giveaway import GIVEAWAY_SERVICE

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

MAIN_CHANNEL_IDS = [
    1203921985898291260,  # VGN
    1207734770726080532,  # TSE
    1211737640274100254,  # B2B
    1209698146775466014,  # C&C
]
MAIN_CHANNEL_MESSAGES = []

TRADE_CHANNEL_IDS = [
    1207541055243816960,  # VGN
    958390692734963763,   # TSE
    890691235323474012,   # B2B
    1060927689113993216,  # C&C
]

GUILDS = {}

WELCOME_MESSAGE = "**Video Game Nation Portal (ALPHA)**\n\n" \
                  "Welcome! Video Game Nation is a sub-community of NBA Top Shot that has been dedicated to " \
                  "connect Web3 communities with gamification and automation services.\n\n" \
                  "**Link NBA Top Shot Account** to connect your discord account with ts account.\n" \
                  "**Enter NBA Top Shot Exchange** to post listings for exchange/trade.\n" \
                  "**Verify NBA Top Shot Collection** to get roles and access to games, giveaways and other events." \

STARTED = False


@bot.event
async def on_ready():
    if not STARTED:
        for guild in bot.guilds:
            gid = guild.id
            if guild.id not in GUILDS:
                GUILDS[gid] = {
                    "guild": guild,
                    "channels": {}
                }

        verify_rules, _ = get_role_verifications(list(GUILDS.keys()))
        trade_channels = []
        for gid in GUILDS:
            guild = GUILDS[gid]['guild']
            bot_member = guild.me

            if gid in verify_rules:
                roles = await guild.fetch_roles()
                role_map = {r.id: r for r in roles}

                for rule in verify_rules[gid]:
                    if rule['role_id'] in role_map:
                        rule['role'] = role_map[rule['role_id']]
                    else:
                        rule['role'] = None

                guild_rules = list(filter(lambda r: r['role'] is not None, verify_rules[gid]))
                if len(guild_rules) > 0:
                    GUILDS[gid]['roles'] = guild_rules

            for channel in guild.channels:
                if channel.type != discord.ChannelType.text:
                    continue
                if channel.id == ADMIN_CHANNEL_ID:
                    ADMIN_LOGGER.init("App", channel)
                    continue
                if channel.id in MAIN_CHANNEL_IDS:
                    view = MainPage(GUILDS)
                    message = await channel.send(WELCOME_MESSAGE, view=view)
                    MAIN_CHANNEL_MESSAGES.append(message)
                if channel.id in TRADE_CHANNEL_IDS:
                    trade_channels.append(channel)

                permissions = channel.permissions_for(bot_member)
                if not has_giveaway_permissions(permissions):
                    continue

                GUILDS[gid]['channels'][channel.id] = channel

        await GIVEAWAY_SERVICE.load_from_guilds(GUILDS)
        LISTING_SERVICE.set_channels(trade_channels)
        refresh_entry.start()
        refresh_giveaways.start()

        global STARTED
        STARTED = True


@bot.command(name='menu', help='Get video game nation portal menu')
async def menu(context):
    if not isinstance(context.channel, discord.channel.DMChannel):
        return

    await context.channel.send(WELCOME_MESSAGE, view=MainPage(GUILDS, False))


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
    for i in range(0, len(MAIN_CHANNEL_MESSAGES)):
        message = MAIN_CHANNEL_MESSAGES[i]
        view = MainPage(GUILDS)
        try:
            await message.edit(content=WELCOME_MESSAGE, view=view)
            return
        except Exception as err:
            await ADMIN_LOGGER.error(f"App:Refresh:{err}")

        try:
            new_message = await message.channel.send(content=WELCOME_MESSAGE, view=view)
            MAIN_CHANNEL_MESSAGES[i] = new_message
        except Exception as err:
            await ADMIN_LOGGER.error(f"App:Resend:{err}")

        time.sleep(0.2)


@tasks.loop(seconds=60)
async def refresh_giveaways():
    await GIVEAWAY_SERVICE.refresh()


# start the bot
bot.run(TOKEN)
