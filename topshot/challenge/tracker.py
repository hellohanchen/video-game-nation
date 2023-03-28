from enum import Enum

from nba_api.live.nba.endpoints import boxscore


class TrackerType(Enum):
    PLAYER = 1
    TEAM = 2


class LeaderBoardTracker:
    def __init__(self, count):
        self.tier_breakers = []
        self.count = count

    def add_tier_breaker(self, tier_breaker):
        self.tier_breakers.append(tier_breaker)

    def get_team_stats(self, games, teams):
        result = {}

        for game_id in games:
            game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
            if game_stats['gameStatus'] == 1:
                continue

            if game_stats['homeTeam']['teamTricode'] in teams:
                result[game_stats['homeTeam']['teamTricode']] = {}
                for i in range(0, len(self.tier_breakers)):
                    result[game_stats['homeTeam']['teamTricode']]["TB" + str(i)] = \
                        self.tier_breakers[i].load_team_stats(game_stats['homeTeam']['players'])

            if game_stats['awayTeam']['teamTricode'] in teams:
                result[game_stats['awayTeam']['teamTricode']] = {}
                for i in range(0, len(self.tier_breakers)):
                    result[game_stats['awayTeam']['teamTricode']]["TB" + str(i)] = \
                        self.tier_breakers[i].load_team_stats(game_stats['awayTeam']['players'])

        return self.get_sorted_result(result)

    def get_player_stats(self, games, players):
        result = {}

        for game_id in games:
            game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
            if game_stats['gameStatus'] == 1:
                continue

            for player_stats in game_stats['homeTeam']['players']:
                if player_stats['name'].lower() in players:
                    for i in range(0, len(self.tier_breakers)):
                        result[player_stats['name']]["TB" + str(i)] = \
                            self.tier_breakers[i].load_play_stats(player_stats)

            for player_stats in game_stats['awayTeam']['players']:
                if player_stats['name'].lower() in players:
                    for i in range(0, len(self.tier_breakers)):
                        result[player_stats['name']]["TB" + str(i)] = \
                            self.tier_breakers[i].load_play_stats(player_stats)

        return self.get_sorted_result(result)

    def get_sorted_result(self, result):
        keys = list(result.keys())

        for i in range(len(self.tier_breakers) - 1, -1, -1):
            keys.sort(reverse=self.tier_breakers[i].order == "DESC", key=lambda k: result[k]["TB" + str(i)])

        return [result[k] for k in keys]
