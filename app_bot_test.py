#!/usr/bin/env python3

import os

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from app import MainPage
from repository.discord_roles import get_role_verifications
from repository.ts_giveaways import get_giveaway
from service.exchange.listing import LISTING_SERVICE
from service.giveaway.giveaway import GIVEAWAY_SERVICE, Giveaway
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

bot = commands.Bot(command_prefix='.vgntest.', intents=intents)
ADMIN_CHANNEL_ID = 1097055938441130004

MAIN_CHANNELS = ["🎮-fantasy-test"]
TRADE_CHANNEL_IDS = [1207541055243816960]
MAIN_CHANNEL_MESSAGES = []

GUILDS = {}

WELCOME_MESSAGE = "**Video Game Nation Portal (TEST)**\n\n" \
                  "Welcome! Video Game Nation is a sub-community of NBA Top Shot that has been dedicated to " \
                  "connect Web3 communities with gamification and automation services.\n\n" \
                  "**Link NBA Top Shot Account** to connect your discord account with ts account.\n" \
                  "**Enter NBA Top Shot Exchange** to post listings for exchange/trade.\n" \
                  "**Verify NBA Top Shot Collection** to get roles and access to games, giveaways and other events." \



@bot.event
async def on_ready():
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
                ADMIN_LOGGER.init("AppTest", channel)
                continue
            if channel.name in MAIN_CHANNELS:
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
