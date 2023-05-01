from typing import List, Dict, Any, Tuple

from nba_api.live.nba.endpoints import boxscore, PlayByPlay

from topshot.challenge.tier_breaker import TierBreaker
from topshot.challenge.trackers.tracker import Tracker
from utils import get_game_info


class PlayByPlayTracker(Tracker):
    def __init__(self, count_per_game: int):
        super().__init__()
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

    def get_team_scores(self, games_teams: Dict[str, List[str]]) -> Tuple[int, List[Dict[str, Any]]]:
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

        return len(result), result

    def get_player_scores(self, games_players: Dict[str, List[int]]) -> Tuple[int, List[Dict[str, Any]]]:
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

            hit = self.tier_breakers[0].get_action(actions, set(games_players[game_id]))

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

        return len(result), result
