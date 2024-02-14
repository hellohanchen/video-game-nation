from typing import List, Dict

from utils import parse_boxscore_minutes

STATS_MAP = {
    "PTS": "points",
    "FGA": "field goal attempts",
    "FGM": "field goals made",
    "3PT": "three pointers made",
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


class FBBucket:
    def __init__(self, bucket_json):
        self.stats = bucket_json['stats']
        self.order = bucket_json['order']
        if bucket_json.get('each'):
            self.each = True
            self.each_target = float(bucket_json['target'])
            self.target = 5.0
        else:
            self.each = False
            self.each_target = 0.0
            self.target = float(bucket_json['target'])

    def get_formatted(self):
        if self.each:
            if self.order == 'DESC':
                return f"{int(self.each_target)} {STATS_MAP[self.stats]} each"
            else:
                return f"at most {int(self.each_target)} {STATS_MAP[self.stats]} each"

        if self.order == 'DESC':
            return f"{int(self.target)} {STATS_MAP[self.stats]}"
        else:
            return f"at most {int(self.target)} {STATS_MAP[self.stats]}"

    def load_score(self, player_stat) -> [float, float]:
        if player_stat is None:
            return 0.0

        if self.stats == 'AMT':
            assists = 0.0 if BOXSCORE_MAP['AST'] not in player_stat else player_stat[BOXSCORE_MAP['AST']]
            turnovers = 0.0 if BOXSCORE_MAP['TOV'] not in player_stat else player_stat[BOXSCORE_MAP['TOV']]
            raw_score = assists - turnovers
        else:
            key = BOXSCORE_MAP[self.stats]
            if key not in player_stat:
                return 0.0, 0.0
            if self.stats == 'MIN':
                raw_score = parse_boxscore_minutes(player_stat[key])
            else:
                raw_score = float(player_stat[key])

        if self.each:
            if self.order == 'DESC':
                return 1.0 if raw_score >= self.each_target else 0.0, raw_score
            else:
                return 0.0 if raw_score >= self.each_target else 1.0, raw_score

        return raw_score, raw_score


class FastBreak:
    def __init__(self, fb_json: Dict[str, any]):
        self.count: int = fb_json['count']
        self.is_combine: bool = fb_json['isCombine']
        self.buckets: List[FBBucket] = self.load_buckets(fb_json['buckets'])

    @staticmethod
    def load_buckets(buckets_json):
        return [FBBucket(b) for b in buckets_json]

    def get_formatted(self) -> str:
        if self.is_combine:
            return f"**{self.count} Players, " \
                   f"{', '.join(self.format_buckets(self.buckets))}\n\n**"
        else:
            raise NotImplementedError

    @staticmethod
    def format_buckets(fb_buckets: List[FBBucket]) -> List[str]:
        return [b.get_formatted() for b in fb_buckets]

    def formatted_score(self, player_stats: Dict[str, any]):
        message = f"**{player_stats['name']}**"
        for i in range(0, len(self.buckets)):
            bucket = self.buckets[i]
            score, raw_score = bucket.load_score(player_stats)
            if bucket.each:
                message += " {:.0f}/{:.0f} {}".format(raw_score, bucket.each_target, bucket.stats)
            if bucket.stats in ['DD2', 'TD3', 'QD4', 'FD5']:
                message += " {:.0f}p {:.0f}r {:.0f}a {:.0f}s {:.0f}b".format(
                    player_stats['points'], player_stats['reboundsTotal'], player_stats['assists'],
                    player_stats['steals'], player_stats['blocks'],
                )
            else:
                message += " {:.1f} {}".format(score, bucket.stats)

        return message

    def compute_score(self, player_ids, player_stats):
        num_buckets = len(self.buckets)
        sums = [0.0] * num_buckets
        player_scores = {pid: [0.0] * num_buckets for pid in player_ids}

        for pid in player_ids:
            if pid is None:
                continue

            player = player_stats.get(pid)
            if player is None:
                continue

            for i in range(0, num_buckets):
                bucket = self.buckets[i]
                score, _ = bucket.load_score(player)
                player_scores[pid][i] = score
                sums[i] = sums[i] + score

        message = "Total"
        passed = True
        rate = 0.0
        for i in range(0, num_buckets):
            bucket = self.buckets[i]
            s = sums[i]
            if bucket.order == 'DESC':
                if s < bucket.target:
                    passed = False
                rate += s / bucket.target
            elif bucket.order == 'ASC':
                if s > bucket.target:
                    passed = False
                rate += 2.0 - s / bucket.target

            message += f" **{round(s, 1)}/{bucket.target}** {bucket.stats if not bucket.each else 'PASSED'}"

        if passed:
            message += "\n🟢 **YOU WIN**"

        return sum(sums), passed, 0.0 if num_buckets == 0 else round(rate / num_buckets, 2), message
