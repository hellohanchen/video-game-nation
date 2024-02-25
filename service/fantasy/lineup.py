import math
from typing import List, Dict, Union, Optional

from provider.nba.nba_provider import NBA_PROVIDER
from repository.vgn_collections import get_collections
from repository.vgn_lineups import get_lineups, upsert_lineup, submit_lineup
from repository.vgn_players import get_players
from utils import compute_vgn_score, compute_vgn_scores

SALARY_CAP = 165.00
SALARY_GROUPS = [5, 10, 20, 30, 45]
PAGE_SIZE = 10
LINEUP_SIZE = 9


class LineupProvider:
    def __init__(self):
        self.coming_game_date: str = ""
        self.team_to_opponent: Dict[str, str] = {}
        self.team_to_players: Dict[str, List[int]] = {}
        self.formatted_teams: Dict[str, str] = {}

        self.player_to_team: Dict[int, str] = {}
        self.players: Dict[int, Dict[str, any]] = {}
        self.player_ids: List[int] = []

        self.lineups: Dict[int, Lineup] = {}
        self.collections: Dict[int, Dict[int, Dict[str, int]]] = {}

        self.formatted_schedule: str = ""
        self.salary_pages: Dict[int, int] = {
            45: 1,
            30: 1,
            20: 1,
            10: 1,
            5: 1,
        }
        self.reload()

    def __load_players(self):
        player_ids_to_load: List[int] = []

        for game_id, game in NBA_PROVIDER.get_games_on_date(self.coming_game_date).items():
            for team in [game['homeTeam'], game['awayTeam']]:
                self.team_to_opponent[team] = game['homeTeam'] if team == game['awayTeam'] else game['awayTeam']
                self.team_to_players[team] = []
                for player_id in NBA_PROVIDER.get_players_for_team(team):
                    self.player_to_team[player_id] = team
                    player_ids_to_load.append(player_id)

        players = get_players(player_ids_to_load, [("current_salary", "DESC")])
        group = 0
        i = len(players) - 1
        while i >= 0:
            if players[i]['current_salary'] / 100.0 >= float(SALARY_GROUPS[group]):
                self.salary_pages[SALARY_GROUPS[group]] = int(i / PAGE_SIZE) + 1
                i += 1
                if group == 4:
                    break
                group += 1
            i -= 1

        index = 0
        self.player_ids = []  # ensure players have indexes assigned
        for player in players:
            player_id = player['id']
            index += 1

            self.players[player_id] = player
            self.players[player_id]['index'] = index
            self.players[player_id]['formatted'], self.players[player_id]['score'] = self.__format_player(player, None)
            self.player_ids.append(player_id)

            self.team_to_players[self.player_to_team[player_id]].append(player_id)

        for team in self.team_to_players:
            self.formatted_teams[team] = self.__format_team(team)

    def __load_lineups_and_collections(self):
        lineups = get_lineups(self.coming_game_date)
        for lineup in lineups:
            self.lineups[lineup['user_id']] = Lineup(lineup, self)

        if len(self.lineups) > 0:
            self.collections = get_collections(self.lineups.keys(), self.players.keys())

    def reload(self):
        coming_game_date = NBA_PROVIDER.get_coming_game_date()
        if self.coming_game_date != coming_game_date:
            self.coming_game_date = coming_game_date
            self.team_to_opponent = {}
            self.team_to_players = {}
            self.formatted_teams = {}

            self.player_to_team = {}
            self.players = {}
            self.player_ids = []

            self.lineups = {}
            self.collections = {}

            self.formatted_schedule = self.__formatted_schedule()

        self.__load_players()
        self.__load_lineups_and_collections()

    def __create_lineup(self, user_id: int):
        self.lineups[user_id] = Lineup(
            {
                "user_id": user_id,
                "game_date": self.coming_game_date,
                "captain_1": None,
                "starter_2": None,
                "starter_3": None,
                "starter_4": None,
                "starter_5": None,
                "bench_6": None,
                "bench_7": None,
                "bench_8": None,
                "backup_9": None,
                "submitted": False
            },
            self
        )

    def get_or_create_lineup(self, user_id: int) -> 'Lineup':
        if user_id not in self.lineups:
            self.__create_lineup(user_id)

        return self.lineups[user_id]

    def load_user_collection(self, user_id: int):
        collection = get_collections([user_id], self.player_ids)

        if collection is not None:
            self.collections[user_id] = collection[user_id]

    def get_user_collection(self, user_id: int) -> Dict[int, Dict[str, int]]:
        if user_id not in self.collections:
            self.load_user_collection(user_id)

        return self.collections.get(user_id)

    def get_opponent(self, player_id: int) -> str:
        return self.team_to_opponent[self.player_to_team[player_id]]

    def __format_player(self, player: Dict[str, any], collection: Optional[Dict[str, int]]) -> [str, float]:
        score = compute_vgn_score(player, collection)
        return \
            "**{})** **{} +{:.2f}v {}** vs *{}* **${:.2f}m** **{}**\n" \
            "{:.1f}p {:.1f}r {:.1f}a {:.1f}s {:.1f}b\n".format(
                player['index'],
                player['full_name'],
                score,
                self.player_to_team[player['id']],
                self.get_opponent(player['id']),
                player['current_salary'] / 100,
                NBA_PROVIDER.get_player_injury(player['full_name']),
                player['points_recent'],
                player['defensive_rebounds_recent'] + player['offensive_rebounds_recent'],
                player['assists_recent'],
                player['steals_recent'],
                player['blocks_recent']
            ), \
            score

    def get_player_idxes_of_page(self, page: int) -> List[int]:
        start = (page - 1) * PAGE_SIZE + 1
        end = len(self.players) if page * PAGE_SIZE > len(self.players) else page * PAGE_SIZE

        return list(range(start, end + 1))

    def formatted_players_of_page(self, page: int) -> str:
        start_idx = (page - 1) * PAGE_SIZE + 1
        end_idx = len(self.players) if page * PAGE_SIZE > len(self.players) else page * PAGE_SIZE

        message = ""
        for player_id in self.player_ids[start_idx - 1:end_idx]:
            message += self.players[player_id]['formatted']
        return message

    def __format_team(self, team: str) -> str:
        message = ""
        for player_id in self.team_to_players[team]:
            player_msg = self.players[player_id]['formatted']
            parenthesis = player_msg.find(')')
            message += player_msg[parenthesis + 4:]
        return message

    def get_formatted_team(self, team: str) -> str:
        return self.formatted_teams.get(team, "{} is not playing on {}.".format(team, self.coming_game_date))

    def detailed_player(self, player: Dict[str, any], collection: Dict[str, int]) -> str:
        scores, total, bonus = compute_vgn_scores(player, collection)
        return \
            "**{}.** ***{} {}#{}*** *vs {}* **${:.2f}m** **{}**\n" \
            "**{:.2f}** points **{:.2f}v** (+{:.2f}) " \
            "bonus **{:.2f}v** (+{:.2f})\n" \
            "**{:.2f}** three-pointers **{:.2f}v** (+{:.2f})\n" \
            "**{:.2f}** defensive reb **{:.2f}v** (+{:.2f})\n" \
            "**{:.2f}** offensive reb **{:.2f}v** (+{:.2f})\n" \
            "**{:.2f}** assists **{:.2f}v** (+{:.2f})\n" \
            "**{:.2f}** steals **{:.2f}v** (+{:.2f})\n" \
            "**{:.2f}** blocks **{:.2f}v** (+{:.2f})\n" \
            "**{:.2f}** missed fgs **{:.2f}v** (+{:.2f})\n" \
            "**{:.2f}** missed fts **{:.2f}v** (+{:.2f})\n" \
            "**{:.2f}** turnovers **{:.2f}v** (+{:.2f})\n" \
            "**{:.2f}** fouls **{:.2f}v** (+{:.2f}) " \
            "foul-out **{:.2f}v**\n" \
            "**{:.2f}** win **{:.2f}v** (+{:.2f})\n" \
            "**{:.2f}** double-double **{:.2f}v**\n" \
            "**{:.2f}** triple-double **{:.2f}v**\n" \
            "**{:.2f}** quadruple-double **{:.2f}v**\n" \
            "**{:.2f}** five-double **{:.2f}v**\n" \
            "***Total: {:.2f}v (+{:.2f})***\n\n" \
            "".format(
                player['index'], player['full_name'], self.player_to_team[player['id']], player['jersey_number'],
                self.get_opponent(player['id']), player['current_salary'] / 100,
                NBA_PROVIDER.get_player_injury(player['full_name']),
                player['points'], scores['points']['score'], scores['points']['bonus'],
                scores['pointBonus']['score'], scores['pointBonus']['bonus'],
                player['threePointersMade'], scores['threePointersMade']['score'], scores['threePointersMade']['bonus'],
                player['defensive_rebounds_recent'], scores['reboundsDefensive']['score'],
                scores['reboundsDefensive']['bonus'],
                player['offensive_rebounds_recent'], scores['reboundsOffensive']['score'],
                scores['reboundsOffensive']['bonus'],
                player['assists'], scores['assists']['score'], scores['assists']['bonus'],
                player['steals'], scores['steals']['score'], scores['steals']['bonus'],
                player['blocks'], scores['blocks']['score'], scores['blocks']['bonus'],
                player['fieldGoalsMissed'], scores['fieldGoalsMissed']['score'], scores['fieldGoalsMissed']['bonus'],
                player['freeThrowsMissed'], scores['freeThrowsMissed']['score'], scores['freeThrowsMissed']['bonus'],
                player['turnovers'], scores['turnovers']['score'], scores['turnovers']['bonus'],
                player['foulsPersonal'], scores['foulsPersonal']['score'], scores['foulsPersonal']['bonus'],
                scores['foulOut']['score'],
                player['win'], scores['win']['score'], scores['win']['bonus'],
                player['doubleDouble'], scores['doubleDouble']['score'],
                player['tripleDouble'], scores['tripleDouble']['score'],
                player['quadrupleDouble'], scores['quadrupleDouble']['score'],
                player['fiveDouble'], scores['fiveDouble']['score'],
                total, bonus
            )

    def detailed_player_by_id(self, player_id: int, user_id: int):
        collection = self.get_user_collection(user_id)
        if collection is None:
            return "Fail to load user collection."
        return self.detailed_player(self.players[player_id], collection.get(player_id))

    def get_coming_games(self) -> List[Dict[str, str]]:
        return NBA_PROVIDER.get_games_on_date(self.coming_game_date).items()

    def __formatted_schedule(self) -> str:
        message = "🏀 ***{} GAMES***\n".format(self.coming_game_date)
        for _, game in self.get_coming_games():
            message += f"{game['awayTeam']} at {game['homeTeam']}\n"

        return message


