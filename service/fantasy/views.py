from typing import Optional, List

import discord

import utils
from provider.topshot.cadence.flow_collections import get_account_plays
from repository.vgn_collections import upsert_collection as repo_upsert_collection
from repository.vgn_lineups import get_weekly_score
from repository.vgn_users import get_user
from service.fantasy.lineup import PAGE_SIZE, LINEUP_SIZE, LineupProvider, Lineup
from service.fantasy.ranking import RANK_PROVIDER, RankingProvider


class FantasyView(discord.ui.View):
    def __init__(self, lineup_provider: LineupProvider, user_id: int):
        super().__init__()
        self.lineup_provider: LineupProvider = lineup_provider
        self.user_id: int = user_id

    def back_to_lineup(self) -> [str, discord.ui.View]:
        message = self.lineup_provider.get_or_create_lineup(self.user_id).formatted()

        return message, LineupView(self.lineup_provider, self.user_id)


class LineupButton(discord.ui.Button[FantasyView]):
    def __init__(self, row: int):
        super().__init__(style=discord.ButtonStyle.success, label="My lineup", row=row)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        message, new_view = self.view.back_to_lineup()

        await interaction.response.edit_message(content=message, view=new_view)


class MainPage(discord.ui.View):
    def __init__(self, lineup_provider: LineupProvider, rank_provider: RankingProvider):
        super().__init__()
        self.add_item(MainStartButton())
        self.lineup_provider: LineupProvider = lineup_provider
        self.rank_provider: RankingProvider = rank_provider

    def launch_fantasy(self, user_id: int) -> [str, discord.ui.View]:
        if self.rank_provider.status != "IN_GAME":
            message = self.lineup_provider.get_or_create_lineup(user_id).formatted()
        else:
            message = self.rank_provider.formatted_user_score(user_id)[0]

        return message, LineupView(self.lineup_provider, user_id)


class MainStartButton(discord.ui.Button[MainPage]):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="GO!", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        message, new_view = self.view.launch_fantasy(interaction.user.id)

        await interaction.response.send_message(content=message, view=new_view, ephemeral=True, delete_after=600.0)


class LineupView(FantasyView):
    def __init__(self, lineup_provider: LineupProvider, user_id: int):
        super().__init__(lineup_provider, user_id)
        self.add_item(LineupPlayersButton())
        self.add_item(LineupTeamsButton())
        self.add_item(LineupRemoveButton())
        self.add_item(LineupSwapButton())
        self.add_item(LineupSubmitButton())
        self.add_item(LineupButton(3))
        self.add_item(LineupScoreButton())
        self.add_item(LineupWeekScoreButton())
        self.lineup: Lineup = self.lineup_provider.get_or_create_lineup(self.user_id)

    def jump_to_players(self) -> [str, discord.ui.View]:
        message = self.lineup_provider.formatted_players_of_page(1)
        view = PageView(1, self.lineup_provider, self.user_id)

        return message, view

    def jump_to_teams(self) -> [str, discord.ui.View]:
        message = self.lineup_provider.formatted_schedule
        return message, TeamsView(self.lineup_provider, self.user_id)

    def submit_lineup(self) -> [bool, str, discord.ui.View]:
        successful, message = self.lineup.submit()

        return successful, message, self

    def remove_player(self) -> [str, discord.ui.View]:
        return self.lineup.formatted() + "\nRemove a player from your lineup", \
               RemoveView(self.lineup_provider, self.user_id)

    def swap_player(self) -> [str, discord.ui.View]:
        return self.lineup.formatted() + "\nSwap 2 players in your lineup", SwapView(self.lineup_provider, self.user_id)

    def check_score(self) -> [str, discord.ui.View]:
        return RANK_PROVIDER.formatted_user_score(self.user_id)[0], self

    def check_week_score(self) -> [str, discord.ui.View]:
        if RANK_PROVIDER.current_game_date == "":
            date = self.lineup_provider.coming_game_date
        else:
            date = RANK_PROVIDER.current_game_date

        dates = utils.get_the_past_week_from_sunday(date)
        score = get_weekly_score(dates, self.user_id)
        return f"Total score {dates[0]}~{dates[-1]}: **{score}**", self

    async def reload_collection(self) -> [str, discord.ui.View, bool]:
        vgn_user = get_user(self.user_id)

        if vgn_user is None:
            return "Account not found, contact admin for registration.", self, False

        user_id = vgn_user[0]
        flow_address = vgn_user[2]

        try:
            plays = await get_account_plays(flow_address)
        except:
            return "Failed to fetch collection, try again or contact admin.", self, False

        try:
            message = repo_upsert_collection(user_id, plays)
        except:
            return "Failed to update database, try again or contact admin.", self, False

        self.lineup_provider.load_user_collection(self.user_id)
        return message, self, True


