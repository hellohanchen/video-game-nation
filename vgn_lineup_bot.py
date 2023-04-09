# vgn_bot.py
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from awsmysql.collections_repo import upsert_collection
from awsmysql.users_repo import add_user, get_user
from topshot.cadence.flow_collections import get_account_plays

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='/', intents=intents)


@bot.event
async def on_ready():
    for guild in bot.guilds:
        if guild.name == GUILD:
            break

    print(
        f'{bot.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )


@bot.command(name='echo', help='Echo the input message')
async def on_message(context, content):
    print("{}: {}".format(context.author.id, content))
    await context.channel.send(content)


@bot.command(name='find', help='Find the snowflake id of a user')
async def find_user_id(context, username):
    guild = discord.utils.find(lambda g: g.name == GUILD, bot.guilds)
    member = discord.utils.find(lambda m: username == "{}#{}".format(m.name, m.discriminator), guild.members)

    if member is None:
        await context.channel.send("User {} not found.".format(username))
    else:
        await context.channel.send(member.id)


@bot.command(name='collection', help="Update user's topshot collections info")
async def update_user_collection(context):
    user = context.message.author
    vgn_user = await get_user(user.id)

    if vgn_user is None:
        await context.channel.send("Account not found, contact admin for registration.")

    try:
        plays = get_account_plays(vgn_user[2])
    except:
        await context.channel.send("Failed to fetch collection, try again or contact admin.")
        return

    try:
        await upsert_collection(vgn_user[0], plays)
    except:
        await context.channel.send("Failed to update database, try again or contact admin.")

    await context.channel.send("Updated!")


bot.run(TOKEN)
