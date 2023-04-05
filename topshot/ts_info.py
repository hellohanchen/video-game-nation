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


TS_SET_INFO = {}
TS_PLAYER_NAME_TO_ID = {}
TS_TEAM_NAME_TO_ID = {}

load_set_data()
load_player_data()
load_team_data()

