from typing import List

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

    def load_score(self, player_stat) -> float:
        if player_stat is None:
            return 0.0

        if self.stats == 'AMT':
            assists = float(player_stat.get(BOXSCORE_MAP['AST'], default=0.0))
            turnovers = float(player_stat.get(BOXSCORE_MAP['TOV'], default=0.0))
            raw_score = assists - turnovers
        else:
            key = BOXSCORE_MAP[self.stats]
            if key not in player_stat:
                return 0.0
            if self.stats == 'MIN':
                raw_score = parse_boxscore_minutes(player_stat[key])
            else:
                raw_score = float(player_stat[key])

        if self.each:
            if self.order == 'DESC':
                return 1.0 if raw_score >= self.each_target else 0.0
            else:
                return 0.0 if raw_score >= self.each_target else 1.0

        return raw_score


class FastBreak:
    def __init__(self, fb_json):
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

    def formatted_scores(self, player_ids, player_stats):
        num_buckets = len(self.buckets)
        sums = [0.0] * num_buckets
        player_scores = {pid: [0.0] * num_buckets for pid in player_ids}

        message = ""
        for pid in player_ids:
            if pid is None:
                message += f"🏀 No pick\n"
                continue

            player = player_stats.get(pid)
            if player is None:
                message += f"🏀 Player stats not available\n"
                continue

            message += f"🏀 **{player['name']}**"
            for i in range(0, num_buckets):
                bucket = self.buckets[i]
                score = bucket.load_score(player)
                player_scores[pid][i] = score
                sums[i] = sums[i] + score
                if bucket.each:
                    message += " {:.0f} PASS".format(score)
                else:
                    message += " {:.1f} {}".format(score, bucket.stats)

            message += "\n{} {}-{} {} {}\n".format(
                player['gameInfo']['awayTeam'], player['gameInfo']['awayScore'],
                player['gameInfo']['homeScore'], player['gameInfo']['homeTeam'],
                player['gameInfo']['statusText']
            )

        message += "\n**Total"
        passed = 0
        for i in range(0, num_buckets):
            bucket = self.buckets[i]
            s = sums[i]
            if s >= bucket.target and bucket.order == 'DESC':
                passed += 1
            elif s <= bucket.target and bucket.order == 'ASC':
                passed += 1

            message += " {:.1f} {}".format(s, bucket.stats)
        message += "**\n"

        if passed >= num_buckets:
            message += "🟢 **YOU WIN**\n"

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
                score = bucket.load_score(player)
                player_scores[pid][i] = score
                sums[i] = sums[i] + score

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

        return sum(sums), passed, 0.0 if num_buckets == 0 else round(rate / num_buckets, 2)
