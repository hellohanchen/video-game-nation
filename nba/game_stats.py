import json
import os.path
import pathlib

from nba_api.live.nba.endpoints import scoreboard, boxscore

GAME_SCHEDULE = json.load(open(os.path.join(pathlib.Path(__file__).parent.resolve(), 'results/game_dates.json'), 'r'))
GAME_TEAMS = json.load(open(os.path.join(pathlib.Path(__file__).parent.resolve(), 'results/game_teams.json'), 'r'))


def get_scoreboard():
    """
    Get latest scoreboard.

    :return: scoreboard in dictionary
    """
    return scoreboard.ScoreBoard().get_dict()['scoreboard']


def get_games_on_date(date):
    """
    Get all game ids for a provided date.

    :param date: game date, example 01/01/2023
    :return: list of game ids
    """
    return GAME_SCHEDULE[date]


def get_teams_for_games(games):
    """
    Get teams' tri codes for a list of games.

    :param games: list of game id
    :return: a dictionary of {game_id, [teamTriCodes]}
    """
    return {game_id: get_teams_for_game(game_id) for game_id in games}


def get_teams_for_game(game_id):
    """
    Return 2 teams' tri code for a game.

    :param game_id: game id
    :return: [homeTeamTriCode, awayTeamTriCode]
    """
    return {GAME_TEAMS[game_id]['homeTeam'], GAME_TEAMS[game_id]['awayTeam']}


def get_players_for_games(games_teams):
    """
    Get players' ids set of each game in a list.

    :param games_teams: games and teams in each game
    :return: a dictionary of {game_id, {player_ids}}
    """
    
    result = {}

    for game_id in games_teams:
        try:
            game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
        except Exception:
            continue

        if game_stats['gameStatus'] == 1:
            continue

        player_ids = []
        if game_stats['homeTeam']['teamTricode'] in games_teams[game_id]:
            player_ids.extend([player['personId'] for player in game_stats['homeTeam']['players']])
        if game_stats['awayTeam']['teamTricode'] in games_teams[game_id]:
            player_ids.extend([player['personId'] for player in game_stats['awayTeam']['players']])

        if len(player_ids) > 0:
            result[game_id] = set(player_ids)

    return result
