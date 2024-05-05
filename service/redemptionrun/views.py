import discord

from service.redemptionrun.lineup import LineupService, Lineup
from service.redemptionrun.ranking import RankingService
from vgnlog.channel_logger import ADMIN_LOGGER


class RedemptionRunView(discord.ui.View):
    def __init__(self, lineup_service: LineupService, ranking_service: RankingService, user_id: int):
        super().__init__()
        self.lineup_service: LineupService = lineup_service
        self.ranking_service: RankingService = ranking_service
        self.user_id: int = user_id

    def back_to_lineup(self):
        view = LineupView(self.lineup_service, self.ranking_service, self.user_id)
        return view.lineup.formatted(), view


class MainStartButton(discord.ui.Button['Start']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="Join Redemption Run", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: MainPage = self.view
        message, new_view = view.launch_rr(interaction.user.id)

        await interaction.response.send_message(content=message, view=new_view, ephemeral=True, delete_after=600.0)


class MainPage(discord.ui.View):
    def __init__(self, lineup_service: LineupService, ranking_service: RankingService):
        super().__init__()
        self.add_item(MainStartButton())
        self.lineup_service = lineup_service
        self.ranking_service = ranking_service

    def launch_rr(self, user_id):
        view = LineupView(self.lineup_service, self.ranking_service, user_id)
        return view.lineup.formatted(), view


class LineupButton(discord.ui.Button[RedemptionRunView]):
    def __init__(self, row):
        super().__init__(style=discord.ButtonStyle.success, label="My Selections", row=row)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: RedemptionRunView = self.view
        message, new_view = view.back_to_lineup()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupBucketsButton(discord.ui.Button['LineupView']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="Make Selection", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message, new_view = view.jump_to_buckets()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupScheduleButton(discord.ui.Button['LineupView']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="Run Results", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message, new_view = await view.get_rr_results()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupRulesButton(discord.ui.Button['LineupView']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="Rules", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message = f"***REDEMPTION RUN RULES***\n\n" \
                  f"**1.**Make predictions of every night, you need required types of moments of players/teams to " \
                  f"make selections.\n" \
                  f"**2.**Every night the leaderboard will be sorted by [correct predictions], " \
                  f"[sum of smallest serials], [count of players/teams with legendary/ultimate moments], " \
                  f"[count of players/teams with rare moments]\n" \
                  f"**3.**Your position needs to achieve a certain percentage on the leaderboard per night, or you " \
                  f"will lose **1 life**\n" \
                  f"**4.**You will need to have series 23-24 playoff/redemption moments of the teams in the " \
                  f"current round to get enough lives to submit new predictions."
        await interaction.response.edit_message(content=message, view=view)


class LineupSubmitButton(discord.ui.Button['LineupView']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="Submit", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        await interaction.response.edit_message(content=f"Submission in progress...\n", view=view)
        followup = interaction.followup
        try:
            message = await view.lineup.submit()
            await followup.send(message, ephemeral=True)
        except Exception as err:
            await ADMIN_LOGGER.error(f"Submit:{err}")
            await followup.send(f"Submission failed, please retry", ephemeral=True)


class LineupScoreButton(discord.ui.Button['LineupLeaderboard']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="Top 20", row=2)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message, new_view = view.check_score()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupLeaderboardButton(discord.ui.Button['LineupLeaderboard']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="My Score", row=2)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message, new_view = view.check_leaderboard()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupView(RedemptionRunView):
    def __init__(self, lineup_service, ranking_service, user_id):
        super().__init__(lineup_service, ranking_service, user_id)
        self.add_item(LineupBucketsButton())
        self.add_item(LineupRulesButton())
        self.add_item(LineupSubmitButton())
        self.add_item(LineupScheduleButton())
        self.add_item(LineupButton(2))
        self.add_item(LineupScoreButton())
        self.add_item(LineupLeaderboardButton())
        self.lineup: Lineup = lineup_service.get_or_create_lineup(user_id)

    def check_score(self):
        return self.ranking_service.formatted_user_score(self.user_id), self

    def check_leaderboard(self):
        return self.ranking_service.formatted_leaderboard(20), self

    def jump_to_buckets(self):
        return self.lineup.formatted(), BucketsView(self.lineup_service, self.ranking_service, self.user_id)

    async def get_rr_results(self):
        slate_results = await self.lineup_service.get_user_slate_results(self.user_id)
        return slate_results, self


class BucketOptionButton(discord.ui.Button['BucketsView']):
    def __init__(self, bucket_idx, option, option_label, row):
        super().__init__(style=discord.ButtonStyle.primary, label=option_label, row=row)
        self.bucket_idx = bucket_idx
        self.option = option

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: BucketsView = self.view
        content, new_view = await view.select(self.bucket_idx, self.option)

        await interaction.response.edit_message(content=content, view=new_view)


class BucketsView(RedemptionRunView):
    def __init__(self, lineup_service, ranking_service, user_id):
        super().__init__(lineup_service, ranking_service, user_id)

        buckets = lineup_service.rr.buckets
        for i in range(len(buckets)):
            bucket = buckets[i]
            self.add_item(BucketOptionButton(i, bucket.options[0][0], bucket.options[0][1], int(i / 4)))
            self.add_item(BucketOptionButton(i, bucket.options[1][0], bucket.options[1][1], int(i / 4)))

        self.add_item(LineupButton(int((len(buckets) - 1) / 4) + 1))
        self.lineup = lineup_service.get_or_create_lineup(user_id)

    async def select(self, bucket_idx, selected):
        message = await self.lineup.select(bucket_idx, selected)
        return message, self
