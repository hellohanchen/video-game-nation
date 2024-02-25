import asyncio
import datetime
from typing import Dict, List

from nba_api.live.nba.endpoints import boxscore

from constants import TZ_PT, GameDateStatus, INVALID_ID
from provider.nba.nba_provider import NBAProvider, NBA_PROVIDER
from provider.topshot.cadence.flow_collections import get_account_plays_with_lowest_serial
from provider.topshot.fb_provider import FB_PROVIDER
from provider.topshot.ts_provider import TS_PROVIDER
from repository.fb_lineups import get_lineups, upsert_score, get_slate_ranks, get_user_results, upsert_lineup, \
    submit_lineup, get_lineup, get_player_usages, get_user_slate_result
from repository.vgn_players import get_empty_players_stats, get_players
from repository.vgn_users import get_user_new
from service.fastbreak.fastbreak import FastBreak
from service.fastbreak.utils import build_fb_collections
from utils import get_game_info, cast_player_id
from vgnlog.channel_logger import ADMIN_LOGGER


class AbstractDynamicLineupService:
    def __init__(self):
        self.current_game_date: str = ""
        self.status: GameDateStatus = GameDateStatus.INIT
        self.fb: FastBreak | None = None

        self.players: Dict[int, Dict[str, any]] = {}
        self.player_ids: List[int] = []
        self.player_games: Dict[int, Dict[str, str]] = {}

        self.user_scores: Dict[int, Dict[str, any]] = {}
        self.leaderboard: List[int] = []

        self.games: Dict[str, any] = {}
        self.formatted_games: str = ""

    def formatted_player(self, player_id: int) -> str:
        pass


