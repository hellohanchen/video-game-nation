from typing import Dict, List, Any, Optional, Set, Tuple

STATS_MAP = {
    "PTS": "points",
    "FGA": "fieldGoalsAttempted",
    "FGM": "fieldGoalsMade",
    "FGP": "fieldGoalsPercentage",
    "3PT": "threePointersMade",
    "3PA": "threePointersAttempted",
    "3PM": "threePointersMade",
    "3PP": "threePointersPercentage",
    "REB": "reboundsTotal",
    "ORB": "reboundsOffensive",
    "DRE": "reboundsDefensive",
    "AST": "assists",
    "STL": "steals",
    "BLK": "blocks",
    "FTA": "freeThrowsAttempted",
    "FTM": "freeThrowsMade",
    "FTP": "freeThrowsPercentage",
    "PMP": "plusMinusPoints",
    "WIN": "teamWin"
}


class TierBreaker:
    def __init__(self, stats: List[str], order: str = "DESC") -> None:
        """
        Initialize a TierBreaker object.

        :param stats: list of statistics used to break tiers
        :param order: order of tier breaking results, either "ASC" or "DESC"
        """
        self.stats = stats
        self.order = order

    def load_team_stats(self, team_player_stats: List[Dict]) -> int:
        """
        Load team statistics for tier breaking.

        :param team_player_stats: list of player statistics for a team
        :return: sum of the specified statistics for the team
        """
        result = 0

        for player_stats in team_player_stats:
            result += self.load_player_stats(player_stats['statistics'])

        return result

    def load_player_stats(self, player_stats: Dict) -> Any:
        """
        Load player statistics for tier breaking.

        :param player_stats: dictionary of statistics for a player
        :return: sum of the specified statistics for the player
        """
        result = 0

        for stat in self.stats:
            if stat == "WIN":
                return 'W' if player_stats[STATS_MAP[stat]] == 1 else 'L'
            else:
                result += int(float(player_stats[STATS_MAP[stat]]))

        return result

    def get_action(self, actions: List[Dict], players: Optional[Set] = None) -> Optional[Dict]:
        """
        Get the action that breaks the tier.

        :param actions: list of actions to be considered for tier breaking
        :param players: set of player ids whose actions should be considered for tier breaking
        :return: action that breaks the tier, or None if no such action exists
        """
        if self.order == "DESC":
            actions = reversed(actions)

        for action in actions:
            if players and action['personId'] not in players:
                continue

            if self.stats[0] == "3PM" and action['actionType'] == '3pt' and action['shotResult'] == 'Made':
                return action

        return None


class Qualifier(TierBreaker):
    def __init__(self, stats: List[str], target: int):
        super().__init__(stats)
        self.target = target

    def load_team_stats(self, team_player_stats: List[Dict]) -> tuple[float, int]:
        result = 0

        for player_stats in team_player_stats:
            result += self.load_player_stats(player_stats['statistics'])[1]

        return min(1.0, float(result)/float(self.target)), result

    def load_player_stats(self, player_stats: Dict) -> tuple[float, int]:
        result = super().load_player_stats(player_stats)

        return min(1.0, float(result)/float(self.target)), result


class QualifierPass(Qualifier):
    def __init__(self, target):
        super().__init__(["☑"], target)

    def load_team_stats(self, team_player_stats: List[Dict]) -> tuple[float, int]:
        return 0.0, 0

    def load_player_stats(self, player_stats: Dict) -> tuple[float, int]:
        return 0.0, 0


class QualifierProgress(Qualifier):
    def __init__(self):
        super().__init__(["%"], 0)

    def load_team_stats(self, team_player_stats: List[Dict]) -> tuple[float, int]:
        return 0.0, 0

    def load_player_stats(self, player_stats: Dict) -> tuple[float, int]:
        return 0.0, 0
