#!/usr/bin/env python3

import os
import typing

import discord
from discord import ActionRow, Button, ButtonStyle
from discord.ext import commands
from dotenv import load_dotenv

# config bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
# intents.message_content = True
# intents.members = True
# intents.typing = False
# intents.presences = False

bot = commands.Bot(command_prefix='.', intents=intents)
LB_CHANNEL_NAMES = ["📊-leaderboard"]
GAMES_CHANNEL_NAMES = ["📅-games"]
PLAYERS_CHANNEL_NAMES = ["⛹-players"]
ADMIN_CHANNELS = ["💻-admin"]

LB_CHANNELS = []
GAMES_CHANNELS = []
PLAYERS_CHANNELS = []
ADMIN_CHANNEL_IDS = []

LB_MESSAGE_IDS = {}
GAMES_MESSAGE_IDS = {}
PLAYERS_MESSAGE_IDS = {}


@bot.event
async def on_ready():
    pass


@bot.command(name='test')
async def buttons(ctx):
    await ctx.send('Hey here are some Buttons', components=[[
        Button(label="Hey i\'m a red Button",
               custom_id="this is an custom_id1",
               style=ButtonStyle.red),
        Button(label="Hey i\'m a green Button",
               custom_id="this is an custom_id2",
               style=ButtonStyle.green),
        Button(label="Hey i\'m a blue Button",
               custom_id="this is an custom_id3",
               style=ButtonStyle.blurple),
        Button(label="Hey i\'m a grey Button",
               custom_id="this is an custom_id4",
               style=ButtonStyle.grey),
        Button(label="Hey i\'m a URL Button",
               url="https://pypi.org/project/discord.py-message-components",
               style=ButtonStyle.url)
    ]])


@bot.command(name='buttons', description='sends you some nice Buttons')
async def buttons(ctx: commands.Context):
    components = [ActionRow(Button(label='Option Nr.1',
                                   custom_id='option1',
                                   emoji="🆒",
                                   style=ButtonStyle.green
                                   ),
                            Button(label='Option Nr.2',
                                   custom_id='option2',
                                   emoji="🆗",
                                   style=ButtonStyle.blurple)),
                  ActionRow(Button(label='A Other Row',
                                   custom_id='sec_row_1st option',
                                   style=ButtonStyle.red,
                                   emoji='😀'),
                            Button(url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                                   label="This is an Link",
                                   style=ButtonStyle.url,
                                   emoji='🎬'))
                  ]
    an_embed = discord.Embed(title='Here are some Button\'s', description='Choose an option',
                             color=discord.Color.random())
    msg = await ctx.send(embed=an_embed, components=components)

    def _check(i: discord.Interaction, b):
        return i.message == msg and i.member == ctx.author

    interaction, button = await bot.wait_for('button_click', check=_check)
    button_id = button.custom_id

    # This sends the Discord-API that the interaction has been received and is being "processed"
    await interaction.defer()
    # if this is not used and you also do not edit the message within 3 seconds as described below,
    # Discord will indicate that the interaction has failed.

    # If you use interaction.edit instead of interaction.message.edit, you do not have to defer the interaction,
    # if your response does not last longer than 3 seconds.
    await interaction.edit(embed=an_embed.add_field(name='Choose', value=f'Your Choose was `{button_id}`'),
                           components=[components[0].disable_all_buttons(), components[1].disable_all_buttons()])

    # The Discord API doesn't send an event when you press a link button so we can't "receive" that.


pointers = []


class Pointer:
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self._possition_x = 0
        self._possition_y = 0

    @property
    def possition_x(self):
        return self._possition_x

    def set_x(self, x: int):
        self._possition_x += x
        return self._possition_x

    @property
    def possition_y(self):
        return self._possition_y

    def set_y(self, y: int):
        self._possition_y += y
        return self._possition_y


def get_pointer(obj: typing.Union[discord.Guild, int]):
    if isinstance(obj, discord.Guild):
        for p in pointers:
            if p.guild.id == obj.id:
                return p
        pointers.append(Pointer(obj))
        return get_pointer(obj)

    elif isinstance(obj, int):
        for p in pointers:
            if p.guild.id == obj:
                return p
        guild = bot.get_guild(obj)
        if guild:
            pointers.append(Pointer(guild))
            return get_pointer(guild)
        return None


