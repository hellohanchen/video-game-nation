import discord

from constants import INVALID_ID
from service.fastbreak.dynamic_lineup import DynamicLineupService, Lineup


class FastBreakView(discord.ui.View):
    def __init__(self, lineup_service: DynamicLineupService, user_id: int, is_ranked=False):
        super().__init__()
        self.service: DynamicLineupService = lineup_service
        self.user_id: int = user_id
        self.is_ranked = is_ranked

    def back_to_lineup(self):
        message = self.service.load_or_create_lineup(self.user_id).formatted()

        if self.is_ranked:
            return message, RankedLineupView(self.service, self.user_id)
        else:
            return message, LineupView(self.service, self.user_id)


class MainStartButton(discord.ui.Button['Start']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="Join FastBreak", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: MainPage = self.view
        message, new_view = view.launch_fb(interaction.user.id)

        await interaction.response.send_message(content=message, view=new_view, ephemeral=True, delete_after=600.0)


class MainPage(discord.ui.View):
    def __init__(self, service: DynamicLineupService):
        super().__init__()
        self.add_item(MainStartButton())
        self.service = service

    def launch_fb(self, user_id):
        return self.service.load_or_create_lineup(user_id).formatted(), LineupView(self.service, user_id)


class LineupButton(discord.ui.Button[FastBreakView]):
    def __init__(self, row):
        super().__init__(style=discord.ButtonStyle.success, label="My lineup", row=row)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: FastBreakView = self.view
        message, new_view = view.back_to_lineup()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupTeamsButton(discord.ui.Button['LineupTeams']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="Add Player", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message, new_view = view.jump_to_teams()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupRemoveButton(discord.ui.Button['LineupRemove']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, label="Remove Player", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message, new_view = view.remove_player()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupScheduleButton(discord.ui.Button['LineupSchedule']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="Schedule", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message, new_view = await view.get_fb_schedule()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupView(FastBreakView):
    def __init__(self, service, user_id, is_ranked=False):
        super().__init__(service, user_id, is_ranked)
        if not is_ranked:
            self.add_item(LineupTeamsButton())
            self.add_item(LineupRemoveButton())
            self.add_item(LineupButton(1))
            self.add_item(LineupScheduleButton())
        self.lineup = self.service.load_or_create_lineup(self.user_id)

    def jump_to_teams(self):
        return self.service.formatted_games, TeamsView(self.service, self.user_id, self.is_ranked)

    def remove_player(self):
        return self.lineup.formatted() + "\nRemove a player from your lineup", \
               RemoveView(self.service, self.user_id, self.is_ranked)

    async def get_fb_schedule(self):
        schedule = await self.service.schedule_with_scores(self.user_id)
        return schedule, self


class LineupRulesButton(discord.ui.Button['LineupRules']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="Rules", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: RankedLineupView = self.view
        message = f"***FASTBREAK RULES***\n\n" \
                  f"**Rule 0.** The gameplay is the same as the Topshot Fastbreak: " \
                  f"users will select 3 to 5 players. Each game night has different stats and different scores " \
                  f"that the lineup must beat in order to get a win.\n" \
                  f"**Rule 1.** Users must link their own Topshot accounts with Discord account to join the game, " \
                  f"and submit the same lineup as Topshot Fastbreak for every night.\n" \
                  f"**Rule 2.** The DAILY leaderboard will be determined by score of the lineup. Tierbreaker is \n" \
                  f"*sum of lowest serials of the highest tier moments of each player*.\n" \
                  f"**Rule 3.** The WEEKLY leaderboard will be determined by the number of wins. Tierbreaker is sum " \
                  f"of the completion rate of each night.\n" \
                  f"**completion rate** = sum of (score of each stat / target of each stat) / number of stats.\n" \
                  f"For example, if the targets are 50 rebounds and 25 assists, the user's lineup scores are " \
                  f"60 rebounds and 15 assists, then: \n" \
                  f"completion rate = (60 / 50 + 15 / 25) / 2 = 0.9\n" \
                  f"**bonus:** if a user submits lineup every night in a week, a 10% bonus will be given.\n"
        await interaction.response.edit_message(content=message, view=view)


class LineupSubmitButton(discord.ui.Button['LineupSubmit']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="Submit", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: RankedLineupView = self.view
        message = f"Submission in progress...\n" \
                  f"Unblock bot DM to receive the result or click 'My Lineup' to check if is submitted."
        await interaction.response.edit_message(content=message, view=view)
        message = await view.lineup.submit()
        await interaction.user.send(content=message)


class LineupLeaderboardButton(discord.ui.Button['LineupLeaderboard']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="Leaderboard", row=2)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: RankedLineupView = self.view
        message, new_view = view.check_leaderboard()

        await interaction.response.edit_message(content=message, view=new_view)


class RankedLineupView(LineupView):
    def __init__(self, service, user_id):
        super().__init__(service, user_id, True)
        self.add_item(LineupTeamsButton())
        self.add_item(LineupRemoveButton())
        self.add_item(LineupSubmitButton())
        self.add_item(LineupScheduleButton())
        self.add_item(LineupRulesButton())
        self.add_item(LineupButton(2))
        self.add_item(LineupLeaderboardButton())

    def check_leaderboard(self):
        return self.service.formatted_leaderboard(20), self


class RemovePlayerButton(discord.ui.Button['RemovePlayer']):
    def __init__(self, row, player_name, pos_idx):
        super().__init__(style=discord.ButtonStyle.primary, label=player_name, row=row)
        self.pos_idx = pos_idx

    # This function is called whenever this particular button is pressed
    # This is part of the "meat" of the game logic
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: RemoveView = self.view
        self.style = discord.ButtonStyle.secondary
        self.disabled = True
        message, new_view = view.remove_player(self.pos_idx)

        await interaction.response.edit_message(content=message, view=new_view)


class RemoveView(FastBreakView):
    def __init__(self, service, user_id, is_ranked=False):
        super().__init__(service, user_id, is_ranked)
        self.lineup = self.service.get_or_create_lineup(self.user_id)

        player_ids = self.lineup.player_ids
        i = 0
        for j in range(0, self.service.fb.count):
            if player_ids[j] != INVALID_ID:
                self.add_item(RemovePlayerButton(int(i / 4), self.service.players[player_ids[j]]['full_name'], j))
                i += 1
        self.add_item(LineupButton(int((i + 3) / 4) + 1))

    # This method update current player info
    def remove_player(self, pos_idx):
        message = self.lineup.remove_player(pos_idx, self.is_ranked)
        return f"{self.lineup.formatted()}\n{message}", self


class TeamsTeamButton(discord.ui.Button['TeamsTeam']):
    def __init__(self, row, team):
        super().__init__(style=discord.ButtonStyle.primary, label=team, row=row)
        self.team = team

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TeamsView = self.view
        content, new_view = view.get_team_info(self.team)

        await interaction.response.edit_message(content=content, view=new_view)


class TeamsGameButton(discord.ui.Button['TeamsGame']):
    def __init__(self, row, home_team, away_team):
        super().__init__(style=discord.ButtonStyle.primary, label=f"{away_team}@{home_team}", row=row)
        self.home_team = home_team
        self.away_team = away_team

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TeamsView = self.view
        content, new_view = view.get_game_info(self.home_team, self.away_team)

        await interaction.response.edit_message(content=content, view=new_view)


class TeamsView(FastBreakView):
    def __init__(self, lineup_service, user_id, is_ranked=False):
        super().__init__(lineup_service, user_id, is_ranked)

        teams = list(self.service.team_players.keys())
        i = 0
        if len(teams) <= 16:
            for game_id, game in self.service.get_coming_games():
                self.add_item(TeamsTeamButton(int(i / 4), game['awayTeam']))
                self.add_item(TeamsTeamButton(int(i / 4), game['homeTeam']))
                i += 2
        else:
            for game_id, game in self.service.get_coming_games():
                self.add_item(TeamsGameButton(int(i / 4), game['homeTeam'], game['awayTeam']))
                i += 1
        self.add_item(LineupButton(int((i - 1) / 4) + 1))

    def get_team_info(self, team):
        return self.service.formatted_team_players(team), TeamView(team, self.service, self.user_id, self.is_ranked)

    def get_game_info(self, home_team, away_team):
        return f"{away_team} at {home_team}", GameView(home_team, away_team, self.service, self.user_id, self.is_ranked)


class GameTeamButton(discord.ui.Button['GameTeam']):
    def __init__(self, team):
        super().__init__(style=discord.ButtonStyle.primary, label=team, row=1)
        self.team = team

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: GameView = self.view
        content, new_view = view.get_team_info(self.team)

        await interaction.response.edit_message(content=content, view=new_view)


class GameView(FastBreakView):
    def __init__(self, home_team, away_team, lineup_service, user_id, is_ranked=False):
        super().__init__(lineup_service, user_id, is_ranked)

        self.add_item(GameTeamButton(away_team))
        self.add_item(GameTeamButton(home_team))
        self.add_item(LineupButton(2))

    def get_team_info(self, team):
        return self.service.formatted_team_players(team), TeamView(team, self.service, self.user_id, self.is_ranked)


class TeamPlayerButton(discord.ui.Button['TeamPlayer']):
    def __init__(self, row, player_idx, player_name):
        super().__init__(style=discord.ButtonStyle.primary, label=f"{player_name}", row=row)
        self.player_idx = player_idx

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TeamView = self.view
        content, new_view = view.add_to_lineup(self.player_idx)

        await interaction.response.edit_message(content=content, view=new_view)


class TeamTeamsButton(discord.ui.Button['TeamTeams']):
    def __init__(self, row):
        super().__init__(style=discord.ButtonStyle.success, label='Teams', row=row)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TeamView = self.view
        content, new_view = view.back_to_teams()

        await interaction.response.edit_message(content=content, view=new_view)


class TeamView(FastBreakView):
    def __init__(self, team, service, user_id, is_ranked=False):
        super().__init__(service, user_id, is_ranked)
        self.team = team
        self.lineup: Lineup = self.service.get_or_create_lineup(user_id)

        player_ids = self.service.team_players[team]
        for i in range(0, len(player_ids)):
            player = self.service.players[player_ids[i]]
            self.add_item(TeamPlayerButton(int(i / 5), player['index'], player['full_name']))

        last_row = min(int((len(player_ids) - 1) / 5) + 1, 4)
        self.add_item(LineupButton(last_row))
        self.add_item(TeamTeamsButton(last_row))

    def add_to_lineup(self, player_idx):
        pos_idx = self.service.fb.count
        for i in range(0, self.service.fb.count):
            if self.lineup.player_ids[i] == INVALID_ID:
                pos_idx = i
                break

        if pos_idx == self.service.fb.count:
            return "Lineup is already full, please remove a player.", self

        return self.lineup.add_player_by_idx(player_idx, pos_idx, self.is_ranked), self

    def back_to_teams(self):
        return self.service.formatted_games, TeamsView(self.service, self.user_id, self.is_ranked)
