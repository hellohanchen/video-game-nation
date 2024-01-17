import re
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
    "DRB": "reboundsDefensive",
    "AST": "assists",
    "STL": "steals",
    "BLK": "blocks",
    "FTA": "freeThrowsAttempted",
    "FTM": "freeThrowsMade",
    "FTP": "freeThrowsPercentage",
    "PMP": "plusMinusPoints",
    "WIN": "teamWin",
    "BENCH": "order",
    "START": "order",
    "MIN": "minutes",
}


def compute_espn_fantasy_score(player_stats):
    pts = int(float(player_stats['points']))
    tpm = int(float(player_stats['threePointersMade']))
    fga = int(float(player_stats['fieldGoalsAttempted']))
    fgm = int(float(player_stats['fieldGoalsMade']))
    fta = int(float(player_stats['freeThrowsAttempted']))
    ftm = int(float(player_stats['freeThrowsMade']))
    reb = int(float(player_stats['reboundsTotal']))
    ast = int(float(player_stats['assists']))
    stl = int(float(player_stats['steals']))
    blk = int(float(player_stats['blocks']))
    tov = int(float(player_stats['turnovers']))
    return pts + tpm - fga + 2 * fgm - fta + ftm + reb + 2 * ast + 4 * stl + 4 * blk - 2 * tov


class TierBreaker:
    def __init__(self, stats: List[str], order: str = "DESC") -> None:
        """
        Initialize a TierBreaker object.

        :param: stats: list of statistics used to break tiers
        :param: order: order of tier breaking results, either "ASC" or "DESC"
        """
        self.stats = stats
        self.order = order

    def load_team_stats(self, team_player_stats: List[Dict], win: int) -> int:
        """
        Load team statistics for tier breaking.

        :param: team_player_stats: list of player statistics for a team
        :return: sum of the specified statistics for the team
        """
        result = 0

        for player_stats in team_player_stats:
            if len(self.stats) > 0 and self.stats[0] == "WIN":
                return win
            ps = player_stats['statistics']
            ps['order'] = player_stats['order']
            result += self.load_player_stats(ps)

        return result

    def load_player_stats(self, player_stats: Dict) -> Any:
        """
        Load player statistics for tier breaking.

        :param: player_stats: dictionary of statistics for a player
        :return: sum of the specified statistics for the player
        """
        result = 0

        for stat in self.stats:
            if stat == "WIN":
                return 'W' if player_stats[STATS_MAP[stat]] == 1 else 'L'
            elif stat == "FPT":
                return compute_espn_fantasy_score(player_stats)
            elif stat.startswith("BENCH"):
                if player_stats[STATS_MAP["BENCH"]] > 5:
                    bench_stat = stat[6:]
                    result += int(float(player_stats[STATS_MAP[bench_stat]]))
            elif stat.startswith("START"):
                if player_stats[STATS_MAP["START"]] <= 5:
                    start_stat = stat[6:]
                    result += int(float(player_stats[STATS_MAP[start_stat]]))
            elif stat == 'MIN':
                match = re.match('^PT(.+)M(.+)S', player_stats[STATS_MAP[stat]])
                minutes = float(match.group(1))
                seconds = round(float(match.group(2)) / 60.0, 2)
                result = float(result) + minutes + seconds
            else:
                result += int(float(player_stats[STATS_MAP[stat]]))

        return result

    def get_action(self, actions: List[Dict], players: Optional[Set] = None) -> Optional[Dict]:
        """
        Get the action that breaks the tier.

        :param: actions: list of actions to be considered for tier breaking
        :param: players: set of player ids whose actions should be considered for tier breaking
        :return: action that breaks the tier, or None if no such action exists
        """
        if self.order == "DESC":
            actions = reversed(actions)

        for action in actions:
            if players and action['personId'] not in players:
                continue

            if self.stats[0] == "3PM" and action['actionType'] == '3pt' and action['shotResult'] == 'Made':
                return action
            if self.stats[0] == "PTS" and action.get('shotResult', '') == 'Made':
                return action

        return None


class Qualifier(TierBreaker):
    def __init__(self, stats: List[str], target: int) -> None:
        """
        Initialize a Qualifier object.

        :param: stats: list of statistics used to qualify for the threshold
        :param: target: the threshold value that must be reached for a player to qualify
        """
        super().__init__(stats)
        self.target: int = target

    def load_team_stats(self, team_player_stats: List[Dict], win: int) -> Tuple[float, int]:
        """
        Load team statistics for tier breaking.

        :param: team_player_stats: list of player statistics for a team
        :return: a tuple containing the ratio of players who meet the threshold and the sum of their specified statistics
        """
        result: int = 0

        for player_stats in team_player_stats:
            result += self.load_player_stats(player_stats['statistics'])[1]

        return min(1.0, float(result) / float(self.target)), result

    def load_player_stats(self, player_stats: Dict[str, Any]) -> Tuple[float, int]:
        """
        Load player statistics for tier breaking.

        :param: player_stats: dictionary of statistics for a player
        :return: a tuple containing the ratio of statistics that meet the threshold and the sum of the specified statistics
        """
        result: int = super().load_player_stats(player_stats)

        return min(1.0, float(result) / float(self.target)), result


class QualifierPass(Qualifier):
    def __init__(self, target: int) -> None:
        """
        Initialize a QualifierPass object.

        :param: target: the threshold value that must be reached for a player to qualify
        """
        super().__init__(["☑"], target)

    def load_team_stats(self, team_player_stats: List[Dict]) -> Tuple[float, int]:
        """
        Load team statistics for tier breaking.

        :param: team_player_stats: list of player statistics for a team
        :return: a tuple containing 0.0 and 0, indicating that the team passes the threshold
        """
        return 0.0, 0

    def load_player_stats(self, player_stats: Dict[str, Any]) -> Tuple[float, int]:
        """
        Load player statistics for tier breaking.

        :param: player_stats: dictionary of statistics for a player
        :return: a tuple containing 0.0 and 0, indicating that the player passes the threshold
        """
        return 0.0, 0


class QualifierProgress(Qualifier):
    def __init__(self) -> None:
        """
        Initialize a QualifierProgress object.
        """
        super().__init__(["%"], 0)

    def load_team_stats(self, team_player_stats: List[Dict]) -> Tuple[float, int]:
        """
        Load team statistics for tier breaking.

        :param: team_player_stats: list of player statistics for a team
        :return: a tuple containing 0.0 and 0, indicating that the team does not qualify based on progress
        """
        return 0.0, 0

    def load_player_stats(self, player_stats: Dict[str, Any]) -> Tuple[float, int]:
        """
        Load player statistics for tier breaking.

        :param: player_stats: dictionary of statistics for a player
        :return: a tuple containing 0.0 and 0, indicating that the player does not qualify based on progress
        """
        return 0.0, 0
