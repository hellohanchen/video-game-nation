import discord

from repository.vgn_users import get_user_new
from service.giveaways.views import GiveawayView
from service.profile.views import TO_LINK_MESSAGE, ProfileView


class MainAccountButton(discord.ui.Button['Account']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="TS Account", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: MainPage = self.view
        message, new_view = view.load_user_profile(interaction.user.id)

        await interaction.response.send_message(content=message, view=new_view, ephemeral=True, delete_after=600.0)


class MainGiveawayButton(discord.ui.Button['Giveaway']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="Giveaways", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: MainPage = self.view
        message, new_view = view.load_giveaway_accesses(interaction.user.id)

        await interaction.response.send_message(content=message, view=new_view, ephemeral=True, delete_after=600.0)


class MainPage(discord.ui.View):
    def __init__(self, guilds):
        super().__init__()
        self.add_item(MainAccountButton())
        self.add_item(MainGiveawayButton())
        self.guilds = guilds

    @staticmethod
    def load_user_profile(user_id):
        user, _ = get_user_new(user_id)
        if user is None:
            return TO_LINK_MESSAGE, ProfileView(user_id)

        return f"TS username: **{user['topshot_username']}**\n" \
               f"Address: **{user['flow_address']}**", ProfileView(user_id, user['flow_address'])

    def load_giveaway_accesses(self, user_id):
        message, view = GiveawayView.new_giveaway_view(user_id, self.guilds)
        if view is None:
            return message, self
        else:
            return message, view

