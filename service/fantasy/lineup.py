import math

from provider.nba.nba_provider import NBA_PROVIDER
from repository.vgn_collections import get_collections
from repository.vgn_lineups import get_lineups, upsert_lineup, submit_lineup
from repository.vgn_players import get_players_stats
from utils import compute_vgn_score, truncate_message, compute_vgn_scores

SALARY_CAP = 165.00
SALARY_GROUPS = [5, 10, 20, 30, 45]


class LineupProvider:
    def __init__(self):
        self.coming_game_date = ""
        self.team_to_opponent = {}
        self.team_to_players = {}
        self.player_to_team = {}
        self.players = {}
        self.player_ids = []
        self.lineups = {}
        self.collections = {}
        self.formatted_schedule = ""
        self.formatted_all_players = ""
        self.salary_pages = {
            45: 1,
            30: 1,
            20: 1,
            10: 1,
            5: 1,
        }
        self.reload()

    def __load_players(self):
        self.player_ids = []
        players_to_load = []

        for game_id, game in NBA_PROVIDER.get_games_on_date(self.coming_game_date).items():
            for team in [game['homeTeam'], game['awayTeam']]:
                self.team_to_opponent[team] = game['homeTeam'] if team == game['awayTeam'] else game['awayTeam']
                self.team_to_players[team] = []
                for player in NBA_PROVIDER.get_players_for_team(team):
                    self.player_to_team[player] = team
                    players_to_load.append(player)

        loaded = get_players_stats(players_to_load, [("current_salary", "DESC")])
        group = 0
        i = len(loaded) - 1
        while i >= 0:
            if loaded[i]['current_salary'] / 100.0 >= float(SALARY_GROUPS[group]):
                self.salary_pages[SALARY_GROUPS[group]] = int(i / 10) + 1
                i += 1
                if group == 4:
                    break
                group += 1
            i -= 1

        index = 0
        for player in loaded:
            player_id = player['id']
            index += 1

            self.players[player_id] = player
            self.players[player_id]['index'] = index
            self.players[player_id]['formatted'], self.players[player_id]['score'] = self.formatted_player(player, None)
            self.player_ids.append(player_id)

            self.team_to_players[self.player_to_team[player_id]].append(player_id)

    def __load_lineups(self):
        loaded = get_lineups(self.coming_game_date)
        for lineup in loaded:
            self.lineups[lineup['user_id']] = Lineup(lineup, self)

        if len(self.lineups) > 0:
            self.collections = get_collections(self.lineups.keys(), self.players.keys())

    def reload(self):
        coming_game_date = NBA_PROVIDER.get_coming_game_date()
        if self.coming_game_date != coming_game_date:
            self.team_to_opponent = {}
            self.team_to_players = {}
            self.player_to_team = {}
            self.players = {}
            self.player_ids = []
            self.lineups = {}

            self.coming_game_date = coming_game_date
            self.formatted_schedule = self.__formatted_schedule()
            self.__load_players()
            self.formatted_all_players = self.__formatted_all_players()

        self.__load_lineups()

    def __create_lineup(self, user_id):
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
                "submitted": False
            },
            self
        )

    def get_or_create_lineup(self, user_id):
        if user_id not in self.lineups:
            self.__create_lineup(user_id)

        return self.lineups[user_id]

    def load_user_collection(self, user_id):
        collection = get_collections([user_id], self.player_ids)

        if collection is not None:
            self.collections[user_id] = collection[user_id]

    def get_user_collection(self, user_id):
        if user_id not in self.collections:
            self.load_user_collection(user_id)

        return self.collections.get(user_id)

    def get_opponent(self, player_id):
        return self.team_to_opponent[self.player_to_team[player_id]]

    @staticmethod
    def formatted_injury(player_name):
        injury = NBA_PROVIDER.get_player_injury(player_name)
        if injury is None:
            return ""
        return f"**({injury})**"

    def formatted_player(self, player, collection):
        score = compute_vgn_score(player, collection)
        return \
            "***{}.*** **{} +{:.2f}v {}** vs *{}* **${:.2f}m** {}\n" \
            "{:.2f}p {:.2f}r {:.2f}a {:.2f}s {:.2f}b\n".format(
                player['index'],
                player['full_name'],
                score,
                self.player_to_team[player['id']],
                self.get_opponent(player['id']),
                player['current_salary'] / 100,
                self.formatted_injury(player['full_name']),
                player['points_recent'],
                player['defensive_rebounds_recent'] + player['offensive_rebounds_recent'],
                player['assists_recent'],
                player['steals_recent'],
                player['blocks_recent']
            ), \
            score

    def __formatted_all_players(self):
        messages = []
        message = ""

        for player_id in self.players:
            new_message = "***{}.*** *{}* {} ${:.2f}m\n".format(
                self.players[player_id]['index'],
                self.player_to_team[self.players[player_id]['id']],
                self.players[player_id]['full_name'],
                self.players[player_id]['current_salary'] / 100,
            )
            message, _ = truncate_message(messages, message, new_message, 1950)

        if message != "":
            messages.append(message)

        return messages

    def formatted_10_players(self, page):
        start = (page - 1) * 10 + 1
        end = len(self.players) if page * 10 > len(self.players) else page * 10

        message = ""
        for player_id in self.player_ids[start - 1:end]:
            message += self.players[player_id]['formatted']
        return message

    def formatted_team_players(self, team):
        if team not in self.team_to_players:
            return ["{} is not playing on {}.".format(team, self.coming_game_date)]

        messages = []
        message = ""

        for player_id in self.team_to_players[team]:
            new_message = self.players[player_id]['formatted']
            message, _ = truncate_message(messages, message, new_message, 1950)

        if message != "":
            messages.append(message)

        return messages

    def detailed_player(self, player, collection):
        scores, total, bonus = compute_vgn_scores(player, collection)
        return \
            "**{}.** ***{} {}#{}*** *vs {}* **${:.2f}m** {}\n" \
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
                self.get_opponent(player['id']), player['current_salary'] / 100, self.formatted_injury(player['full_name']),
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

    def detailed_players(self, players, user_id):
        collection = self.get_user_collection(user_id)
        if collection is None:
            return ["Fail to load user collection."]

        messages = []
        message = ""

        for dbPlayer in players:
            player_id = dbPlayer['id']
            if player_id not in self.players:
                new_message = "Player **{}** is not playing the coming games.\n".format(dbPlayer['full_name'])
            else:
                new_message = self.detailed_player(self.players[player_id], collection.get(player_id))
            message, _ = truncate_message(messages, message, new_message, 1950)

        if message != "":
            messages.append(message)

        return messages

    def detailed_player_by_id(self, player_id, user_id):
        collection = self.get_user_collection(user_id)
        if collection is None:
            return "Fail to load user collection."
        return self.detailed_player(self.players[player_id], collection.get(player_id))

    def get_coming_games(self):
        return NBA_PROVIDER.get_games_on_date(self.coming_game_date).items()

    def __formatted_schedule(self):
        message = "🏀 ***{} GAMES***\n".format(self.coming_game_date)
        for game_id, game in self.get_coming_games():
            message += f"{game['awayTeam']} at {game['homeTeam']}\n"

        return message


