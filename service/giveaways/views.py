import discord

from constants import NBA_TEAMS
from repository.ts_giveaways import get_user_giveaway_accesses, create_giveaway, submit_giveaway, message_giveaway, \
    get_drafts_for_user
from service.views import BaseView


class GiveawayBaseView(BaseView):
    def __init__(self, user_id, guilds, guild_ids, channel_ids):
        super(GiveawayBaseView, self).__init__(user_id)
        self.guilds = guilds
        self.guild_ids = guild_ids
        self.channel_ids = channel_ids

    def restart(self):
        guilds, guild_ids, channel_ids, _ = get_user_giveaway_accesses(self.user_id, self.guilds)
        return GiveawayView(self.user_id, guilds, guild_ids, channel_ids)


class GiveawayCreateButton(discord.ui.Button['Create']):
    def __init__(self):
        super(GiveawayCreateButton, self).__init__(style=discord.ButtonStyle.success, label='Create a new giveaway',
                                                   row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: GiveawayView = self.view
        message, new_view = view.create()
        await interaction.response.edit_message(content=message, view=new_view)


class GiveawayDraftButton(discord.ui.Button['Draft']):
    def __init__(self):
        super(GiveawayDraftButton, self).__init__(style=discord.ButtonStyle.blurple, label='Manage drafts', row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: GiveawayView = self.view
        message, new_view = view.load_drafts()
        await interaction.response.edit_message(content=message, view=new_view)


class GiveawayView(GiveawayBaseView):
    def __init__(self, user_id, guilds, guild_ids, channel_ids):
        super(GiveawayView, self).__init__(user_id, guilds, guild_ids, channel_ids)
        self.add_item(GiveawayCreateButton())
        self.add_item(GiveawayDraftButton())

    @staticmethod
    def new_giveaway_view(user_id, guilds):
        guilds, guild_ids, channel_ids, _ = get_user_giveaway_accesses(user_id, guilds)
        if guilds is None or len(guilds) == 0:
            return "You don't have access to manage giveaways", None

        return f"Manage giveaways here.", GiveawayView(user_id, guilds, guild_ids, channel_ids)

    def create(self):
        return "Select 1 discord server:", GiveawayCreateView(self)

    def load_drafts(self):
        drafts, err = get_drafts_for_user(self.user_id, self.guild_ids, self.channel_ids)
        if err is not None:
            return f"Failed to load drafts: {err}", self
        if len(drafts) == 0:
            return f"You don't have drafts in the past 24 hours.", self

        message = f"Select 1 draft:\n\n"
        for gid in drafts:
            message += f"**{gid}**.{drafts[gid]['name']}\n"
        return message, GiveawayDraftsView(self, drafts)


class GiveawayGuildSelectMenu(discord.ui.Select):
    def __init__(self, guilds, guild_ids):
        super(GiveawayGuildSelectMenu, self).__init__()
        self.append_option(discord.SelectOption(label="<-- BACK TO MENU", value="0"))
        for gid in guild_ids:
            self.append_option(discord.SelectOption(label=guilds[gid]['guild'].name, value=gid))

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: GiveawayCreateView = self.view
        selection = interaction.data.get('values')[0]
        if selection == "0":
            await interaction.response.edit_message(content="Manage giveaways here.", view=view.restart())
            return

        guild_id = int(selection)
        message, new_view = view.select_guild(guild_id)
        await interaction.response.edit_message(content=message, view=new_view)


class GiveawayChannelSelectMenu(discord.ui.Select):
    def __init__(self, channels):
        super(GiveawayChannelSelectMenu, self).__init__()
        self.append_option(discord.SelectOption(label="<-- BACK TO MENU", value="0"))
        for cid in channels:
            self.append_option(discord.SelectOption(label=channels[cid].name, value=cid))

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: GiveawayCreateView = self.view
        selection = interaction.data.get('values')[0]
        if selection == "0":
            await interaction.response.edit_message(content="Manage giveaways here.", view=view.restart())
            return

        channel_id = int(selection)
        await interaction.response.send_modal(view.select_channel(channel_id))


class GiveawayCreateView(GiveawayBaseView):
    def __init__(self, view: GiveawayView):
        super(GiveawayCreateView, self).__init__(view.user_id, view.guilds, view.guild_ids, view.channel_ids)
        self.menu = GiveawayGuildSelectMenu(view.guilds, view.guild_ids)
        self.add_item(self.menu)
        self.guild_id = None

    def select_guild(self, guild_id):
        self.guild_id = guild_id
        self.remove_item(self.menu)
        self.menu = GiveawayChannelSelectMenu(self.guilds[guild_id]['channels'])
        self.add_item(self.menu)
        return "Select 1 channel", self

    def select_channel(self, channel_id):
        return GiveawayCreateModal(self, self.guild_id, channel_id)


class GiveawayCreateModal(discord.ui.Modal, title='Create a giveaway'):
    giveaway_name = discord.ui.TextInput(label='Name (<= 64 chars)')
    description = discord.ui.TextInput(label='Description (Optional, <= 256 chars)', required=False)
    winners = discord.ui.TextInput(label='Winners (1 ~ 10)')
    duration = discord.ui.TextInput(label='Duration (in hours, <= 240)')

    def __init__(self, view: GiveawayCreateView, guild_id, channel_id):
        super(GiveawayCreateModal, self).__init__()
        self.view: GiveawayCreateView = view
        self.guild_id = guild_id
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        giveaway_name = str(self.giveaway_name).strip().replace('*', '')
        description = str(self.description).strip().replace('*', '')

        winners_input = str(self.winners)
        if not winners_input.isnumeric():
            message = f"Invalid winners: {winners_input}"
            await interaction.response.edit_message(content=message, view=self.view.restart())
            return
        winners = int(winners_input)
        if winners < 1 or winners > 10:
            message = f"Invalid winners: {winners_input}"
            await interaction.response.edit_message(content=message, view=self.view.restart())
            return

        duration_input = str(self.duration)
        if not duration_input.isnumeric():
            message = f"Invalid duration: {duration_input}"
            await interaction.response.edit_message(content=message, view=self.view.restart())
            return
        duration = int(duration_input)
        if duration < 1 or duration > 240:
            message = f"Invalid duration: {duration_input}"
            await interaction.response.edit_message(content=message, view=self.view.restart())
            return

        giveaway_id, err = create_giveaway(
            self.guild_id, self.channel_id, self.view.user_id, giveaway_name, description, winners, duration)
        if giveaway_id is None:
            message = f"Create giveaway failed: {err}"
            await interaction.response.edit_message(content=message, view=self.view.restart())
            return

        giveaway = {
            'id': giveaway_id,
            'name': giveaway_name,
            'description': description,
            'winners': winners,
            'duration': duration,
        }
        message = GiveawayDraftView.formatted_giveaway(giveaway)
        await interaction.response.edit_message(
            content=message,
            view=GiveawayDraftView(self.view, giveaway, self.view.guilds[self.guild_id]['channels'][self.channel_id]))


class GiveawaySubmitModal(discord.ui.Modal, title='Complete details'):
    fav_teams = discord.ui.TextInput(label="Fav teams, optional, e.g. 'ATL,BOS'", required=False)
    team_set_weights = discord.ui.TextInput(label="Team set weights, optional", required=False)

    def __init__(self, view: GiveawayBaseView, giveaway, channel):
        super(GiveawaySubmitModal, self).__init__()
        self.view = view
        self.giveaway = giveaway
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        fav_teams_input = str(self.fav_teams).strip().upper()
        fav_teams = []
        if len(fav_teams_input) > 0:
            fav_teams = fav_teams_input.split(',')
        for team in fav_teams:
            if team not in NBA_TEAMS:
                message = f"Invalid team: {team}"
                await interaction.response.edit_message(content=message, view=self.view.restart())
                return

        team_set_weights_input = str(self.team_set_weights).strip()
        weights = []
        if len(team_set_weights_input) > 0:
            weights = team_set_weights_input.split(',')
        for weight in weights:
            if not weight.isnumeric():
                message = f"Invalid weight: {weight}"
                await interaction.response.edit_message(content=message, view=self.view.restart())
                return
            w = int(weight)
            if w < 1 or w > 4:
                message = f"Invalid weight: {weight}"
                await interaction.response.edit_message(content=message, view=self.view.restart())
                return

        success, err = submit_giveaway(self.giveaway['id'], self.giveaway['duration'], fav_teams_input,
                                       team_set_weights_input)

        if not success:
            message = f"Submit giveaway failed: {err}"
            await interaction.response.edit_message(content=message, view=self.view.restart())
            return

        embed = JoinGiveawayView.formatted_embed(
            self.giveaway['name'], self.giveaway['description'], self.giveaway['winners'])
        try:
            join_view = JoinGiveawayView(embed, 0)
            message = await self.channel.send(embed=embed, view=join_view)
            join_view.set_message(message)
            message_giveaway(self.giveaway['id'], message.id)
        except Exception as err:
            message = f"Failed sending message to {self.channel.name}: {err}"
            await interaction.response.edit_message(content=message, view=self.view.restart())
            return

        message = f"Successfully created giveaway in {self.channel.name}"
        await interaction.response.edit_message(content=message, view=self.view.restart())


class GiveawayDraftMenuButton(discord.ui.Button['DraftMenu']):
    def __init__(self):
        super(GiveawayDraftMenuButton, self).__init__(style=discord.ButtonStyle.success, label='Menu', row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: GiveawayDraftView = self.view
        await interaction.response.edit_message(content="Manage giveaways here.", view=view.view.restart())


class GiveawayDraftSubmitButton(discord.ui.Button['DraftSubmit']):
    def __init__(self):
        super(GiveawayDraftSubmitButton, self).__init__(style=discord.ButtonStyle.success, label='Submit', row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: GiveawayDraftView = self.view
        await interaction.response.send_modal(view.get_submit_giveaway_modal())


class GiveawayDraftView(BaseView):
    def __init__(self, view: GiveawayBaseView, giveaway, channel):
        super(GiveawayDraftView, self).__init__(view.user_id)
        self.add_item(GiveawayDraftMenuButton())
        self.add_item(GiveawayDraftSubmitButton())
        self.view = view
        self.giveaway = giveaway
        self.channel = channel

    def get_submit_giveaway_modal(self):
        return GiveawaySubmitModal(self.view, self.giveaway, self.channel)

    @staticmethod
    def formatted_message(gid, name, description, winners, duration):
        return f"***GIVEAWAY DRAFT***\n\n" \
               f"ID: **{gid}**\n" \
               f"Name: **{name}**\n" \
               f"Description: **{description} **\n" \
               f"Winners: **{winners}**\n" \
               f"Duration: **{duration}** hours\n\n" \
               f"*Please fill in more details to start it:*\n" \
               f"**Fav Teams**: a comma separated list of team abbreviations, optional, example: ATL,BOS\n" \
               f"**Team Set Weights**: a common separated list of weights of each team set, optional, " \
               f"starting from All to S4, each weight not exceeding 4, for example: " \
               f"**4,2,1,1,1,1** representing 4 for All, 2 for Contemporary, 1 for Series 1~4 sets."

    @staticmethod
    def formatted_giveaway(giveaway):
        return GiveawayDraftView.formatted_message(
            giveaway['id'], giveaway['name'], giveaway['description'], giveaway['winners'], giveaway['duration'])


class GiveawayDraftSelectMenu(discord.ui.Select):
    def __init__(self, drafts):
        super(GiveawayDraftSelectMenu, self).__init__()
        self.append_option(discord.SelectOption(label="<-- BACK TO MENU", value="0"))
        for gid in drafts:
            self.append_option(discord.SelectOption(label=f"{gid}.{drafts[gid]['name']}", value=gid))
        self.drafts = drafts

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: GiveawayDraftsView = self.view
        selection = interaction.data.get('values')[0]
        if selection == "0":
            await interaction.response.edit_message(content="Manage giveaways here.", view=view.restart())
            return

        giveaway = self.drafts[selection]
        message = GiveawayDraftView.formatted_giveaway(giveaway)
        await interaction.response.edit_message(
            content=message,
            view=GiveawayDraftView(
                view, giveaway, view.guilds[giveaway['guild_id']]['channels'][giveaway['channel_id']]
            )
        )


class GiveawayDraftsView(GiveawayBaseView):
    def __init__(self, view: GiveawayView, drafts):
        super(GiveawayDraftsView, self).__init__(view.user_id, view.guilds, view.guild_ids, view.channel_ids)
        self.add_item(GiveawayDraftSelectMenu(drafts))


class JoinGiveawayButton(discord.ui.Button['Join']):
    def __init__(self, count):
        super(JoinGiveawayButton, self).__init__(style=discord.ButtonStyle.success, label=f"Join", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: JoinGiveawayView = self.view
        view.join(interaction.user.id)
        self.label = f"Joined: {view.count}"
        await interaction.response.send_message(content="Joined!", ephemeral=True, delete_after=30.0)
        await view.refresh()


class JoinGiveawayView(discord.ui.View):
    def __init__(self, embed, count):
        super(JoinGiveawayView, self).__init__()
        self.add_item(JoinGiveawayButton(count))
        self.embed = embed
        self.count = count
        self.message = None

    def set_message(self, message):
        self.message = message

    def join(self, user_id):
        self.count += 1

    async def refresh(self):
        await self.message.edit(embed=self.embed, view=self)

    @staticmethod
    def formatted_embed(giveaway_name, description, winners):
        return discord.Embed(title=giveaway_name, description=f"{description}\n\nWinners:{winners}\n\nEnds at: ...")
