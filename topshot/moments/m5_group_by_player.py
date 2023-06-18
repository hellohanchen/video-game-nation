import json
import os
import pathlib


TIER_MAP = {
    "C": "Common",
    "R": "Rare",
    "F": "Fandom",
    "L": "Legendary",
    "A": "Unknown"
}


def group_play_by_player():
    result = {}

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/enriched_plays.json"),
              'r') as enriched_file:
        loaded = json.load(enriched_file)['plays']

        for play_id in loaded:
            for moment in loaded[play_id]:
                player_id = moment.get('playerId')

                if player_id is None:
                    continue

                if player_id not in result:
                    result[player_id] = {
                        'id': player_id,
                        'name': moment['playerName'],
                        'series': [],
                        'badges': {
                            1: {},
                            2: {},
                            3: {},
                            4: {}
                        }
                    }

                if moment['series'] not in result[player_id]['series']:
                    result[player_id]['series'].append(moment['series'])

                for badge in moment['badges']:
                    if badge not in result[player_id]['badges'][moment['series']]:
                        result[player_id]['badges'][moment['series']][badge] = True

    player_ids = list(result.keys())
    player_ids.sort(reverse=True)

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/player_moments.json"),
              'w') as output_file:
        json.dump({player_id: result[player_id] for player_id in player_ids}, output_file, indent=2)


if __name__ == '__main__':
    group_play_by_player()
