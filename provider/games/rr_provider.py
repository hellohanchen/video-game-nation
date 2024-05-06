import datetime
import json
import os
import pathlib
from typing import Dict, List

from constants import NBA_TEAMS
from provider.nba.nba_provider import NBA_PROVIDER
from utils import parse_slash_date, to_slash_date


class RedemptionRunProvider:
    def __init__(self):
        self.rr_details: Dict[str, Dict[str, any]] = {}
        self.eligible_team_ids: List[int] = []
        self.coming_date = ""
        self.reload()

    def reload(self):
        rr_data = load_rr_data()
        self.rr_details = rr_data['runs']
        self.eligible_team_ids = [NBA_TEAMS[t] for t in rr_data['teams']]
        self.set_coming_game_date()

    def get_coming_game_date(self):
        self.set_coming_game_date()
        return self.coming_date

    def set_coming_game_date(self):
        cur_date = parse_slash_date(NBA_PROVIDER.get_coming_game_date())
        max_date = parse_slash_date(NBA_PROVIDER.latest_date)

        while cur_date <= max_date:
            if to_slash_date(cur_date) in self.rr_details:
                self.coming_date = to_slash_date(cur_date)
                return

            cur_date = cur_date + datetime.timedelta(days=1)

        self.coming_date = to_slash_date(cur_date)

    def get_next_game_date(self, start_date):
        max_date = parse_slash_date(NBA_PROVIDER.latest_date)
        last_date_with_rr = parse_slash_date(max(list(self.rr_details.keys())))

        while start_date <= max_date:
            start_date = start_date + datetime.timedelta(days=1)

            slash_start_date = to_slash_date(start_date)
            if slash_start_date in self.rr_details:
                return slash_start_date

            if slash_start_date in NBA_PROVIDER.game_schedule and start_date > last_date_with_rr:
                return slash_start_date

        return to_slash_date(start_date)

    def get_rr(self, game_date) -> Dict[str, any]:
        return self.rr_details.get(game_date, {"buckets": [], "threshold": 1.0})


def load_rr_data():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "redemptionrun/resource/current.json"), 'r') as rr_file:
        result = json.load(rr_file)

    return result


RR_PROVIDER = RedemptionRunProvider()

if __name__ == '__main__':
    print(RR_PROVIDER.get_next_game_date(parse_slash_date("02/15/2024")))
