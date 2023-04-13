from enum import Enum

from nba.provider import NBA_PROVIDER
from topshot.challenge.player_filter import TopshotFilter
from topshot.challenge.team_filter import TeamFilter
from topshot.challenge.tier_breaker import TierBreaker
from topshot.challenge.tracker import LeaderBoardTracker, PlayByPlayTracker


class BucketType(Enum):
    LB = 1  # leaderboard
    QA = 2  # qualifier
    NL = 3  # nested leaderboard
    PBP = 4 # play-by-play


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
            self.tracker = LeaderBoardTracker(count)
        if bucket_type == BucketType.PBP:
            self.tracker = PlayByPlayTracker(30)

        self.is_team = is_team
        self.games = []
        self.player_filters = []
        self.team_filter = None

    def add_tier_breaker(self, tier_breaker):
        """
        Add a new tier breaker to the tracker.

        :param tier_breaker: a tier breaker object
        :return: None
        """
        self.tracker.add_tier_breaker(tier_breaker)

    def add_date(self, date):
        """
        Add all games from a date to this bucket to track.

        :param date: a game date
        :return: None
        """
        self.games.extend(NBA_PROVIDER.get_games_on_date(date).keys())

    def add_game(self, game_id):
        """
        Add a single game to this bucket to track.

        :param game_id: a game
        :return: None
        """

        self.games.append(game_id)

    def add_player_filter(self, player_filter):
        """
        Add a player filter to pre-select players.

        :param player_filter: a player filter
        :return: None
        """
        self.player_filters.append(player_filter)

    def set_team_filter(self, team_filter):
        """
        Set the filter to pre-select teams

        :param team_filter: a team filter
        :return: NOne
        """
        self.team_filter = team_filter

    def get_current_ranking(self):
        """
        Get the current ranking of teams/players from ALL games tracked by this bucket.

        :return: a dictionary of {name, stats:{}}
        """
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

        if self.is_team:
            return self.tracker.get_team_ranking(games_teams)

        # get players for each game
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

        return self.tracker.get_player_ranking(game_players)

    @staticmethod
    def build_from_dict(dict_obj):
        """Create a Bucket object from a dictionary.

        Args:
            dict_obj (dict): a dictionary representing a Bucket object

        Returns:
            Bucket: the Bucket object created from the dictionary
        """
        bucket = Bucket(
            dict_obj['description'],
            dict_obj['is_wildcard'],
            BucketType[dict_obj['type']],
            dict_obj['count'],
            dict_obj['is_team'])

        if dict_obj['type'] == BucketType.LB.name or dict_obj['type'] == BucketType.PBP.name:
            for tier_breaker in dict_obj['tier_breakers']:
                bucket.add_tier_breaker(
                    TierBreaker(
                        tier_breaker['stats'].split(','),
                        tier_breaker['order']
                    )
                )

        if 'team_filter' in dict_obj:
            bucket.set_team_filter(TeamFilter(dict_obj['team_filter']))

        if 'player_filters' not in dict_obj or len(dict_obj['player_filters']) == 0:
            bucket.add_player_filter(TopshotFilter([]))
        else:
            for filter_def in dict_obj['player_filters']:
                bucket.add_player_filter(TopshotFilter(filter_def.split(',')))

        if "dates" in dict_obj:
            for date in dict_obj['dates']:
                bucket.add_date(date)
        else:
            for game_id in dict_obj['games']:
                bucket.add_game(game_id)

        return bucket
