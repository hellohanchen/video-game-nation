import datetime
from typing import Dict, Union

from constants import EMPTY_PLAYER_COLLECTION, STATS_PLAY_TYPE, STATS_SCORE


def truncate_message(msgs: list, msg: str, add: str, limit: int) -> tuple:
    """
    Truncates a message by adding a string to it until the limit is reached.

    This function appends the truncated message to the input `msgs` list if the length of the original `msg` plus the
    length of `add` is greater than or equal to the `limit`. If the length of the original `msg` plus the length of `add`
    is less than the `limit`, then the function returns the truncated message with any remaining `add` string to be
    added to the message later.
    """
    if len(msg) + len(add) >= limit:
        msgs.append(msg)
        return add, ""
    else:
        return msg + add, ""


def get_lead_team(team1: str, team1_score: int, team2: str, team2_score: int) -> Union[str, None]:
    """
    Determines which team is currently in the lead based on their scores.

    This function takes in the names of two teams and their respective scores, and returns the name of the team that
    is currently in the lead based on their scores. If both teams have the same score, the function returns "TIE".
    If any of the input arguments are None or if the input scores are negative, the function returns None.
    """
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


def compute_vgn_score(player, collection=None):
    if player is None:
        return 0.0

    if collection is None:
        collection = EMPTY_PLAYER_COLLECTION

    total_score = 0.0
    for stats, play_type in STATS_PLAY_TYPE.items():
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
    for stats, play_type in STATS_PLAY_TYPE.items():
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


async def update_channel_messages(msgs, channels, messages_ids):
    for channel in channels:
        channel_id = channel.id
        if channel_id not in messages_ids:
            messages_ids[channel_id] = []
        try:
            for i in range(0, min(len(msgs), len(messages_ids[channel_id]))):
                prev_message = await channel.fetch_message(messages_ids[channel_id][i])
                await prev_message.edit(content=msgs[i])

            for i in range(len(messages_ids[channel_id]), len(msgs)):
                new_message = await channel.send(msgs[i])
                messages_ids[channel_id].append(new_message.id)

            if len(msgs) < len(messages_ids[channel_id]):
                redundant_messages = [await channel.fetch_message(messages_ids[channel_id][i]) for i in range(len(msgs), len(messages_ids[channel_id]))]
                await channel.delete_messages(redundant_messages)
                messages_ids[channel.id] = messages_ids[channel.id][0:len(msgs)]

        except Exception as err:
            print(err)
            continue


async def send_channel_messages(msgs, channels):
    for channel in channels:
        try:
            for i in range(0, len(msgs)):
                await channel.send(msgs[i])

        except Exception as err:
            print(err)
            continue


def parse_dash_date(dt):
    return datetime.datetime.strptime(dt, '%Y-%m-%d')


def parse_slash_date(dt):
    return datetime.datetime.strptime(dt, '%m/%d/%Y')


def to_slash_date(dt):
    return dt.strftime('%m/%d/%Y')


def get_the_past_week(date):
    today = parse_slash_date(date)
    idx = (today.weekday() + 1) % 7  # Mon = 1, ..., Sat = 6, Sun = 0

    dates = []
    for i in range(idx, -1, -1):
        d = today - datetime.timedelta(days=i)
        dates.append(to_slash_date(d))

    return dates


def equals(s1: list, s2: list) -> bool:
    """
    Compares two lists element-wise and returns True if they are equal, False otherwise.

    Args:
        s1: The first list to compare.
        s2: The second list to compare.

    Returns:
        True if the two lists are equal, False otherwise.
    """
    # If the two lists are not of equal length, they are not equal.
    if len(s1) != len(s2):
        return False

    # Compare the elements of the two lists.
    for i in range(len(s1)):
        if s1[i] != s2[i]:
            return False

    # If all the elements are equal, the two lists are equal.
    return True
