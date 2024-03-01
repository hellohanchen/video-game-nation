import discord

from provider.topshot.fb_provider import FB_PROVIDER
from repository.vgn_users import get_user_new
from service.common.profile.views import ProfileView, LINK_TS_ACCOUNT_MESSAGE
from service.fastbreak.dynamic_lineup import DynamicLineupService
from service.fastbreak.views import MainPage, RankedLineupView, LineupView


class MainAccountButton(discord.ui.Button['Account']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.green, label="Link TS Account", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        message, new_view = ProfileView.load_profile_view(interaction.user.id)

        await interaction.response.send_message(content=message, view=new_view, ephemeral=True, delete_after=600.0)


class RankedMainPage(MainPage):
    def __init__(self, service: DynamicLineupService):
        super().__init__(service)
        self.add_item(MainAccountButton())

    def launch_fb(self, user_id, channel_id):
        user, _ = get_user_new(user_id)
        if user is None:
            return LINK_TS_ACCOUNT_MESSAGE, ProfileView(user_id)

        contest_id = FB_PROVIDER.get_contest_id(self.service.current_game_date, channel_id)
        if contest_id is not None:
            view = RankedLineupView(self.service, user_id, contest_id)
        else:
            view = LineupView(self.service, user_id)
        return view.lineup.formatted(contest_id), view
