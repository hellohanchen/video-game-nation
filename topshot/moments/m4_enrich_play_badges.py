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
        new_plays = json.load(play_file)

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/enriched_plays.json"),
              'r') as enriched_file:
        loaded = json.load(enriched_file)['plays']
        existing_plays = {}

        for play_id in loaded:
            existing_plays[play_id] = loaded[play_id]

    for play_id in new_plays:
        if play_id in existing_plays:
            for new_moment in new_plays[play_id]:
                new_moment['tier'] = TIER_MAP[new_moment['tier']]
                new_moment['badges'] = existing_plays[play_id][0]['badges']
        else:
            for new_moment in new_plays[play_id]:
                new_moment['tier'] = TIER_MAP[new_moment['tier']]

    for play_id in existing_plays:
        if play_id not in new_plays:
            new_plays[play_id] = existing_plays[play_id]

    max_play_id = list(new_plays.keys())[0]
    missing_ids = []

    for i in range(1, int(max_play_id)):
        if str(i) not in new_plays:
            missing_ids.append(i)

    play_ids = list(new_plays.keys())
    play_ids.sort(reverse=True, key=lambda pid: int(pid))

    result = {
        "notFound": missing_ids,
        "count": sum([len(new_plays[pid]) for pid in play_ids]),
        "plays": {}
    }

    for play_id in play_ids:
        result['plays'][play_id] = new_plays[play_id]

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/enriched_plays.json"),
              'w') as enriched_file:
        json.dump(result, enriched_file, indent=2)


if __name__ == '__main__':
    enrich_plays()
