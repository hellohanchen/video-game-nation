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


def enrich_plays():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/plays.json"), 'r') as play_file:
        play_moments = json.load(play_file)

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/enriched_plays.json"),
              'r') as enriched_file:
        loaded = json.load(enriched_file)['plays']
        previous_results = {}

        for play_id in loaded:
            previous_results[play_id] = loaded[play_id][0]

    for play_id in play_moments:
        if play_id in previous_results:
            previous_result = previous_results[play_id]
            for moment in play_moments[play_id]:
                moment['tier'] = TIER_MAP[moment['tier']]
                moment['badges'] = previous_result['badges']
        else:
            for moment in play_moments[play_id]:
                moment['tier'] = TIER_MAP[moment['tier']]

    max_play_id = list(play_moments.keys())[0]
    missing_ids = []

    for i in range(1, int(max_play_id)):
        if str(i) not in play_moments:
            missing_ids.append(i)

    play_ids = list(play_moments.keys())
    play_ids.sort(reverse=True, key=lambda pid: int(pid))

    result = {
        "notFound": missing_ids,
        "count": sum([len(play_moments[pid]) for pid in play_ids]),
        "plays": {}
    }

    for play_id in play_ids:
        result['plays'][play_id] = play_moments[play_id]

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/enriched_plays.json"),
              'w') as enriched_file:
        json.dump(result, enriched_file, indent=2)


if __name__ == '__main__':
    enrich_plays()
