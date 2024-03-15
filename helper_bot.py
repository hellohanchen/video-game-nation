#!/usr/bin/env python3

import os
import time

import discord
from discord.ext import commands
from dotenv import load_dotenv

from repository.fb_lineups import get_submitted_users
from vgnlog.channel_logger import ADMIN_LOGGER

# config bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN_FASTBREAK')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='.helper.', intents=intents)
ADMIN_CHANNEL_ID = 1097055938441130004


@bot.event
async def on_ready():
    for guild in bot.guilds:

        for channel in guild.channels:
            if channel.type != discord.ChannelType.text:
                continue
            if channel.id == ADMIN_CHANNEL_ID:
                ADMIN_LOGGER.init("Helper", channel)
                continue

        if guild.id == 718491088142204998:
            await assign_fb_role(guild)

    await ADMIN_LOGGER.info(f"Done")


async def assign_fb_role(guild):
    role = guild.get_role(1095033370855080006)
    users, err = get_submitted_users()
    if err is not None:
        await ADMIN_LOGGER.error(f"Users:{err}")
        return

    for user in users:
        member = guild.get_member(user['user_id'])
        if member is not None:
            try:
                await member.add_roles(role)
                time.sleep(1)
            except Exception as err:
                await ADMIN_LOGGER.error(f"Add:{err}")
                continue
            print(member.name)


# start the bot
bot.run(TOKEN)
