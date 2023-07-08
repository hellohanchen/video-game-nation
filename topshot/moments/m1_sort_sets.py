import json
import os
import pathlib


def sort_sets():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/s4_sets.json"), 'r') as set_file:
        data = json.load(set_file)['sets']

    data.sort(reverse=True, key=lambda d : d['flowId'])

    sorted_data = {'sets': data}

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/s4_sets.json"), 'w') as set_file:
        json.dump(sorted_data, set_file, indent=2)


if __name__ == '__main__':
    sort_sets()
