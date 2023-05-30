import json
import os
import pathlib

import unidecode


def load_set_data():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "moments/resource/sets.json"), 'r') as set_file:
        data = json.load(set_file)

        for set in data['sets']:
            TS_SET_INFO[set['flowId']] = {
                'id': set['id'],
                'flowName': set['flowName'],
                'flowSeriesNumber': set['flowSeriesNumber']
            }


def load_play_data():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "moments/resource/enriched_plays.json"), 'r') as set_file:
        for play_id, play in json.load(set_file)['plays'].items():
            TS_PLAY_INFO[play[0]['flowId']] = play


def load_team_data():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "moments/resource/teams.json"), 'r') as team_file:
        data = json.load(team_file)

        for team in data['teams']:
            TS_TEAM_NAME_TO_ID[team['name']] = {
                'id': team['id']
            }


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
TS_PLAY_INFO = {}
TS_TEAM_NAME_TO_ID = {}
TS_PLAYER_ID_MOMENTS = load_player_moment_info()
TS_ENRICHED_PLAYS = load_enriched_plays()

load_set_data()
load_play_data()
load_team_data()

