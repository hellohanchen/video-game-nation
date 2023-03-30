import json
import os.path
import pathlib

from nba_api.live.nba.endpoints import scoreboard, boxscore

GAME_SCHEDULE = json.load(open(os.path.join(pathlib.Path(__file__).parent.resolve(), 'game_dates.json'), 'r'))
GAME_TEAMS = json.load(open(os.path.join(pathlib.Path(__file__).parent.resolve(), 'game_teams.json'), 'r'))


def get_scoreboard():
    return scoreboard.ScoreBoard().get_dict()['scoreboard']


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
        try:
            game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
        except Exception:
            continue

        if game_stats['gameStatus'] == 1:
            continue

        if game_stats['homeTeam']['teamTricode'] in teams:
            result.extend([player['personId'] for player in game_stats['homeTeam']['players']])
        if game_stats['awayTeam']['teamTricode'] in teams:
            result.extend([player['personId'] for player in game_stats['awayTeam']['players']])

    return set(result)
