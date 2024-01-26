import asyncio
import datetime

from nba_api.live.nba.endpoints import boxscore

from vgnlog.channel_logger import ADMIN_LOGGER
from provider.nba.nba_provider import NBAProvider, NBA_PROVIDER
from provider.topshot.fb_provider import FB_PROVIDER
from repository.fb_lineups import get_lineups, upsert_score, get_weekly_ranks
from repository.vgn_players import get_empty_players_stats
from service.fastbreak.fastbreak import FastBreak
from service.fastbreak.lineup import Lineup, LINEUP_SERVICE
from service.fastbreak.service import FastBreakService
from utils import get_game_info


class RankingService(FastBreakService):
    def __init__(self):
        super(RankingService, self).__init__()
        self.current_game_date = ""
        self.lineups = {}
        self.games = []

        self.status = "PRE_GAME"
        self.player_stats = {}
        self.user_scores = {}
        self.leaderboard = []

        asyncio.run(self.update())

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
        self.lineups = {}
        self.user_scores = {}
        self.leaderboard = []
        self.__load_lineups()

    async def update(self):
        scoreboard = NBAProvider.get_scoreboard()
        new_status = NBAProvider.get_status(scoreboard['games'])
        if new_status == "NO_GAME" or new_status == "PRE_GAME":
            if self.status == "POST_GAME":
                await self.__update_stats()
                await self.__upload_leaderboard()

                NBA_PROVIDER.reload()
                LINEUP_SERVICE.reload()

            self.status = "PRE_GAME"
        elif self.status == "PRE_GAME":
            self.current_game_date = datetime.datetime.strptime(scoreboard['gameDate'], '%Y-%m-%d').strftime('%m/%d/%Y')
            self.games = [game['gameId'] for game in scoreboard['games']]
            # noinspection PyBroadException
            try:
                self.reload()
                self.status = new_status
                LINEUP_SERVICE.reload()
            except Exception as err:
                await ADMIN_LOGGER.error(f"FBRanking:Update:{err}")
                return
        else:
            self.status = new_status

        await self.__update_stats()

    async def __update_stats(self):
        player_stats = {}
        for game_id in self.games:
            # noinspection PyBroadException
            try:
                game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
            except Exception as err:
                await ADMIN_LOGGER.error(f"FBRanking:BoxScore:{err}")
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
        if self.status == "NO_GAME" or self.status == "PRE_GAME":
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
            message += f"**#{i+1}.** **{loaded[i]['username']}** *{loaded[i]['wins']}* wins, " \
                       f"*{round(loaded[i]['total_score'], 2)}* CR"
            if loaded[i].get('all_checked_in'):
                message += " (with +10% bonus)\n"
            else:
                message += "\n"

        return message


RANK_SERVICE = RankingService()
