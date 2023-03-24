import json
import os

import unidecode


def load_set_data():
    with open(os.path.abspath("C:\\workspace\\python\\video-game-nation\\topshot\\resource\\sets.json"), 'r') as set_file:
        data = json.load(set_file)

        for set in data['sets']:
            TOPSHOT_SET_INFO[set['flowId']] = {}
            TOPSHOT_SET_INFO[set['flowId']]['id'] = set['id']
            TOPSHOT_SET_INFO[set['flowId']]['flowName'] = set['flowName']
            TOPSHOT_SET_INFO[set['flowId']]['flowSeriesNumber'] = set['flowSeriesNumber']


def load_player_data():
    with open(os.path.abspath("C:\\workspace\\python\\video-game-nation\\topshot\\resource\\players.json"), 'r') as player_file:
        data = json.load(player_file)

        for player in data['players']:
            player_name = unidecode.unidecode(player['label'])

            TOPSHOT_PLAYER_INFO[player_name] = {}
            TOPSHOT_PLAYER_INFO[player_name]['id'] = player['playerID']

    with open(os.path.abspath("C:\\workspace\\python\\video-game-nation\\topshot\\resource\\players_2.json"), 'r') as player_file:
        data = json.load(player_file)

        for player in data['players']:
            player_name = unidecode.unidecode(player['name'])

            if player_name in TOPSHOT_PLAYER_INFO:
                continue
            TOPSHOT_PLAYER_INFO[player_name] = {}
            TOPSHOT_PLAYER_INFO[player_name]['id'] = int(player['id'])


def load_team_data():
    with open(os.path.abspath("C:\\workspace\\python\\video-game-nation\\topshot\\resource\\teams.json"), 'r') as team_file:
        data = json.load(team_file)

        for team in data['teams']:
            TOPSHOT_TEAM_INFO[team['name']] = {}
            TOPSHOT_TEAM_INFO[team['name']]['id'] = team['id']


def get_player_flow_id_str(player_fullname):
    player_fullname_decoded = unidecode.unidecode(player_fullname)

    if player_fullname_decoded not in TOPSHOT_PLAYER_INFO:
        return ""

    return str(TOPSHOT_PLAYER_INFO[player_fullname_decoded]['id'])


TOPSHOT_SET_INFO = {}
TOPSHOT_PLAYER_INFO = {}
TOPSHOT_TEAM_INFO = {}

load_set_data()
load_player_data()
load_team_data()

