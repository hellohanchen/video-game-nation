import json
import os
import pathlib


class TopshotProvider:
    def __init__(self):
        self.play_info = {}
        self.player_moments = {}
        self.set_info = {}
        self.set_checklists = {}
        self.team_name_to_id = {}
        self.team_checklists = {}
        self.reload()

    def reload(self):
        self.play_info = load_enriched_plays()
        self.player_moments = load_player_moment_info()
        self.set_info = load_set_data()
        self.set_checklists = load_set_checklists()
        self.team_name_to_id = load_team_data()
        self.team_checklists = load_team_checklists()


def load_set_data():
    result = {}

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "moments/resource/sets.json"), 'r') as set_file:
        data = json.load(set_file)

        for set in data['sets']:
            result[set['flowId']] = {
                'id': set['id'],
                'flowName': set['flowName'],
                'flowSeriesNumber': set['flowSeriesNumber']
            }

    return result


def load_team_data():
    result = {}

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "moments/resource/teams.json"), 'r') as team_file:
        data = json.load(team_file)

        for team in data['teams']:
            result[team['name']] = {
                'id': team['id']
            }

    return result


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


TS_PROVIDER = TopshotProvider()
