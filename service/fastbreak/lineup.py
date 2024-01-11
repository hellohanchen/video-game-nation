import math

from provider.nba.nba_provider import NBA_PROVIDER
from provider.topshot.fb_provider import FB_PROVIDER
from repository.fb_lineups import get_lineups, upsert_lineup
from repository.vgn_players import get_players_stats
from service.fastbreak.fastbreak import FastBreak
from service.fastbreak.service import FastBreakService


class Lineup:
    def __init__(self, db_lineup, service: FastBreakService):
        self.user_id = db_lineup['user_id']
        self.game_date = db_lineup['game_date']
        self.player_ids: [int] = [
            self.__cast_player_id(db_lineup['player_1']),
            self.__cast_player_id(db_lineup['player_2']),
            self.__cast_player_id(db_lineup['player_3']),
            self.__cast_player_id(db_lineup['player_4']),
            self.__cast_player_id(db_lineup['player_5']),
            self.__cast_player_id(db_lineup['player_6']),
            self.__cast_player_id(db_lineup['player_7']),
            self.__cast_player_id(db_lineup['player_8']),
        ]
        self.service = service

    @staticmethod
    def __cast_player_id(db_player_id):
        if db_player_id is not None and not math.isnan(float(db_player_id)):
            return db_player_id
        return None

    def formatted(self):
        message = self.service.formatted_schedule + "\n"

        message += "Your lineup for **{}**.\n".format(self.game_date)
        for i in range(0, self.service.fb.count):
            message += "🏀 {}\n".format(self.formatted_lineup_player(i))

        return message

    def formatted_lineup_player(self, pos_idx):
        player_id = self.player_ids[pos_idx]

        if player_id is None:
            return "---"
        else:
            return self.service.players[player_id]['formatted']

    def add_player_by_idx(self, player_idx, pos_idx):
        if pos_idx < 0 or pos_idx > self.service.fb.count:
            return "Player index should be between [0, {}]".format(self.service.fb.count - 1)
        if player_idx < 1 or player_idx > len(self.service.player_ids):
            return "Player index should be between [1, {}]".format(len(self.service.player_ids))

        player_id = self.service.player_ids[player_idx - 1]
        if player_id in self.player_ids:
            return "Player **{}. {}** is already in the lineup.".format(
                self.service.players[player_id]['index'],
                self.service.players[player_id]['full_name'],
            )

        message = ""

        player_to_remove = self.player_ids[pos_idx]
        if player_to_remove is not None:
            message += "Removed **{}. {}**. ".format(
                self.service.players[player_to_remove]['index'],
                self.service.players[player_to_remove]['full_name'],
            )
        self.player_ids[pos_idx] = player_id

        successful, _ = upsert_lineup(
            (self.user_id, self.game_date, self.player_ids[0], self.player_ids[1], self.player_ids[2],
             self.player_ids[3], self.player_ids[4], self.player_ids[5], self.player_ids[6], self.player_ids[7])
        )
        if successful:
            message += "Added **{}**".format(self.service.players[self.player_ids[pos_idx]]['full_name'])

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
                self.service.players[player_to_remove]['index'],
                self.service.players[player_to_remove]['full_name'],
            )
        else:
            self.player_ids[pos_idx] = player_to_remove
            return "Failed to update lineup, please retry."

    def is_valid(self):
        count = 0
        for i in range(0, self.service.fb.count):
            if self.player_ids[i] is not None:
                count += 1

        return count == self.service.fb.count


class LineupService(FastBreakService):
    def __init__(self):
        super(LineupService, self).__init__()
        self.coming_game_date = ""
        self.team_to_opponent = {}
        self.team_to_players = {}
        self.player_to_team = {}
        self.lineups = {}
        self.formatted_teams = {}
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

        loaded = get_players_stats(players_to_load, [("full_name", "ASC")])
        index = 0
        for player in loaded:
            player_id = player['id']
            index += 1

            self.players[player_id] = player
            self.players[player_id]['index'] = index
            self.players[player_id]['formatted'] = self.formatted_player(player)
            self.player_ids.append(player_id)

            self.team_to_players[self.player_to_team[player_id]].append(player_id)

        for team in self.team_to_players:
            message = ""
            for player_id in self.team_to_players[team]:
                message += self.players[player_id]['formatted'] + "\n"
            self.formatted_teams[team] = message

    def __load_lineups(self):
        loaded = get_lineups(self.coming_game_date)
        for lineup in loaded:
            self.lineups[lineup['user_id']] = Lineup(lineup, self)

    def reload(self):
        coming_game_date = NBA_PROVIDER.get_coming_game_date()
        if self.coming_game_date != coming_game_date:
            self.coming_game_date = coming_game_date
            self.team_to_opponent = {}
            self.team_to_players = {}
            self.player_to_team = {}
            self.players = {}
            self.player_ids = []
            self.formatted_teams = {}
            self.lineups = {}

        FB_PROVIDER.reload()
        self.fb = FastBreak(FB_PROVIDER.get_fb(self.coming_game_date))
        self.formatted_schedule = self.__formatted_schedule()
        self.__load_players()
        self.__load_lineups()

    def __create_lineup(self, user_id):
        self.lineups[user_id] = Lineup(
            {
                "user_id": user_id,
                "game_date": self.coming_game_date,
                "player_1": None,
                "player_2": None,
                "player_3": None,
                "player_4": None,
                "player_5": None,
                "player_6": None,
                "player_7": None,
                "player_8": None,
            },
            self
        )

    def get_or_create_lineup(self, user_id) -> Lineup:
        if user_id not in self.lineups:
            self.__create_lineup(user_id)

        return self.lineups[user_id]

    def get_opponent(self, player_id):
        return self.team_to_opponent[self.player_to_team[player_id]]

    def formatted_player(self, player):
        return \
            "**{} {}** vs *{}*".format(
                player['full_name'],
                self.player_to_team[player['id']],
                self.get_opponent(player['id']),
            )

    def formatted_team_players(self, team):
        if team not in self.formatted_teams:
            return ["{} is not playing on {}.".format(team, self.coming_game_date)]
        return self.formatted_teams[team]

    def get_coming_games(self):
        return NBA_PROVIDER.get_games_on_date(self.coming_game_date).items()

    def __formatted_schedule(self):
        message = "🏀 ***{} GAMES***\n".format(self.coming_game_date)
        if self.fb is not None:
            message += self.fb.get_formatted()

        for game_id, game in self.get_coming_games():
            message += f"{game['awayTeam']} at {game['homeTeam']}\n"

        return message


LINEUP_SERVICE = LineupService()