class Lineup:
    def __init__(self, db_lineup, provider):
        self.user_id = db_lineup['user_id']
        self.game_date = db_lineup['game_date']
        self.player_ids = [
            self.__cast_player_id(db_lineup['captain_1']),
            self.__cast_player_id(db_lineup['starter_2']),
            self.__cast_player_id(db_lineup['starter_3']),
            self.__cast_player_id(db_lineup['starter_4']),
            self.__cast_player_id(db_lineup['starter_5']),
            self.__cast_player_id(db_lineup['bench_6']),
            self.__cast_player_id(db_lineup['bench_7']),
            self.__cast_player_id(db_lineup['bench_8']),
        ]
        self.submitted = db_lineup['submitted']
        self.provider = provider

    @staticmethod
    def __cast_player_id(db_player_id):
        if db_player_id is not None and not math.isnan(float(db_player_id)):
            return db_player_id
        return None

    def formatted(self):
        message = self.provider.formatted_schedule + "\n"

        message += "Your lineup for **{}** is {}.\n" \
            .format(self.game_date, "**submitted**" if self.submitted else "**NOT** submitted")
        message += "🏅 {}\n".format(self.formatted_lineup_player(0))
        message += "🏀 {}\n".format(self.formatted_lineup_player(1))
        message += "🏀 {}\n".format(self.formatted_lineup_player(2))
        message += "🏀 {}\n".format(self.formatted_lineup_player(3))
        message += "🏀 {}\n".format(self.formatted_lineup_player(4))
        message += "🎽 {}\n".format(self.formatted_lineup_player(5))
        message += "🎽 {}\n".format(self.formatted_lineup_player(6))
        message += "🎽 {}\n".format(self.formatted_lineup_player(7))

        total_salary = self.get_total_salary()
        message += "\nTotal salary ${:.2f}m, cap $165.00m, space ${:.2f}m".format(total_salary, SALARY_CAP - total_salary)
        return message

    def formatted_lineup_player(self, z_idx_pos):
        player_id = self.player_ids[z_idx_pos]

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

    def add_player_by_idx(self, player_idx, pos_idx):
        if player_idx < 1 or player_idx > len(self.provider.player_ids):
            return "Player index should be between [1, {}]".format(len(self.provider.player_ids))

        player_id = self.provider.player_ids[player_idx - 1]
        if player_id in self.player_ids:
            return "Player **{}. {}** is already in the lineup.".format(
                self.provider.players[player_id]['index'],
                self.provider.players[player_id]['full_name'],
            )

        message = ""

        player_to_remove = self.player_ids[pos_idx]
        if player_to_remove is not None:
            message += "Removed **{}. {}**. ".format(
                self.provider.players[player_to_remove]['index'],
                self.provider.players[player_to_remove]['full_name'],
            )
        self.player_ids[pos_idx] = player_id

        if self.submitted and self.get_total_salary() > SALARY_CAP:
            self.player_ids[pos_idx] = player_to_remove
            return "Total salary exceeds cap, please adjust lineup."

        successful, _ = upsert_lineup(
            (self.user_id, self.game_date, self.player_ids[0], self.player_ids[1], self.player_ids[2],
             self.player_ids[3], self.player_ids[4], self.player_ids[5], self.player_ids[6], self.player_ids[7])
        )
        if successful:
            message += "Added **{}. {}** to {}. ".format(
                self.provider.players[self.player_ids[pos_idx]]['index'],
                self.provider.players[self.player_ids[pos_idx]]['full_name'],
                "🏅 Captain" if pos_idx == 0 else "🏀 Starter" if pos_idx < 5 else "🎽 Bench"
            )

            return message
        else:
            self.player_ids[pos_idx] = player_to_remove
            return "Failed to update lineup, please retry."

    def remove_player(self, pos_idx):
        if self.player_ids[pos_idx] is None:
            return "No player at this position."

        player_to_remove = self.player_ids[pos_idx]
        self.player_ids[pos_idx] = None

        successful, _ = upsert_lineup(
            (self.user_id, self.game_date, self.player_ids[0], self.player_ids[1], self.player_ids[2],
             self.player_ids[3], self.player_ids[4], self.player_ids[5], self.player_ids[6], self.player_ids[7])
        )

        if successful:
            return "Removed **{}. {}**. ".format(
                self.provider.players[player_to_remove]['index'],
                self.provider.players[player_to_remove]['full_name'],
            )
        else:
            self.player_ids[pos_idx] = player_to_remove
            return "Failed to update lineup, please retry."

    def swap_players(self, pos_idx_1, pos_idx_2):
        if self.player_ids[pos_idx_1] is None and self.player_ids[pos_idx_2] is None:
            return "Swapped."

        tmp = self.player_ids[pos_idx_1]
        self.player_ids[pos_idx_1] = self.player_ids[pos_idx_2]
        self.player_ids[pos_idx_2] = tmp

        successful, _ = upsert_lineup(
            (self.user_id, self.game_date, self.player_ids[0], self.player_ids[1], self.player_ids[2],
             self.player_ids[3], self.player_ids[4], self.player_ids[5], self.player_ids[6], self.player_ids[7])
        )

        if successful:
            return "Swapped."
        else:
            self.player_ids[pos_idx_2] = self.player_ids[pos_idx_1]
            self.player_ids[pos_idx_1] = tmp
            return "Failed to update lineup, please retry."

    def submit(self):
        if None in self.player_ids:
            return "Still have {} unfilled positions"\
                .format(len([i for i in range(0, 8) if self.player_ids[i] is None]))

        if self.get_total_salary() > SALARY_CAP:
            return self.formatted() + "\nTotal salary exceeds cap, please adjust lineup."

        successful, _ = submit_lineup(self.user_id, self.game_date)
        if successful:
            self.submitted = True
            return self.formatted() + "\nSubmitted."
        else:
            return self.formatted() + "\nFailed to update lineup, please retry."

    def get_total_salary(self):
        total_salary = 0
        for player_id in self.player_ids:
            if player_id is not None:
                player = self.provider.players[player_id]
                total_salary += player['current_salary'] / 100
        return total_salary


LINEUP_PROVIDER = LineupProvider()
