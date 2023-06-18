from typing import Dict, List, Any, Tuple, Optional

from nba_api.live.nba.endpoints import boxscore

from topshot.challenge.tier_breaker import TierBreaker
from utils import get_game_info


class Tracker:
    def __init__(self) -> None:
        """
        Initialize a Tracker object.
        """
        self.tier_breakers: List[TierBreaker] = []

    def add_tier_breaker(self, tier_breaker: TierBreaker) -> None:
        """
        Add a TierBreaker object to the list of tier breakers.

        :param: tier_breaker: a TierBreaker object to be added
        """
        pass

    def get_team_scores(self, games_teams: Dict[str, List[str]]) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Get the team scores based on the specified tier breakers.

        :param: games_teams: dictionary mapping game ids to lists of team ids
        :return: a tuple containing the total number of teams and a list of dictionaries containing team information and scores
        """
        pass

    def get_player_scores(self, games_players: Dict[str, List[int]]) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Get the player scores based on the specified tier breakers.

        :param: games_players: dictionary mapping game ids to lists of player ids
        :return: a tuple containing the total number of players and a list of dictionaries containing player information and scores
        """
        pass

    @staticmethod
    def load_game_stats(game_id: str) -> Tuple[Optional[Dict[str, Any]], bool, Optional[Dict[str, Any]]]:
        """
        Load game statistics for a given game id.

        :param: game_id: a string representing the game id
        :return: a tuple containing the game statistics, a boolean indicating whether the game has ended, and the game information
        """
        try:
            game_boxscore = boxscore.BoxScore(game_id=game_id).get_dict()['game']
        except Exception:
            return None, True, None

        if game_boxscore['gameStatus'] == 1:
            return None, False, None

        return game_boxscore, game_boxscore['gameStatus'] == 3, get_game_info(game_boxscore)
