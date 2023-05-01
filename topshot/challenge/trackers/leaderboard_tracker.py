from typing import List, Dict, Any, Union, Tuple

from topshot.challenge.tier_breaker import TierBreaker, Qualifier
from topshot.challenge.trackers.tracker import Tracker
from utils import equals


class LeaderBoardTracker(Tracker):
    """
    Represents a leaderboard tracker that tracks players or teams statistics.

    :param: count: the maximum number of results to return
    """

    def __init__(self, count: int):
        super().__init__()
        self.count: int = count

    def add_tier_breaker(self, tier_breaker: TierBreaker) -> None:
        """
        Add a tier breaker to the leaderboard tracker.

        :param: tier_breaker: the tier breaker to add
        """
        self.tier_breakers.append(tier_breaker)

    def load_team_stats(self, team_player_stats: List[Dict[str, Any]]) -> List[float]:
        """
        Load team statistics based on the specified tier breakers.

        :param: team_player_stats: list of player statistics for a team
        :return: a list of float values containing the team scores based on the tier breakers
        """
        return [tb.load_team_stats(team_player_stats) for tb in self.tier_breakers]

    def get_team_scores(self, games_teams: Dict[str, List[str]]) -> Tuple[int, List[Dict[str, Any]]]:
        scores: Dict[str, Dict[str, Any]] = {}

        all_final = True
        for game_id in games_teams:
            game_stats, game_final, game_info = Tracker.load_game_stats(game_id)
            all_final &= game_final
            if game_stats is None:
                continue

            if game_stats['homeTeam']['teamTricode'] in games_teams[game_id]:
                scores[game_stats['homeTeam']['teamTricode'] + '/' + str(game_id)] = {
                    'game': game_info,
                    'stats': self.load_team_stats(game_stats['homeTeam']['players'])
                }

            if game_stats['awayTeam']['teamTricode'] in games_teams[game_id]:
                scores[game_stats['awayTeam']['teamTricode'] + '/' + str(game_id)] = {
                    'game': game_info,
                    'stats': self.load_team_stats(game_stats['awayTeam']['players'])
                }

        return self.sort(scores, all_final)

    def load_player_stats(self, player_stats: Dict[str, Any]) -> List[Any]:
        """
        Load player statistics based on the specified tier breakers.

        :param player_stats: dictionary of statistics for a player
        :return: a list of values containing the player scores based on the tier breakers
        """
        return [tb.load_player_stats(player_stats) for tb in self.tier_breakers]

    def get_player_scores(self, games_players: Dict[str, List[int]]) -> Tuple[int, List[Dict[str, Any]]]:
        scores: Dict[str, Dict[str, Any]] = {}

        all_final = True
        for game_id in games_players:
            game_stats, game_final, game_info = Tracker.load_game_stats(game_id)
            all_final &= game_final
            if game_stats is None:
                continue

            for player_stats in game_stats['homeTeam']['players']:
                if player_stats['status'] == 'ACTIVE' and player_stats['personId'] in games_players[game_id]:
                    statistics = player_stats['statistics']
                    statistics['teamWin'] = \
                        1 if int(game_stats['homeTeam']['score']) > int(game_stats['awayTeam']['score']) else 0
                    scores[player_stats['name'] + '/' + str(game_id)] = {
                        'game': game_info,
                        'stats': self.load_player_stats(statistics)
                    }

            for player_stats in game_stats['awayTeam']['players']:
                if player_stats['status'] == 'ACTIVE' and player_stats['personId'] in games_players[game_id]:
                    statistics = player_stats['statistics']
                    statistics['teamWin'] = \
                        1 if int(game_stats['homeTeam']['score']) > int(game_stats['awayTeam']['score']) else 0
                    scores[player_stats['name'] + '/' + str(game_id)] = {
                        'game': game_info,
                        'stats': self.load_player_stats(statistics)
                    }

        return self.sort(scores, all_final)

    def sort(self, scores: Dict[str, Dict[str, Union[Dict[str, Any], List[float]]]], all_final: bool) \
            -> Tuple[int, List[Dict[str, Any]]]:
        """
        Sort the scores based on the specified tier breakers.

        :param: scores: dictionary mapping names to dictionaries containing score statistics
        :param: all_final: a boolean indicating whether to return all teams/players or just the top teams/players
        :return: a tuple containing the total number of teams/players and a list of dictionaries containing team/player
                information and scores
        """
        keys = list(scores.keys())

        # Sort the keys in descending order based on the scores for each tier breaker, as specified by the order of the
        # tier breakers in the leaderboard tracker
        for i in range(len(self.tier_breakers) - 1, -1, -1):
            keys.sort(reverse=self.tier_breakers[i].order == "DESC", key=lambda k: scores[k]['stats'][i])

        sorted_stats = []
        idx = 0

        # Append the top 2 * count (or at least 5) players/teams to the sorted_stats list, sorted by their total scores
        # across all tier breakers, as well as any players/teams with the same total score as the last player/team in
        # the sorted_stats list
        out_count = max(5, self.count * 2) if not all_final else self.count
        hit = len(scores)
        while len(sorted_stats) < out_count and idx < len(scores):
            sorted_stats.append({"name": keys[idx], "score": scores[keys[idx]]})
            idx += 1
            while idx < len(scores) and equals(scores[keys[idx - 1]]['stats'], scores[keys[idx]]['stats']):
                sorted_stats.append({"name": keys[idx], "score": scores[keys[idx]]})
                idx += 1
            if idx >= self.count:
                hit = idx

        return hit, sorted_stats


