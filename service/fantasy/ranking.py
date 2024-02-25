import datetime
from typing import Dict

from nba_api.live.nba.endpoints import boxscore

from provider.nba.nba_provider import NBAProvider, NBA_PROVIDER
from repository.vgn_collections import get_collections
from repository.vgn_lineups import get_lineups, upsert_score, get_weekly_ranks, get_submission_count
from repository.vgn_players import get_empty_players_stats
from repository.vgn_users import get_users
from service.fantasy.lineup import Lineup, LINEUP_PROVIDER, LINEUP_SIZE
from utils import compute_vgn_score, truncate_message, compute_vgn_scores, get_game_info, to_slash_date


class RankingProvider:
    def __init__(self):
        self.current_game_date = ""
        self.lineups = {}
        self.collections: Dict[int, Dict[int, Dict[str, int]]] = {}

        self.status = "PRE_GAME"
        self.games = []

        self.player_stats = {}
        self.scores = {}
        self.leaderboard = []
        self.player_leaderboard = []

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
                    if player_id is None:
                        continue

                    self.collections[user_id][player_id] = all_collections[user_id].get(player_id)

            player_ids = list(set(player_ids))
            if None in player_ids:
                player_ids.remove(None)
            self.player_stats = get_empty_players_stats(player_ids)

    def reload(self):
        self.lineups = {}
        self.collections = {}
        self.player_stats = {}
        self.scores = {}
        self.leaderboard = []
        self.player_leaderboard = []
        self.__load_lineups_and_collections()

    def update(self):
        scoreboard = NBAProvider.get_scoreboard()
        new_status = NBAProvider.get_status(scoreboard['games'])
        if new_status == "NO_GAME" or new_status == "PRE_GAME":
            if self.status == "POST_GAME":
                self.__update_leaderboard()
                self.__upload_leaderboard()

                NBA_PROVIDER.reload()
                LINEUP_PROVIDER.reload()

            self.status = "PRE_GAME"
        elif self.status == "PRE_GAME":  # more from PRE_GAME to IN_GAME or POST_GAME
            self.current_game_date = to_slash_date(datetime.datetime.strptime(scoreboard['gameDate'], '%Y-%m-%d'))
            self.games = [game['gameId'] for game in scoreboard['games']]
            try:
                self.reload()  # load collections for today
                self.status = new_status
                LINEUP_PROVIDER.reload()  # move lineup_provider to next day
            except Exception as err:
                return
        else:
            self.status = new_status

        self.__update_leaderboard()

    def record_player_stats(self, all_player_stats, raw_stats, game_info, team_win):
        if raw_stats['played'] == '1':
            player_id = raw_stats['personId']
            all_player_stats[player_id] = self.enrich_stats(raw_stats['statistics'])
            all_player_stats[player_id]['win'] = 1 if team_win else 0
            all_player_stats[player_id]['name'] = raw_stats['name']
            all_player_stats[player_id]['gameInfo'] = game_info
            if player_id in self.player_stats:
                all_player_stats[player_id]['current_salary'] = self.player_stats[player_id]['current_salary']
            else:
                all_player_stats[player_id]['current_salary'] = None

    def __update_leaderboard(self):
        if self.status == "PRE_GAME" or self.status == "NO_GAME":
            return

        all_player_stats: Dict[int, Dict[str, any]] = {}
        for game_id in self.games:
            try:
                game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
            except Exception as err:
                continue

            if game_stats['gameStatus'] == 1:
                continue

            game_info = get_game_info(game_stats)

            win = game_stats['homeTeam']['score'] > game_stats['awayTeam']['score']
            for raw_stats in game_stats['homeTeam']['players']:
                if raw_stats['played'] == '1':
                    self.record_player_stats(all_player_stats, raw_stats, game_info, win)

            win = game_stats['awayTeam']['score'] > game_stats['homeTeam']['score']
            for raw_stats in game_stats['awayTeam']['players']:
                if raw_stats['played'] == '1':
                    self.record_player_stats(all_player_stats, raw_stats, game_info, win)

        user_scores: Dict[int, Dict[str, float]] = {}
        for user_id in self.lineups:
            vgn_scores = [compute_vgn_score(
                all_player_stats.get(player_id),
                self.collections[user_id].get(player_id)
            ) for player_id in self.lineups[user_id].player_ids]

            for i in range(0, 8):
                player_id = self.lineups[user_id].player_ids[i]
                player_stats = all_player_stats.get(player_id)
                if player_stats is None:
                    vgn_scores[i] = vgn_scores[8]
                    break

            user_scores[user_id] = {
                'score': sum([vgn_scores[0] * 1.5, vgn_scores[1], vgn_scores[2], vgn_scores[3], vgn_scores[4],
                              vgn_scores[5] * 0.5, vgn_scores[6] * 0.5, vgn_scores[7] * 0.5])
            }

        user_ids = list(user_scores.keys())
        user_ids.sort(key=lambda uid: user_scores[uid]['score'], reverse=True)

        leaderboard = []
        for i, user_id in enumerate(user_ids):
            user_scores[user_id]['rank'] = i + 1
            leaderboard.append(user_id)

        self.scores = user_scores
        self.leaderboard = leaderboard

        player_scores = {}
        for player_id in all_player_stats:
            self.player_stats[player_id] = all_player_stats[player_id]
            player_scores[player_id] = compute_vgn_score(all_player_stats[player_id])
        player_ids = list(player_scores.keys())
        player_ids.sort(key=lambda pid: player_scores[pid], reverse=True)
        self.player_leaderboard = player_ids

    def __upload_leaderboard(self):
        for user_id in self.lineups:
            upsert_score(user_id, self.lineups[user_id].game_date, self.scores[user_id]['score'])

    def formatted_leaderboard(self, top):
        if self.status != "IN_GAME" and self.status != "POST_GAME":
            message = "***Leaderboard {}***\n\n".format(LINEUP_PROVIDER.coming_game_date)
            submissions = get_submission_count(LINEUP_PROVIDER.coming_game_date)
            return [message + "Games are not started yet.\nTotal submissions: **{}**\n".format(submissions)]

        message = "***Leaderboard {}***\n\n".format(self.current_game_date)
        messages = []
        for i in range(0, min(top, len(self.leaderboard))):
            new_message = "#**{}.**  **{}** *+{:.2f}v*\n".format(
                i + 1, self.collections[self.leaderboard[i]][0], self.scores[self.leaderboard[i]]['score'])
            message, _ = truncate_message(messages, message, new_message, 1950)

        message, _ = truncate_message(messages, message, "Total submissions: **{}**\n".format(len(self.lineups)), 1950)
        if message != "":
            messages.append(message)

        return messages

    def formatted_players(self, top):
        if self.status != "IN_GAME" and self.status != "POST_GAME":
            message = "***Players {}***\n\n".format(LINEUP_PROVIDER.coming_game_date)
            return [message + "Games are not started yet.\n"]

        message = "***Players {}***\n\n".format(self.current_game_date)
        messages = []
        for i in range(0, min(top, len(self.player_leaderboard))):
            new_message = self.__formatted_player_by_id(self.player_leaderboard[i], i + 1)
            message, _ = truncate_message(messages, message, new_message, 1950)

        if message != "":
            messages.append(message)

        return messages

    @staticmethod
    def formatted_weekly_leaderboard(dates, top):
        messages = []
        message = "***Weekly Leaderboard {}~{}***\n\n".format(dates[0], dates[-1])
        loaded = get_weekly_ranks(dates, top)
        for i in range(0, min(top, len(loaded))):
            new_message = "#**{}.**  **{}** *+{:.2f}v*\n".format(
                i + 1, loaded[i]['username'], loaded[i]['total_score'])
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
        message = "**{} {:.2f}v Rank#{}**\n".format(
            self.collections[user_id][0], self.scores[user_id]['score'], self.scores[user_id]['rank']
        )
        for i in range(0, LINEUP_SIZE):
            new_message = self.formatted_player(user_id, i)
            message, _ = truncate_message(messages, message, new_message, 1950)

        if message != "":
            messages.append(message)

        return messages

    def formatted_player(self, user_id, idx):
        player_id = self.lineups[user_id].player_ids[idx]
        if player_id is None:
            if idx == 0:
                message = "🏅 No player\n\n"
            elif idx < 5:
                message = "🏀 No player\n\n"
            elif idx < 8:
                message = "🎽 No player\n\n"
            else:
                message = "🚩 No player\n\n"
            return message

        player = self.player_stats.get(player_id)
        collection = self.collections[user_id][player_id]
        _, total_score, total_bonus = compute_vgn_scores(player, collection)

        if idx == 0:
            message = "🏅 **{} {:.2f}v** (+{:.2f}v) ".format(player['name'], total_score, total_bonus)
        elif idx < 5:
            message = "🏀 **{} {:.2f}v** (+{:.2f}v) ".format(player['name'], total_score, total_bonus)
        elif idx < 8:
            message = "🎽 **{} {:.2f}v** (+{:.2f}v) ".format(player['name'], total_score, total_bonus)
        else:
            message = "🚩 **{} {:.2f}v** (+{:.2f}v) ".format(player['name'], total_score, total_bonus)

        message += "{} {}-{} {} {}\n".format(
            player['gameInfo']['awayTeam'], player['gameInfo']['awayScore'],
            player['gameInfo']['homeScore'], player['gameInfo']['homeTeam'],
            player['gameInfo']['statusText']
        )
        message += "{}pts {}reb[{}+{}] {}ast {}stl {}blk\n[{}/{}]fg [{}/{}]3p [{}/{}]ft {}tov {}fouls {}\n".format(
            player["points"], player['reboundsTotal'], player["reboundsOffensive"], player["reboundsDefensive"],
            player['assists'], player['steals'], player['blocks'],
            player['fieldGoalsMade'], player['fieldGoalsAttempted'],
            player["threePointersMade"], player['threePointersAttempted'],
            player["freeThrowsMade"], player['freeThrowsAttempted'],
            player['turnovers'], player['foulsPersonal'], 'WIN' if player['win'] else ''
        )

        return message

    def __formatted_player_by_id(self, player_id, rank):
        player = self.player_stats.get(player_id)
        _, total_score, _ = compute_vgn_scores(player)

        message = "***#{}.*** **{} {:.2f}v **".format(rank, player['name'], total_score)

        message += "{} {}-{} {} {} ".format(
            player['gameInfo']['awayTeam'], player['gameInfo']['awayScore'],
            player['gameInfo']['homeScore'], player['gameInfo']['homeTeam'],
            player['gameInfo']['statusText']
        )
        if player['current_salary'] is None:
            message += "**no pick**\n"
        else:
            message += "**${:.2f}m**\n".format(player['current_salary'] / 100)

        message += "{}pts {}reb[{}+{}] {}ast {}stl {}blk\n[{}/{}]fg [{}/{}]3p [{}/{}]ft {}tov {}fouls {}\n".format(
            player["points"], player['reboundsTotal'], player["reboundsOffensive"], player["reboundsDefensive"],
            player['assists'], player['steals'], player['blocks'],
            player['fieldGoalsMade'], player['fieldGoalsAttempted'],
            player["threePointersMade"], player['threePointersAttempted'],
            player["freeThrowsMade"], player['freeThrowsAttempted'],
            player['turnovers'], player['foulsPersonal'], 'WIN' if player['win'] else ''
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


RANK_PROVIDER = RankingProvider()
