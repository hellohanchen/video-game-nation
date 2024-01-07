import discord

from service.fastbreak.lineup import LineupService
from service.fastbreak.ranking import RankingService, RANK_SERVICE


class FastBreakView(discord.ui.View):
    def __init__(self, lineup_service, user_id):
        super().__init__()
        self.lineup_service: LineupService = lineup_service
        self.user_id = user_id

    def back_to_lineup(self):
        message = self.lineup_service.get_or_create_lineup(self.user_id).formatted()

        return message, LineupView(self.lineup_service, self.user_id)


class MainStartButton(discord.ui.Button['Start']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="BREAK!", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: MainPage = self.view
        message, new_view = view.launch_fb(interaction.user.id)

        await interaction.response.send_message(content=message, view=new_view, ephemeral=True, delete_after=600.0)


class MainPage(discord.ui.View):
    def __init__(self, lineup_service: LineupService, rank_service: RankingService):
        super().__init__()
        self.add_item(MainStartButton())
        self.lineup_service = lineup_service
        self.rank_service = rank_service

    def launch_fb(self, user_id):
        if self.rank_service.status != "IN_GAME":
            message = self.lineup_service.get_or_create_lineup(user_id).formatted()
        else:
            message = self.rank_service.formatted_user_score(user_id)

        return message, LineupView(self.lineup_service, user_id)


class LineupButton(discord.ui.Button['Lineup']):
    def __init__(self, row):
        super().__init__(style=discord.ButtonStyle.success, label="My lineup", row=row)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: FastBreakView = self.view
        message, new_view = view.back_to_lineup()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupTeamsButton(discord.ui.Button['LineupTeams']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="Teams", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message, new_view = view.jump_to_teams()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupRemoveButton(discord.ui.Button['LineupRemove']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, label="Remove", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message, new_view = view.remove_player()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupScoreButton(discord.ui.Button['LineupScore']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="My Score", row=2)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message, new_view = view.check_score()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupView(FastBreakView):
    def __init__(self, lineup_service, user_id):
        super().__init__(lineup_service, user_id)
        self.add_item(LineupTeamsButton())
        self.add_item(LineupRemoveButton())
        self.add_item(LineupButton(2))
        self.add_item(LineupScoreButton())
        self.lineup = self.lineup_service.get_or_create_lineup(self.user_id)

    def jump_to_teams(self):
        message = self.lineup_service.formatted_schedule
        return message, TeamsView(self.lineup_service, self.user_id)

    def remove_player(self):
        return self.lineup.formatted() + "\nRemove a player from your lineup", RemoveView(self.lineup_service, self.user_id)

    def check_score(self):
        return RANK_SERVICE.formatted_user_score(self.user_id), self


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
    def __init__(self, lineup_service, user_id):
        super().__init__(lineup_service, user_id)
        self.lineup = self.lineup_service.get_or_create_lineup(self.user_id)

        player_ids = self.lineup.player_ids
        i = 0
        for j in range(0, self.lineup_service.fb.count):
            if player_ids[j] is not None:
                self.add_item(RemovePlayerButton(int(i / 4), self.lineup_service.players[player_ids[j]]['full_name'], j))
                i += 1
        self.add_item(LineupButton(int((i + 3) / 4) + 1))

    # This method update current player info
    def remove_player(self, pos_idx):
        message = self.lineup.remove_player(pos_idx)

        return self.lineup.formatted() + "\n" + message, self


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
    def __init__(self, lineup_service, user_id):
        super().__init__(lineup_service, user_id)

        teams = list(self.lineup_service.team_to_players.keys())
        i = 0
        if len(teams) <= 16:
            for game_id, game in self.lineup_service.get_coming_games():
                self.add_item(TeamsTeamButton(int(i / 4), game['awayTeam']))
                self.add_item(TeamsTeamButton(int(i / 4), game['homeTeam']))
                i += 2
        else:
            for game_id, game in self.lineup_service.get_coming_games():
                self.add_item(TeamsGameButton(int(i / 4), game['homeTeam'], game['awayTeam']))
                i += 1
        self.add_item(LineupButton(int((i - 1) / 4) + 1))

    def get_team_info(self, team):
        message = self.lineup_service.formatted_team_players(team)[0]

        return message, TeamView(team, self.lineup_service, self.user_id)

    def get_game_info(self, home_team, away_team):
        message = f"{away_team} at {home_team}"

        return message, GameView(home_team, away_team, self.lineup_service, self.user_id)


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
    def __init__(self, home_team, away_team, lineup_service, user_id):
        super().__init__(lineup_service, user_id)

        self.add_item(GameTeamButton(away_team))
        self.add_item(GameTeamButton(home_team))
        self.add_item(LineupButton(2))

    def get_team_info(self, team):
        message = self.lineup_service.formatted_team_players(team)[0]

        return message, TeamView(team, self.lineup_service, self.user_id)


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
    def __init__(self, team, lineup_service, user_id):
        super().__init__(lineup_service, user_id)
        self.team = team
        self.lineup = self.lineup_service.get_or_create_lineup(user_id)

        player_ids = self.lineup_service.team_to_players[team]
        for i in range(0, len(player_ids)):
            player = self.lineup_service.players[player_ids[i]]
            self.add_item(TeamPlayerButton(int(i / 5), player['index'], player['full_name']))

        last_row = int((len(player_ids) - 1) / 5) + 1
        self.add_item(LineupButton(last_row))
        self.add_item(TeamTeamsButton(last_row))

    def add_to_lineup(self, player_idx):
        lineup = self.lineup_service.get_or_create_lineup(self.user_id)
        if lineup is None:
            return "Fail to load lineup.", self

        pos_idx = self.lineup_service.fb.count
        for i in range(0, self.lineup_service.fb.count):
            if lineup.player_ids[i] is None:
                pos_idx = i
                break

        if pos_idx == self.lineup_service.fb.count:
            return "Lineup is already full, please remove a player.", self

        return lineup.add_player_by_idx(player_idx, pos_idx), self

    def back_to_teams(self):
        return self.lineup_service.formatted_schedule, TeamsView(self.lineup_service, self.user_id)
