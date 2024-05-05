import datetime
from typing import Dict, List

from nba_api.live.nba.endpoints import boxscore

from constants import GameDateStatus
from provider.games.rr_provider import RR_PROVIDER
from provider.nba.nba_provider import NBAProvider, NBA_PROVIDER
from repository.rr_lineups import get_lineups, upsert_score, get_submission_count, get_slate_ranks
from service.redemptionrun.lineup import AbstractLineupService, Lineup, RR_LINEUP_SERVICE
from service.redemptionrun.redemption_run import RedemptionRun
from utils import to_slash_date, get_game_info, truncate_message


class RankingService(AbstractLineupService):
    def __init__(self):
        super(RankingService, self).__init__()
        self.lineups: Dict[int, Lineup] = {}

        self.status: GameDateStatus = GameDateStatus.PRE_GAME
        self.games: List[int] = []

        # self.teams_players_stats: Dict[int, Dict[int, Dict[str, any]]] = {}
        # self.players_stats: Dict[int, Dict[str, any]] = {}
        #
        # self.bucket_scores: List[Tuple[float, float]] = []
        self.scores: Dict[int, Dict[str, any]] = {}
        self.leaderboard: List[int] = []

        self.update()

    def __load_players_and_lineups(self):
        self.load_players()

        loaded: List[Dict[str, any]] = get_lineups(self.current_game_date, True)
        for lineup in loaded:
            self.lineups[lineup['user_id']] = Lineup(lineup, self)

    def reload(self):
        self.players = {}
        self.lineups: Dict[int, Lineup] = {}
        # self.teams_players_stats: Dict[int, Dict[int, Dict[str, any]]] = {}
        # self.players_stats: Dict[int, Dict[str, any]] = {}
        # self.bucket_scores: List[Tuple[float, float]] = []
        self.scores: Dict[int, Dict[str, any]] = {}
        self.leaderboard: List[int] = []
        self.__load_players_and_lineups()

        rr = RR_PROVIDER.get_rr(self.current_game_date)
        self.rr = RedemptionRun(rr['buckets'], self.players, rr['threshold'])

    def update(self):
        scoreboard = NBAProvider.get_scoreboard()
        new_status = NBAProvider.get_status_enum(scoreboard['games'])
        if new_status == GameDateStatus.NO_GAME or new_status == GameDateStatus.PRE_GAME:
            if self.status == GameDateStatus.POST_GAME:
                self.__update_leaderboard()
                self.__upload_leaderboard()

                NBA_PROVIDER.reload()
                RR_LINEUP_SERVICE.reload()

            self.status = GameDateStatus.PRE_GAME
        elif self.status == GameDateStatus.PRE_GAME:  # more from PRE_GAME to IN_GAME or POST_GAME
            self.current_game_date = to_slash_date(datetime.datetime.strptime(scoreboard['gameDate'], '%Y-%m-%d'))
            self.games = [game['gameId'] for game in scoreboard['games']]
            try:
                self.reload()  # load collections for today
                self.status = new_status
                RR_LINEUP_SERVICE.reload()  # move lineup_provider to next day
            except Exception as err:
                return
        else:
            self.status = new_status

        self.__update_leaderboard()

    def record_player_stats(self, all_player_stats: Dict[int, Dict[str, any]], raw_stats: Dict[str, any],
                            game_info: Dict[str, any], team_win: int) -> int:
        player_id = int(raw_stats['personId'])
        all_player_stats[player_id] = self.enrich_stats(raw_stats['statistics'])
        all_player_stats[player_id]['win'] = 1 if team_win else 0
        all_player_stats[player_id]['name'] = raw_stats['name']
        all_player_stats[player_id]['gameInfo'] = game_info
        return int(player_id)

    def __update_leaderboard(self):
        if self.status == GameDateStatus.PRE_GAME or self.status == GameDateStatus.NO_GAME:
            return

        played_player_stats: Dict[int, Dict[str, any]] = {}
        teams_players_stats: Dict[int, List[Dict[str, any]]] = {}
        for game_id in self.games:
            try:
                game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
            except Exception as err:
                continue

            if game_stats['gameStatus'] == 1:
                continue

            game_info = get_game_info(game_stats)

            team_players_stats = []
            win = game_stats['homeTeam']['score'] > game_stats['awayTeam']['score']
            for raw_stats in game_stats['homeTeam']['players']:
                if raw_stats['played'] == '1':
                    player_id = self.record_player_stats(played_player_stats, raw_stats, game_info, win)
                    team_players_stats.append(played_player_stats[player_id])
            teams_players_stats[int(game_stats['homeTeam']['teamId'])] = team_players_stats

            team_players_stats = []
            win = game_stats['awayTeam']['score'] > game_stats['homeTeam']['score']
            for raw_stats in game_stats['awayTeam']['players']:
                if raw_stats['played'] == '1':
                    player_id = self.record_player_stats(played_player_stats, raw_stats, game_info, win)
                    team_players_stats.append(played_player_stats[player_id])
            teams_players_stats[int(game_stats['awayTeam']['teamId'])] = team_players_stats

        bucket_scores = self.rr.compute_bucket_scores(teams_players_stats, played_player_stats)

        user_scores: Dict[int, Dict[str, any]] = {}
        for user_id in self.lineups:
            lineup = self.lineups[user_id]
            wins, sum_score, serials, legos, rares, message = self.rr.compute_selections_score(
                lineup.selections, bucket_scores)

            user_scores[user_id] = {
                'wins': wins,
                'sum_score': sum_score,
                'serials': serials,
                'legos': legos,
                'rares': rares,
                'message': message
            }

        user_ids = list(user_scores.keys())
        user_ids.sort(key=lambda uid: user_scores[uid]['rares'], reverse=True)
        user_ids.sort(key=lambda uid: user_scores[uid]['legos'], reverse=True)
        user_ids.sort(key=lambda uid: user_scores[uid]['serials'])
        user_ids.sort(key=lambda uid: user_scores[uid]['sum_score'], reverse=True)
        user_ids.sort(key=lambda uid: user_scores[uid]['wins'], reverse=True)

        leaderboard = []
        threshold = int(len(user_ids) * 0.5)  # TODO: confirm percentage
        for i, user_id in enumerate(user_ids):
            user_scores[user_id]['rank'] = i + 1
            user_scores[user_id]['win'] = i <= threshold
            leaderboard.append(user_id)

        self.scores = user_scores
        self.leaderboard = leaderboard

    def __upload_leaderboard(self):
        for user_id in self.scores:
            score = self.scores[user_id]
            upsert_score(
                user_id, self.current_game_date, score['wins'], score['sum_score'], score['rank'], score['win'])

    def formatted_leaderboard(self, top):
        if self.status != GameDateStatus.IN_GAME and self.status != GameDateStatus.POST_GAME:
            message = "***Leaderboard {}***\n\n".format(RR_LINEUP_SERVICE.current_game_date)
            submissions = get_submission_count(RR_LINEUP_SERVICE.current_game_date)
            return [message + "Games are not started yet.\nTotal submissions: **{}**\n".format(submissions)]

        submissions, _ = get_submission_count(self.current_game_date)
        message = f"***Leaderboard {self.current_game_date}***\n\n"
        for i in range(0, min(top, len(self.leaderboard))):
            uid = self.leaderboard[i]
            score = self.scores[uid]
            message += f"**#{i + 1}.** **{self.lineups[uid].username}**\n" \
                       f"{score['wins']}x🟢, {score['sum_score']}"

        message += f"\nTotal submissions: **{submissions}**\n"

        return message

    @staticmethod
    def formatted_slate_leaderboard(dates, top):
        messages = []
        message = "***Slate Leaderboard {}~{}***\n\n".format(dates[0], dates[-1])
        loaded = get_slate_ranks(dates, top)
        for i in range(0, min(top, len(loaded))):
            new_message = f"#**{i + 1}.**  **{loaded[i]['username']}** " \
                          f"*{loaded[i]['wins']}xWINS* *{loaded[i]['total_points']}x🟢* " \
                          f"*{loaded[i]['losses']}xLOSSES* *{loaded[i]['total_score']:.2f}*\n"
            message, _ = truncate_message(messages, message, new_message, 1950)

        if message != "":
            messages.append(message)

        return messages

    def formatted_user_score(self, user_id):
        if self.status != GameDateStatus.IN_GAME and self.status != GameDateStatus.POST_GAME:
            return ["Games are not started yet."]

        if user_id not in self.lineups:
            return ["User lineup not found."]

        if user_id not in self.scores:
            return ["Scores are not updated yet."]

        return [f"{self.scores[user_id]['message']}\n"
                f"You need to be top **{int(len(self.scores) * self.rr.threshold)}** to survive."]

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


RR_RANKING_SERVICE = RankingService()