def display(x: int, y: int):
    base = [
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    ]
    base[y][x] = 1
    base.reverse()
    return ''.join(
        f"\n{''.join([str(base[i][w]) for w in range(len(base[i]))]).replace('0', '⬛').replace('1', '⬜')}" for i in
        range(len(base)))


empty_button1 = discord.Button(style=discord.ButtonStyle.Secondary, label=".", custom_id="empty1", disabled=True)
empty_button2 = discord.Button(style=discord.ButtonStyle.Secondary, label=".", custom_id="empty2", disabled=True)


def arrow_button():
    return discord.Button(style=discord.ButtonStyle.Primary)


@bot.command(name="start_game")
async def start_game(ctx: commands.Context):
    pointer: Pointer = get_pointer(ctx.guild)
    await ctx.send(embed=discord.Embed(title="Little Game",
                                       description=display(x=0, y=0)),
                   components=[
                       discord.ActionRow(empty_button1, arrow_button().set_label('↑').set_custom_id('up'),
                                         empty_button2),
                       discord.ActionRow(
                           arrow_button().update(disabled=True).set_label('←').set_custom_id('left').disable_if(
                               pointer.possition_x <= 0),
                           arrow_button().set_label('↓').set_custom_id('down').disable_if(pointer.possition_y <= 0),
                           arrow_button().set_label('→').set_custom_id('right'))
                   ]
                   )


@bot.on_click()
async def up(i: discord.Interaction, button):
    pointer: Pointer = get_pointer(i.guild)
    pointer.set_y(1)
    await i.edit(embed=discord.Embed(title="Little Game",
                                     description=display(x=pointer.possition_x, y=pointer.possition_y)),
                 components=[discord.ActionRow(empty_button1,
                                               arrow_button().set_label('↑').set_custom_id('up').disable_if(
                                                   pointer.possition_y >= 9), empty_button2),
                             discord.ActionRow(arrow_button().set_label('←').set_custom_id('left').disable_if(
                                 pointer.possition_x <= 0),
                                 arrow_button().set_label('↓').set_custom_id('down'),
                                 arrow_button().set_label('→').set_custom_id('right').disable_if(
                                     pointer.possition_x >= 9))]
                 )


@bot.on_click()
async def down(i: discord.Interaction, button):
    pointer: Pointer = get_pointer(i.guild)
    pointer.set_y(-1)
    await i.edit(embed=discord.Embed(title="Little Game",
                                     description=display(x=pointer.possition_x, y=pointer.possition_y)),
                 components=[
                     discord.ActionRow(empty_button1, arrow_button().set_label('↑').set_custom_id('up'),
                                       empty_button2),
                     discord.ActionRow(
                         arrow_button().set_label('←').set_custom_id('left').disable_if(pointer.possition_x <= 0),
                         arrow_button().set_label('↓').set_custom_id('down').disable_if(pointer.possition_y <= 0),
                         arrow_button().set_label('→').set_custom_id('right').disable_if(pointer.possition_x >= 9))]
                 )


@bot.on_click()
async def right(i: discord.Interaction, button):
    pointer: Pointer = get_pointer(i.guild)
    pointer.set_x(1)
    await i.edit(embed=discord.Embed(title="Little Game",
                                     description=display(x=pointer.possition_x, y=pointer.possition_y)),
                 components=[
                     discord.ActionRow(empty_button1, arrow_button().set_label('↑').set_custom_id('up'),
                                       empty_button2),
                     discord.ActionRow(arrow_button().set_label('←').set_custom_id('left'),
                                       arrow_button().set_label('↓').set_custom_id('down'),
                                       arrow_button().set_label('→').set_custom_id('right').disable_if(
                                           pointer.possition_x >= 9))]
                 )


@bot.on_click()
async def left(i: discord.Interaction, button):
    pointer: Pointer = get_pointer(i.guild)
    pointer.set_x(-1)
    await i.edit(embed=discord.Embed(title="Little Game",
                                     description=display(x=pointer.possition_x, y=pointer.possition_y)),
                 components=[
                     discord.ActionRow(empty_button1, arrow_button().set_label('↑').set_custom_id('up'),
                                       empty_button2),
                     discord.ActionRow(
                         arrow_button().set_label('←').set_custom_id('left').disable_if(pointer.possition_x <= 0),
                         arrow_button().set_label('↓').set_custom_id('down'),
                         arrow_button().set_label('→').set_custom_id('right'))]
                 )


# start the bot
bot.run(TOKEN)
