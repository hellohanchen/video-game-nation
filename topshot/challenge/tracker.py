from enum import Enum

from nba_api.live.nba.endpoints import boxscore, PlayByPlay


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
            try:
                game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
            except Exception:
                continue

            if game_stats['gameStatus'] == 1:
                continue

            game_info = {
                'stats': game_stats['gameStatus'],
                'quarter': game_stats['period'],
                'clock': game_stats['gameClock'],
                'awayTeam': game_stats['awayTeam']['teamTricode'],
                'awayScore': game_stats['awayTeam']['score'],
                'homeTeam': game_stats['homeTeam']['teamTricode'],
                'homeScore': game_stats['homeTeam']['score']
            }

            if game_stats['homeTeam']['teamTricode'] in teams:
                stats = [tb.load_team_stats(game_stats['homeTeam']['players']) for tb in self.tier_breakers]
                result[game_stats['homeTeam']['teamTricode']] = {
                    'game': game_info,
                    'stats': stats
                }

            if game_stats['awayTeam']['teamTricode'] in teams:
                stats = [tb.load_team_stats(game_stats['awayTeam']['players']) for tb in self.tier_breakers]
                result[game_stats['awayTeam']['teamTricode']] = {
                    'game': game_info,
                    'stats': stats
                }

        return self.get_sorted(result)

    def get_player_stats(self, games, players):
        scores = {}

        for game_id in games:
            try:
                game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
            except Exception:
                continue

            if game_stats['gameStatus'] == 1:
                continue

            game_info = {
                'stats': game_stats['gameStatus'],
                'quarter': game_stats['period'],
                'clock': game_stats['gameClock'],
                'awayTeam': game_stats['awayTeam']['teamTricode'],
                'awayScore': game_stats['awayTeam']['score'],
                'homeTeam': game_stats['homeTeam']['teamTricode'],
                'homeScore': game_stats['homeTeam']['score']
            }

            for player_stats in game_stats['homeTeam']['players']:
                if player_stats['status'] == 'ACTIVE' and player_stats['personId'] in players:
                    statistics = player_stats['statistics']
                    statistics['teamWin'] = \
                        1 if int(game_stats['homeTeam']['score']) > int(game_stats['awayTeam']['score']) else 0
                    stats = [tb.load_play_stats(statistics) for tb in self.tier_breakers]
                    scores[player_stats['name']] = {
                        'game': game_info,
                        'stats': stats
                    }

            for player_stats in game_stats['awayTeam']['players']:
                if player_stats['status'] == 'ACTIVE' and player_stats['personId'] in players:
                    statistics = player_stats['statistics']
                    statistics['teamWin'] = \
                        1 if int(game_stats['awayTeam']['score']) > int(game_stats['homeTeam']['score']) else 0
                    stats = [tb.load_play_stats(statistics) for tb in self.tier_breakers]
                    scores[player_stats['name']] = {
                        'game': game_info,
                        'stats': stats
                    }

        return self.get_sorted(scores)

    def get_sorted(self, scores):
        keys = list(scores.keys())

        for i in range(len(self.tier_breakers) - 1, -1, -1):
            keys.sort(reverse=self.tier_breakers[i].order == "DESC", key=lambda k: scores[k]['stats'][i])

        sorted_stats = []
        idx = 0

        while len(sorted_stats) < max(5, self.count * 2) and idx < len(scores):
            sorted_stats.append({"name": keys[idx], "score": scores[keys[idx]]})
            idx += 1
            while idx < len(scores) and equals(scores[keys[idx - 1]]['stats'], scores[keys[idx]]['stats']):
                sorted_stats.append({"name": keys[idx], "score": scores[keys[idx]]})
                idx += 1

        return sorted_stats


class PlayByPlayTracker:
    def __init__(self, count_per_game):
        self.tier_breakers = []
        self.count = count_per_game

    def add_tier_breaker(self, tier_breaker):
        self.tier_breakers.append(tier_breaker)

    def get_team_stats(self, games, teams):
        result = []

        for game_id in games:
            try:
                game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
                actions = PlayByPlay(game_id).get_dict()['game']['actions']
            except Exception:
                continue

            if len(actions) == 0:
                continue

            game_info = {
                'stats': game_stats['gameStatus'],
                'quarter': game_stats['period'],
                'clock': game_stats['gameClock'],
                'awayTeam': game_stats['awayTeam']['teamTricode'],
                'awayScore': game_stats['awayTeam']['score'],
                'homeTeam': game_stats['homeTeam']['teamTricode'],
                'homeScore': game_stats['homeTeam']['score']
            }

            hit = self.tier_breakers[0].get_action(actions)

            if hit is not None:
                result.append({
                    'name': hit['teamTricode'],
                    'score': {
                        'game': game_info,
                        'stats': [
                            "Q{} {}:{}".format(
                                hit['period'],
                                int(hit['clock'][2:4]),
                                hit['clock'][5:-4]
                            )
                        ]
                    }
                })

        return result

    def get_player_stats(self, games, players):
        result = []

        for game_id in games:
            try:
                game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
                actions = PlayByPlay(game_id).get_dict()['game']['actions']
            except Exception:
                continue

            if len(actions) == 0:
                continue

            game_info = {
                'stats': game_stats['gameStatus'],
                'quarter': game_stats['period'],
                'clock': game_stats['gameClock'],
                'awayTeam': game_stats['awayTeam']['teamTricode'],
                'awayScore': game_stats['awayTeam']['score'],
                'homeTeam': game_stats['homeTeam']['teamTricode'],
                'homeScore': game_stats['homeTeam']['score']
            }

            hit = self.tier_breakers[0].get_action(actions, players)

            if hit is not None:
                result.append({
                    'name': "{} {}".format(hit['teamTricode'], hit['playerNameI']),
                    'score': {
                        'game': game_info,
                        'stats': [
                            "Q{} {}:{}".format(
                                hit['period'],
                                int(hit['clock'][2:4]),
                                hit['clock'][5:-4]
                            )
                        ]
                    }
                })

        return result

def equals(s1, s2):
    for i in range(len(s1)):
        if s1[i] != s2[i]:
            return False

    return True