class Lineup:
    def __init__(self, db_lineup: Dict[str, any], provider: LineupProvider):
        self.user_id: int = db_lineup['user_id']
        self.game_date: str = db_lineup['game_date']
        self.player_ids: List[Optional[int]] = [
            self.__cast_player_id(db_lineup['captain_1']),
            self.__cast_player_id(db_lineup['starter_2']),
            self.__cast_player_id(db_lineup['starter_3']),
            self.__cast_player_id(db_lineup['starter_4']),
            self.__cast_player_id(db_lineup['starter_5']),
            self.__cast_player_id(db_lineup['bench_6']),
            self.__cast_player_id(db_lineup['bench_7']),
            self.__cast_player_id(db_lineup['bench_8']),
            self.__cast_player_id(db_lineup['backup_9']),
        ]
        self.submitted: bool = db_lineup['submitted']
        self.provider: LineupProvider = provider

    @staticmethod
    def __cast_player_id(db_player_id) -> Optional[int]:
        if db_player_id is not None and not math.isnan(float(db_player_id)):
            return int(db_player_id)
        return None

    def formatted(self) -> str:
        message = self.provider.formatted_schedule + "\n"

        message += "Your lineup for **{}** is {}.\n" \
            .format(self.game_date, "**SUBMITTED**" if self.submitted else "**NOT** submitted")
        message += "🏅 {}\n".format(self.__format_player(0))
        message += "🏀 {}\n".format(self.__format_player(1))
        message += "🏀 {}\n".format(self.__format_player(2))
        message += "🏀 {}\n".format(self.__format_player(3))
        message += "🏀 {}\n".format(self.__format_player(4))
        message += "🎽 {}\n".format(self.__format_player(5))
        message += "🎽 {}\n".format(self.__format_player(6))
        message += "🎽 {}\n".format(self.__format_player(7))
        message += "🚩 {}\n".format(self.__format_player(8))

        total_salary = self.get_total_salary()
        message += "\nTotal salary ${:.2f}m, cap $165.00m, space ${:.2f}m".format(total_salary,
                                                                                  SALARY_CAP - total_salary)
        return message

    def __format_player(self, player_idx: int) -> str:
        player_id = self.player_ids[player_idx]

        if player_id is None:
            return "---"
        else:
            player = self.provider.players[player_id]
            return "**{}** ***+{:.2f}v {}*** vs *{}* **${:.2f}m**".format(
                player['full_name'],
                player['score'],
                self.provider.player_to_team[player_id],
                self.provider.get_opponent(player_id),
                player['current_salary'] / 100
            )

    def __upsert_lineup(self) -> bool:
        successful, _ = upsert_lineup(
            (self.user_id, self.game_date,
             self.player_ids[0], self.player_ids[1], self.player_ids[2], self.player_ids[3], self.player_ids[4],
             self.player_ids[5], self.player_ids[6], self.player_ids[7], self.player_ids[8])
        )
        return successful

    def add_player_by_idx(self, player_idx: int, pos: int) -> str:
        if player_idx < 1 or player_idx > len(self.provider.player_ids):
            return "Player index should be between [1, {}]".format(len(self.provider.player_ids))

        player_id = self.provider.player_ids[player_idx - 1]
        if player_id in self.player_ids:
            return "Player **{}. {}** is already in the lineup.".format(
                self.provider.players[player_id]['index'],
                self.provider.players[player_id]['full_name'],
            )

        message = ""

        player_to_remove = self.player_ids[pos]
        if player_to_remove is not None:
            message += "Removed **{}. {}**. ".format(
                self.provider.players[player_to_remove]['index'],
                self.provider.players[player_to_remove]['full_name'],
            )
        self.player_ids[pos] = player_id

        if self.submitted and self.get_total_salary() > SALARY_CAP:
            self.player_ids[pos] = player_to_remove
            return "Total salary exceeds cap, please adjust lineup."

        successful = self.__upsert_lineup()
        if successful:
            if pos == 0:
                logo = "🏅 Captain"
            elif pos < 5:
                logo = "🏀 Starter"
            elif pos < 8:
                logo = "🎽 Bench"
            else:
                logo = "🚩 Backup"

            message += "Added **{}. {}** to {}. ".format(
                self.provider.players[self.player_ids[pos]]['index'],
                self.provider.players[self.player_ids[pos]]['full_name'],
                logo,
            )

            return message
        else:
            self.player_ids[pos] = player_to_remove
            return "Failed to update lineup, please retry."

    def remove_player(self, pos: int) -> str:
        if self.player_ids[pos] is None:
            return "No player at this position."

        player_to_remove = self.player_ids[pos]
        self.player_ids[pos] = None

        successful = self.__upsert_lineup()
        if successful:
            return "Removed **{}. {}**. ".format(
                self.provider.players[player_to_remove]['index'],
                self.provider.players[player_to_remove]['full_name'],
            )
        else:
            self.player_ids[pos] = player_to_remove
            return "Failed to update lineup, please retry."

    def swap_players(self, pos_1: int, pos_2: int) -> str:
        if self.player_ids[pos_1] is None and self.player_ids[pos_2] is None:
            return "Swapped."

        tmp = self.player_ids[pos_1]
        self.player_ids[pos_1] = self.player_ids[pos_2]
        self.player_ids[pos_2] = tmp

        successful = self.__upsert_lineup()
        if successful:
            return "Swapped."
        else:
            self.player_ids[pos_2] = self.player_ids[pos_1]
            self.player_ids[pos_1] = tmp
            return "Failed to update lineup, please retry."

    def submit(self) -> [bool, str]:
        if None in self.player_ids[:LINEUP_SIZE - 1]:
            return False, "Still have {} unfilled positions" \
                .format(len([i for i in range(0, LINEUP_SIZE - 1) if self.player_ids[i] is None]))

        if self.get_total_salary() > SALARY_CAP:
            return False, self.formatted() + "\nTotal salary exceeds cap, please adjust lineup."

        successful, _ = submit_lineup(self.user_id, self.game_date)
        if successful:
            self.submitted = True
            return True, self.formatted() + "\nSubmitted."
        else:
            return False, self.formatted() + "\nFailed to update lineup, please retry."

    def get_total_salary(self) -> float:
        total_salary = 0
        for player_id in self.player_ids:
            if player_id is not None:
                player = self.provider.players[player_id]
                total_salary += player['current_salary'] / 100
        return total_salary


LINEUP_PROVIDER = LineupProvider()