class Lineup:
    def __init__(self, db_lineup: Dict[str, int | bool | str], service: AbstractDynamicLineupService):
        self.user_id: int = INVALID_ID
        self.username: str = ""
        self.player_ids: [int] = []
        self.is_ranked: bool = False
        self.serial: int = 0
        self.service: AbstractDynamicLineupService = service
        self.reload(db_lineup)

    def reload(self, db_lineup: Dict[str, int | bool | str]):
        self.user_id = db_lineup['user_id']
        self.username = db_lineup['topshot_username']
        self.player_ids: [int] = [
            cast_player_id(db_lineup['player_1']),
            cast_player_id(db_lineup['player_2']),
            cast_player_id(db_lineup['player_3']),
            cast_player_id(db_lineup['player_4']),
            cast_player_id(db_lineup['player_5']),
            cast_player_id(db_lineup['player_6']),
            cast_player_id(db_lineup['player_7']),
            cast_player_id(db_lineup['player_8']),
        ]
        self.is_ranked = db_lineup['is_ranked']
        self.serial = db_lineup['sum_serial']

    def formatted(self) -> str:
        message = self.service.formatted_games + "\n"
        if self.service.fb is not None:
            message += self.service.fb.get_formatted()

        message += f"Your lineup for **{self.service.current_game_date}**"
        if self.is_ranked:
            message += " is **SUBMITTED**.\n"
        else:
            message += ".\n"

        for player_id in self.player_ids[0: self.service.fb.count]:
            message += self.service.formatted_player(player_id)

        if self.user_id in self.service.user_scores:
            score = self.service.user_scores[self.user_id]
            message += f"\n{score['message']}\n\n" \
                       f"Your current rank is **{score['rank']}/{len(self.service.user_scores)}**"

        if self.service.status == GameDateStatus.PRE_GAME:
            message += f"\nGames are not started yet."

        return message

    def add_player_by_idx(self, player_idx: int, pos_idx: int, is_ranked: bool = False) -> str:
        if self.is_ranked and not is_ranked:
            return f"B2B contest lineup can only be updated in B2B server."
        if pos_idx < 0 or pos_idx > self.service.fb.count:
            return "Player index should be between [0, {}]".format(self.service.fb.count - 1)
        if player_idx < 1 or player_idx > len(self.service.player_ids):
            return "Player index should be between [1, {}]".format(len(self.service.player_ids))

        player_id = self.service.player_ids[player_idx - 1]
        player_name = self.service.players[player_id]['full_name']
        if player_id in self.player_ids:
            return f"Player **{player_name}** is already in the lineup."
        if self.is_player_game_started(player_id):
            return f"Player **{player_name}** is in a started game."

        message = ""

        player_to_remove = self.player_ids[pos_idx]
        if player_to_remove != INVALID_ID:
            message += f"Removed **{self.service.players[player_to_remove]['full_name']}**."
        self.player_ids[pos_idx] = player_id

        updated_lineup, err = upsert_lineup(
            (self.user_id, self.service.current_game_date, self.player_ids[0], self.player_ids[1], self.player_ids[2],
             self.player_ids[3], self.player_ids[4], self.player_ids[5], self.player_ids[6], self.player_ids[7])
        )
        if err is None:
            message += f"Added **{player_name}**"
            if self.is_ranked:
                if is_ranked:
                    message += "\nClick **Submit** to save your changes."
                else:
                    message += "\nPlease **Submit** to save your changes in B2B server."

            if self.user_id in self.service.user_scores:
                self.service.leaderboard.remove(self.user_id)
                del self.service.user_scores[self.user_id]

            self.reload(updated_lineup[0])
            return message
        else:
            self.player_ids[pos_idx] = player_to_remove

            if err == "player is used":
                return f"Player reaches maximum usages: {player_name}"

            return f"Failed to update lineup: {err}"

    def remove_player(self, pos_idx: int, is_ranked: bool = False) -> str:
        if self.is_ranked and not is_ranked:
            return f"B2B contest lineup can only be updated in B2B server."
        if self.player_ids[pos_idx] is INVALID_ID:
            return "No player at this position."

        player_to_remove = self.player_ids[pos_idx]
        if self.is_player_game_started(player_to_remove):
            return f"Player **{self.service.players[player_to_remove]['full_name']}** is in a started game."

        # remove player
        self.player_ids[pos_idx] = INVALID_ID
        updated_lineup, err = upsert_lineup(
            (self.user_id, self.service.current_game_date, self.player_ids[0], self.player_ids[1], self.player_ids[2],
             self.player_ids[3], self.player_ids[4], self.player_ids[5], self.player_ids[6], self.player_ids[7])
        )
        if err is None:
            message = f"Removed **{self.service.players[player_to_remove]['full_name']}**."
            if self.is_ranked:
                if is_ranked:
                    message += "\nClick **Submit** to save your changes."
                else:
                    message += "\nPlease **Submit** to save your changes in B2B server."

            if self.user_id in self.service.user_scores:
                self.service.leaderboard.remove(self.user_id)
                del self.service.user_scores[self.user_id]

            self.reload(updated_lineup[0])
            return message
        else:
            self.player_ids[pos_idx] = player_to_remove
            return "Failed to update lineup, please retry."

    async def submit(self) -> str:
        user, err = get_user_new(self.user_id)
        if user is None:
            await ADMIN_LOGGER.error(f"DynamicLineup:Submit:{err}")
            return "Failed to load user collection, please retry."

        # load submitted serials if the lineup is already submitted
        submitted_serials = {}
        game_date = self.service.current_game_date
        if self.is_ranked:
            submitted, err = get_lineup(self.user_id, game_date)
            if err is not None:
                await ADMIN_LOGGER.error(f"DynamicLineup:Submit:GetLineup:{err}")
            else:
                if submitted['player_1'] != INVALID_ID:
                    submitted_serials[submitted['player_1']] = submitted['player_1_serial']
                if submitted['player_2'] != INVALID_ID:
                    submitted_serials[submitted['player_2']] = submitted['player_2_serial']
                if submitted['player_3'] != INVALID_ID:
                    submitted_serials[submitted['player_3']] = submitted['player_3_serial']
                if submitted['player_4'] != INVALID_ID:
                    submitted_serials[submitted['player_4']] = submitted['player_4_serial']
                if submitted['player_5'] != INVALID_ID:
                    submitted_serials[submitted['player_5']] = submitted['player_5_serial']

        plays = await get_account_plays_with_lowest_serial(user['flow_address'])
        collections, _ = build_fb_collections(TS_PROVIDER, plays, self.player_ids[0:5])
        serials = []
        serial_sum = 0

        for pid in self.player_ids[0:5]:
            if pid == INVALID_ID:
                serials.append(None)
            elif pid not in collections:
                return f"You don't have any moment of {self.service.players[pid]['full_name']}, please check lineup."
            elif pid in submitted_serials and self.is_player_game_started(pid):
                serial_sum += submitted_serials[pid]
                serials.append(submitted_serials[pid])
            else:
                serial_sum += collections[pid]['serial']
                serials.append(collections[pid]['serial'])

        if game_date in FB_PROVIDER.date_to_rounds:
            player_usages, err = get_player_usages(self.user_id, game_date)
            if err is not None:
                await ADMIN_LOGGER.error(f"FBR:Submit:PlayerUsages:{err}")

            validation = FB_PROVIDER.rounds[FB_PROVIDER.date_to_rounds[game_date]]['validation']
            if validation == "ONE":
                for pid in self.player_ids[0:5]:
                    if pid != INVALID_ID:
                        if pid in player_usages:
                            return f"Submission failed: {self.service.players[pid]['full_name']} reaches limit: 1"
            elif validation == "TS":
                for pid in self.player_ids[0:5]:
                    if pid != INVALID_ID:
                        if collections[pid]['tier'] == "Legendary":
                            limit = 4
                        elif collections[pid]['tier'] == 'Rare':
                            limit = 2
                        else:
                            limit = 1
                        if pid in player_usages and player_usages[pid] == limit:
                            return f"Submission failed: {self.service.players[pid]['full_name']} reaches limit: {limit}"

        successful, err = submit_lineup((
            self.user_id, user['topshot_username'], game_date,
            self.player_ids[0], serials[0],
            self.player_ids[1], serials[1], self.player_ids[2], serials[2],
            self.player_ids[3], serials[3], self.player_ids[4], serials[4],
            serial_sum
        ))
        if not successful:
            return f"Submission failed: {err}"

        self.is_ranked = True
        self.serial = serial_sum
        self.username = user['topshot_username']
        message = "You've submitted lineup using the following players:\n\n"
        for pid in self.player_ids[0:5]:
            if pid == INVALID_ID:
                continue
            message += f"🏀 **{self.service.players[pid]['full_name']}** " \
                       f"{collections[pid]['tier']}({collections[pid]['serial']})\n"
        message += f"\nTotal serial **{serial_sum}**"

        return message

    def is_player_game_started(self, player_id):
        game: Dict[str, any] = self.service.games.get(self.service.player_games[player_id]['id'], {})
        return game.get('status', 1) in [2, 3]


