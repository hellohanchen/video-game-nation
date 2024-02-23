import datetime
import json
import os
import pathlib
from typing import Dict

from provider.nba.nba_provider import NBA_PROVIDER
from utils import parse_slash_date, to_slash_date


class FastBreakProvider:
    def __init__(self):
        self.fb_info = {}
        self.rounds = {}
        self.date_to_rounds = {}
        self.coming_date = ""
        self.reload()

    def reload(self):
        fb_data = load_fb_data()
        fbs = {}
        rounds = {}
        dates_to_rounds = {}

        for r in fb_data['rounds']:
            i = r['id']
            dates = []
            for d in r['dates']:
                f = r['dates'][d]
                fbs[d] = f
                dates.append(d)
                dates_to_rounds[d] = i

            rounds[i] = {
                "dates": dates,
                "validation": r['validation']
            }

        self.fb_info = fbs
        self.rounds = rounds
        self.date_to_rounds = dates_to_rounds
        self.set_coming_game_date()

    def get_coming_game_date(self):
        self.set_coming_game_date()
        return self.coming_date

    def set_coming_game_date(self):
        cur_date = parse_slash_date(NBA_PROVIDER.get_coming_game_date())
        max_date = parse_slash_date(NBA_PROVIDER.latest_date)

        while cur_date <= max_date:
            if to_slash_date(cur_date) in self.fb_info:
                self.coming_date = to_slash_date(cur_date)
                return

            cur_date = cur_date + datetime.timedelta(days=1)

        self.coming_date = "N/A"

    def get_next_game_date(self, start_date):
        max_date = parse_slash_date(NBA_PROVIDER.latest_date)
        last_date_with_fb = parse_slash_date(max(list(self.fb_info.keys())))

        while start_date <= max_date:
            start_date = start_date + datetime.timedelta(days=1)

            slash_start_date = to_slash_date(start_date)
            if slash_start_date in self.fb_info:
                return slash_start_date

            if slash_start_date in NBA_PROVIDER.game_schedule and start_date > last_date_with_fb:
                return slash_start_date

        return to_slash_date(start_date)

    def get_fb(self, game_date) -> Dict[str, any]:
        f = self.fb_info.get(game_date)
        if f is None:
            return {
                "count": 8,
                "isCombine": True,
                "buckets": []
            }
        return f

    def get_dates(self):
        return list(self.fb_info.keys())


def load_fb_data():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "fastbreak/resource/current.json"), 'r') as set_file:
        result = json.load(set_file)

    return result


FB_PROVIDER = FastBreakProvider()


if __name__ == '__main__':
    print(FB_PROVIDER.get_next_game_date(parse_slash_date("02/15/2024")))
