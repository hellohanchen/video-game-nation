import json
import os
import pathlib


class FastBreakProvider:
    def __init__(self):
        self.fb_info = {}
        self.reload()

    def reload(self):
        self.fb_info = load_fb_data()

    def get_fb(self, game_date):
        fb = self.fb_info.get(game_date)
        if fb is None:
            return {
                "count": 8,
                "isCombine": True,
                "buckets": []
            }
        return


def load_fb_data():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "fastbreak/resource/current.json"), 'r') as set_file:
        result = json.load(set_file)

    return result


FB_PROVIDER = FastBreakProvider()


if __name__ == '__main__':
    fb = load_fb_data()
    print(fb)