class LineupPlayersButton(discord.ui.Button[LineupView]):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="Players", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        message, new_view = self.view.jump_to_players()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupTeamsButton(discord.ui.Button[LineupView]):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="Teams", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        message, new_view = self.view.jump_to_teams()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupSubmitButton(discord.ui.Button[LineupView]):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="Submit", row=2)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LineupView = self.view

        await interaction.response.edit_message(content=f"Submission in progress...\n", view=view)
        followup = interaction.followup
        try:
            is_submitted, message, new_view = view.submit_lineup()

            if is_submitted:
                content = f"Your submission is successfully submitted, please review snapshot\n\n{message}\n"
                msg, _, is_reloaded = await view.reload_collection()
                if is_reloaded:
                    await followup.send(
                        content=content + f"Your collection is also updated successfully: {msg}", ephemeral=True)
                else:
                    await followup.send(content=content + f"Your collection is not updated: {msg}", ephemeral=True)
            else:
                await followup.send(message, ephemeral=True)
        except Exception as err:
            await followup.send(content=f"Submission failed, please retry or contact admin: {err}", ephemeral=True)


class LineupRemoveButton(discord.ui.Button[LineupView]):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, label="Remove", row=2)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        message, new_view = self.view.remove_player()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupSwapButton(discord.ui.Button[LineupView]):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, label="Swap", row=2)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        message, new_view = self.view.swap_player()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupScoreButton(discord.ui.Button[LineupView]):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="My Score", row=3)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        message, new_view = self.view.check_score()

        await interaction.response.edit_message(content=message, view=new_view)


class LineupWeekScoreButton(discord.ui.Button[LineupView]):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="My Week", row=3)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        message, new_view = self.view.check_week_score()

        await interaction.response.edit_message(content=message, view=new_view)


class RemoveView(FantasyView):
    def __init__(self, lineup_provider: LineupProvider, user_id: int):
        super().__init__(lineup_provider, user_id)
        self.lineup = self.lineup_provider.get_or_create_lineup(self.user_id)

        player_ids = self.lineup.player_ids
        i = 0
        for j in range(0, LINEUP_SIZE):
            if player_ids[j] is not None:
                self.add_item(RemovePlayerButton(
                    int(i / 4),
                    self.lineup_provider.players[player_ids[j]]['full_name'],
                    j))
                i += 1
        self.add_item(LineupButton(int((i + 3) / 4) + 1))

    # This method update current player info
    def remove_player(self, pos: int) -> [str, discord.ui.View]:
        return self.lineup.formatted() + "\n" + self.lineup.remove_player(pos), self


class RemovePlayerButton(discord.ui.Button['RemoveView']):
    def __init__(self, row: int, player_name: str, pos: int):
        super().__init__(style=discord.ButtonStyle.primary, label=player_name, row=row)
        self.pos = pos

    # This function is called whenever this particular button is pressed
    # This is part of the "meat" of the game logic
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        self.style = discord.ButtonStyle.secondary
        self.disabled = True
        message, new_view = self.view.remove_player(self.pos)

        await interaction.response.edit_message(content=message, view=new_view)


class SwapView(FantasyView):
    def __init__(self, lineup_provider: LineupProvider, user_id: int):
        super().__init__(lineup_provider, user_id)
        self.lineup = self.lineup_provider.get_or_create_lineup(self.user_id)

        player_ids = self.lineup.player_ids
        i = 0
        for j in range(0, LINEUP_SIZE):
            if player_ids[j] is not None:
                self.add_item(SwapPlayerButton(int(i / 4), self.lineup_provider.players[player_ids[j]]['full_name'], j))
                i += 1
        self.add_item(LineupButton(int((i + 3) / 4) + 1))
        self.selected: Optional[int] = None

    # This method update current player info
    def swap_player(self, pos: int) -> [str, discord.ui.View]:
        if self.selected is None:
            message = "Select another player."
            view = self
            self.selected = pos
        else:
            message = self.lineup.swap_players(self.selected, pos)
            view = LineupView(self.lineup_provider, self.user_id)

        return self.lineup.formatted() + "\n" + message, view


