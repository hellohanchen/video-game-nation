import datetime
import json
import os
import pathlib
from typing import Dict, List, Optional

from constants import INVALID_ID
from provider.nba.nba_provider import NBA_PROVIDER
from utils import parse_slash_date, to_slash_date


class FastBreakProvider:
    def __init__(self):
        self.contests: Dict[int, Dict[str, any]] = {}
        self.fb_details: Dict[str, Dict[int, Dict[str, any]]] = {}
        self.date_contests: Dict[str, Dict[int, int]] = {}
        self.coming_date = ""
        self.reload()

    def reload(self):
        fb_data = load_fb_data()
        contests: Dict[int, Dict[str, any]] = {}
        fb_details: Dict[str, Dict[int, Dict]] = {}
        date_contests: Dict[str, Dict[int, int]] = {}

        for c in fb_data['contests']:
            cid = c['id']
            default_cid = c['defaultContestID']
            if cid == default_cid:
                dates = []
                validation = c['validation']
                for d in c['dates']:
                    if d not in fb_details:
                        fb_details[d] = {}
                    if d not in date_contests:
                        date_contests[d] = {}

                    fb_details[d][cid] = c['dates'][d]

                    for ch in c['channels']:
                        date_contests[d][ch] = cid

                    date_contests[d][INVALID_ID] = cid
                    dates.append(d)
            else:
                dates = contests[default_cid]['dates']
                validation = contests[default_cid]['validation']
                for d in dates:
                    if d in c['dates']:
                        fb_details[d][cid] = c['dates'][d]
                    else:
                        fb_details[d][cid] = fb_details[d][default_cid]

                    for ch in c['channels']:
                        date_contests[d][ch] = cid

            contests[cid] = {
                "dates": dates,
                "validation": validation,
                "name": c['name']
            }

        self.fb_details = fb_details
        self.contests = contests
        self.date_contests = date_contests
        self.set_coming_game_date()

    def get_coming_game_date(self):
        self.set_coming_game_date()
        return self.coming_date

    def set_coming_game_date(self):
        cur_date = parse_slash_date(NBA_PROVIDER.get_coming_game_date())
        max_date = parse_slash_date(NBA_PROVIDER.latest_date)

        while cur_date <= max_date:
            if to_slash_date(cur_date) in self.fb_details:
                self.coming_date = to_slash_date(cur_date)
                return

            cur_date = cur_date + datetime.timedelta(days=1)

        self.coming_date = "N/A"

    def get_next_game_date(self, start_date):
        max_date = parse_slash_date(NBA_PROVIDER.latest_date)
        last_date_with_fb = parse_slash_date(max(list(self.fb_details.keys())))

        while start_date <= max_date:
            start_date = start_date + datetime.timedelta(days=1)

            slash_start_date = to_slash_date(start_date)
            if slash_start_date in self.fb_details:
                return slash_start_date

            if slash_start_date in NBA_PROVIDER.game_schedule and start_date > last_date_with_fb:
                return slash_start_date

        return to_slash_date(start_date)

    def get_fbs(self, game_date) -> Dict[int, Dict[str, any]]:
        return self.fb_details.get(game_date, {})

    def get_dates(self, game_date):
        return self.contests[self.date_contests[game_date][INVALID_ID]]['dates']

    def get_contest_id(self, game_date, channel_id) -> Optional[int]:
        return self.date_contests.get(game_date, {}).get(channel_id)


def load_fb_data():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "fastbreak/resource/current.json"), 'r') as set_file:
        result = json.load(set_file)

    return result


FB_PROVIDER = FastBreakProvider()

if __name__ == '__main__':
    print(FB_PROVIDER.get_next_game_date(parse_slash_date("02/15/2024")))
