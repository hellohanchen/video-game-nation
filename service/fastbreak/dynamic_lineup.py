import asyncio
import datetime
import math

from nba_api.live.nba.endpoints import boxscore

from constants import TZ_PT
from provider.nba.nba_provider import NBAProvider, NBA_PROVIDER
from provider.topshot.cadence.flow_collections import get_account_plays_with_lowest_serial
from provider.topshot.fb_provider import FB_PROVIDER
from provider.topshot.ts_provider import TS_PROVIDER
from repository.fb_lineups import get_lineups, upsert_score, get_weekly_ranks, get_user_results, upsert_lineup, \
    submit_lineup
from repository.vgn_players import get_empty_players_stats, get_players
from repository.vgn_users import get_user_new
from service.fastbreak.fastbreak import FastBreak
from service.fastbreak.service import FastBreakService
from service.fastbreak.utils import build_fb_collections
from utils import get_game_info
from vgnlog.channel_logger import ADMIN_LOGGER


class Lineup:
    def __init__(self, db_lineup, service):
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
        game_id = self.service.player_to_game[player_id]
        if self.service.active_game_status.get(game_id) in [2, 3]:
            return f"Player **{self.service.players[player_id]['full_name']}** is in a started game."

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
        game_id = self.service.player_to_game[player_to_remove]
        if self.service.active_game_status.get(game_id) in [2, 3]:
            return f"Player **{self.service.players[player_to_remove]['full_name']}** is in a started game."

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
        user, err = get_user_new(self.user_id)
        if user is None:
            await ADMIN_LOGGER.error(f"DynamicLineup:Submit:{err}")
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


