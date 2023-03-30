from topshot.challenge.bucket import Bucket, dict_to_bucket
from topshot.challenge.tier_breaker import TierBreaker
from utils import truncate_message


class Challenge:
    def __init__(self, id, title):
        self.id = id
        self.title = title
        self.buckets = []

    def add_bucket(self, description, is_wildcard, bucket_type, count, is_team):
        self.add_bucket_obj(Bucket(description, is_wildcard, bucket_type, count, is_team))

    def add_bucket_obj(self, bucket):
        self.buckets.append(bucket)

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

    def get_formatted_stands(self):
        messages = []
        message = ""
        new_message = "-" * 40
        new_message += "\n:zap: ***{}***\n\n".format(self.title)

        for bucket in self.buckets:
            new_message += ":bar_chart: **{}** ".format(bucket.description)

            for tier_breaker in bucket.tracker.tier_breakers:
                new_message += "[{}] ".format(','.join(tier_breaker.stats))

            new_message += "\n"

            scores = bucket.get_current_stands()

            if len(scores) == 0:
                new_message += "\n\n"
                continue

            for i in range(0, min(bucket.tracker.count, len(scores))):
                score = scores[i]
                new_message += "**{}.** **{}** ".format(i+1, score['name'])
                for stat in score['score']['stats']:
                    new_message += "[{}] ".format(stat)
                new_message += " {} {}-{} {} Q{} {}:{}\n".format(
                    score['score']['game']['awayTeam'],
                    score['score']['game']['awayScore'],
                    score['score']['game']['homeScore'],
                    score['score']['game']['homeTeam'],
                    score['score']['game']['quarter'],
                    int(score['score']['game']['clock'][2:4]),
                    score['score']['game']['clock'][5:-4]
                )

                message, new_message = truncate_message(messages, message, new_message, 1950)

            for i in range(bucket.tracker.count, len(scores)):
                score = scores[i]
                new_message += "{}. {} ".format(i + 1, score['name'])
                for stat in score['score']['stats']:
                    new_message += "[{}] ".format(stat)
                new_message += " {} {}-{} {} Q{} {}:{}\n".format(
                    score['score']['game']['awayTeam'],
                    score['score']['game']['awayScore'],
                    score['score']['game']['homeScore'],
                    score['score']['game']['homeTeam'],
                    score['score']['game']['quarter'],
                    int(score['score']['game']['clock'][2:4]),
                    score['score']['game']['clock'][5:-4]
                )

                message, new_message = truncate_message(messages, message, new_message, 1950)

            new_message += "\n\n"

        messages.append(message)
        return messages


def dict_to_challenge(dict):
    challenge = Challenge(dict['id'], dict['title'])

    for bucket in dict["buckets"]:
        challenge.add_bucket_obj(dict_to_bucket(bucket))

    return challenge
