from typing import List, Dict, Tuple

from constants import NBA_TEAMS, NBA_TEAM_NAMES
from utils import parse_boxscore_minutes, list_to_str

STATS_MAP = {
    "PTS": "points",
    "FGA": "field goal attempts",
    "FGM": "field goals made",
    "3PT": "three pointers made",
    "3PM": "three pointers made",
    "3PA": "three pointer attempts",
    "REB": "rebounds",
    "ORB": "offensive rebounds",
    "DRB": "defensive rebounds",
    "AST": "assists",
    "STL": "steals",
    "BLK": "blocks",
    "FTA": "free throw attempts",
    "FTM": "free throws made",
    "WIN": "wins",
    "MIN": "minutes",
    "DD2": "double doubles",
    "TD3": "triple doubles",
    "PFD": "fouls drawn",
    "PIP": "points in paint",
    "PMP": "plus minus",
    "AMT": "assists minus turnovers",
    "TOV": "turnovers",
    "SPB": "steals plus blocks",
}
BOXSCORE_MAP = {
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
    "DRB": "reboundsDefensive",
    "AST": "assists",
    "STL": "steals",
    "BLK": "blocks",
    "FTA": "freeThrowsAttempted",
    "FTM": "freeThrowsMade",
    "FTP": "freeThrowsPercentage",
    "PMP": "plusMinusPoints",
    "WIN": "teamWin",
    "MIN": "minutes",
    "PFD": "foulsDrawn",
    "PIP": "pointsInThePaint",
    "DD2": "doubleDouble",
    "TD3": "tripleDouble",
    "QD4": "quadrupleDouble",
    "FD5": "fiveDouble",
    "TOV": "turnovers",
}


class RRBucket:
    def __init__(self, bucket_json, players):
        self.stats = bucket_json['stats']
        self.order = bucket_json['order']
        self.moment_types = bucket_json['momentTypes'].split(',')
        self.is_team = bucket_json['isTeam']
        if self.is_team:
            self.options: List[Tuple[int, str]] = [(NBA_TEAMS[o], NBA_TEAM_NAMES[o]) for o in bucket_json['options']]
        else:
            self.options: List[Tuple[int, str]] = [
                (int(o), players[int(o)]['full_name']) for o in bucket_json['options']]

    def get_formatted_stats(self):
        return f"__{'Team' if self.is_team else 'Player'} {'Higher' if self.order == 'DESC' else 'Lower'} " \
               f"{'total ' if self.is_team else ''}{self.stats}:__\n"

    def get_formatted(self):
        return f"{self.get_formatted_stats()}*Moment types: {list_to_str(self.moment_types)}*\n" \
               f"{self.options[0][1]} vs {self.options[1][1]}\n\n"

    def load_team_score(self, team_players_stats: List[Dict[str, any]]) -> float:
        result = 0.0

        for player_stats in team_players_stats:
            result += self.load_player_score(player_stats)

        return result

    def load_player_score(self, single_player_stat: Dict[str, any]) -> float:
        if self.stats == 'AMT':
            assists = 0.0 if BOXSCORE_MAP['AST'] not in single_player_stat else single_player_stat[BOXSCORE_MAP['AST']]
            turnovers = 0.0 if BOXSCORE_MAP['TOV'] not in single_player_stat else single_player_stat[BOXSCORE_MAP['TOV']]
            raw_score = assists - turnovers
        elif self.stats == 'SPB':
            steals = 0.0 if BOXSCORE_MAP['STL'] not in single_player_stat else single_player_stat[BOXSCORE_MAP['STL']]
            blocks = 0.0 if BOXSCORE_MAP['BLK'] not in single_player_stat else single_player_stat[BOXSCORE_MAP['BLK']]
            raw_score = steals + blocks
        else:
            key = BOXSCORE_MAP[self.stats]
            if key not in single_player_stat:
                return 0.0
            if self.stats == 'MIN':
                raw_score = parse_boxscore_minutes(single_player_stat[key])
            else:
                raw_score = float(single_player_stat[key])

        return raw_score

    def get_option_name(self, i: int) -> str:
        if i == self.options[0][0]:
            return self.options[0][1]
        return self.options[1][1]