class DynamicLineupService(FastBreakService):
    def __init__(self):
        super(DynamicLineupService, self).__init__()
        self.current_game_date = ""
        self.team_to_opponent = {}
        self.team_to_players = {}
        self.player_to_team = {}
        self.player_to_game = {}
        self.formatted_teams = {}

        self.player_ids = []
        self.lineups = {}
        self.active_game_status = {}

        self.status = "INIT"
        self.player_stats = {}
        self.user_scores = {}
        self.leaderboard = []

        asyncio.run(self.update())

    def __load_players(self):
        self.player_ids = []
        players_to_load = []

        for game_id, game in NBA_PROVIDER.get_games_on_date(self.current_game_date).items():
            for team in [game['homeTeam'], game['awayTeam']]:
                self.team_to_opponent[team] = game['homeTeam'] if team == game['awayTeam'] else game['awayTeam']
                self.team_to_players[team] = []
                for player in NBA_PROVIDER.get_players_for_team(team):
                    if player in TS_PROVIDER.player_moments:  # only load players with TS moments
                        self.player_to_team[player] = team
                        self.player_to_game[player] = game_id
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
        if self.fb is None:
            return

        game_day_players = []
        for game_id, game in NBA_PROVIDER.get_games_on_date(self.current_game_date).items():
            for team in [game['homeTeam'], game['awayTeam']]:
                for player in NBA_PROVIDER.get_players_for_team(team):
                    game_day_players.append(player)

        loaded = get_lineups(self.current_game_date)
        player_ids = []
        for lineup in loaded:
            self.lineups[lineup['user_id']] = Lineup(lineup, self)

        if len(self.lineups) > 0:
            for user_id in self.lineups:
                player_ids.extend(self.lineups[user_id].player_ids)

            player_ids = list(set(player_ids))
            if None in player_ids:
                player_ids.remove(None)
            self.player_stats = get_empty_players_stats(player_ids)

    def reload(self):
        FB_PROVIDER.reload()
        self.fb = FastBreak(FB_PROVIDER.get_fb(self.current_game_date))

        self.team_to_opponent = {}
        self.team_to_players = {}
        self.player_to_team = {}
        self.player_to_game = {}
        self.players = {}
        self.player_ids = []
        self.formatted_teams = {}
        self.formatted_schedule = self.__formatted_schedule([])
        self.lineups = {}
        self.user_scores = {}
        self.leaderboard = []
        self.__load_players()
        self.__load_lineups()

    async def update(self):
        scoreboard = NBAProvider.get_scoreboard()
        scoreboard_date = datetime.datetime.strptime(scoreboard['gameDate'], '%Y-%m-%d')
        active_games = list(filter(lambda g: g['gameStatusText'] != "PPD", scoreboard['games']))
        new_status = NBAProvider.get_status(scoreboard['games'])

        if new_status == "POST_GAME":
            pst_time = datetime.datetime.now(TZ_PT).replace(tzinfo=None)
            diff = pst_time - scoreboard_date
            if diff.days >= 1:
                new_status = "PRE_GAME"
                current_game_date = FB_PROVIDER.get_next_game_date(scoreboard_date)
            else:
                current_game_date = scoreboard_date.strftime('%m/%d/%Y')
        elif new_status == "NO_GAME":
            current_game_date = FB_PROVIDER.get_next_game_date(scoreboard_date)
            new_status = "PRE_GAME"  # skip dates with no game
        else:
            current_game_date = scoreboard_date.strftime('%m/%d/%Y')

        if self.status == "INIT":
            self.current_game_date = current_game_date
            self.status = new_status
            self.reload()
            if current_game_date == scoreboard_date.strftime('%m/%d/%Y'):
                # the current game date is still ongoing, we need to load current games and lineups
                self.active_game_status = {game['gameId']: game['gameStatus'] for game in active_games}
                self.formatted_schedule = self.__formatted_schedule(active_games)

                if new_status == "IN_GAME" or new_status == "POST_GAME":
                    await self.__update_stats()
            else:
                # the current game date is not started yet, no need to load game stats
                self.active_game_status = {}

            return
        elif self.status == "PRE_GAME":
            if new_status == "IN_GAME":
                self.active_game_status = {game['gameId']: game['gameStatus'] for game in active_games}
                await self.__update_stats()
        elif self.status == "IN_GAME":
            await self.__update_stats()
            self.formatted_schedule = self.__formatted_schedule(active_games)
        else:  # POST_GAME
            await self.__update_stats()
            if new_status == "PRE_GAME":
                await self.__upload_leaderboard()

                # start a new date
                self.current_game_date = current_game_date.strftime('%m/%d/%Y')
                self.reload()  # the reloaded lineups should be empty

        self.status = new_status

    async def __update_stats(self):
        player_stats = {}
        for game_id in self.active_game_status:
            if self.active_game_status[game_id] == 1:
                continue  # game not started yet

            try:
                game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
            except Exception as err:
                ADMIN_LOGGER.error(f"Ranking:UpdateStats:{err}")
                continue

            if game_stats['gameStatus'] == 1:
                continue

            game_info = get_game_info(game_stats)

            for player in game_stats['homeTeam']['players']:
                if player['status'] == 'ACTIVE':
                    player_id = player['personId']
                    player_stats[player_id] = self.enrich_stats(player['statistics'])
                    player_stats[player_id]['name'] = player['name']
                    player_stats[player_id]['gameInfo'] = game_info

            for player in game_stats['awayTeam']['players']:
                if player['status'] == 'ACTIVE':
                    player_id = player['personId']
                    player_stats[player_id] = self.enrich_stats(player['statistics'])
                    player_stats[player_id]['name'] = player['name']
                    player_stats[player_id]['gameInfo'] = game_info

        for player_id in player_stats:
            self.player_stats[player_id] = player_stats[player_id]

        user_scores = {}
        for user_id in self.lineups:
            lineup = self.lineups[user_id]
            if not lineup.is_submitted:
                continue

            score, passed, rate = self.fb.compute_score(lineup.player_ids[0:self.fb.count], self.player_stats)
            user_scores[user_id] = {
                'score': score,
                'serial': lineup.serial,
                'passed': passed,
                'rate': rate,
            }

        user_ids = list(user_scores.keys())
        user_ids.sort(key=lambda uid: user_scores[uid]['serial'], reverse=False)
        user_ids.sort(key=lambda uid: user_scores[uid]['score'], reverse=True)

        leaderboard = []
        for i, user_id in enumerate(user_ids):
            user_scores[user_id]['rank'] = i + 1
            leaderboard.append(user_id)

        self.user_scores = user_scores
        self.leaderboard = leaderboard

    async def __upload_leaderboard(self):
        for user_id in self.lineups:
            if user_id not in self.user_scores:
                continue
            err = upsert_score(user_id, self.lineups[user_id].game_date,
                               self.user_scores[user_id]['rate'], self.user_scores[user_id]['passed'])
            if err is not None:
                await ADMIN_LOGGER.error(f"FBRanking:Upload:{err}")

    def formatted_user_score(self, user_id):
        if self.status == "PRE_GAME":
            return "Games are not started yet."

        if self.current_game_date not in FB_PROVIDER.fb_info:
            return "Games are not started yet."

        if user_id not in self.lineups:
            return "User lineup not found."
        lineup = self.lineups[user_id]

        message = "🏀 ***{} GAMES***\n".format(self.current_game_date)
        if self.fb is not None:
            message += self.fb.get_formatted()

        message += self.fb.formatted_scores(lineup.player_ids[0:self.fb.count], self.player_stats)
        if user_id in self.user_scores:
            message += f"\nYour current rank is **{self.user_scores[user_id]['rank']}/{len(self.user_scores)}**"

        return message

    async def schedule_with_scores(self, user_id):
        dates = FB_PROVIDER.get_dates()
        user_results, err = get_user_results(user_id, dates)
        if err is not None:
            await ADMIN_LOGGER.error(f"FBRanking:UserProgress:{err}")
            return f"Error loading progress: {err}"
        if user_id in self.user_scores:
            user_results[self.current_game_date] = 1 if self.user_scores[user_id]['passed'] else -1

        dates.sort()
        wins = 0
        message = "***FASTBREAK SCHEDULE***\n\n"
        for d in dates:
            if d > self.current_game_date:
                message += "🟡 "
            elif user_results[d] == 1:
                message += "🟢 "
                wins += 1
            elif user_results[d] == 0:
                message += "🔴 "
            else:
                message += "🟡 "
            fb = FastBreak(FB_PROVIDER.fb_info[d])
            message += f"**{d}**\n{fb.get_formatted()[2:-4]}\n"

        message += f"\n🟢 **{wins} WINS**"

        return message

    @staticmethod
    def enrich_stats(player_stats):
        player_stats['fieldGoalsMissed'] = player_stats['fieldGoalsAttempted'] - player_stats['fieldGoalsMade']
        player_stats['freeThrowsMissed'] = player_stats['freeThrowsAttempted'] - player_stats['freeThrowsMade']

        doubles = 0
        for stats in ['points', 'reboundsTotal', 'assists', 'steals', 'blocks']:
            if player_stats[stats] >= 10:
                doubles += 1

        player_stats['doubleDouble'] = 1.0 if doubles > 1 else 0
        player_stats['tripleDouble'] = 1.0 if doubles > 2 else 0
        player_stats['quadrupleDouble'] = 1.0 if doubles > 3 else 0
        player_stats['fiveDouble'] = 1.0 if doubles > 4 else 0

        return player_stats

    def formatted_leaderboard(self, top):
        if self.status != "IN_GAME" and self.status != "POST_GAME":
            return "Games are not started yet.\n"

        message = f"***Leaderboard {self.current_game_date}***\n\n"
        for i in range(0, min(top, len(self.leaderboard))):
            uid = self.leaderboard[i]
            if self.user_scores[uid]['passed']:
                message += "🟢 "
            else:
                message += "🔴 "
            message += f"**#{i + 1}.**  **{self.lineups[uid].username}** " \
                       f"points {self.user_scores[uid]['score']}, serial {int(self.lineups[uid].serial)}\n"

        message += f"\nTotal submissions: **{len(self.user_scores)}**\n"

        return message

    @staticmethod
    def formatted_weekly_leaderboard(dates, top):
        message = "***Weekly Leaderboard {}~{}***\n\n".format(dates[0], dates[-1])
        loaded = get_weekly_ranks(dates, top)
        for i in range(0, min(top, len(loaded))):
            message += f"**#{i + 1}.** **{loaded[i]['username']}** *{loaded[i]['wins']}* wins, " \
                       f"*{round(loaded[i]['total_score'], 2)}* CR"
            if loaded[i].get('all_checked_in'):
                message += " (with +10% bonus)\n"
            else:
                message += "\n"

        return message

    def __create_lineup(self, user_id):
        self.lineups[user_id] = Lineup(
            {
                "user_id": user_id,
                "game_date": self.current_game_date,
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
            return ["{} is not playing on {}.".format(team, self.current_game_date)]
        return self.formatted_teams[team]

    def get_coming_games(self):
        return NBA_PROVIDER.get_games_on_date(self.current_game_date).items()

    def __formatted_schedule(self, games):
        message = "🏀 ***{} GAMES***\n".format(self.current_game_date)
        if self.fb is not None:
            message += self.fb.get_formatted()

        if self.status == "PRE_GAME":
            for game_id, game in self.get_coming_games():
                message += f"{game['awayTeam']} at {game['homeTeam']}\n"

            return message
        else:
            message = "🏀 ***{} GAMES***\n".format(self.current_game_date)

            for game in games:
                message += "**{}** {} : {} **{}** {}\n".format(
                    game['awayTeam']['teamTricode'],
                    game['awayTeam']['score'],
                    game['homeTeam']['score'],
                    game['homeTeam']['teamTricode'],
                    game['gameStatusText']
                )

        return message


DYNAMIC_LINEUP_SERVICE = DynamicLineupService()
