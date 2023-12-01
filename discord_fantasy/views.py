import discord

import utils
from repository.vgn_collections import upsert_collection as repo_upsert_collection
from repository.vgn_lineups import get_weekly_score
from repository.vgn_users import get_user
from service.fantasy.ranking import RANK_PROVIDER
from topshot.cadence.flow_collections import get_account_plays


class FantasyView(discord.ui.View):
    def __init__(self, lineup_provider, user_id):
        super().__init__()
        self.lineup_provider = lineup_provider
        self.user_id = user_id

    def back_to_lineup(self):
        message = self.lineup_provider.get_or_create_lineup(self.user_id).formatted()

        return message, LineupView(self.lineup_provider, self.user_id)


class MainStartButton(discord.ui.Button['Start']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="GO!", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: MainPage = self.view
        message, new_view = view.launch_fantasy(interaction.user.id)

        await interaction.response.send_message(content=message, view=new_view, ephemeral=True, delete_after=600.0)


class MainPage(discord.ui.View):
    def __init__(self, lineup_provider, rank_provider):
        super().__init__()
        self.add_item(MainStartButton())
        self.lineup_provider = lineup_provider
        self.rank_provider = rank_provider

    def launch_fantasy(self, user_id):
        if self.rank_provider.status != "IN_GAME":
            message = self.lineup_provider.get_or_create_lineup(user_id).formatted()
        else:
            message = self.rank_provider.formatted_user_score(user_id)[0]

        return message, LineupView(self.lineup_provider, user_id)


class LineupButton(discord.ui.Button['Lineup']):
    def __init__(self, row):
        super().__init__(style=discord.ButtonStyle.success, label="My lineup", row=row)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: FantasyView = self.view
        message, new_view = view.back_to_lineup()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupPlayersButton(discord.ui.Button['LineupPlayers']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="Players", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message, new_view = view.jump_to_players()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupTeamsButton(discord.ui.Button['LineupTeams']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="Teams", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message, new_view = view.jump_to_teams()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupSubmitButton(discord.ui.Button['LineupSubmit']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="Submit", row=2)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message, new_view = view.submit_lineup()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupRemoveButton(discord.ui.Button['LineupRemove']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, label="Remove", row=2)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message, new_view = view.remove_player()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupSwapButton(discord.ui.Button['LineupSwap']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, label="Swap", row=2)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message, new_view = view.swap_player()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupScoreButton(discord.ui.Button['LineupScore']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="My Score", row=3)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message, new_view = view.check_score()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupWeekScoreButton(discord.ui.Button['LineupWeek']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="My Week", row=3)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message, new_view = view.check_week_score()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupReloadButton(discord.ui.Button['LineupReload']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="Refresh TS Moments", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view
        message, new_view = await view.reload_collection()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupView(FantasyView):
    def __init__(self, lineup_provider, user_id):
        super().__init__(lineup_provider, user_id)
        self.add_item(LineupPlayersButton())
        self.add_item(LineupTeamsButton())
        self.add_item(LineupReloadButton())
        self.add_item(LineupRemoveButton())
        self.add_item(LineupSwapButton())
        self.add_item(LineupSubmitButton())
        self.add_item(LineupButton(3))
        self.add_item(LineupScoreButton())
        self.add_item(LineupWeekScoreButton())
        self.lineup = self.lineup_provider.get_or_create_lineup(self.user_id)

    def jump_to_players(self):
        message = self.lineup_provider.formatted_10_players(1)
        view = PlayersView(1, self.lineup_provider, self.user_id)

        return message, view

    def jump_to_teams(self):
        message = self.lineup_provider.formatted_schedule
        return message, TeamsView(self.lineup_provider, self.user_id)

    def submit_lineup(self):
        message = self.lineup.submit()

        return message, self

    def remove_player(self):
        return self.lineup.formatted() + "\nRemove a player from your lineup", RemoveView(self.lineup_provider, self.user_id)

    def swap_player(self):
        return self.lineup.formatted() + "\nSwap 2 players in your lineup", SwapView(self.lineup_provider, self.user_id)

    def check_score(self):
        return RANK_PROVIDER.formatted_user_score(self.user_id)[0], self

    def check_week_score(self):
        if RANK_PROVIDER.current_game_date == "":
            date = self.lineup_provider.coming_game_date
        else:
            date = RANK_PROVIDER.current_game_date

        dates = utils.get_the_past_week(date)
        score = get_weekly_score(dates, self.user_id)
        return f"Total score {dates[0]}~{dates[-1]}: **{score}**", self

    async def reload_collection(self):
        vgn_user = get_user(self.user_id)

        if vgn_user is None:
            return "Account not found, contact admin for registration.", self

        user_id = vgn_user[0]
        flow_address = vgn_user[2]

        try:
            plays = await get_account_plays(flow_address)
        except:
            return "Failed to fetch collection, try again or contact admin.", self

        try:
            message = repo_upsert_collection(user_id, plays)
        except:
            return "Failed to update database, try again or contact admin.", self

        self.lineup_provider.load_user_collection(self.user_id)
        return message, self


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


class RemoveView(FantasyView):
    def __init__(self, lineup_provider, user_id):
        super().__init__(lineup_provider, user_id)
        self.lineup = self.lineup_provider.get_or_create_lineup(self.user_id)

        player_ids = self.lineup.player_ids
        i = 0
        for j in range(0, 8):
            if player_ids[j] is not None:
                self.add_item(RemovePlayerButton(int(i / 4), self.lineup_provider.players[player_ids[j]]['full_name'], j))
                i += 1
        self.add_item(LineupButton(int((i + 3) / 4) + 1))

    # This method update current player info
    def remove_player(self, pos_idx):
        message = self.lineup.remove_player(pos_idx)

        return self.lineup.formatted() + "\n" + message, self


class SwapPlayerButton(discord.ui.Button['SwapPlayer']):
    def __init__(self, row, player_name, pos_idx):
        super().__init__(style=discord.ButtonStyle.primary, label=player_name, row=row)
        self.pos_idx = pos_idx

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: SwapView = self.view
        self.style = discord.ButtonStyle.secondary
        self.disabled = True
        message, new_view = view.swap_player(self.pos_idx)

        await interaction.response.edit_message(content=message, view=new_view)


class SwapView(FantasyView):
    def __init__(self, lineup_provider, user_id):
        super().__init__(lineup_provider, user_id)
        self.lineup = self.lineup_provider.get_or_create_lineup(self.user_id)

        player_ids = self.lineup.player_ids
        i = 0
        for j in range(0, 8):
            if player_ids[j] is not None:
                self.add_item(SwapPlayerButton(int(i / 4), self.lineup_provider.players[player_ids[j]]['full_name'], j))
                i += 1
        self.add_item(LineupButton(int((i + 3) / 4) + 1))
        self.selected = None

    # This method update current player info
    def swap_player(self, pos_idx):
        if self.selected is None:
            message = "Select another player."
            view = self
            self.selected = pos_idx
        else:
            message = self.lineup.swap_players(self.selected, pos_idx)
            view = LineupView(self.lineup_provider, self.user_id)

        return self.lineup.formatted() + "\n" + message, view


# Defines a custom button that contains the logic of checking player information
class PlayerToggleButton(discord.ui.Button['Player']):
    def __init__(self, offset):
        super().__init__(
            style=discord.ButtonStyle.secondary if offset != 0 else discord.ButtonStyle.primary,
            row=2 if offset != 0 else 1)
        self.offset = offset
        if offset > 0:
            self.label = "Next"
        elif offset < 0:
            self.label = "Prev"
        else:
            self.label = "Reload"

    # This function is called whenever this particular button is pressed
    # This is part of the "meat" of the game logic
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: PlayerView = self.view
        view.current_player += self.offset
        content = view.get_player_info()

        await interaction.response.edit_message(content=content, view=view)


class PlayerAddButton(discord.ui.Button['PlayerAdd']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="Add", row=1)

    # This function is called whenever this particular button is pressed
    # This is part of the "meat" of the game logic
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: PlayerView = self.view
        message, new_view = view.add_to_lineup()

        await interaction.response.edit_message(content=message, view=new_view)


class PlayerPlayersButton(discord.ui.Button['PlayerPlayers']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="Players", row=3)

    # This function is called whenever this particular button is pressed
    # This is part of the "meat" of the game logic
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: PlayerView = self.view
        message, new_view = view.back_to_players()

        await interaction.response.edit_message(content=message, view=new_view)


class PlayerTeamButton(discord.ui.Button['PlayerTeam']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="Team", row=3)

    # This function is called whenever this particular button is pressed
    # This is part of the "meat" of the game logic
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: PlayerView = self.view
        message, new_view = view.back_to_team()

        await interaction.response.edit_message(content=message, view=new_view)


class PlayerView(FantasyView):
    def __init__(self, player_idx, lineup_provider, user_id):
        super().__init__(lineup_provider, user_id)
        self.current_player = player_idx
        self.add_item(PlayerAddButton())
        self.add_item(PlayerToggleButton(0))
        self.add_item(PlayerToggleButton(-1))
        self.add_item(PlayerToggleButton(1))
        self.add_item(LineupButton(3))
        self.add_item(PlayerPlayersButton())
        self.add_item(PlayerTeamButton())

    # This method update current player info
    def get_player_info(self):
        if self.current_player > len(self.lineup_provider.player_ids):
            self.current_player = len(self.lineup_provider.player_ids)
        elif self.current_player < 1:
            self.current_player = 1

        player_id = self.lineup_provider.player_ids[self.current_player - 1]
        return self.lineup_provider.detailed_player_by_id(player_id, self.user_id)

    def add_to_lineup(self):
        lineup = self.lineup_provider.get_or_create_lineup(self.user_id)
        if lineup is None:
            return "Fail to load lineup.", self

        pos_idx = 8
        for i in range(0, 8):
            if lineup.player_ids[i] is None:
                pos_idx = i
                break

        if pos_idx == 8:
            return "Lineup is already full, please remove a player.", self

        return lineup.add_player_by_idx(self.current_player, pos_idx), self

    def back_to_players(self):
        page = int((self.current_player - 1) / 10) + 1

        message = self.lineup_provider.formatted_10_players(page)
        view = PlayersView(page, self.lineup_provider, self.user_id)

        return message, view

    def back_to_team(self):
        player_id = self.lineup_provider.player_ids[self.current_player - 1]
        team = self.lineup_provider.player_to_team[player_id]

        message = self.lineup_provider.formatted_team_players(team)[0]
        return message, TeamView(team, self.lineup_provider, self.user_id)


class PlayersPlayerButton(discord.ui.Button['PlayersPlayer']):
    def __init__(self, idx_in_page):
        super().__init__(style=discord.ButtonStyle.primary,
                         label=f'#{idx_in_page}',
                         row=int((idx_in_page + 2) / 3) - 1 if idx_in_page != 10 else 2)
        self.idx_in_page = idx_in_page

    # This function is called whenever this particular button is pressed
    # This is part of the "meat" of the game logic
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: PlayersView = self.view
        message, new_view = view.get_player_info(self.idx_in_page)

        await interaction.response.edit_message(content=message, view=new_view)


class PlayersToggleButton(discord.ui.Button['Players']):
    def __init__(self, offset):
        super().__init__(style=discord.ButtonStyle.secondary, row=4)
        self.offset = offset
        if offset > 0:
            self.label = "Next"
        elif offset < 0:
            self.label = "Prev"

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: PlayersView = self.view
        view.current_page += self.offset
        content, new_view = view.get_players_info()

        await interaction.response.edit_message(content=content, view=new_view)


class PlayersSalaryButton(discord.ui.Button['PlayersSalary']):
    def __init__(self, salary):
        super().__init__(style=discord.ButtonStyle.secondary, row=3, label="${}".format(salary))
        self.salary = salary

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: PlayersView = self.view
        view.current_page = view.get_page_of_salary(self.salary)
        content, new_view = view.get_players_info()

        await interaction.response.edit_message(content=content, view=new_view)


class PlayersView(FantasyView):
    def __init__(self, page, lineup_provider, user_id):
        super().__init__(lineup_provider, user_id)
        self.current_page = page
        self.lineup_provider = lineup_provider
        self.user_id = user_id

        for i in range(1, 11):
            self.add_item(PlayersPlayerButton(i))

        self.add_item(PlayersSalaryButton(45))
        self.add_item(PlayersSalaryButton(30))
        self.add_item(PlayersSalaryButton(20))
        self.add_item(PlayersSalaryButton(10))
        self.add_item(PlayersSalaryButton(5))
        self.add_item(LineupButton(4))
        self.add_item(PlayersToggleButton(-1))
        self.add_item(PlayersToggleButton(1))

    def get_players_info(self):
        if self.current_page > len(self.lineup_provider.player_ids) / 10 + 1:
            self.current_page -= 1
        elif self.current_page < 1:
            self.current_page = 1

        message = self.lineup_provider.formatted_10_players(self.current_page)
        return message, self

    def get_page_of_salary(self, salary):
        return self.lineup_provider.salary_pages[salary]

    def get_player_info(self, idx_in_page):
        player_idx = self.current_page * 10 + idx_in_page - 10
        if player_idx > len(self.lineup_provider.player_ids):
            player_idx = len(self.lineup_provider.player_ids)

        message = self.lineup_provider.detailed_player_by_id(self.lineup_provider.player_ids[player_idx - 1], self.user_id)

        return message, PlayerView(player_idx, self.lineup_provider, self.user_id)


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


class TeamsView(FantasyView):
    def __init__(self, lineup_provider, user_id):
        super().__init__(lineup_provider, user_id)

        teams = list(self.lineup_provider.team_to_players.keys())
        i = 0
        if len(teams) <= 16:
            for game_id, game in self.lineup_provider.get_coming_games():
                self.add_item(TeamsTeamButton(int(i / 4), game['awayTeam']))
                self.add_item(TeamsTeamButton(int(i / 4), game['homeTeam']))
                i += 2
        else:
            for game_id, game in self.lineup_provider.get_coming_games():
                self.add_item(TeamsGameButton(int(i / 4), game['homeTeam'], game['awayTeam']))
                i += 1
        self.add_item(LineupButton(int((i - 1) / 4) + 1))

    def get_team_info(self, team):
        message = self.lineup_provider.formatted_team_players(team)[0]

        return message, TeamView(team, self.lineup_provider, self.user_id)

    def get_game_info(self, home_team, away_team):
        message = f"{away_team} at {home_team}"

        return message, GameView(home_team, away_team, self.lineup_provider, self.user_id)


class GameTeamButton(discord.ui.Button['GameTeam']):
    def __init__(self, team):
        super().__init__(style=discord.ButtonStyle.primary, label=team, row=1)
        self.team = team

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: GameView = self.view
        content, new_view = view.get_team_info(self.team)

        await interaction.response.edit_message(content=content, view=new_view)


class GameView(FantasyView):
    def __init__(self, home_team, away_team, lineup_provider, user_id):
        super().__init__(lineup_provider, user_id)

        self.add_item(GameTeamButton(away_team))
        self.add_item(GameTeamButton(home_team))
        self.add_item(LineupButton(2))

    def get_team_info(self, team):
        message = self.lineup_provider.formatted_team_players(team)[0]

        return message, TeamView(team, self.lineup_provider, self.user_id)


class TeamPlayerButton(discord.ui.Button['TeamPlayer']):
    def __init__(self, row, player_idx, player_name):
        super().__init__(style=discord.ButtonStyle.primary, label=f"{player_name}", row=row)
        self.player_idx = player_idx

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TeamView = self.view
        content, new_view = view.get_player_info(self.player_idx)

        await interaction.response.edit_message(content=content, view=new_view)


class TeamTeamsButton(discord.ui.Button['TeamTeams']):
    def __init__(self, row):
        super().__init__(style=discord.ButtonStyle.success, label='Teams', row=row)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TeamView = self.view
        content, new_view = view.back_to_teams()

        await interaction.response.edit_message(content=content, view=new_view)


class TeamView(FantasyView):
    def __init__(self, team, lineup_provider, user_id):
        super().__init__(lineup_provider, user_id)
        self.team = team

        player_ids = self.lineup_provider.team_to_players[team]
        for i in range(0, len(player_ids)):
            player = self.lineup_provider.players[player_ids[i]]
            self.add_item(TeamPlayerButton(int(i / 5), player['index'], player['full_name']))

        last_row = int(len(player_ids) / 5) + 1
        self.add_item(LineupButton(last_row))
        self.add_item(TeamTeamsButton(last_row))

    def get_player_info(self, player_idx):
        message = self.lineup_provider.detailed_player_by_id(self.lineup_provider.player_ids[player_idx - 1],
                                                             self.user_id)

        return message, PlayerView(player_idx, self.lineup_provider, self.user_id)

    def back_to_teams(self):
        return self.lineup_provider.formatted_schedule, TeamsView(self.lineup_provider, self.user_id)
