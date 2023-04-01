import json

with open('scheduleLeagueV2.json', 'r') as schedule_file:
    schedule_json = json.load(schedule_file)

    result = {}

    for gamesOnDate in schedule_json['leagueSchedule']['gameDates']:
        for game in gamesOnDate['games']:
            result[game['gameId']] = {
                'homeTeam': game['homeTeam']['teamTricode'],
                'awayTeam': game['awayTeam']['teamTricode']
            }

    with open('game_teams.json', 'w') as output_file:
        json.dump(result, output_file, indent=2)
