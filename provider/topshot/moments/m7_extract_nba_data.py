import json
import os
import pathlib


def extract_nba_data():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "../../nba/data/current_nba_players.json"), 'r') as player_file:
        nba_players = json.load(player_file)

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/enriched_plays.json"),
              'r') as plays_file:
        loaded = json.load(plays_file)

        result = {}

        for play_id in loaded['plays']:
            play_1 = loaded['plays'][play_id][0]
            if play_1['playerId'] is not None and str(play_1['playerId']) not in nba_players:
                continue
            if play_1['playerId'] is None and play_1['teamId'] == 0:
                continue

            result[play_id] = {}
            for play in loaded['plays'][play_id]:
                result[play_id][play['setFlowId']] = {
                    'playerId': play['playerId'],
                    'playType': play['playType'],
                    'tier': play['tier'],
                    'badges': play['badges'],
                    'teamId': play['teamId'],
                }

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/nba_plays.json"),
              'w') as vgn_file:
        json.dump(result, vgn_file, indent=2)


if __name__ == '__main__':
    extract_nba_data()
