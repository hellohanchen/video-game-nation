import json

from nba_api.live.nba.endpoints import scoreboard, boxscore

GAME_SCHEDULE = json.load(open('game_dates.json', 'r'))
GAME_TEAMS = json.load(open('game_teams.json', 'r'))

# Today's Score Board
scoreboard = scoreboard.ScoreBoard()
games = boxscore.BoxScore(game_id="0022201097")

# json
print(games.get_json())
g_json = games.get_json()

s_json = scoreboard.get_json()

# dictionary
print(games.get_dict())


def get_games_on_date(date):
    return GAME_SCHEDULE[date]


def get_teams_for_games(games):
    result = []
    for game in games:
        result.extend(get_teams_for_game(game))
    return result


def get_teams_for_game(game_id):
    return [GAME_TEAMS[game_id]['homeTeam'], GAME_TEAMS[game_id]['awayTeam']]


def get_players_for_games(games, teams):
    result = []

    for game_id in games:
        game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
        if game_stats['gameStatus'] == 1:
            continue

        if game_stats['homeTeam']['teamTricode'] in teams:
            result.extend([player['name'] for player in game_stats['homeTeam']['players']])
        if game_stats['awayTeam']['teamTricode'] in teams:
            result.extend([player['name'] for player in game_stats['awayTeam']['players']])

    return list(dict.fromkeys(result))
