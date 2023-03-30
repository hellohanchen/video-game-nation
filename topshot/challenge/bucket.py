from enum import Enum

from nba import stats
from topshot.challenge.tier_breaker import TierBreaker
from topshot.challenge.tracker import LeaderBoardTracker, PlayByPlayTracker


class BucketType(Enum):
    LB = 1  # leaderboard
    QA = 2  # qualifier
    NL = 3  # nested leaderboard
    PBP = 4 # play-by-play


class Bucket:
    def __init__(self, description, is_wildcard, bucket_type, count=0, is_team=False):
        self.description = description
        self.is_wildcard = is_wildcard
        self.bucket_type = bucket_type

        if bucket_type == BucketType.LB:
            self.tracker = LeaderBoardTracker(count)
        if bucket_type == BucketType.PBP:
            self.tracker = PlayByPlayTracker(30)

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

    def get_current_stands(self):
        teams = stats.get_teams_for_games(self.games)
        # teams = filter_teams(teams)

        if self.is_team:
            return self.tracker.get_team_stats(self.games, teams)

        players = stats.get_players_for_games(self.games, teams)
        # players = filter_players(players)

        return self.tracker.get_player_stats(self.games, players)


def dict_to_bucket(dict):
    bucket = Bucket(
        dict['description'],
        dict['is_wildcard'],
        BucketType[dict['type']],
        dict['count'],
        dict['is_team'])

    if dict['type'] == BucketType.LB.name or dict['type'] == BucketType.PBP.name:
        for tier_breaker in dict['tier_breakers']:
            bucket.add_tier_breaker(
                TierBreaker(
                    tier_breaker['stats'].split(','),
                    tier_breaker['order']
                )
            )

    # TODO: add filters

    if "dates" in dict:
        for date in dict['dates']:
            bucket.add_date(date)
    else:
        for game_id in dict['games']:
            bucket.add_game(game_id)

    return bucket
