import datetime
import json
import os
import pathlib
from provider.nba.nba_provider import NBA_PROVIDER
from utils import parse_slash_date, to_slash_date


class FastBreakProvider:
    def __init__(self):
        self.fb_info = {}
        self.coming_date = ""
        self.reload()

    def reload(self):
        self.fb_info = load_fb_data()
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

    def get_fb(self, game_date):
        fb = self.fb_info.get(game_date)
        if fb is None:
            return {
                "count": 8,
                "isCombine": True,
                "buckets": []
            }
        return fb

    def get_dates(self):
        return list(self.fb_info.keys())


def load_fb_data():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "fastbreak/resource/current.json"), 'r') as set_file:
        result = json.load(set_file)

    return result


FB_PROVIDER = FastBreakProvider()


if __name__ == '__main__':
    fb = load_fb_data()
    print(fb)
