import json
import os
import pathlib

historic_sets = [129, 123, 121, 120, 119, 117, 114, 109, 100, 89, 84, 83, 82,
                 76, 75, 74, 72, 71, 61, 57, 49, 48, 47, 46, 25]

excluded_teams = [
    "Eastern Conference All-Stars",
    "Sophomore Team",
    "Rookie Team",
    "Team Durant",
    "Team Giannis",
    "Team LeBron",
    "Team Stewart",
    "Team Wilson",
    "Western Conference All-Stars"
]


def group_play_to_checklists():
    set_checklists = {}
    team_checklists = {}

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/enriched_plays.json"),
              'r') as enriched_file:
        loaded = json.load(enriched_file)['plays']

        for play_id in loaded:
            for moment in loaded[play_id]:
                series = moment['series']
                set_id = moment['setFlowId']
                team = moment['team']
                player_name = moment['playerName']

                if set_id not in set_checklists:
                    set_checklists[set_id] = {
                        'name': f"{moment['set']} {series}",
                        'series': series,
                        'moments': {},
                        'count': 0
                    }

                set_checklists[set_id]['moments'][play_id] = {
                    'player': player_name,
                    'team': team,
                    'playerId': moment['playerId'],
                    'date': moment['date'],
                }
                set_checklists[set_id]['count'] = len(set_checklists[set_id]['moments'])

                if series > 4:
                    continue

                if player_name == team or team in excluded_teams:
                    continue

                if team not in team_checklists:
                    team_checklists[team] = {
                        'series': {},
                        'contemporary': {
                            'count': 0,
                            'players': {}
                        },
                        'all': {
                            'count': 0,
                            'players': {}
                        }
                    }

                player_id = moment['playerId']
                if player_id not in team_checklists[team]['all']['players']:
                    team_checklists[team]['all']['players'][player_id] = {
                        'name': player_name,
                        'plays': []
                    }
                team_checklists[team]['all']['players'][player_id]['plays'].append(int(play_id))
                team_checklists[team]['all']['count'] = len(team_checklists[team]['all']['players'])

                if set_id in historic_sets:
                    continue

                if player_id not in team_checklists[team]['contemporary']['players']:
                    team_checklists[team]['contemporary']['players'][player_id] = {
                        'name': player_name,
                        'plays': []
                    }
                team_checklists[team]['contemporary']['players'][player_id]['plays'].append(int(play_id))
                team_checklists[team]['contemporary']['count'] = len(team_checklists[team]['contemporary']['players'])
                if series not in team_checklists[team]['series']:
                    team_checklists[team]['series'][series] = {
                        'count': 0,
                        'players': {}
                    }
                if player_id not in team_checklists[team]['series'][series]['players']:
                    team_checklists[team]['series'][series]['players'][player_id] = {
                        'name': player_name,
                        'plays': []
                    }
                team_checklists[team]['series'][series]['players'][player_id]['plays'].append(int(play_id))
                team_checklists[team]['series'][series]['count'] = len(
                    team_checklists[team]['series'][series]['players'])

        for play_id in loaded:
            for moment in loaded[play_id]:
                series = moment['series']
                set_id = moment['setFlowId']
                team = moment['team']
                player_name = moment['playerName']

                if series > 4:
                    continue

                if player_name == team or team in excluded_teams:
                    continue

                if set_id not in historic_sets:
                    continue

                checklist = team_checklists[team]
                player_id = moment['playerId']

                if player_id in checklist['contemporary']['players']:
                    if int(play_id) not in checklist['contemporary']['players'][player_id]['plays']:
                        checklist['contemporary']['players'][player_id]['plays'].append(int(play_id))

                if series not in checklist['series']:
                    continue

                if player_id in checklist['series'][series]['players']:
                    if int(play_id) not in checklist['series'][series]['players'][player_id]['plays']:
                        checklist['series'][series]['players'][player_id]['plays'].append(int(play_id))

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/set_checklists.json"),
              'w') as output_file:
        json.dump(set_checklists, output_file, indent=2)

    teams = list(team_checklists.keys())
    teams.sort(reverse=False)
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/team_checklists.json"),
              'w') as output_file:
        json.dump({team: team_checklists[team] for team in teams}, output_file, indent=2)


if __name__ == '__main__':
    group_play_to_checklists()
