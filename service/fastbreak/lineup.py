import math

from provider.nba.nba_provider import NBA_PROVIDER
from provider.topshot.cadence.flow_collections import get_account_plays_with_lowest_serial
from provider.topshot.fb_provider import FB_PROVIDER
from provider.topshot.ts_provider import TS_PROVIDER
from repository.fb_lineups import get_lineups, upsert_lineup, submit_lineup
from repository.vgn_players import get_players
from repository.vgn_users import get_user_new
from service.fastbreak.fastbreak import FastBreak
from service.fastbreak.service import FastBreakService
from service.fastbreak.utils import build_fb_collections


class Lineup:
    def __init__(self, db_lineup, service: FastBreakService):
        self.user_id = db_lineup['user_id']
        self.username = db_lineup['topshot_username']
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
        self.is_submitted = db_lineup['is_ranked']
        self.serial = db_lineup['sum_serial']
        self.service = service

    @staticmethod
    def __cast_player_id(db_player_id):
        if db_player_id is not None and not math.isnan(float(db_player_id)):
            return db_player_id
        return None

    def formatted(self):
        message = self.service.formatted_schedule + "\n"

        message += "Your lineup for **{}**".format(self.game_date)
        if self.is_submitted:
            message += " is **SUBMITTED**.\n"
        else:
            message += ".\n"
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
            return f"Player **{self.service.players[player_id]['full_name']}** is already in the lineup."

        message = ""

        player_to_remove = self.player_ids[pos_idx]
        if player_to_remove is not None:
            message += f"Removed **{self.service.players[player_to_remove]['full_name']}**."
        self.player_ids[pos_idx] = player_id

        successful, _ = upsert_lineup(
            (self.user_id, self.game_date, self.player_ids[0], self.player_ids[1], self.player_ids[2],
             self.player_ids[3], self.player_ids[4], self.player_ids[5], self.player_ids[6], self.player_ids[7])
        )
        if successful:
            message += f"Added **{self.service.players[self.player_ids[pos_idx]]['full_name']}**"

            if self.is_submitted:
                self.is_submitted = False
                message += "\nClick 'Submit' to save your changes"
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
            message = f"Removed **{self.service.players[player_to_remove]['full_name']}**."
            if self.is_submitted:
                self.is_submitted = False
                message += "\nClick 'Submit' to save your changes"
            return message
        else:
            self.player_ids[pos_idx] = player_to_remove
            return "Failed to update lineup, please retry."

    async def submit(self):
        user, _ = get_user_new(self.user_id)
        if user is None:
            return "Failed to load user collection, please retry."
        plays = await get_account_plays_with_lowest_serial(user['flow_address'])
        collections, _ = build_fb_collections(TS_PROVIDER, plays, self.player_ids[0:5])
        serials = []
        serial_sum = 0

        for pid in self.player_ids[0:5]:
            if pid is None:
                serials.append(None)
            elif pid not in collections:
                return f"You don't have any moment of {self.service.players[pid]['full_name']}, please check lineup."
            else:
                serial_sum += collections[pid]['serial']
                serials.append(collections[pid]['serial'])

        successful, err = submit_lineup((
            self.user_id, user['topshot_username'], self.game_date,
            self.player_ids[0], serials[0],
            self.player_ids[1], serials[1], self.player_ids[2], serials[2],
            self.player_ids[3], serials[3], self.player_ids[4], serials[4],
            serial_sum
        ))
        if not successful:
            return f"Submission failed: {err}"

        self.is_submitted = True
        self.serial = serial_sum
        self.username = user['topshot_username']
        message = "You've submitted lineup using the following players:\n\n"
        for pid in self.player_ids[0:5]:
            if pid is None:
                continue
            message += f"🏀 **{self.service.players[pid]['full_name']}** " \
                       f"{collections[pid]['tier']}({collections[pid]['serial']})\n"
        message += f"\nTotal serial **{serial_sum}**"

        return message


class LineupService(FastBreakService):
    def __init__(self):
        super(LineupService, self).__init__()
        self.coming_game_date = ""
        self.team_to_opponent = {}
        self.team_to_players = {}
        self.player_to_team = {}
        self.lineups = {}
        self.formatted_teams = {}
        self.formatted_fb_schedule = ""
        self.reload()

    def __load_players(self):
        self.player_ids = []
        players_to_load = []

        for game_id, game in NBA_PROVIDER.get_games_on_date(self.coming_game_date).items():
            for team in [game['homeTeam'], game['awayTeam']]:
                self.team_to_opponent[team] = game['homeTeam'] if team == game['awayTeam'] else game['awayTeam']
                self.team_to_players[team] = []
                for player in NBA_PROVIDER.get_players_for_team(team):
                    if player in TS_PROVIDER.player_moments:  # only load players with TS moments
                        self.player_to_team[player] = team
                        players_to_load.append(player)

        loaded = get_players(players_to_load, [("full_name", "ASC")])
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
        FB_PROVIDER.reload()
        coming_game_date = FB_PROVIDER.get_coming_game_date()
        if self.coming_game_date != coming_game_date:
            self.coming_game_date = coming_game_date
            self.team_to_opponent = {}
            self.team_to_players = {}
            self.player_to_team = {}
            self.players = {}
            self.player_ids = []
            self.formatted_teams = {}
            self.lineups = {}

            fb_schedule = "**Schedule**\n\n"
            for d in FB_PROVIDER.fb_info:
                fb = FastBreak(FB_PROVIDER.fb_info[d])
                fb_schedule += f"**{d}**\n{fb.get_formatted()[2:-4]}\n"
            self.formatted_fb_schedule = fb_schedule

        self.fb = FastBreak(FB_PROVIDER.get_fb(self.coming_game_date))
        self.formatted_schedule = self.__formatted_schedule()
        self.__load_players()
        self.__load_lineups()

    def __create_lineup(self, user_id):
        self.lineups[user_id] = Lineup(
            {
                "user_id": user_id,
                "game_date": self.coming_game_date,
                "topshot_username": None,
                "player_1": None,
                "player_2": None,
                "player_3": None,
                "player_4": None,
                "player_5": None,
                "player_6": None,
                "player_7": None,
                "player_8": None,
                "is_ranked": False,
                "sum_serial": 0,
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
