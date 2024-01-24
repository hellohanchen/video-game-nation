import discord

from service.common.profile.views import ProfileView
from service.giveaways.views import GiveawayView


class MainAccountButton(discord.ui.Button['Account']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="Link NBA Topshot Account", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        message, new_view = ProfileView.load_profile_view(interaction.user.id)

        await interaction.response.send_message(content=message, view=new_view, ephemeral=True, delete_after=600.0)


class MainGiveawayButton(discord.ui.Button['Giveaway']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="Manage Giveaways (ADMIN ONLY)", row=0)

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

    def load_giveaway_accesses(self, user_id):
        message, view = GiveawayView.new_giveaway_view(user_id, self.guilds)
        if view is None:
            return message, self
        else:
            return message, view