class SwapPlayerButton(discord.ui.Button[SwapView]):
    def __init__(self, row: int, player_name: str, pos: int):
        super().__init__(style=discord.ButtonStyle.primary, label=player_name, row=row)
        self.pos = pos

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        self.style = discord.ButtonStyle.secondary
        self.disabled = True
        message, new_view = self.view.swap_player(self.pos)

        await interaction.response.edit_message(content=message, view=new_view)


class PlayerView(FantasyView):
    def __init__(self, player_idx: int, lineup_provider: LineupProvider, user_id: int):
        super().__init__(lineup_provider, user_id)
        self.current_player: int = player_idx
        self.add_item(PlayerAddButton())
        self.add_item(PlayerToggleButton(0))
        self.add_item(PlayerToggleButton(-1))
        self.add_item(PlayerToggleButton(1))
        self.add_item(LineupButton(3))
        self.add_item(PlayerPlayersButton())
        self.add_item(PlayerTeamButton())

    # This method update current player info
    def get_player_info(self) -> str:
        if self.current_player > len(self.lineup_provider.player_ids):
            self.current_player = len(self.lineup_provider.player_ids)
        elif self.current_player < 1:
            self.current_player = 1

        player_id = self.lineup_provider.player_ids[self.current_player - 1]
        return self.lineup_provider.detailed_player_by_id(player_id, self.user_id)

    def add_to_lineup(self) -> [str, discord.ui.View]:
        lineup = self.lineup_provider.get_or_create_lineup(self.user_id)
        if lineup is None:
            return "Fail to load lineup.", self

        pos = LINEUP_SIZE
        for i in range(0, LINEUP_SIZE):
            if lineup.player_ids[i] is None:
                pos = i
                break

        if pos == LINEUP_SIZE:
            return "Lineup is already full, please remove a player.", self

        return lineup.add_player_by_idx(self.current_player, pos), self

    def back_to_players(self) -> [str, discord.ui.View]:
        page = int((self.current_player - 1) / PAGE_SIZE) + 1

        return self.lineup_provider.formatted_players_of_page(page), \
               PageView(page, self.lineup_provider, self.user_id)

    def back_to_team(self) -> [str, discord.ui.View]:
        player_id = self.lineup_provider.player_ids[self.current_player - 1]
        team = self.lineup_provider.player_to_team[player_id]

        return self.lineup_provider.get_formatted_team(team), \
            TeamView(team, self.lineup_provider, self.user_id)


# Defines a custom button that contains the logic of checking player information
class PlayerToggleButton(discord.ui.Button[PlayerView]):
    def __init__(self, offset: int):
        super().__init__(
            style=discord.ButtonStyle.secondary if offset != 0 else discord.ButtonStyle.primary,
            row=2 if offset != 0 else 1)
        self.offset: int = offset
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


class PlayerAddButton(discord.ui.Button[PlayerView]):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="Add", row=1)

    # This function is called whenever this particular button is pressed
    # This is part of the "meat" of the game logic
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        message, new_view = self.view.add_to_lineup()

        await interaction.response.edit_message(content=message, view=new_view)


class PlayerPlayersButton(discord.ui.Button[PlayerView]):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="Players", row=3)

    # This function is called whenever this particular button is pressed
    # This is part of the "meat" of the game logic
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        message, new_view = self.view.back_to_players()

        await interaction.response.edit_message(content=message, view=new_view)


class PlayerTeamButton(discord.ui.Button[PlayerView]):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="Team", row=3)

    # This function is called whenever this particular button is pressed
    # This is part of the "meat" of the game logic
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        message, new_view = self.view.back_to_team()

        await interaction.response.edit_message(content=message, view=new_view)
        
        
