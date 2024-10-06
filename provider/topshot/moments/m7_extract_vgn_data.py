import json
import os
import pathlib


def extract_vgn_data():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/enriched_plays.json"),
              'r') as plays_file:
        loaded = json.load(plays_file)

        result = {}

        for play_id in loaded['plays']:
            result[play_id] = {}
            for play in loaded['plays'][play_id]:
                result[play_id][play['setFlowId']] = {
                    'playerId': play['playerId'],
                    'playType': play['playType'],
                    'tier': play['tier'],
                    'badges': play['badges'],
                    'teamId': play['teamId'],
                }

        with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/vgn_plays.json"),
                  'w') as vgn_file:
            json.dump(result, vgn_file, indent=2)


if __name__ == '__main__':
    extract_vgn_data()
