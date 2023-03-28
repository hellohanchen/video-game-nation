from topshot.challenge.bucket import Bucket
from topshot.challenge.tier_breaker import TierBreaker


class Challenge:
    def __init__(self, id, title):
        self.id = id
        self.tile = title
        self.buckets = []

    def add_bucket(self, description, is_wildcard, bucket_type, count, is_team):
        self.buckets.append(Bucket(description, is_wildcard, bucket_type, count, is_team))

    def add_bucket_date(self, bucket_idx, date):
        self.buckets[bucket_idx].add_date(date)

    def add_bucket_game(self, bucket_idx, game_id):
        self.buckets[bucket_idx].add_game(game_id)

    def add_bucket_tier_breaker(self, bucket_idx, stats, order):
        self.buckets[bucket_idx].add_tier_breaker(TierBreaker(stats, order))

    def add_bucket_team_filter(self, team_filter):
        pass

    def add_bucket_player_filter(self, player_filter):
        pass


def dict_to_challenge(dict):
    pass


