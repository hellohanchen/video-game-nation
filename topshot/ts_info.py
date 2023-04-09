import json
import os
import pathlib

import unidecode


def load_set_data():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "result/sets.json"), 'r') as set_file:
        data = json.load(set_file)

        for set in data['sets']:
            TS_SET_INFO[set['flowId']] = {
                'id': set['id'],
                'flowName': set['flowName'],
                'flowSeriesNumber': set['flowSeriesNumber']
            }


def load_player_data():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "result/players.json"), 'r') as player_file:
        data = json.load(player_file)

        for player in data['players']:
            player_name = unidecode.unidecode(player['label'])

            TS_PLAYER_NAME_TO_ID[player_name] = {
                'id': int(player['playerID'])
            }

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "result/players_2.json"), 'r') as player_file:
        data = json.load(player_file)

        for player in data['players']:
            player_name = unidecode.unidecode(player['name'])

            if player_name in TS_PLAYER_NAME_TO_ID:
                continue

            TS_PLAYER_NAME_TO_ID[player_name] = {
                'id': int(player['id'])
            }


def load_team_data():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "result/teams.json"), 'r') as team_file:
        data = json.load(team_file)

        for team in data['teams']:
            TS_TEAM_NAME_TO_ID[team['name']] = {
                'id': team['id']
            }
            TS_TEAM_NAME_TO_ID[team['name']]['id'] = team['id']


def get_player_flow_id_str(player_fullname):
    player_fullname_decoded = unidecode.unidecode(player_fullname)

    if player_fullname_decoded not in TS_PLAYER_NAME_TO_ID:
        return ""

    return str(TS_PLAYER_NAME_TO_ID[player_fullname_decoded]['id'])


def load_player_moment_info():
    result = {}

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "result/player_moment_info.json"), 'r') as player_file:
        loaded = json.load(player_file)

        for player_id in loaded:
            result[int(player_id)] = loaded[player_id]

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/current_nba_players.json"), 'r') as player_file:
        loaded = json.load(player_file)

        for player_id in loaded:
            result[int(player_id)]['isNBA'] = loaded[player_id]

    return result


def load_enriched_plays():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "result/otm_enriched_plays_fixed.json"), 'r') as plays_file:
        loaded = json.load(plays_file)

        result = {}

        for play in loaded['plays']:
            if play['flowID'] in result:
                continue

            result[play['flowID']] = play

        return result


TS_SET_INFO = {}
TS_PLAYER_NAME_TO_ID = {}
TS_TEAM_NAME_TO_ID = {}
TS_PLAYER_ID_MOMENTS = load_player_moment_info()
TS_ENRICHED_PLAYS = load_enriched_plays()

load_set_data()
load_player_data()
load_team_data()

