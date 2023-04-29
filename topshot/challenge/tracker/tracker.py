from typing import Dict, List, Any

from nba_api.live.nba.endpoints import boxscore

from topshot.challenge.tier_breaker import TierBreaker
from utils import get_game_info


class Tracker:
    def __init__(self):
        pass

    def add_tier_breaker(self, tier_breaker: TierBreaker) -> None:
        pass

    def get_team_scores(self, games_teams: Dict[int, List[str]]) -> List[Dict[str, Any]]:
        pass

    def get_player_scores(self, games_players: Dict[int, List[int]]) -> List[Dict[str, Any]]:
        pass

    @staticmethod
    def load_game_stats(game_id):
        try:
            game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
        except Exception:
            return None, True, None

        if game_stats['gameStatus'] == 1:
            return None, False, None

        return game_stats, game_stats['gameStatus'] == 3, get_game_info(game_stats)
