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
        scores_for_leaderboard = []
        if len(self.tier_breakers) > 0:
            first_tb = self.tier_breakers[0]
            first_score = first_tb.load_player_stats(player_stats)
            if first_score == 0:  # skip players without stats
                return scores_for_leaderboard
            else:
                scores_for_leaderboard.append(first_score)

        for i in range(1, len(self.tier_breakers)):
            scores_for_leaderboard.append(self.tier_breakers[i].load_player_stats(player_stats))

        return scores_for_leaderboard

    def get_player_scores(self, games_players: Dict[str, List[int]]) -> Tuple[int, List[Dict[str, Any]]]:
        scores: Dict[str, Dict[str, Any]] = {}

        all_final = True
        for game_id in games_players:
            game_boxscore, game_is_final, game_info = Tracker.load_game_stats(game_id)
            all_final &= game_is_final
            if game_boxscore is None:
                continue

            home_team_score = game_boxscore['homeTeam']['score']
            away_team_score = game_boxscore['awayTeam']['score']
            wins = {
                'homeTeam': 1 if home_team_score > away_team_score else 0,
                'awayTeam': 1 if away_team_score > home_team_score else 0
            }

            for team in ['homeTeam', 'awayTeam']:
                for player_boxscore in game_boxscore[team]['players']:
                    if player_boxscore['status'] == 'ACTIVE' and player_boxscore['personId'] in games_players[game_id]:
                        statistics = player_boxscore['statistics']
                        statistics['order'] = player_boxscore['order']
                        statistics['teamWin'] = wins[team]
                        scores_for_leaderboard = self.load_player_stats(statistics)
                        if len(scores_for_leaderboard) > 0:  # skip players without valid stats
                            scores[player_boxscore['name'] + '/' + str(game_id)] = {
                                'game': game_info,
                                'stats': scores_for_leaderboard
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
        # Sort the keys in descending order based on the scores for each tier breaker, as specified by the order of the
        # tier breakers in the leaderboard tracker
        sorted_keys = list(scores.keys())
        sorted_keys.sort(reverse=self.tier_breakers[0].order == "DESC", key=lambda k: scores[k]['stats'][0])
        sorted_keys = sorted_keys[0:30]  # only keep top 30 records to save time
        for i in range(len(self.tier_breakers) - 1, -1, -1):
            sorted_keys.sort(reverse=self.tier_breakers[i].order == "DESC", key=lambda k: scores[k]['stats'][i])

        # Append the top 2 * count (or at least 5) players/teams to the sorted_stats list, sorted by their total scores
        # across all tier breakers, as well as any players/teams with the same total score as the last player/team in
        # the sorted_stats list
        num_to_display = max(5, self.count * 2) if not all_final else self.count

        sorted_scores = []
        idx = 0
        hit = 0
        while len(sorted_scores) < num_to_display and idx < len(sorted_keys):
            # for extra score, we don't need to show ended games
            if hit < self.count or scores[sorted_keys[idx]]['game']['status'] != 3:
                sorted_scores.append({"name": sorted_keys[idx], "score": scores[sorted_keys[idx]]})
                idx += 1

                while idx < len(sorted_keys) and equals(scores[sorted_keys[idx - 1]]['stats'], scores[sorted_keys[idx]]['stats']):
                    if hit < self.count or scores[sorted_keys[idx]]['game']['status'] != 3:
                        sorted_scores.append({"name": sorted_keys[idx], "score": scores[sorted_keys[idx]]})
                        idx += 1
                if idx >= self.count > hit:
                    hit = idx
            else:
                idx += 1

        return hit, sorted_scores


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
