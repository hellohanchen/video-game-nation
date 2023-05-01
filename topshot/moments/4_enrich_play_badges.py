import json
import os
import pathlib


def enrich_plays():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/plays.json"), 'r') as play_file:
        plays = json.load(play_file)

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/otm_enriched_plays.json"),
              'r') as enriched_file:
        loaded = json.load(enriched_file)['plays']
        otm_plays = {}

        for play in loaded:
            otm_plays[play['flowID']] = play

    for pid in plays:
        int_pid = int(pid)
        if int_pid in otm_plays:
            otm_play = otm_plays[int_pid]
            for moment in plays[pid]:
                if moment['id'] == otm_play['playID']:
                    for m in plays[pid]:
                        m['tier'] = otm_play['tier']

                    for badge in ["TSD", "RY", "RP", "MVP", "CY", "CR", "RM"]:
                        if otm_play[badge]:
                            for m in plays[pid]:
                                m['badges'].append(badge)
                    break

    max_play_id = list(plays.keys())[0]
    missing_ids = []

    for i in range(1, int(max_play_id)):
        if str(i) not in plays:
            missing_ids.append(i)

    play_ids = list(plays.keys())
    play_ids.sort(reverse=True, key=lambda pid: int(pid))

    result = {
        "notFound": missing_ids,
        "count": sum([len(plays[pid]) for pid in play_ids]),
        "plays": {}
    }

    for pid in play_ids:
        result['plays'][pid] = plays[pid]

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/enriched_plays.json"),
              'w') as enriched_file:
        json.dump(result, enriched_file, indent=2)


if __name__ == '__main__':
    enrich_plays()
