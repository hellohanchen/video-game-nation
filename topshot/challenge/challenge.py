from typing import List, Dict, Any, Tuple

from topshot.challenge.buckets.bucket import Bucket
from topshot.challenge.buckets.segment_bucket import SegmentBucket
from topshot.challenge.player_filter import TopshotFilter
from topshot.challenge.team_filter import TeamFilter
from topshot.challenge.tier_breaker import TierBreaker
from utils import truncate_message


class Challenge:
    def __init__(self, challenge_id: int, title: str):
        """
        Constructor for the Challenge class.

        Args:
            challenge_id (int): the ID of the challenge
            title (str): the title of the challenge
        """
        self.id = challenge_id
        self.title = title
        self.buckets: List[Bucket] = []

    def build_bucket(self, description: str, is_wildcard: bool, bucket_type: str, count: int, is_team: bool) -> None:
        """Create a new Bucket object and add it to the list of buckets in the challenge.

        Args:
            description (str): description of the Bucket
            is_wildcard (bool): whether the Bucket is a wildcard Bucket
            bucket_type (str): type of the Bucket
            count (int): maximum number of entries in the Bucket
            is_team (bool): whether the Bucket is for a team challenge
        """
        self.add_bucket(Bucket(description, is_wildcard, bucket_type, count, is_team))

    def add_bucket(self, bucket: Bucket) -> None:
        """Add a Bucket object to the list of buckets in the challenge.

        Args:
            bucket (Bucket): the Bucket object to add
        """
        self.buckets.append(bucket)

    def add_bucket_date(self, bucket_idx: int, date: str) -> None:
        """Add a date to the specified Bucket's tracker object.

        Args:
            bucket_idx (int): the index of the Bucket in the list of buckets
            date (str): the date to add to the Bucket's tracker
        """
        self.buckets[bucket_idx].add_date(date)

    def add_bucket_game(self, bucket_idx: int, game_id: int) -> None:
        """Add a game ID to the specified Bucket's tracker object.

        Args:
            bucket_idx (int): the index of the Bucket in the list of buckets
            game_id (int): the ID of the game to add to the Bucket's tracker
        """
        self.buckets[bucket_idx].add_game(game_id)

    def build_bucket_tier_breaker(self, bucket_idx: int, stats: List[str], order: str) -> None:
        """Add a TierBreaker object to the specified Bucket's tracker object.

        Args:
            bucket_idx (int): the index of the Bucket in the list of buckets
            stats (List[str]): a list of stat categories to use for the TierBreaker
            order (str): the order in which to sort the TierBreaker
        """
        self.buckets[bucket_idx].add_tier_breaker(TierBreaker(stats, order))

    def set_bucket_team_filter(self, bucket_idx: int, team_filter: TeamFilter) -> None:
        """Set the team filter for the specified Bucket.

        Args:
            bucket_idx (int): the index of the Bucket in the list of buckets
            team_filter : the team filter
        """
        self.buckets[bucket_idx].set_team_filter(team_filter)

    def add_bucket_player_filter(self, bucket_idx: int, player_filter: TopshotFilter) -> None:
        """Add a player filter to the specified Bucket.

        Args:
            bucket_idx (int): the index of the Bucket in the list of buckets
            player_filter (str): the player to filter by
        """
        self.buckets[bucket_idx].add_player_filter(player_filter)

    def get_formatted_messages(self) -> List[str]:
        messages = []
        msg = ""
        new_msg = "-" * 40
        new_msg += "\n:zap: ***{}***\n\n".format(self.title)

        msg, new_msg = truncate_message(messages, msg, new_msg, 1950)

        for bucket in self.buckets:
            new_msg += ":bar_chart: **{}** ".format(bucket.description)

            for tier_breaker in bucket.tracker.tier_breakers:
                new_msg += "[{}] ".format(','.join(tier_breaker.stats))

            new_msg += "\n"

            bucket_results = bucket.get_current_scores()

            if len(bucket_results) == 0:
                new_msg += "\n"
                msg, new_msg = truncate_message(messages, msg, new_msg, 1950)
                continue

            for result in bucket_results:
                hit, scores = result

                if len(scores) == 0:
                    continue

                msg, new_msg = self.format_ranking(scores[:hit], new_msg, messages, msg)
                msg, new_msg = self.format_ranking(scores[hit:min(len(result), 20)], new_msg, messages, msg, hit)

                new_msg += "\n"

            msg, new_msg = truncate_message(messages, msg, new_msg, 1950)
            if msg.endswith("\n") and not msg.endswith("\n\n"):
                msg += "\n"

        if msg != "":
            messages.append(msg)
        return messages

    @staticmethod
    def format_ranking(
            ranking: List[Dict[str, Any]], new_message: str, messages: List[str], message: str, offset: int = 0
    ) -> Tuple[str, str]:
        """Format a list of scores into a string and truncate it if it exceeds the character limit.

        Args:
            ranking (List[Dict[str, Any]]): a list of rank dictionaries
            new_message (str): the new message to append the formatted scores to
            messages (List[str]): a list of messages
            message (str): the current message being built
            offset (int): the rank offset

        Returns:
            Tuple[str, str]: a tuple containing the updated message and new_message
        """
        for i, rank in enumerate(ranking):
            if offset == 0:
                new_message += "**{}.** **{}** ".format(i + 1, rank['name'].split('/')[0])
            else:
                new_message += "{}. {} ".format(i + 1 + offset, rank['name'].split('/')[0])

            for stat in rank['score']['stats']:
                new_message += "[{}] ".format(stat)

            new_message += " {} {}-{} {} ".format(
                rank['score']['game']['awayTeam'],
                rank['score']['game']['awayScore'],
                rank['score']['game']['homeScore'],
                rank['score']['game']['homeTeam'],
            )

            if rank['score']['game']['statusText'] == "Final":
                new_message += "Final\n"
            else:
                new_message += "**{}**\n".format(
                    rank['score']['game']['statusText'],
                )

            message, new_message = truncate_message(messages, message, new_message, 1950)

        return message, new_message

    @staticmethod
    def build_from_dict(dict_obj):
        """Create a Challenge object from a dictionary.

        Args:
            dict_obj (dict): a dictionary representing a Challenge object

        Returns:
            Challenge: the Challenge object created from the dictionary
        """
        challenge = Challenge(dict_obj['id'], dict_obj['title'])

        for bucket in dict_obj["buckets"]:
            if 'segment' in bucket:
                challenge.add_bucket(SegmentBucket.build_from_dict(bucket))
            else:
                challenge.add_bucket(Bucket.build_from_dict(bucket))

        return challenge
