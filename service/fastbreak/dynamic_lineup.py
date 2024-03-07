import asyncio
import datetime
from typing import Dict, List, Optional

import pytz
from nba_api.live.nba.endpoints import boxscore

from constants import TZ_PT, GameDateStatus, INVALID_ID
from provider.nba.nba_provider import NBAProvider, NBA_PROVIDER
from provider.topshot.cadence.flow_collections import get_account_plays_with_lowest_serial
from provider.topshot.fb_provider import FB_PROVIDER
from provider.topshot.ts_provider import TS_PROVIDER
from repository.fb_lineups import get_lineups, upsert_score, get_slate_ranks, get_user_results, upsert_lineup, \
    submit_lineup, get_lineup, get_user_slate_result, get_usages, get_submissions
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
        self.contest_fbs: Dict[int, FastBreak] = {}

        self.players: Dict[int, Dict[str, any]] = {}
        self.player_ids: List[int] = []
        self.player_games: Dict[int, Dict[str, str]] = {}

        self.user_usages: Dict[int, Dict[int, int]] = {}
        self.contest_scores: Dict[int, Dict[int, Dict[str, any]]] = {}
        self.leaderboards: Dict[int, List[int]] = {}

        self.games: Dict[str, any] = {}
        self.formatted_games: str = ""

    def formatted_player(self, player_id: int, fb: FastBreak) -> str:
        pass

    @staticmethod
    def get_fb_on(game_date, contest_id: Optional[int] = None) -> FastBreak:
        if contest_id is None:
            contest_id = FB_PROVIDER.date_contests.get(game_date, {}).get(INVALID_ID)

        if game_date in FB_PROVIDER.fb_details and contest_id in FB_PROVIDER.fb_details[game_date]:
            return FastBreak(FB_PROVIDER.fb_details[game_date][contest_id])
        return FastBreak.get_empty()

    def get_fb(self, contest_id: Optional[int] = None) -> FastBreak:
        game_date = self.current_game_date
        if contest_id is None:
            default_contest_id = FB_PROVIDER.date_contests.get(game_date, {}).get(INVALID_ID)
            return self.contest_fbs.get(default_contest_id, FastBreak.get_empty())

        return self.contest_fbs.get(contest_id, FastBreak.get_empty())

    def remove_user_scores(self, user_id: int):
        for cid in self.contest_scores:
            if user_id in self.leaderboards[cid]:
                self.leaderboards[cid].remove(user_id)
            if user_id in self.contest_scores[cid]:
                del self.contest_scores[cid][user_id]


