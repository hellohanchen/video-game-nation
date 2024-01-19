import discord

from provider.topshot.graphql.get_address import get_flow_account_info
from repository.vgn_users import insert_and_get_user
from service.views import BaseView

TO_LINK_MESSAGE = "Please click 'Link' to link to a TS username & address.\n" \
                  "Once linked, you can update your TS username,\n" \
                  "but you can only contact admin to change your Flow address."


class ProfileLinkModal(discord.ui.Modal, title='Link TS Account'):
    username = discord.ui.TextInput(
        label='TS Username')

    def __init__(self, user_id, view: discord.ui.View, existing_address=None):
        super(ProfileLinkModal, self).__init__()
        self.user_id = user_id
        self.msg_view = view
        self.existing_address = existing_address

    async def on_submit(self, interaction: discord.Interaction):
        topshot_username = str(self.username)
        topshot_username, flow_address, _ = await get_flow_account_info(topshot_username)

        if flow_address is not None:
            if self.existing_address is not None and flow_address != self.existing_address:
                message = "Flow address mismatched, you need to contact admin to change your Flow address."
            else:
                user, _ = insert_and_get_user(self.user_id, topshot_username, flow_address)
                if user is None:
                    message = TO_LINK_MESSAGE
                else:
                    message = f"TS username: **{user['topshot_username']}**\n" \
                              f"Flow address: **{user['flow_address']}**\n\n**Linked**"
        else:
            message = f"**{self.username}** not found\nPlease click 'Link' to link to a TS account\n\n"

        await interaction.response.edit_message(content=message, view=self.msg_view)


class ProfileLinkButton(discord.ui.Button['Link']):
    def __init__(self, label, existing_address=None):
        super().__init__(style=discord.ButtonStyle.success, label=label, row=0)
        self.existing_address = existing_address

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        await interaction.response.send_modal(ProfileLinkModal(interaction.user.id, self.view, self.existing_address))


class ProfileView(BaseView):
    def __init__(self, user_id, existing_address=None):
        super(ProfileView, self).__init__(user_id)
        if existing_address is not None:
            self.add_item(ProfileLinkButton("Update name", existing_address))
        else:
            self.add_item(ProfileLinkButton("Link", existing_address))
