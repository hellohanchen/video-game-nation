import json
import os
import pathlib

with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/otm/postman_test_run_750.json"), 'r') as player_file:
    result = json.load(player_file)
    for value in result['values']:
        if value['key'] == 'responses':
            play_info = json.loads(value['value'].replace("\\\"", "\""))

    print(play_info)