class RRSelection:
    def __init__(self, selected: int, serial: int, tier: str):
        self.selected = selected
        self.serial = serial
        self.tier = tier

    def to_db_str(self):
        return f"{self.selected},{self.serial},{self.tier}"

    @staticmethod
    def from_db_str(db_str) -> 'RRSelection':
        values = db_str.split(',')
        return RRSelection(int(values[0]), int(values[1]), str(values[2]))

    def format_with_bucket(self, bucket: RRBucket) -> str:
        if self.selected == bucket.options[0][0]:
            return f"{bucket.get_formatted_stats()}*Moment types: {list_to_str(bucket.moment_types)}*\n" \
                   f"**{bucket.options[0][1]}** vs {bucket.options[1][1]}\n\n"
        else:
            return f"{bucket.get_formatted_stats()}*Moment types: {list_to_str(bucket.moment_types)}*\n" \
                   f"{bucket.options[0][1]} vs **{bucket.options[1][1]}**\n\n"

    def format_with_bucket_and_score(self, bucket: RRBucket, op_0_score: float, op_1_score: float) -> str:
        if self.selected == bucket.options[0][0]:
            return f"{bucket.get_formatted_stats()}" \
                   f"**{bucket.options[0][1]}** vs {bucket.options[1][1]}\n" \
                   f"**{op_0_score} {bucket.stats}** - {op_1_score} {bucket.stats}\n\n"
        else:
            return f"{bucket.get_formatted_stats()}" \
                   f"{bucket.options[0][1]} vs **{bucket.options[1][1]}**\n" \
                   f"{op_0_score} {bucket.stats} - **{op_1_score} {bucket.stats}**\n\n"

    def compute_score(self, bucket: RRBucket, op_0_score: float, op_1_score: float) -> [bool, float]:
        if self.selected == bucket.options[0][0]:
            selected_score = op_0_score
            non_selected_score = op_1_score
        else:
            selected_score = op_1_score
            non_selected_score = op_0_score

        if bucket.order == "DESC":
            return selected_score >= non_selected_score, selected_score
        else:
            return selected_score <= non_selected_score, - selected_score


class RedemptionRun:
    def __init__(self, buckets: List[Dict[str, any]], players, threshold):
        self.buckets: List[RRBucket] = self.load_buckets(buckets, players)
        self.threshold = threshold

    @staticmethod
    def get_empty_rr() -> 'RedemptionRun':
        return RedemptionRun([], {}, 0.0)

    @staticmethod
    def load_buckets(buckets: List[Dict[str, any]], players):
        return [RRBucket(b, players) for b in buckets]

    def compute_selections_score(self, selections: List[RRSelection], buckets_scores: List[Tuple[float, float]]) \
            -> [int, float, int, int, int, str]:
        wins = 0
        sum_score = 0.0
        serials = 0
        legos = 0
        rares = 0
        message = ""

        for i in range(len(self.buckets)):
            selection = selections[i]
            bucket = self.buckets[i]
            bucket_scores = buckets_scores[i]

            win, raw_score = selection.compute_score(bucket, bucket_scores[0], bucket_scores[1])
            if win:
                wins += 1
            sum_score += raw_score
            serials += selection.serial
            if selection.tier == "Legendary" or selection.tier == "Ultimate":
                legos += 1
            elif selection.tier == "Rare":
                rares += 1

            message += selection.format_with_bucket_and_score(bucket, bucket_scores[0], bucket_scores[1])

        message += f"{wins * '✔' if wins > 0 else '**0**'}, {sum_score} score, {serials} total serial\n\n"

        return wins, sum_score, serials, legos, rares, message

    def compute_buckets_scores(self, teams_players_stats, players_stats) -> List[Tuple[float, float]]:
        buckets_scores = []

        for bucket in self.buckets:
            if bucket.is_team:
                option_0_score = bucket.load_team_score(teams_players_stats.get(bucket.options[0][0], []))
                option_1_score = bucket.load_team_score(teams_players_stats.get(bucket.options[1][0], []))
            else:
                option_0_score = bucket.load_player_score(players_stats.get(bucket.options[0][0], {}))
                option_1_score = bucket.load_player_score(players_stats.get(bucket.options[1][0], {}))
            buckets_scores.append((option_0_score, option_1_score))

        return buckets_scores
