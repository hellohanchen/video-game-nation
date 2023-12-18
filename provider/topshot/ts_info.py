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

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "moments/resource/player_moments.json"), 'r') as player_file:
        loaded = json.load(player_file)

        for player_id in loaded:
            result[int(player_id)] = loaded[player_id]

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "../../provider/nba/data/current_nba_players.json"), 'r') as player_file:
        loaded = json.load(player_file)

        for player_id in loaded:
            player_id_int = int(player_id)
            if player_id_int in result:
                result[player_id_int]['isNBA'] = loaded[player_id]

    return result


def load_enriched_plays():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "moments/resource/enriched_plays.json"), 'r') as plays_file:
        loaded = json.load(plays_file)

        result = {}

        for play_id in loaded['plays']:
            play = loaded['plays'][play_id][0]
            if play['flowId'] in result:
                continue

            result[play['flowId']] = loaded['plays'][play_id]

        return result


def load_set_checklists():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "moments/resource/set_checklists.json"), 'r') as in_file:
        return json.load(in_file)


def load_team_checklists():
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "moments/resource/team_checklists.json"), 'r') as in_file:
        return json.load(in_file)


TS_SET_INFO = {}
TS_PLAY_INFO = {}
TS_TEAM_NAME_TO_ID = {}
TS_PLAYER_ID_MOMENTS = load_player_moment_info()
TS_ENRICHED_PLAYS = load_enriched_plays()
TS_SET_CHECKLISTS = load_set_checklists()
TS_TEAM_CHECKLISTS = load_team_checklists()

load_set_data()
load_play_data()
load_team_data()