class DynamicLineupService(AbstractDynamicLineupService):
    def __init__(self):
        super(DynamicLineupService, self).__init__()

        self.team_players: Dict[str, List[int]] = {}
        self.formatted_teams: Dict[str, str] = {}

        self.lineups: Dict[int, Lineup] = {}

        # live status
        self.player_stats: Dict[int, Dict[str: any]] = {}

        asyncio.run(self.update())

    def __load_players(self):
        self.player_ids = []
        players_to_load = []

        for game_id, game in NBA_PROVIDER.get_games_on_date(self.current_game_date).items():
            # create placeholder for games if not live data cached
            if game_id not in self.games:
                self.games[game_id] = {
                    'awayTeam': game['awayTeam'],
                    'awayScore': 0,
                    'homeTeam': game['homeTeam'],
                    'homeScore': 0,
                    'statusText': '',
                    'status': 1
                }

            for team in [game['homeTeam'], game['awayTeam']]:
                self.team_players[team] = []
                self.formatted_teams[team] = ""
                for player_id in NBA_PROVIDER.get_players_for_team(team):
                    if player_id in TS_PROVIDER.player_moments:  # only load players with TS moments
                        self.player_games[player_id] = {
                            'id': game_id,
                            'team': team,
                            'opponent': game['homeTeam'] if team == game['awayTeam'] else game['awayTeam']
                        }
                        players_to_load.append(player_id)

        loaded = get_players(players_to_load, [("full_name", "ASC")])
        index = 0
        for player in loaded:
            player_id = player['id']
            player_name = player['full_name']
            index += 1

            self.players[player_id] = player
            self.players[player_id]['index'] = index
            self.player_ids.append(player_id)

            game = self.player_games[player_id]
            team = game['team']
            self.team_players[team].append(player_id)
            injury = NBA_PROVIDER.get_player_injury(player_name)
            self.formatted_teams[team] += f"**{player_name}**  *{game['team']}* vs {game['opponent']} **{injury}**\n"

        player_stats = get_empty_players_stats(self.player_ids)
        for player_id in player_stats:
            if player_id not in self.player_stats:
                self.player_stats[player_id] = player_stats[player_id]

    def __load_lineups(self):
        if self.fb is None:
            return

        game_day_players = []
        for game_id, game in NBA_PROVIDER.get_games_on_date(self.current_game_date).items():
            for team in [game['homeTeam'], game['awayTeam']]:
                for player in NBA_PROVIDER.get_players_for_team(team):
                    game_day_players.append(player)

        loaded = get_lineups(self.current_game_date)
        for lineup in loaded:
            self.lineups[lineup['user_id']] = Lineup(lineup, self)

    def reload(self):
        FB_PROVIDER.reload()
        self.fb = FastBreak(FB_PROVIDER.get_fb(self.current_game_date))

        self.players = {}
        self.player_ids = []
        self.player_games = {}
        self.team_players = {}
        self.formatted_teams = {}
        self.__load_players()

        self.lineups = {}
        self.__load_lineups()

        self.user_scores = {}
        self.leaderboard = []

    async def update(self):
        scoreboard = NBAProvider.get_scoreboard()
        scoreboard_date = datetime.datetime.strptime(scoreboard['gameDate'], '%Y-%m-%d')
        active_games = list(filter(lambda g: g['gameStatusText'] != "PPD", scoreboard['games']))
        new_status = NBAProvider.get_status_enum(scoreboard['games'])

        if new_status == GameDateStatus.POST_GAME:
            pst_time = datetime.datetime.now(TZ_PT).replace(tzinfo=None)
            diff = pst_time - scoreboard_date
            if diff.days >= 1:
                new_status = GameDateStatus.PRE_GAME
                current_game_date = FB_PROVIDER.get_next_game_date(scoreboard_date)
            else:
                current_game_date = scoreboard_date.strftime('%m/%d/%Y')
        elif new_status == GameDateStatus.NO_GAME:
            current_game_date = FB_PROVIDER.get_next_game_date(scoreboard_date)
            new_status = GameDateStatus.PRE_GAME  # skip dates with no game
        else:
            current_game_date = scoreboard_date.strftime('%m/%d/%Y')

        # reboot the service with loading all info for current date
        if self.status == GameDateStatus.INIT:
            self.current_game_date = current_game_date
            self.status = new_status
            self.reload()
            if current_game_date == scoreboard_date.strftime('%m/%d/%Y'):
                # the current game date is still ongoing, we need to load current games and lineups
                if new_status == GameDateStatus.IN_GAME or new_status == GameDateStatus.POST_GAME:
                    await self.__update_stats()
                self.formatted_games = self.__formatted_games(active_games)
            else:
                self.formatted_games = self.__formatted_games([])

            return

        # service state machine
        if self.status == GameDateStatus.PRE_GAME:
            if new_status == GameDateStatus.IN_GAME:
                await self.__update_stats()
        elif self.status == GameDateStatus.IN_GAME:
            await self.__update_stats()
            self.formatted_games = self.__formatted_games(active_games)
        else:  # POST_GAME
            await self.__update_stats()
            if new_status == GameDateStatus.PRE_GAME:
                # upload leader board if move to a new game date
                await self.__upload_leaderboard()

                # start a new date
                self.current_game_date = current_game_date
                self.games = {}
                self.formatted_games = self.__formatted_games([])
                self.player_stats = {}
                self.reload()  # the reloaded lineups should be empty

        self.status = new_status

    async def __update_stats(self):
        player_stats: Dict[int, Dict[str, any]] = {}
        games: Dict[str, Dict[str, any]] = {}
        for game_id in self.games:
            if self.games[game_id] == 1:
                continue  # game not started yet

            try:
                game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
            except Exception as err:
                #  await ADMIN_LOGGER.error(f"Ranking:UpdateStats:{err}")  TODO: look into this noisy error
                continue

            if game_stats['gameStatus'] == 1:
                continue

            games[game_id] = get_game_info(game_stats)

            for player in game_stats['homeTeam']['players']:
                if player['status'] == 'ACTIVE':
                    player_id = player['personId']
                    player_stats[player_id] = self.enrich_stats(player['statistics'])
                    player_stats[player_id]['name'] = player['name']

            for player in game_stats['awayTeam']['players']:
                if player['status'] == 'ACTIVE':
                    player_id = player['personId']
                    player_stats[player_id] = self.enrich_stats(player['statistics'])
                    player_stats[player_id]['name'] = player['name']

        # store new stats
        for player_id in player_stats:
            self.player_stats[player_id] = player_stats[player_id]
        for game_id in games:
            self.games[game_id] = games[game_id]

        user_scores = {}
        for user_id in self.lineups:
            lineup = self.lineups[user_id]
            if not lineup.is_ranked:
                continue

            score, passed, rate, message = self.fb.compute_score(lineup.player_ids[0:self.fb.count], self.player_stats)
            user_scores[user_id] = {
                'score': score,
                'serial': lineup.serial,
                'passed': passed,
                'rate': rate,
                'message': message
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
            err = upsert_score(user_id, self.current_game_date, self.user_scores[user_id]['score'],
                               self.user_scores[user_id]['rate'], self.user_scores[user_id]['rank'],
                               self.user_scores[user_id]['passed'])
            if err is not None:
                await ADMIN_LOGGER.error(f"FBRanking:Upload:{err}")

    def formatted_player(self, player_id: int) -> str:
        if player_id == INVALID_ID:
            return "🏀 ---\n\n"

        player_stats = self.player_stats.get(player_id)
        if player_stats is None:
            player = self.players.get(player_id)
            if player is None:
                return f"🏀 invalid player id: **{player_id}**\n\n"
            message = f"🏀 **{player['full_name']}**\n"
        else:
            if self.fb is None:
                message = f"🏀 **{player_stats['full_name']}**\n"
            else:
                message = f"🏀 {self.fb.formatted_score(player_stats)}\n"

        player_game = self.player_games[player_id]
        game = self.games[player_game['id']]
        if player_game['team'] == game['homeTeam']:
            return f"{message}" \
                   f"{game['awayTeam']} {game['awayScore']}-" \
                   f"**{game['homeScore']} {game['homeTeam']}** " \
                   f"{game['statusText']}\n"
        else:
            return f"{message}" \
                   f"**{game['awayTeam']} {game['awayScore']}**-" \
                   f"{game['homeScore']} {game['homeTeam']} " \
                   f"{game['statusText']}\n"

    async def schedule_with_scores(self, user_id):
        dates = FB_PROVIDER.get_dates(self.current_game_date)
        daily_results, err = get_user_results(user_id, dates)
        if err is not None:
            await ADMIN_LOGGER.error(f"FBRanking:UserDailyResult:{err}")
            return f"Error loading daily results: {err}"
        slate_result, err = get_user_slate_result(user_id, dates)
        if err is not None:
            await ADMIN_LOGGER.error(f"FBRanking:UserSlateResult:{err}")
            return f"Error loading slate result: {err}"
        if user_id in self.user_scores:
            score = self.user_scores[user_id]
            daily_results[self.current_game_date] = {
                "is_passed": score['passed'],
                "score": score['score'],
                "rate": score['rate'],
                "rank": score['rank'],
            }
        else:
            daily_results[self.current_game_date] = None

        dates.sort()
        wins = 0
        message = "***FASTBREAK SCHEDULE***\n\n"
        for d in dates:
            if d > self.current_game_date:
                message += f"🟡 **{d[0:-5]}**\n"
            else:
                result = daily_results[d]
                if result is None:
                    message += f"🟡 **{d[0:-5]}**\n"
                else:
                    if result['is_passed']:
                        message += f"🟢 **{d[0:-5]} | {result['score']}/{result['rate']} #{int(result['rank'])}**\n"
                        wins += 1
                    elif d == self.current_game_date and self.status != GameDateStatus.POST_GAME:
                        message += f"🟡 **{d[0:-5]} | {result['score']}/{result['rate']} #{int(result['rank'])}**\n"
                    else:
                        message += f"🔴 **{d[0:-5]} | {result['score']}/{result['rate']} #{int(result['rank'])}**\n"

            fb = FastBreak(FB_PROVIDER.fb_info[d])
            message += f"{fb.get_formatted()[2:-4]}\n"

        message += f"\n🟢 **{wins} WINS**"
        if slate_result is not None:
            message += f"\n\nYour rank of *{dates[0][0:-5]}~{dates[-1][0:-5]}*:\n" \
                       f"**{slate_result['wins']}** wins, **{round(slate_result['total_score'], 2)}** CR,"
            message += f" **#{slate_result['rank']}**\n" \
                       f"*current game date not included*"

        return message

    def formatted_leaderboard(self, top):
        if self.status == GameDateStatus.PRE_GAME:
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
    def formatted_slate_leaderboard(dates, top):
        message = "***Slate Leaderboard {}~{}***\n\n".format(dates[0], dates[-1])
        loaded = get_slate_ranks(dates, top)
        for i in range(0, min(top, len(loaded))):
            message += f"**#{i + 1}.** **{loaded[i]['username']}** *{loaded[i]['wins']}* wins, " \
                       f"*{round(loaded[i]['total_score'], 2)}* CR"
            if loaded[i].get('all_checked_in'):
                message += " (with +10% bonus)\n"
            else:
                message += "\n"

        return loaded[:10], message

    def formatted_team_players(self, team) -> str:
        if team not in self.formatted_teams:
            return "{} is not playing on {}.".format(team, self.current_game_date)
        return self.formatted_teams[team]

    def get_coming_games(self):
        return NBA_PROVIDER.get_games_on_date(self.current_game_date).items()

    def __formatted_games(self, games):
        message = "🏀 ***{} GAMES***\n".format(self.current_game_date)

        if self.status == GameDateStatus.PRE_GAME or len(games) == 0:
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

    def __create_lineup(self, user_id):
        self.lineups[user_id] = Lineup(
            {
                "user_id": user_id,
                "game_date": self.current_game_date,
                "topshot_username": "",
                "player_1": INVALID_ID,
                "player_2": INVALID_ID,
                "player_3": INVALID_ID,
                "player_4": INVALID_ID,
                "player_5": INVALID_ID,
                "player_6": INVALID_ID,
                "player_7": INVALID_ID,
                "player_8": INVALID_ID,
                "is_ranked": False,
                "sum_serial": 0,
            },
            self
        )

    def get_or_create_lineup(self, user_id) -> Lineup:
        if user_id not in self.lineups:
            self.__create_lineup(user_id)

        return self.lineups[user_id]

    def load_or_create_lineup(self, user_id: int) -> Lineup:
        lineup, err = get_lineup(user_id, self.current_game_date)
        if len(lineup) == 0:
            self.__create_lineup(user_id)
        else:
            self.lineups[user_id] = Lineup(lineup, self)

        return self.lineups[user_id]


DYNAMIC_LINEUP_SERVICE = DynamicLineupService()
