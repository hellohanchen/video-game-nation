import json
import os
import pathlib

from topshot.load_plays import load_detailed_play_data_key_flowid, load_detailed_play_data_key_uid

BADGES = {
    "topShotDebutBadge": "TSD",
    "rookieYearBadge": "RY",
    "rookiePremiereBadge": "RP",
    "rookieMintBadge": "RM",
    "mvpYearBadge": "MVP",
    "championshipYearBadge": "CY",
    "challengeReward": "CR"
}


def enrich_detailed_plays(detailed_plays):
    for play_uid in detailed_plays:
        detailed_plays[play_uid]['CR'] = False
        detailed_plays[play_uid]['RM'] = False
        detailed_plays[play_uid]['tier'] = "Unknown"

    file_list = os.listdir(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/otm/"))

    not_found_play_uids = []

    for file in file_list:
        if file.startswith("postman_test_run"):
            postman_variables = json.load(open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/otm/"+file), 'r'))['values']
            for variable in postman_variables:
                if variable['key'] == 'responses':
                    otm_moment_data = json.loads(variable['value'].replace("\\\"", "\""))

                    for moments in otm_moment_data:
                        for moment in moments:
                            play_uid = moment['playId']
                            if play_uid in detailed_plays:
                                detailed_plays[play_uid]['tier'] = moment['tier']
                            else:
                                not_found_play_uids.append(play_uid)
                                detailed_plays[play_uid] = {
                                    "flowID": -1,
                                    "playID": play_uid,
                                    "playerName": moment['playerName'],
                                    "playerID": 0,
                                    "playType": moment['playCategory'],
                                    "playDate": "",
                                    "TSD": False,
                                    "RY": False,
                                    "RP": False,
                                    "MVP": False,
                                    "CY": False,
                                    "TEAM": False,
                                    "tier": moment['tier'],
                                    "RM": False,
                                    "CR": False
                                }
                            for badge in BADGES:
                                detailed_plays[play_uid][BADGES[badge]] = moment[badge]

    print("Not found play uids count: {}, list: {}".format(len(not_found_play_uids), ', '.join(not_found_play_uids)))


load_detailed_play_data_key_flowid()
detailed_plays = load_detailed_play_data_key_uid()
enrich_detailed_plays(detailed_plays)

play_uids = list(detailed_plays.keys())
play_uids.sort(key=lambda uid: detailed_plays[uid]['flowID'], reverse=True)

with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/otm_enriched_plays.json"), 'w') as output_file:
    json.dump([detailed_plays[uid] for uid in play_uids], output_file, indent=2)
