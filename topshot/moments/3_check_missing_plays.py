import asyncio
import json
import os
import pathlib

from topshot.graphql.get_set_plays import get_set_plays


def find_missing_plays():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/plays.json"), 'r') as play_file:
        data = json.load(play_file)

    max_play_id = list(data.keys())[0]

    for i in range(1, int(max_play_id)):
        if str(i) not in data:
            print(f"missing play id: {i}")


if __name__ == '__main__':
    find_missing_plays()