class Lineup:
    def __init__(self, db_lineup: Dict[str, int | bool | str], service: AbstractDynamicLineupService):
        self.user_id: int = INVALID_ID
        self.username: str = ""
        self.player_ids: [int] = []
        self.is_submitted: bool = False
        self.serial: int = 0
        self.service: AbstractDynamicLineupService = service
        self.contests: Dict[int, Dict[str, any]] = {}
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
        self.is_submitted = db_lineup['is_ranked']
        self.serial = db_lineup['sum_serial']
        self.contests, _ = get_submissions(self.user_id, self.service.current_game_date)

    def formatted(self, contest_id: Optional[int] = None) -> str:
        message = self.service.formatted_games + "\n"
        fb = self.service.get_fb(contest_id)
        if fb is not None:
            message += fb.get_formatted()

        message += f"Your lineup for **{self.service.current_game_date}**"
        if self.is_submitted and contest_id is not None and contest_id in self.contests:
            message += f" is **SUBMITTED** to *{FB_PROVIDER.contests[contest_id]['name']}*.\n"
        else:
            if contest_id is not None:
                message += f" is **NOT** submitted to *{FB_PROVIDER.contests[contest_id]['name']}*.\n"
            else:
                message += ".\n"

        for player_id in self.player_ids[0: fb.count]:
            message += self.service.formatted_player(player_id, fb)

        if contest_id in self.service.contest_scores:
            contest_scores = self.service.contest_scores[contest_id]
            if self.user_id in contest_scores:
                score = contest_scores[self.user_id]
                message += f"\n{score['message']}\n\n" \
                           f"Your current rank is **{score['rank']}/{len(contest_scores)}**"

        if self.service.status == GameDateStatus.PRE_GAME:
            message += f"\nGames are not started yet."

        return message

    def add_player_by_idx(self, player_idx: int, pos_idx: int, is_ranked: bool = False,
                          contest_id: Optional[int] = None) -> str:
        fb = self.service.get_fb(contest_id)
        if self.is_submitted and not is_ranked:
            return f"**SUBMITTED** lineup can't be modified here, please go to the original Discord server."
        if pos_idx < 0 or pos_idx > fb.count:
            return "Player index should be between [0, {}]".format(fb.count - 1)
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
            if self.is_submitted:
                message += "\n**You need to SUBMIT again to save your changes to join leaderboard.**"

            self.service.remove_user_scores(self.user_id)

            self.reload(updated_lineup[0])
            return message
        else:
            self.player_ids[pos_idx] = player_to_remove

            if err == "player is used":
                return f"Player reaches maximum usages: {player_name}"

            return f"Failed to update lineup: {err}"

    def remove_player(self, pos_idx: int, is_ranked: bool = False) -> str:
        if self.is_submitted and not is_ranked:
            return f"**SUBMITTED** lineup can't be modified here, please go to the original Discord server."
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
            if self.is_submitted:
                message += "\n**You need to SUBMIT again to save your changes to join leaderboard.**"

            self.service.remove_user_scores(self.user_id)

            self.reload(updated_lineup[0])
            return message
        else:
            self.player_ids[pos_idx] = player_to_remove
            return "Failed to update lineup, please retry."

    async def submit(self, contest_id: Optional[int]) -> str:
        if contest_id is None:
            return "Discord server doesn't have on-going Fastbreak contest."
        user, err = get_user_new(self.user_id)
        if user is None:
            await ADMIN_LOGGER.error(f"DynamicLineup:Submit:{err}")
            return "Failed to load user collection, please retry."

        # load submitted serials if the lineup is already submitted
        submitted_serials = {}
        game_date = self.service.current_game_date
        if len(self.contests) > 0:
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

        if contest_id in FB_PROVIDER.contests:
            validation = FB_PROVIDER.contests[contest_id]['validation']
            player_usages = self.service.user_usages.get(self.user_id, {})
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

        successful, updated_lineup, err = submit_lineup((
            self.user_id, user['topshot_username'], game_date,
            self.player_ids[0], serials[0],
            self.player_ids[1], serials[1], self.player_ids[2], serials[2],
            self.player_ids[3], serials[3], self.player_ids[4], serials[4],
            serial_sum
        ), self.user_id, contest_id)
        if not successful:
            return f"Submission failed: {err}"
        self.reload(updated_lineup[0])

        message = f"You've submitted lineup for *{FB_PROVIDER.contests[contest_id]['name']}* " \
                  f"using the following players:\n\n"
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
        if len(self.contest_fbs) == 0:
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
        self.contest_fbs = {cid: FastBreak(cfb) for cid, cfb in FB_PROVIDER.get_fbs(self.current_game_date).items()}

        self.players = {}
        self.player_ids = []
        self.player_games = {}
        self.team_players = {}
        self.formatted_teams = {}
        self.__load_players()

        self.lineups = {}
        self.__load_lineups()

        self.user_usages, err = get_usages(self.current_game_date)
        if err is not None:
            asyncio.run(ADMIN_LOGGER.error(f"FBR:UserUsages:{err}"))
        self.contest_scores = {}
        self.leaderboards = {}

    async def update(self, skip_upload=False):
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
                if not skip_upload:
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
            try:
                game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
            except Exception as err:
                # game stats not available
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

        contest_scores = {cid: {} for cid in self.contest_fbs}
        leaderboards = {}
        for user_id in self.lineups:
            lineup = self.lineups[user_id]
            if len(lineup.contests) == 0:
                continue

            for cid in lineup.contests:
                fb = self.get_fb(cid)
                score, passed, rate, message = fb.compute_score(lineup.player_ids[0:fb.count], self.player_stats)
                contest_scores[cid][user_id] = {
                    'score': score,
                    'serial': lineup.serial,
                    'passed': passed,
                    'rate': rate,
                    'message': message
                }

        for cid in self.contest_fbs:
            user_scores = contest_scores[cid]
            user_ids = list(user_scores.keys())
            user_ids.sort(key=lambda uid: user_scores[uid]['serial'], reverse=False)
            user_ids.sort(key=lambda uid: user_scores[uid]['score'], reverse=True)

            leaderboard = []
            for i, user_id in enumerate(user_ids):
                user_scores[user_id]['rank'] = i + 1
                leaderboard.append(user_id)
            leaderboards[cid] = leaderboard

        self.contest_scores = contest_scores
        self.leaderboards = leaderboards

    async def __upload_leaderboard(self):
        for contest_id in self.contest_scores:
            user_scores = self.contest_scores[contest_id]
            for user_id in user_scores:
                score = user_scores[user_id]
                err = upsert_score(user_id, contest_id, self.current_game_date,
                                   score['score'], score['rate'], score['rank'], score['passed'])
                if err is not None:
                    await ADMIN_LOGGER.error(f"FBRanking:Upload:{err}")

    def formatted_player(self, player_id: int, fb: FastBreak) -> str:
        if player_id == INVALID_ID:
            return "🏀 ---\n\n"

        player_stats = self.player_stats.get(player_id)
        if player_stats is None:
            player = self.players.get(player_id)
            if player is None:
                return f"🏀 invalid player id: **{player_id}**\n\n"
            message = f"🏀 **{player['full_name']}**\n"
        else:
            message = f"🏀 {fb.formatted_score(player_stats)}\n"

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

    async def schedule_with_scores(self, user_id, contest_id: Optional[int] = None):
        dates = FB_PROVIDER.get_dates(self.current_game_date)
        if contest_id is not None:
            daily_results, err = get_user_results(user_id, contest_id, dates)
            if err is not None:
                await ADMIN_LOGGER.error(f"FBRanking:UserDailyResult:{err}")
                return f"Error loading daily results: {err}"
            slate_result, err = get_user_slate_result(user_id, contest_id, dates)
            if err is not None:
                await ADMIN_LOGGER.error(f"FBRanking:UserSlateResult:{err}")
                return f"Error loading slate result: {err}"
        else:
            daily_results = {}
            slate_result = None
        if contest_id is not None and contest_id in self.contest_scores and user_id in self.contest_scores[contest_id]:
            score = self.contest_scores[contest_id][user_id]
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
                result = daily_results.get(d)
                if result is None:
                    message += f"🟡 **{d[0:-5]}**\n"
                else:
                    if result['is_passed']:
                        message += f"🟢 **{d[0:-5]} | {result['score']}/{result['rate']} #{result['rank']}**\n"
                        wins += 1
                    elif d == self.current_game_date and self.status != GameDateStatus.POST_GAME:
                        message += f"🟡 **{d[0:-5]} | {result['score']}/{result['rate']} #{result['rank']}**\n"
                    else:
                        message += f"🔴 **{d[0:-5]} | {result['score']}/{result['rate']} #{result['rank']}**\n"

            message += f"{self.get_fb_on(d, contest_id).get_formatted()[2:-4]}\n"

        message += f"\n🟢 **{wins} WINS**"
        if slate_result is not None:
            contest_name = FB_PROVIDER.contests.get(contest_id, {'name': f'{dates[0][0:-5]}~{dates[-1][0:-5]}'})['name']
            message += f"\n\nYour rank of *{contest_name}*:\n" \
                       f"**{int(slate_result['wins'])}** wins, **{round(slate_result['total_score'], 2)}** CR," \
                       f" **#{slate_result['rank']}**\n" \
                       f"*current game date not included*"

        return message

    def formatted_leaderboard(self, top, contest_id: Optional[int]):
        if self.status == GameDateStatus.PRE_GAME:
            return "Games are not started yet.\n"
        if contest_id not in self.leaderboards:
            return "No live leaderboard.\n"

        message = f"***Leaderboard {self.current_game_date}***\n" \
                  f"*{FB_PROVIDER.contests[contest_id]['name']}*\n\n"
        for i in range(0, min(top, len(self.leaderboards[contest_id]))):
            uid = self.leaderboards[contest_id][i]
            score = self.contest_scores[contest_id][uid]
            if score['passed']:
                message += "🟢 "
            else:
                message += "🔴 "
            message += f"**#{i + 1}.**  **{self.lineups[uid].username}** " \
                       f"points {score['score']}, serial {int(self.lineups[uid].serial)}\n"

        message += f"\nTotal submissions: **{len(self.contest_scores[contest_id])}**\n"

        return message

    @staticmethod
    def formatted_slate_leaderboard(dates, top, contest_id: int):
        message = f"***Slate Leaderboard {dates[0]}~{dates[-1]}***\n" \
                  f"*{FB_PROVIDER.contests[contest_id]['name']}*\n\n"
        loaded = get_slate_ranks(contest_id, dates, top)
        for i in range(0, min(top, len(loaded))):
            message += f"**#{i + 1}.** **{loaded[i]['username']}** *{loaded[i]['wins']}* wins, " \
                       f"*{round(loaded[i]['total_score'], 2)}* CR"
            if loaded[i].get('all_checked_in'):
                message += " (with +10% bonus)\n"
            else:
                message += "\n"

        return loaded[:min(10, len(loaded))], message

    def formatted_team_players(self, team: str, user_id: int) -> str:
        if team not in self.formatted_teams:
            return "{} is not playing on {}.".format(team, self.current_game_date)

        message = self.formatted_teams[team]
        message += "\n"
        has_used = False
        usage = self.user_usages.get(user_id, {})
        for pid in self.team_players[team]:
            if pid in usage:
                if not has_used:
                    has_used = True
                    message += "*PLAYERS USED*:\n"
                message += f"**{usage[pid]}x {self.players[pid]['full_name']}**\n"
        return message

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
