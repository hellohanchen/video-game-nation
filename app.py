import discord

from provider.topshot.cadence.flow_collections import get_account_plays
from repository.vgn_users import get_user_new
from service.common.profile.views import ProfileView, LINK_TS_ACCOUNT_MESSAGE
from service.exchange.views import EXCHANGE_MESSAGE, ExchangeMainView
from service.giveaway.views import GiveawayView
from service.role.verify import verify_roles
from vgnlog.channel_logger import ADMIN_LOGGER


class MainGiveawayButton(discord.ui.Button['Giveaway']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="Manage Giveaways (ADMIN ONLY)", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: MainPage = self.view
        message, new_view = view.manage_giveaway(interaction.user.id)

        await interaction.response.send_message(content=message, view=new_view, ephemeral=True, delete_after=600.0)


class MainAccountButton(discord.ui.Button['Account']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="Link NBA Top Shot Account", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        message, new_view = ProfileView.load_profile_view(interaction.user.id)

        await interaction.response.send_message(content=message, view=new_view, ephemeral=True, delete_after=600.0)


class MainExchangeButton(discord.ui.Button['Exchange']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.red, label="Enter NBA Top Shot Exchange", row=2)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: MainPage = self.view
        message, new_view = view.enter_exchange(interaction.user)

        await interaction.response.send_message(content=message, view=new_view, ephemeral=True, delete_after=600.0)


class MainVerifyButton(discord.ui.Button['Verify']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.gray, label="Verify NBA Top Shot Collection", row=4)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: MainPage = self.view
        message, new_view = await view.verify_member(interaction.user)

        if new_view is None:
            await interaction.response.send_message(content=message, ephemeral=True, delete_after=60.0)
        else:
            await interaction.response.send_message(content=message, view=new_view, ephemeral=True, delete_after=600.0)


class MainPage(discord.ui.View):
    def __init__(self, guilds, verify_on=True):
        super().__init__()
        self.add_item(MainAccountButton())
        self.add_item(MainGiveawayButton())
        if verify_on:
            self.add_item(MainVerifyButton())
        self.add_item(MainExchangeButton())
        self.guilds = guilds

    def manage_giveaway(self, user_id):
        message, view = GiveawayView.new_giveaway_view(user_id, self.guilds)
        if view is None:
            return message, self
        else:
            return message, view

    @staticmethod
    def enter_exchange(d_user):
        user, _ = get_user_new(d_user.id)
        if user is None:
            return LINK_TS_ACCOUNT_MESSAGE, ProfileView(d_user.id)

        return EXCHANGE_MESSAGE, ExchangeMainView(user, d_user.name)

    async def verify_member(self, member: discord.Member):
        guild_id = member.guild.id
        if guild_id not in self.guilds or 'roles' not in self.guilds[guild_id]:
            return f"This server has no roles managed.", None

        user, _ = get_user_new(member.id)
        if user is None:
            return LINK_TS_ACCOUNT_MESSAGE, ProfileView(member.id)

        try:
            plays = await get_account_plays(user['flow_address'])
        except Exception as err:
            await ADMIN_LOGGER.error(f"App:Verify:GetPlays:{err}")
            return f"Failed to verify collection, please retry or contact admin.", None

        verified = verify_roles(self.guilds[guild_id]['roles'], plays)
        if len(verified) == 0:
            return f"You are not qualified for any role", None
        for role in verified:
            try:
                await member.add_roles(role)
            except Exception as err:
                await ADMIN_LOGGER.error(f"App:Verify:AddRole{role.name}:{err}")
                return f"Failed to verify collection, please retry or contact admin.", None

        return f"You are successfully verified for roles: **{', '.join([r.name for r in verified])}**", None
