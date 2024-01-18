from enum import Enum
from typing import List, Dict, Any, Tuple, Optional

from provider.nba.nba_provider import NBA_PROVIDER
from provider.topshot.challenge.player_filter import TopshotFilter, PlayerIDFilter, TopshotSetFilter
from provider.topshot.challenge.team_filter import TeamFilter
from provider.topshot.challenge.tier_breaker import TierBreaker, Qualifier
from provider.topshot.challenge.trackers.leaderboard_tracker import LeaderBoardTracker, QualifierTracker
from provider.topshot.challenge.trackers.playbyplay_tracker import PlayByPlayTracker
from provider.topshot.challenge.trackers.tracker import Tracker


class BucketType(Enum):
    LB = 1  # leaderboard
    QA = 2  # qualifier
    NL = 3  # nested leaderboard
    PBP = 4  # play-by-play


class Bucket:
    """
    Bucket represents a set of rules to select teams/players in topshot challenges.

    ...
    Attributes
    ----------
    description: str
        usually describes which moment is needed for qualified teams/players and briefly explains the rules
    is_wildcard: bool
        moments qualified for a wildcard bucket can be used in other buckets for a given challenge
    bucket_type: BucketType
        bucket type determines which tracker to use to select teams/players
    count: int
        the maximum number of teams/players can be qualified
    is_team:
        whether this bucket resolved into a list of teams

    """

    def __init__(self, description, is_wildcard, bucket_type, count=0, is_team=False):
        self.description = description
        self.is_wildcard = is_wildcard
        self.bucket_type = bucket_type

        if bucket_type == BucketType.LB:
            self.tracker: Tracker = LeaderBoardTracker(count)
        if bucket_type == BucketType.PBP:
            self.tracker: Tracker = PlayByPlayTracker(30)
        if bucket_type == BucketType.QA:
            self.tracker: Tracker = QualifierTracker(count)

        self.is_team = is_team
        self.games = []
        self.player_filters = []
        self.team_filter = None

    def add_tier_breaker(self, tier_breaker):
        """
        Add a new tier breaker to the tracker.

        :param: tier_breaker: a tier breaker object
        :return: None
        """
        self.tracker.add_tier_breaker(tier_breaker)

    def add_date(self, date):
        """
        Add all games from a date to this bucket to track.

        :param: date: a game date
        :return: None
        """
        self.games.extend(NBA_PROVIDER.get_games_on_date(date).keys())

    def add_game(self, game_id):
        """
        Add a single game to this bucket to track.

        :param: game_id: a game
        :return: None
        """

        self.games.append(game_id)

    def add_player_filter(self, player_filter):
        """
        Add a player filter to pre-select players.

        :param: player_filter: a player filter
        :return: None
        """
        self.player_filters.append(player_filter)

    def set_team_filter(self, team_filter):
        """
        Set the filter to pre-select teams

        :param: team_filter: a team filter
        :return: NOne
        """
        self.team_filter = team_filter

    def get_filtered_games_teams(self) -> Dict[str, List[str]]:
        games_teams = NBA_PROVIDER.get_teams_for_games(self.games)

        # apply team filter if exists
        if self.team_filter:
            for game_id in games_teams:
                games_teams[game_id] = self.team_filter.filter_teams(game_id, games_teams[game_id])

            # remove games without qualified teams
            games_to_remove = []
            for game_id in games_teams.keys():
                if len(games_teams[game_id]) == 0:
                    games_to_remove.append(game_id)
            for game_id in games_to_remove:
                games_teams.pop(game_id)

        return games_teams

    def get_filtered_games_players(self, games_teams) -> Dict[str, List[int]]:
        game_players = NBA_PROVIDER.get_players_for_games(games_teams)

        # apply player filters if exist
        for f in self.player_filters:
            for game_id in game_players:
                game_players[game_id] = f.filter_players(game_players[game_id])

            # remove games without qualified players
            games_to_remove = []
            for game_id in game_players.keys():
                if len(game_players[game_id]) == 0:
                    games_to_remove.append(game_id)
            for game_id in games_to_remove:
                game_players.pop(game_id)

        return game_players

    def get_current_scores(self,
                           games_stats: Dict[str, Tuple[Optional[Dict[str, Any]], bool, Optional[Dict[str, Any]]]]) -> \
    List[Tuple[int, List[Dict[str, Any]]]]:
        """
        Get the current ranking of teams/players from ALL games tracked by this bucket.

        :games_stats: dictionary of game_id to (game_boxscore, isFinal, game_info) tuple
        :return: a dictionary of {name, stats:{}}
        """
        games_teams = self.get_filtered_games_teams()

        if self.is_team:
            return [self.tracker.get_team_scores(games_teams, games_stats)]

        # get players for each game
        game_players = self.get_filtered_games_players(games_teams)

        return [self.tracker.get_player_scores(game_players, games_stats)]

    @staticmethod
    def build_from_dict(dict_obj):
        """Create a Bucket object from a dictionary.

        Args:
            dict_obj (dict): a dictionary representing a Bucket object

        Returns:
            Bucket: the Bucket object created from the dictionary
        """
        bucket = Bucket(
            dict_obj.get('description'),
            dict_obj.get('is_wildcard'),
            BucketType[dict_obj.get('type')],
            dict_obj.get('count', 0),
            dict_obj.get('is_team')
        )

        return fill_bucket(bucket, dict_obj)


