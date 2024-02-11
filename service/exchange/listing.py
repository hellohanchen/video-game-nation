import json
import os
import pathlib


EXCHANGE_SETS = {}
with open(os.path.join(
        pathlib.Path(__file__).parent.resolve(),
        'resource/sets.json'
), 'r') as json_file:
    EXCHANGE_SETS = json.load(json_file)


