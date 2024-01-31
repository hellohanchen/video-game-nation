import json
import os
import pathlib

import requests

from constants import NBA_TEAMS


def download_schedule():
    url = 'https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/scheduleLeagueV2.json"), 'w') as file:
            json.dump(data, file)

        store_dates_games_teams(data)
    else:
        print(f'Request failed with status code {response.status_code}')


def store_dates_games_teams(schedule_json):
    games_dates = {}
    games_teams = {}

    for gamesOnDate in schedule_json['leagueSchedule']['gameDates']:
        date = gamesOnDate['gameDate'][:10]
        games_dates[date] = {}

        for game in gamesOnDate['games']:
            if game['homeTeam']['teamTricode'] not in NBA_TEAMS or game['awayTeam']['teamTricode'] not in NBA_TEAMS:
                continue

            games_dates[date][game['gameId']] = {
                'homeTeam': game['homeTeam']['teamTricode'],
                'awayTeam': game['awayTeam']['teamTricode']
            }
            games_teams[game['gameId']] = {
                'homeTeam': game['homeTeam']['teamTricode'],
                'awayTeam': game['awayTeam']['teamTricode']
            }

        if len(games_dates[date]) == 0:
            del games_dates[date]

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), 'data/game_dates.json'), 'w') as output_file:
        json.dump(games_dates, output_file, indent=2)

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), 'data/game_teams.json'), 'w') as output_file:
        json.dump(games_teams, output_file, indent=2)


if __name__ == '__main__':
    download_schedule()
