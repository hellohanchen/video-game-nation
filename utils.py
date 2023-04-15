from typing import Dict, Union

from constants import EMPTY_PLAYER_COLLECTION


def truncate_message(msgs, msg, add, limit):
    if len(msg) + len(add) >= limit:
        msgs.append(msg)
        return add, ""
    else:
        return msg + add, ""


def get_lead_team(team1, team1_score, team2, team2_score):
    if team1_score == team2_score:
        return "TIE"
    if team1_score > team2_score:
        return team1
    return team2


def get_game_info(game_boxscore: Dict[str, Union[str, Dict[str, Union[str, int]]]]) -> Dict[str, Union[str, int]]:
    """
    Returns a dictionary with game information from the given game boxscore.

    Args:
        game_boxscore (dict): A dictionary containing game boxscore information.

    Returns:
        dict: A dictionary with the following keys:
            - stats (str): The game status.
            - quarter (int): The current quarter of the game.
            - clock (str): The game clock.
            - awayTeam (str): The team tricode of the away team.
            - awayScore (int): The score of the away team.
            - homeTeam (str): The team tricode of the home team.
            - homeScore (int): The score of the home team.
            - leadTeam (str): The team tricode of the team currently in the lead.
    """
    return {
        'status': game_boxscore['gameStatus'],
        'statusText': game_boxscore['gameStatusText'],
        'quarter': game_boxscore['period'],
        'clock': game_boxscore['gameClock'],
        'awayTeam': game_boxscore['awayTeam']['teamTricode'],
        'awayScore': game_boxscore['awayTeam']['score'],
        'homeTeam': game_boxscore['homeTeam']['teamTricode'],
        'homeScore': game_boxscore['homeTeam']['score'],
        'leadTeam': get_lead_team(
            game_boxscore['awayTeam']['teamTricode'],
            game_boxscore['awayTeam']['score'],
            game_boxscore['homeTeam']['teamTricode'],
            game_boxscore['homeTeam']['score']
        )
    }


STATS_SCORE = {
    'points': 1.0,
    'threePointersMade': 1.0,
    'reboundsDefensive': 1.0,
    'reboundsOffensive': 2.0,
    'assists': 2.0,
    'steals': 2.5,
    'blocks': 2.5,
    'fieldGoalsMissed': -0.5,
    'freeThrowsMissed': -0.5,
    'turnovers': -2.0,
    'foulsPersonal': -1.5,
    'win': 3.0,
    'doubleDouble': 3.0,
    'tripleDouble': 6.0,
    'quadrupleDouble': 12.0,
    'fiveDouble': 24.0
}
STATS_BONUS = {
    'points': 'dunk',
    'threePointersMade': 'three_pointer',
    'reboundsDefensive': 'badge',
    'reboundsOffensive': 'debut',
    'assists': 'assist',
    'steals': 'steal',
    'blocks': 'block_shot',
    'fieldGoalsMissed': 'jump_shot',
    'freeThrowsMissed': 'hook_shot',
    'turnovers': 'handle',
    'foulsPersonal': 'layup',
    "win": "team"
}


def compute_vgn_score(player, collection=None):
    if player is None:
        return 0.0

    if collection is None:
        collection = EMPTY_PLAYER_COLLECTION

    total_score = 0.0
    for stats, play_type in STATS_BONUS.items():
        if STATS_SCORE[stats] > 0.0:
            total_score += player[stats] * STATS_SCORE[stats] * (1000.0 + float(collection[play_type])) / 1000.0
        else:
            total_score += player[stats] * STATS_SCORE[stats] * (1000.0 - float(collection[play_type])) / 1000.0

    point_bonus = int(player['points'] / 10)
    total_score += (1000.0 + float(collection['reel'])) * float(point_bonus) * float(point_bonus + 1) / 2000.0

    for stats in ['doubleDouble', 'tripleDouble', 'quadrupleDouble', 'fiveDouble']:
        total_score += player[stats] * STATS_SCORE[stats]

    if player['foulsPersonal'] >= 6:
        total_score -= 5.0

    return total_score


def compute_vgn_scores(player, collection=None):
    if player is None:
        return {}, 0.0, 0.0

    if collection is None:
        collection = EMPTY_PLAYER_COLLECTION

    scores = {}
    total_score = 0.0
    total_bonus = 0.0
    for stats, play_type in STATS_BONUS.items():
        if STATS_SCORE[stats] > 0.0:
            scores[stats] = {
                'score': player[stats] * STATS_SCORE[stats],
                'bonus': player[stats] * STATS_SCORE[stats] * float(collection[play_type]) / 1000.0,
            }
            total_score += scores[stats]['score']
            total_bonus += scores[stats]['bonus']
        else:
            scores[stats] = {
                'score': player[stats] * STATS_SCORE[stats],
                'bonus': - player[stats] * STATS_SCORE[stats] * float(collection[play_type]) / 1000.0,
            }
            total_score += scores[stats]['score']
            total_bonus += scores[stats]['bonus']

    point_bonus = int(player['points'] / 10)
    scores['pointBonus'] = {
        'score': float(point_bonus) * float(point_bonus + 1) / 2,
        'bonus': float(collection['reel']) * float(point_bonus) * float(point_bonus + 1) / 2000.0,
    }
    total_score += scores['pointBonus']['score']
    total_bonus += scores['pointBonus']['bonus']

    for stats in ['doubleDouble', 'tripleDouble', 'quadrupleDouble', 'fiveDouble']:
        scores[stats] = {
            'score': player[stats] * STATS_SCORE[stats]
        }
        total_score += scores[stats]['score']

    if player['foulsPersonal'] >= 6:
        scores['foulOut'] = {
            'score': - 5.0
        }
    else:
        scores['foulOut'] = {
            'score': 0
        }

    return scores, total_score, total_bonus
