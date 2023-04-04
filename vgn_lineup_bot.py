# vgn_bot.py
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from awsmysql.users import add_user, get_user

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


@bot.command(name='update', help="Update user's topshot collections info")
async def verify_user(context):
    user = context.message.author
    vgn_user = await get_user(user.id)

    if vgn_user is None:
        await context.channel.send("Couldn't find your account.")

    await context.channel.send("Updated!")


bot.run(TOKEN)
