from enum import Enum
from typing import Dict, List, Any, Tuple

from provider.nba_provider import NBA_PROVIDER, EAST_CONFERENCE, WEST_CONFERENCE
from topshot.challenge.buckets.bucket import Bucket, BucketType, fill_bucket


class SegmentType(Enum):
    CONFERENCE = 1
    GAME = 2
    DATE = 3


class SegmentBucket(Bucket):
    def __init__(self, segment_type, description, is_wildcard, bucket_type, count=0, is_team=False):
        super().__init__(description, is_wildcard, bucket_type, count, is_team)
        self.segment_type = segment_type

    def get_current_scores(self) -> List[Tuple[int, List[Dict[str, Any]]]]:
        """
        Get the current ranking of teams/players from ALL games tracked by this bucket.

        :return: a dictionary of {name, stats:{}}
        """
        games_teams = self.get_filtered_games_teams()

        segments = self.__segment(games_teams)
        results = []

        for segment in segments:
            if self.is_team:
                results.append(self.tracker.get_team_scores(segment))
            else:
                # get players for each game
                game_players = self.get_filtered_games_players(segment)

                results.append(self.tracker.get_player_scores(game_players))

        return results

    def __segment(self, games_teams: Dict[str, List[str]]) -> List[Dict[str, List[str]]]:
        """
        Private method that divides the teams or players into segments.

        :param: games_teams: a dictionary of game IDs mapped to lists of team IDs
        :return: a list of dictionaries, where each dictionary maps game IDs to lists of team IDs
        """
        if self.segment_type == SegmentType.GAME:
            return [{game_id: games_teams[game_id]} for game_id in games_teams]

        if self.segment_type == SegmentType.DATE:
            games_dates = {}

            for game_id in games_teams:
                game_date = NBA_PROVIDER.get_date_for_game(game_id)
                if game_date not in games_dates:
                    games_dates[game_date] = {}

                games_dates[game_date][game_id] = games_teams[game_id]

            return [games for _, games in games_dates.items()]

        if self.segment_type == SegmentType.CONFERENCE:
            segment_east = {}
            segment_west = {}

            for game_id, teams in games_teams.items():
                for team in teams:
                    if team in EAST_CONFERENCE:
                        if game_id not in segment_east:
                            segment_east[game_id] = [team]
                        else:
                            segment_east[game_id].extend(team)
                    elif team in WEST_CONFERENCE:
                        if game_id not in segment_west:
                            segment_west[game_id] = [team]
                        else:
                            segment_west[game_id].extend(team)

            return [segment_east, segment_west]

    @staticmethod
    def build_from_dict(dict_obj):
        bucket = SegmentBucket(
            SegmentType[dict_obj.get('segment')],
            dict_obj.get('description'),
            dict_obj.get('is_wildcard'),
            BucketType[dict_obj.get('type')],
            dict_obj.get('count', 0),
            dict_obj.get('is_team')
        )

        return fill_bucket(bucket, dict_obj)
