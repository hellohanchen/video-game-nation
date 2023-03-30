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
    def __init__(self, stats, order="DESC"):
        self.stats = stats
        self.order = order

    def load_team_stats(self, team_player_stats):
        result = 0

        for player_stats in team_player_stats:
            result += self.load_play_stats(player_stats['statistics'])

        return result

    def load_play_stats(self, player_stats):
        result = 0

        for stat in self.stats:
            result += player_stats[STATS_MAP[stat]]

        return result

    def get_action(self, actions, players=None):
        if self.order == "DESC":
            r = range(len(actions) - 1, -1, -1)
        else:
            r = range(0, len(actions))

        for i in r:
            action = actions[i]

            if players and action['personId'] not in players:
                continue

            if self.stats[0] == "3PM":
                if action['actionType'] == '3pt' and action['shotResult'] == 'Made':
                    return action

        return None

