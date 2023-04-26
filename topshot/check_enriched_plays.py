import json
import os
import pathlib


def load_enriched_plays():
    result = {}
    count = 0

    plays = json.load(open(os.path.join(pathlib.Path(__file__).parent.resolve(), "result/otm_enriched_plays_fixed.json"), 'r'))
    for play in plays:
        if play['flowID'] == -1:
            continue

        if play['flowID'] in result:
            print('-'*88)
            print(result[play['flowID']])
            print(play)
            count += 1
        else:
            result[play['flowID']] = play

    print(count)
    return result


print(len(load_enriched_plays()))
