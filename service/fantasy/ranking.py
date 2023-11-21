import datetime

from nba_api.live.nba.endpoints import boxscore

from provider.nba_provider import NBAProvider, NBA_PROVIDER
from repository.vgn_collections import get_collections
from repository.vgn_lineups import get_lineups
from repository.vgn_players import get_empty_players_stats
from repository.vgn_users import get_users
from service.fantasy.lineup import Lineup, LINEUP_PROVIDER
from utils import compute_vgn_score, truncate_message, compute_vgn_scores, get_game_info


class RankingProvider:
    def __init__(self):
        self.current_game_date = ""
        self.lineups = {}
        self.collections = {}

        self.status = "PRE_GAME"
        self.games = []

        self.player_stats = {}
        self.scores = {}
        self.leaderboard = []

        self.update()

    def __load_lineups_and_collections(self):
        game_day_players = []
        for game_id, game in NBA_PROVIDER.get_games_on_date(self.current_game_date).items():
            for team in [game['homeTeam'], game['awayTeam']]:
                for player in NBA_PROVIDER.get_players_for_team(team):
                    game_day_players.append(player)

        loaded = get_lineups(self.current_game_date, True)
        player_ids = []
        for lineup in loaded:
            self.lineups[lineup['user_id']] = Lineup(lineup, self)

        if len(self.lineups) > 0:
            all_collections = get_collections(self.lineups.keys(), game_day_players)
            all_users = get_users(self.lineups.keys())

            for user_id in self.lineups:
                self.collections[user_id] = {
                    0: all_users[user_id]['topshot_username']
                }
                player_ids.extend(self.lineups[user_id].player_ids)
                for player_id in self.lineups[user_id].player_ids:
                    self.collections[user_id][player_id] = all_collections[user_id].get(player_id)

            player_ids = list(set(player_ids))
            self.player_stats = get_empty_players_stats(player_ids)

    def reload(self):
        self.lineups = {}
        self.collections = {}
        self.leaderboard = {}
        self.__load_lineups_and_collections()

    def update(self):
        scoreboard = NBAProvider.get_scoreboard()
        new_status = self.get_status(scoreboard['games'])
        if new_status == "NO_GAME" or new_status == "PRE_GAME":
            if self.status == "POST_GAME":
                NBA_PROVIDER.reload()
                LINEUP_PROVIDER.reload()

            self.status = "PRE_GAME"
        elif self.status == "PRE_GAME":
            self.current_game_date = datetime.datetime.strptime(scoreboard['gameDate'], '%Y-%m-%d').strftime('%m/%d/%Y')
            self.games = [game['gameId'] for game in scoreboard['games']]
            try:
                self.reload()
                self.status = new_status
                LINEUP_PROVIDER.reload()
            except:
                return
        else:
            self.status = new_status

        self.__update_leaderboard()

    def __update_leaderboard(self):
        player_stats = {}
        for game_id in self.games:
            try:
                game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
            except Exception:
                continue

            if game_stats['gameStatus'] == 1:
                continue

            game_info = get_game_info(game_stats)

            win = game_stats['homeTeam']['score'] > game_stats['awayTeam']['score']
            for player in game_stats['homeTeam']['players']:
                if player['status'] == 'ACTIVE':
                    player_stats[player['personId']] = self.enrich_stats(player['statistics'])
                    player_stats[player['personId']]['win'] = 1 if win else 0
                    player_stats[player['personId']]['name'] = player['name']
                    player_stats[player['personId']]['gameInfo'] = game_info

            win = game_stats['awayTeam']['score'] > game_stats['homeTeam']['score']
            for player in game_stats['awayTeam']['players']:
                if player['status'] == 'ACTIVE':
                    player_stats[player['personId']] = self.enrich_stats(player['statistics'])
                    player_stats[player['personId']]['win'] = 1 if win else 0
                    player_stats[player['personId']]['name'] = player['name']
                    player_stats[player['personId']]['gameInfo'] = game_info

        scores = {}
        for user_id in self.lineups:
            vgn_scores = [compute_vgn_score(
                player_stats.get(player_id),
                self.collections[user_id].get(player_id)
            ) for player_id in self.lineups[user_id].player_ids]
            scores[user_id] = {
                'score': sum([vgn_scores[0] * 1.5, vgn_scores[1], vgn_scores[2], vgn_scores[3], vgn_scores[4],
                              vgn_scores[5] * 0.5, vgn_scores[6] * 0.5, vgn_scores[7] * 0.5])
            }

        user_ids = list(scores.keys())
        user_ids.sort(key=lambda user_id: scores[user_id]['score'], reverse=True)

        leaderboard = []
        for i, user_id in enumerate(user_ids):
            scores[user_id]['rank'] = i + 1
            leaderboard.append(user_id)

        for player_id in player_stats:
            self.player_stats[player_id] = player_stats[player_id]
        self.scores = scores
        self.leaderboard = leaderboard

    def formatted_leaderboard(self, top):
        if self.status != "IN_GAME":
            return ["Games are not started yet."]

        messages = []
        message = "***Leaderboard {}***\n\n".format(self.current_game_date)
        for i in range(0, min(top, len(self.leaderboard))):
            new_message = "#**{}.**  **{}** *+{:.2f}v*\n".format(
                i + 1, self.collections[self.leaderboard[i]][0], self.scores[self.leaderboard[i]]['score'])
            message, _ = truncate_message(messages, message, new_message, 1950)

        if message != "":
            messages.append(message)

        return messages

    def formatted_user_score(self, user_id):
        if self.status == "NO_GAME" or self.status == "PRE_GAME":
            return ["Games are not started yet."]

        if user_id not in self.lineups:
            return ["User lineup not found."]

        if user_id not in self.scores:
            return ["Scores are not updated yet."]

        messages = []
        message = "**{} +{:.2f}v Rank#{}**\n".format(
            self.collections[user_id][0], self.scores[user_id]['score'], self.scores[user_id]['rank']
        )
        for i in range(0, 8):
            new_message = self.formatted_player(user_id, i)
            message, _ = truncate_message(messages, message, new_message, 1950)

        if message != "":
            messages.append(message)

        return messages

    def formatted_player(self, user_id, idx):
        player_id = self.lineups[user_id].player_ids[idx]
        if player_id is None:
            if idx == 0:
                message = "🏅 No player"
            elif idx < 5:
                message = "🏀 No player"
            else:
                message = "🎽 No player"
            return message

        player = self.player_stats.get(player_id)
        collection = self.collections[user_id][player_id]
        _, total_score, total_bonus = compute_vgn_scores(player, collection)

        if idx == 0:
            message = "🏅 **{} +{:.2f}v** (+{:.2f}v) ".format(player['name'], total_score, total_bonus)
        elif idx < 5:
            message = "🏀 **{} +{:.2f}v** (+{:.2f}v) ".format(player['name'], total_score, total_bonus)
        else:
            message = "🎽 **{} +{:.2f}v** (+{:.2f}v) ".format(player['name'], total_score, total_bonus)

        message += "{} {}-{} {} {}\n".format(
            player['gameInfo']['awayTeam'], player['gameInfo']['awayScore'],
            player['gameInfo']['homeScore'], player['gameInfo']['homeTeam'],
            player['gameInfo']['statusText']
        )
        message += "{}pts {}reb {}ast {}stl {}blk {}x3p\n{}mfg {}mft {}tov {}pfs {}win\n".format(
            player["points"], player["reboundsTotal"], player['assists'], player['steals'], player['blocks'],
            player["threePointersMade"], player["fieldGoalsMissed"], player['freeThrowsMissed'], player['turnovers'],
            player['foulsPersonal'], player['win']
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

    @staticmethod
    def get_status(games):
        if len(games) == 0:
            return "NO_GAME"

        started = False
        final = True
        for game in games:
            if game['gameStatus'] > 1:
                started = True
            if game['gameStatus'] < 3:
                final = False

        if not started and not final:
            return "PRE_GAME"
        if started and not final:
            return "IN_GAME"
        if started and final:
            return "POST_GAME"


RANK_PROVIDER = RankingProvider()