class QualifierTracker(LeaderBoardTracker):
    def __init__(self):
        super().__init__(0)
        self.tier_breakers: List[Qualifier] = []

    def add_tier_breaker(self, tier_breaker: TierBreaker) -> None:
        assert isinstance(tier_breaker, Qualifier), "filter tracker can only use filter breaker"
        self.tier_breakers.append(tier_breaker)

    def load_team_stats(self, team_player_stats: List[Dict]) -> [float]:
        return self.enrich_stats([tb.load_team_stats(team_player_stats) for tb in self.tier_breakers])

    def load_player_stats(self, player_stats: Dict) -> [Any]:
        return self.enrich_stats([tb.load_player_stats(player_stats) for tb in self.tier_breakers])

    def enrich_stats(self, stats: List[Tuple[float, int]]) -> List[float]:
        """
        Enrich the statistics for the qualifier tracker.

        :param: stats: list of statistics for a team/player
        :return: a list of enriched statistics
        """
        total = sum([1.0 if stat[0] == 1.0 else 0.0 for stat in stats])
        progress = sum([stat[0] for stat in stats])
        raw = [stat[1] for stat in stats]

        return [
            '☑' if total >= len(self.tier_breakers) else '☒',
            int(100.0 * progress / float(len(self.tier_breakers)))
        ] + raw

    def sort(self, scores: Dict[str, Dict[str, Union[Dict[str, Any], List[float]]]], all_final: bool) \
            -> Tuple[int, List[Dict[str, Any]]]:
        """
        Sort the scores based on the specified tier breakers.

        :param: scores: dictionary mapping names to dictionaries containing score statistics
        :param: all_final: a boolean indicating whether to return all teams/players or just the top teams/players
        :return: a tuple containing the total number of teams/players and a list of dictionaries containing team/player
                information and scores
        """
        keys = []
        passed = 0

        for key, value in scores.items():
            # if a stats doesn't fulfill the predicate and the game is ended already, skip
            if value['stats'][0] != '☑' and value['game']['status'] == 3:
                continue

            keys.append(key)
            if value['stats'][0] == '☑':
                passed += 1

        # Sort the keys in descending order based on the scores for each tier breaker, as specified by the order of the
        # tier breakers in the leaderboard tracker
        for i in range(len(self.tier_breakers) - 1, -1, -1):
            keys.sort(reverse=True, key=lambda k: scores[k]['stats'][i + 2])

        sorted_stats = []
        idx = 0

        # append all passed stats to the list and add 5 more
        self.count = passed
        out_count = self.count + 5
        while len(sorted_stats) < out_count and idx < len(keys):
            sorted_stats.append({
                "name": keys[idx],
                "score": {
                    'game': scores[keys[idx]]['game'],
                    'stats': scores[keys[idx]]['stats'][2:]
                }
            })
            idx += 1
            while idx < len(keys) and equals(scores[keys[idx - 1]]['stats'], scores[keys[idx]]['stats']):
                sorted_stats.append({
                    "name": keys[idx],
                    "score": {
                        'game': scores[keys[idx]]['game'],
                        'stats': scores[keys[idx]]['stats'][2:]
                    }
                })
                idx += 1

        return passed, sorted_stats
