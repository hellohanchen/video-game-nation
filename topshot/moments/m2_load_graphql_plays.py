import asyncio
import json
import os
import pathlib

from topshot.graphql.get_set_plays import get_set_plays

TIER_MAP = {
    "SET_VISUAL_COMMON": "C",
    "SET_VISUAL_RARE": "R",
    "SET_VISUAL_FANDOM": "F",
    "SET_VISUAL_LEGENDARY": "L",
    "SET_VISUAL_ANTHOLOGY": "A"
}


def load_set_plays():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/s4_sets.json"), 'r') as set_file:
        data = json.load(set_file)['sets']

    plays = {}

    for s in data:
        print(f"loading plays for set ${s['id']}...")
        set_graphql = asyncio.run(get_set_plays(s['id']))
        for play in set_graphql['plays']:
            player_name = play['stats']['playerName'] if 'playerName' in play['stats'] and \
                                                         play['stats']['playerName'] is not None and \
                                                         play['stats']['playerName'] != "" else play['stats'].get(
                'teamAtMoment')

            play_id = int(play['flowID'])
            game_date = play['stats']['dateOfMoment'][:10] if play['stats'].get('dateOfMoment') is not None else ""

            if play_id not in plays:
                plays[play_id] = []

            plays[play_id].append(
                {
                    'id': play['id'],
                    'flowId': int(play['flowID']),
                    'set': s['flowName'],
                    'setId': s['id'],
                    'setFlowId': int(s['flowId']),
                    'playerId': int(play['stats'].get('playerID')) if play['stats'].get('playerID') is not None else None,
                    'playerName': player_name,
                    'team': play['stats'].get('teamAtMoment'),
                    'playType': play['stats'].get('playCategory'),
                    'date': game_date,
                    'series': s['flowSeriesNumber'],
                    'tier': TIER_MAP[set_graphql['setVisualId']],
                    'badges': ['TEAM'] if play['stats'].get('playerID') is None else [],
                }
            )

    play_ids = list(plays.keys())
    play_ids.sort(reverse=True)

    sorted_plays = {}
    for pid in play_ids:
        sorted_plays[pid] = plays[pid]

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/plays.json"), 'w') as play_file:
        json.dump(sorted_plays, play_file, indent=2)


if __name__ == '__main__':
    load_set_plays()
