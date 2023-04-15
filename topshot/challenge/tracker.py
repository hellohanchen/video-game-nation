from typing import List, Dict, Any, Tuple, Union

from nba_api.live.nba.endpoints import boxscore, PlayByPlay

from topshot.challenge.tier_breaker import TierBreaker
from utils import get_game_info


class LeaderBoardTracker:
    """
    Represents a leaderboard tracker that tracks players or teams statistics.

    :param count: the maximum number of results to return
    """
    def __init__(self, count: int):
        self.tier_breakers: List[TierBreaker] = []
        self.count: int = count

    def add_tier_breaker(self, tier_breaker: TierBreaker) -> None:
        """
        Add a tier breaker to the leaderboard tracker.

        :param tier_breaker: the tier breaker to add
        """
        self.tier_breakers.append(tier_breaker)

    def get_team_ranking(self, games_teams: Dict[int, List[str]]) -> List[Dict[str, Any]]:
        """
        Get the team statistics for a set of games.

        :param games_teams: a dictionary mapping game IDs to a list of team tricodes
        :return: a list of dictionaries representing the team statistics, sorted by ranking
        """
        result: Dict[str, Dict[str, Any]] = {}

        final = True
        for game_id in games_teams:
            try:
                game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
            except Exception:
                continue

            if game_stats['gameStatus'] == 1:
                continue
            if game_stats['gameStatus'] != 3:
                final = False

            game_info = get_game_info(game_stats)

            if game_stats['homeTeam']['teamTricode'] in games_teams[game_id]:
                stats = [tb.load_team_stats(game_stats['homeTeam']['players']) for tb in self.tier_breakers]
                result[game_stats['homeTeam']['teamTricode'] + '/' + str(game_id)] = {
                    'game': game_info,
                    'stats': stats
                }

            if game_stats['awayTeam']['teamTricode'] in games_teams[game_id]:
                stats = [tb.load_team_stats(game_stats['awayTeam']['players']) for tb in self.tier_breakers]
                result[game_stats['awayTeam']['teamTricode'] + '/' + str(game_id)] = {
                    'game': game_info,
                    'stats': stats
                }

        return self.get_ranking(result, final)

    def get_player_ranking(self, games_players: Dict[int, List[int]]) -> List[Dict[str, Any]]:
        """
        Get the player statistics for a set of games.

        :param games_players: a dictionary mapping game IDs to a list of player IDs
        :return: a list of dictionaries representing the player statistics, sorted by ranking
        """
        scores = {}

        final = True
        for game_id in games_players:
            try:
                game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
            except Exception:
                continue

            if game_stats['gameStatus'] == 1:
                continue
            if game_stats['gameStatus'] != 3:
                final = False

            game_info = get_game_info(game_stats)

            for player_stats in game_stats['homeTeam']['players']:
                if player_stats['status'] == 'ACTIVE' and player_stats['personId'] in games_players[game_id]:
                    statistics = player_stats['statistics']
                    statistics['teamWin'] = \
                        1 if int(game_stats['homeTeam']['score']) > int(game_stats['awayTeam']['score']) else 0
                    stats = [tb.load_play_stats(statistics) for tb in self.tier_breakers]
                    scores[player_stats['name'] + '/' + str(game_id)] = {
                        'game': game_info,
                        'stats': stats
                    }

            for player_stats in game_stats['awayTeam']['players']:
                if player_stats['status'] == 'ACTIVE' and player_stats['personId'] in games_players[game_id]:
                    statistics = player_stats['statistics']
                    statistics['teamWin'] = \
                        1 if int(game_stats['awayTeam']['score']) > int(game_stats['homeTeam']['score']) else 0
                    stats = [tb.load_play_stats(statistics) for tb in self.tier_breakers]
                    scores[player_stats['name'] + '/' + str(game_id)] = {
                        'game': game_info,
                        'stats': stats
                    }

        return self.get_ranking(scores, final)

    def get_ranking(self, scores: Dict[str, Dict[str, Union[str, List[float]]]], final: bool) \
            -> List[Dict[str, Union[str, Dict[str, Union[str, List[float]]]]]]:
        """
        Given a dictionary of player/team scores, calculates the ranking based on the provided tier breakers.

        Parameters:
        scores (Dict[str, Dict[str, Union[str, List[float]]]]): a dictionary of player/team scores, where each key
            corresponds to the name of a player/team, and each value is a dictionary containing the game information
            (e.g. the name of the opposing team, the quarter, the clock, etc.) and a list of numerical scores
            (one for each tier breaker)

        Returns:
        sorted_stats (List[Dict[str, Union[str, Dict[str, Union[str, List[float]]]]]]): a list of dictionaries, each
            containing the name of a player/team and their corresponding game information and scores, sorted in
            descending order based on the tier breakers
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
        out_count = max(5, self.count * 2) if not final else self.count
        while len(sorted_stats) < out_count and idx < len(scores):
            sorted_stats.append({"name": keys[idx], "score": scores[keys[idx]]})
            idx += 1
            while idx < len(scores) and equals(scores[keys[idx - 1]]['stats'], scores[keys[idx]]['stats']):
                sorted_stats.append({"name": keys[idx], "score": scores[keys[idx]]})
                idx += 1

        return sorted_stats


class PlayByPlayTracker:
    def __init__(self, count_per_game: int):
        self.tier_breakers = []
        self.count = count_per_game

    def add_tier_breaker(self, tier_breaker: TierBreaker) -> None:
        """
        Add a tier breaker to the tracker.

        Args:
        - tier_breaker (TierBreaker): the tier breaker object to add.

        Returns:
        - None
        """
        self.tier_breakers.append(tier_breaker)

    def get_team_ranking(self, games_teams: Dict[int, List[str]]) \
            -> List[Dict[str, Union[str, Dict[str, Union[str, List[str]]]]]]:
        """
        Get the team ranking based on the given games and teams.

        Args:
        - games_teams (Dict[int, List[str]]): a dictionary where the keys are game IDs and the values are lists
          of team tricodes for each game.

        Returns:
        - List[Dict[str, Union[str, Dict[str, Union[str, List[str]]]]]]: a list of dictionaries representing the
          team ranking, where each dictionary has the following keys:
          - "name" (str): the tricode of the team.
          - "score" (Dict[str, Union[str, List[str]]]]): a dictionary representing the team score, where the keys are:
            - "game" (str): the game information string.
            - "stats" (List[str]): the team stats as a list of strings.
        """
        result = []

        for game_id in games_teams:
            try:
                # Get the game stats and the play-by-play actions.
                game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
                actions = PlayByPlay(game_id).get_dict()['game']['actions']
            except Exception:
                continue

            # Skip games with no actions.
            if len(actions) == 0:
                continue

            # Get the game information.
            game_info = get_game_info(game_stats)

            # Get the action that matches the tier breaker.
            hit = self.tier_breakers[0].get_action(actions)

            # If an action was found, add it to the result.
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

    def get_player_ranking(self, games_players: Dict[str, List[int]]) -> List[Dict[str, Any]]:
        """
        Gets the rankings of players based on their stats in games they played in.

        Args:
        - games_players: A dictionary mapping game IDs to a list of player IDs who played in the game.

        Returns:
        - A list of dictionaries representing the rankings of players. Each dictionary contains the following keys:
            - "name": A string representing the name of the player.
            - "score": A dictionary containing the following keys:
                - "game": A dictionary representing information about the game the player played in.
                - "stats": A list of strings representing the player's statistics in the game.
        """
        result = []

        for game_id in games_players:
            try:
                game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
                actions = PlayByPlay(game_id).get_dict()['game']['actions']
            except Exception:
                continue

            if len(actions) == 0:
                continue

            game_info = get_game_info(game_stats)

            hit = self.tier_breakers[0].get_action(actions, games_players[game_id])

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


def equals(s1: list, s2: list) -> bool:
    """
    Compares two lists element-wise and returns True if they are equal, False otherwise.

    Args:
        s1: The first list to compare.
        s2: The second list to compare.

    Returns:
        True if the two lists are equal, False otherwise.
    """
    # If the two lists are not of equal length, they are not equal.
    if len(s1) != len(s2):
        return False

    # Compare the elements of the two lists.
    for i in range(len(s1)):
        if s1[i] != s2[i]:
            return False

    # If all the elements are equal, the two lists are equal.
    return True
