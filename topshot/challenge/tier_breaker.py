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
    "PMP": "plusMinusPoints"
}


class TierBreaker:
    def __init__(self, stats, order="DESC"):
        self.stats = stats
        self.order = order

    def load_team_stats(self, team_player_stats):
        result = 0

        for player_stats in team_player_stats:
            result += self.load_play_stats(player_stats)

        return result

    def load_play_stats(self, player_stats):
        result = 0

        for stat in self.stats:
            result += player_stats[STATS_MAP[stat]]

        return result



