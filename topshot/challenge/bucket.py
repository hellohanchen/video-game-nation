from enum import Enum

from nba import stats
from tracker import LeaderBoardTracker


class BucketType(Enum):
    LB = 1  # leaderboard
    QA = 2  # qualifier
    NL = 3  # nested leaderboard


class Bucket:
    def __init__(self, description, is_wildcard, bucket_type, count=0, is_team=False):
        self.description = description
        self.is_wildcard = is_wildcard
        self.bucket_type = bucket_type

        if bucket_type == BucketType.LB:
            self.tracker = LeaderBoardTracker(count)

        self.is_team = is_team
        self.games = []
        self.player_filters = []
        self.team_filter = None

    def add_tier_breaker(self, tier_breaker):
        self.tracker.add_tier_breaker(tier_breaker)

    def add_date(self, date):
        self.games.extend(stats.get_games_on_date(date).keys())

    def add_game(self, game_id):
        self.games.append(game_id)

    def add_player_filter(self, ts_filter):
        self.player_filters.append(ts_filter)

    def add_team_filter(self, team_filter):
        self.team_filter = team_filter

    def get_current_stands(self, games):
        teams = stats.get_teams_for_games(games)
        # teams = filter_teams(teams)

        if self.is_team:
            return self.tracker.get_team_stats(games, teams)

        players = stats.get_players_for_games(games, teams)
        # players = filter_players(players)

        return self.tracker.get_player_stats(games, players)
