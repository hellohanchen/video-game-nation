import json
import os
import pathlib


def load_player_data():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/detailed_players.json"), 'r') as player_file:
        return json.load(player_file)


TS_PLAYER_INFO = load_player_data()
