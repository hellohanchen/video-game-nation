import discord

from vgnlog.channel_logger import ADMIN_LOGGER
from provider.topshot.graphql.get_account import get_profile_with_ts_username, get_profile_with_address
from repository.vgn_users import insert_and_get_user, get_user_new, update_user
from service.views import BaseView

LINK_TS_ACCOUNT_MESSAGE = "Please click 'Link' to link to a TS username & address.\n" \
                          "Once linked, you can sync your TS username,\n" \
                          "but you can only contact admin to change your Flow address."


class ProfileLinkModal(discord.ui.Modal, title='Link TS Account'):
    username = discord.ui.TextInput(
        label='TS Username')

    def __init__(self, user_id, view: discord.ui.View):
        super(ProfileLinkModal, self).__init__()
        self.user_id = user_id
        self.msg_view = view

    async def on_submit(self, interaction: discord.Interaction):
        topshot_username = str(self.username)
        topshot_username, flow_address, _, err = await get_profile_with_ts_username(topshot_username)
        if err is not None:
            await ADMIN_LOGGER.error(f"Profile:Link:GetFlow:{err}")

        if flow_address is not None:
            user, err = insert_and_get_user(self.user_id, topshot_username, flow_address)
            if err is not None:
                await ADMIN_LOGGER.error(f"Profile:Link:InsertUser:{err}")
            if user is None:
                message = LINK_TS_ACCOUNT_MESSAGE
            else:
                message = f"TS username: **{user['topshot_username']}**\n" \
                          f"Flow address: **{user['flow_address']}**\n\n**Linked**"
        else:
            message = f"**{self.username}** not found\nPlease click 'Link' to link to a TS account\n\n"

        await interaction.response.edit_message(content=message, view=self.msg_view)


class ProfileLinkButton(discord.ui.Button['Link']):
    def __init__(self, label):
        super().__init__(style=discord.ButtonStyle.success, label=label, row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        await interaction.response.send_modal(ProfileLinkModal(interaction.user.id, self.view))


class ProfileUpdateButton(discord.ui.Button['Update']):
    def __init__(self, label, flow_address: str):
        super().__init__(style=discord.ButtonStyle.success, label=label, row=0)
        self.flow_address = flow_address

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        topshot_username, _, err = await get_profile_with_address(self.flow_address)
        if err is not None:
            await ADMIN_LOGGER.error(f"Profile:Update:Get:{err}")
            await interaction.response.edit_message(
                content="Failed to sync account, retry or contact admin", view=self.view)
            return

        if topshot_username is None:
            await ADMIN_LOGGER.warn(f"Profile:Update:Get:No username:{self.flow_address}")
            await interaction.response.edit_message(
                content="Failed to sync account, retry or contact admin", view=self.view)
            return

        err = update_user(topshot_username, self.flow_address)
        if err is not None:
            await ADMIN_LOGGER.error(f"Profile:Update:{err}")
            await interaction.response.edit_message(
                content="Failed to sync account, retry or contact admin", view=self.view)
            return

        message = f"TS username: **{topshot_username}**\n" \
                  f"Flow address: **{self.flow_address}**\n\n**Synced**"

        await interaction.response.edit_message(content=message, view=self.view)


class ProfileView(BaseView):
    def __init__(self, user_id, existing_address=None):
        super(ProfileView, self).__init__(user_id)
        if existing_address is not None:
            self.add_item(ProfileUpdateButton("Sync top shot username", existing_address))
        else:
            self.add_item(ProfileLinkButton("Link"))

    @staticmethod
    def load_profile_view(user_id):
        user, _ = get_user_new(user_id)
        if user is None:
            return LINK_TS_ACCOUNT_MESSAGE, ProfileView(user_id)

        return f"TS username: **{user['topshot_username']}**\n" \
               f"Address: **{user['flow_address']}**", ProfileView(user_id, user['flow_address'])