class PageView(FantasyView):
    def __init__(self, page: int, lineup_provider: LineupProvider, user_id: int):
        super().__init__(lineup_provider, user_id)
        self.current_page: int = page
        self.player_buttons: List[discord.ui.Button] = []
        self.__refresh_player_buttons()

        self.add_item(PageSalaryButton(45))
        self.add_item(PageSalaryButton(30))
        self.add_item(PageSalaryButton(20))
        self.add_item(PageSalaryButton(10))
        self.add_item(PageSalaryButton(5))
        self.add_item(LineupButton(4))
        self.add_item(PageToggleButton(-1))
        self.add_item(PageToggleButton(1))

    def __refresh_player_buttons(self):
        for button in self.player_buttons:
            self.remove_item(button)
        self.player_buttons = []
        idxes = self.lineup_provider.get_player_idxes_of_page(self.current_page)
        for i in idxes:
            button = PagePlayerButton(i)
            self.add_item(button)
            self.player_buttons.append(button)

    def jump_to(self, page: int) -> [str, discord.ui.View]:
        max_page = int((len(self.lineup_provider.player_ids) + PAGE_SIZE - 1) / PAGE_SIZE)
        if page < 1:
            self.current_page = 1
        elif page > max_page:
            self.current_page = max_page
        else:
            self.current_page = page

        self.__refresh_player_buttons()
        message = self.lineup_provider.formatted_players_of_page(self.current_page)
        return message, self

    def get_page_of_salary(self, salary) -> int:
        return self.lineup_provider.salary_pages[salary]

    def get_player(self, player_idx) -> [str, discord.ui.View]:
        if player_idx > len(self.lineup_provider.player_ids):
            player_idx = len(self.lineup_provider.player_ids)

        message = self.lineup_provider.detailed_player_by_id(
            self.lineup_provider.player_ids[player_idx - 1], self.user_id)

        return message, PlayerView(player_idx, self.lineup_provider, self.user_id)


class PagePlayerButton(discord.ui.Button[PageView]):
    def __init__(self, player_idx: int):
        super().__init__(style=discord.ButtonStyle.primary,
                         label=f'{player_idx}',
                         row=min(2, int(((player_idx - 1) % 10) / 3)))
        self.player_idx = player_idx

    # This function is called whenever this particular button is pressed
    # This is part of the "meat" of the game logic
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        message, new_view = self.view.get_player(self.player_idx)

        await interaction.response.edit_message(content=message, view=new_view)


class PageToggleButton(discord.ui.Button[PageView]):
    def __init__(self, offset: int):
        super().__init__(style=discord.ButtonStyle.secondary, row=4)
        self.offset = offset
        if offset > 0:
            self.label = "Next"
        elif offset < 0:
            self.label = "Prev"

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: PageView = self.view
        content, new_view = view.jump_to(view.current_page + self.offset)

        await interaction.response.edit_message(content=content, view=new_view)


class PageSalaryButton(discord.ui.Button[PageView]):
    def __init__(self, salary: int):
        super().__init__(style=discord.ButtonStyle.secondary, row=3, label="${}".format(salary))
        self.salary: int = salary

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: PageView = self.view
        content, new_view = view.jump_to(view.get_page_of_salary(self.salary))

        await interaction.response.edit_message(content=content, view=new_view)


class TeamsView(FantasyView):
    def __init__(self, lineup_provider: LineupProvider, user_id: int):
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

    def get_team(self, team: str) -> [str, 'TeamView']:
        return self.lineup_provider.get_formatted_team(team), TeamView(team, self.lineup_provider, self.user_id)

    def get_game(self, home_team: str, away_team: str) -> [str, 'GameView']:
        return f"{away_team} at {home_team}", GameView(home_team, away_team, self.lineup_provider, self.user_id)


class TeamsTeamButton(discord.ui.Button[TeamsView]):
    def __init__(self, row: int, team: str):
        super().__init__(style=discord.ButtonStyle.primary, label=team, row=row)
        self.team: str = team

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TeamsView = self.view
        content, new_view = view.get_team(self.team)

        await interaction.response.edit_message(content=content, view=new_view)


class TeamsGameButton(discord.ui.Button['TeamsGame']):
    def __init__(self, row, home_team, away_team):
        super().__init__(style=discord.ButtonStyle.primary, label=f"{away_team}@{home_team}", row=row)
        self.home_team = home_team
        self.away_team = away_team

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TeamsView = self.view
        content, new_view = view.get_game(self.home_team, self.away_team)

        await interaction.response.edit_message(content=content, view=new_view)


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
        message = self.lineup_provider.get_formatted_team(team)

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

        last_row = min(int((len(player_ids) - 1) / 5) + 1, 4)
        self.add_item(LineupButton(last_row))
        self.add_item(TeamTeamsButton(last_row))

    def get_player_info(self, player_idx):
        message = self.lineup_provider.detailed_player_by_id(self.lineup_provider.player_ids[player_idx - 1],
                                                             self.user_id)

        return message, PlayerView(player_idx, self.lineup_provider, self.user_id)

    def back_to_teams(self):
        return self.lineup_provider.formatted_schedule, TeamsView(self.lineup_provider, self.user_id)
