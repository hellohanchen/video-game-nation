import json
import os
import pathlib


def load_detailed_play_data_key_flowid():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/detailed_plays_fixed.json"), 'r') as play_file:
        loaded = json.load(play_file)

        result = {}
        dupe_play_uuids = []
        dupe_play_flow_ids = set([])
        for play_uid in loaded:
            flow_id = loaded[play_uid]['flowID']
            if flow_id in result:
                dupe_play_flow_ids.add(str(flow_id))
                dupe_play_uuids.append(play_uid)
            else:
                result[flow_id] = loaded[play_uid]
                result[flow_id]['uuid'] = play_uid

        not_found = []
        for i in range(1, 3550):
            if i not in result:
                not_found.append(str(i))

        print("Loaded moments count: {}".format(len(result)))
        print("Duplicated uuids count: {}, list: {}".format(len(dupe_play_uuids), ','.join(dupe_play_flow_ids)))
        print("Not found flow ids: {}".format(','.join(not_found)))

        return result


def load_detailed_play_data_key_uid():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/detailed_plays_fixed.json"), 'r') as play_file:
        return json.load(play_file)