def fill_bucket(bucket: Bucket, dict_obj: Dict[str, any]) -> Bucket:
    """
    Populate a Bucket object based on the dictionary provided.

    :param bucket: the Bucket object to populate
    :param dict_obj: the dictionary containing the parameters for the Bucket
    :return: the populated Bucket object
    """
    # If the bucket is of type LeaderBoard or PlayByPlay, add the specified TierBreakers to the bucket
    if dict_obj['type'] == BucketType.LB.name or dict_obj['type'] == BucketType.PBP.name:
        for tier_breaker in dict_obj['tier_breakers']:
            bucket.add_tier_breaker(
                TierBreaker(
                    stats=tier_breaker['stats'].split(','),
                    order=tier_breaker['order']
                )
            )

    # If the bucket is of type Qualifier, add the specified Qualifier to the bucket
    if dict_obj['type'] == BucketType.QA.name:
        for tier_breaker in dict_obj['tier_breakers']:
            stats = tier_breaker['stats'].split(',')
            bucket.add_tier_breaker(
                Qualifier(
                    stats=stats[:-1],
                    target=int(stats[-1])
                )
            )

    # If a team filter is specified, set the TeamFilter for the bucket
    if 'team_filter' in dict_obj:
        bucket.set_team_filter(TeamFilter(dict_obj['team_filter']))

    # If player filters are specified, add TopshotFilter for each player filter to the bucket
    if 'player_filters' not in dict_obj or len(dict_obj['player_filters']) == 0:
        bucket.add_player_filter(TopshotFilter([], []))
    else:
        for filter_def in dict_obj['player_filters']:
            if filter_def.startswith("TS"):
                filter_tags = filter_def.split(',')[1:]
                series = []
                badges = []
                for tag in filter_tags:
                    if str(self.description):
                        series.append(tag)
                    else:
                        badges.append(tag)

                bucket.add_player_filter(TopshotFilter(series, badges))
            elif filter_def.startswith("SET"):
                bucket.add_player_filter(TopshotSetFilter(filter_def.split(',')[1]))
            elif filter_def.startswith("ID"):
                bucket.add_player_filter(PlayerIDFilter(filter_def.split(',')[1:]))

    # If dates are specified, add the specified dates to the bucket
    if "dates" in dict_obj:
        for date in dict_obj['dates']:
            bucket.add_date(date)
    # Otherwise, add the specified game IDs to the bucket
    else:
        for game_id in dict_obj['games']:
            bucket.add_game(game_id)

    # Return the populated Bucket object
    return bucket
