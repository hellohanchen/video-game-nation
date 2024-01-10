#!/usr/bin/env python3

import random
import time

import pandas as pd

from provider.nba.players import get_player_avg_stats, fresh_team_players, get_player_stats_dashboard
from repository.config import CNX_POOL


def upsert_player_with_stats(id):
    """
    Adds a new player to the vgn.players MySQL table, given their ID.

    Args:
        id: An integer representing the ID of the player to add.

    Returns:
        None.

    Raises:
        None.

    Examples:
        >>> upsert_player_with_stats(201939)
        Inserted new player id: 201939, name: curry, stephen.

    This function fetches the player's average stats using the `get_player_avg_stats` function, and inserts them
    into the vgn.players MySQL table. The function parses the player's information and statistics, and constructs
    an INSERT statement with the values. If the insertion is successful, the function prints a message to indicate
    that the player was inserted successfully. If an error occurs during fetching or parsing, the function prints
    an error message with the details.
    """

    try:
        info, stats = get_player_avg_stats(id)
    except Exception as err:
        print(f"Failed player id: {id}, fetch error {err}")
        return

    if info is None:
        print(f"Failed player id: {id}, no info")
        return
    if stats is None:
        stats = {
            'PTS': 0.0,
            'FG3M': 0.0,
            'DREB': 0.0,
            'OREB': 0.0,
            'AST': 0.0,
            'STL': 0.0,
            'BLK': 0.0,
            'FGA': 0.0,
            'FGM': 0.0,
            'FTA': 0.0,
            'FTM': 0.0,
            'TOV': 0.0,
            'PF': 0.0,
            'W': 0.0,
            'GP': 1.0,
            'DD2': 0.0,
            'TD3': 0.0,
        }

    try:
        full_name = info['DISPLAY_FIRST_LAST'][0].replace('\'', '\\\'')
        first_name = info['FIRST_NAME'][0].replace('\'', '\\\'')
        last_name = info['LAST_NAME'][0].replace('\'', '\\\'')

        if info['JERSEY'][0] == '00':
            jersey = 100
        elif info['JERSEY'][0] == '':
            jersey = -1
        else:
            jersey = int(info['JERSEY'][0])

        team = info['TEAM_ABBREVIATION'][0]
        win_rate = stats['W'] / stats['GP'] if stats['GP'] > 0 else 0.0
        dd_rate = stats['DD2'] / stats['GP'] if stats['GP'] > 0 else 0.0
        td_rate = stats['TD3'] / stats['GP'] if stats['GP'] > 0 else 0.0
    except Exception as err:
        print(f"Failed player id: {id}, parse error {err}, {info}")
        return

    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = \
            "INSERT INTO vgn.players (id, full_name, first_name, last_name, jersey_number, current_team," \
            "points_recent, points_avg, three_pointers_recent, three_pointers_avg," \
            "defensive_rebounds_recent, defensive_rebounds_avg, offensive_rebounds_recent, offensive_rebounds_avg," \
            "assists_recent, assists_avg, steals_recent, steals_avg, blocks_recent, blocks_avg," \
            "field_goal_misses_recent, field_goal_misses_avg, free_throw_misses_recent, free_throw_misses_avg," \
            "turnovers_recent, turnovers_avg, fouls_recent, fouls_avg, wins_recent, wins_avg," \
            "double_double_recent, double_double_avg, triple_double_recent, triple_double_avg," \
            "quadruple_double_recent, quadruple_double_avg, five_double_recent, five_double_avg, is_current) " \
            "VALUES({}, '{}' ,'{}', '{}', {}, '{}'," \
            "{}, {}, {}, {}," \
            "{}, {}, {}, {}," \
            "{}, {}, {}, {}, {}, {}," \
            "{}, {}, {}, {}," \
            "{}, {}, {}, {}, {}, {}," \
            "{}, {}, {}, {}," \
            "{}, {}, {}, {}, TRUE" \
            ") AS new ON DUPLICATE KEY UPDATE full_name = new.full_name, first_name = new.first_name, " \
            "last_name = new.last_name, jersey_number = new.jersey_number, current_team = new.current_team, " \
            "points_recent = new.points_recent, points_avg = new.points_avg, " \
            "three_pointers_recent = new.three_pointers_recent, three_pointers_avg = new.three_pointers_avg, " \
            "defensive_rebounds_recent = new.defensive_rebounds_recent, defensive_rebounds_avg = new.defensive_rebounds_avg, " \
            "offensive_rebounds_recent = new.offensive_rebounds_recent, offensive_rebounds_avg = new.offensive_rebounds_avg, " \
            "assists_recent = new.assists_recent, assists_avg = new.assists_avg, " \
            "steals_recent = new.steals_recent, steals_avg = new.steals_avg, " \
            "blocks_recent = new.blocks_recent, blocks_avg = new.blocks_avg, " \
            "field_goal_misses_recent = new.field_goal_misses_recent, field_goal_misses_avg = new.field_goal_misses_avg, " \
            "free_throw_misses_recent = new.free_throw_misses_recent, free_throw_misses_avg = new.free_throw_misses_avg, " \
            "turnovers_recent = new.turnovers_recent, turnovers_avg = new.turnovers_avg, " \
            "fouls_recent = new.fouls_recent, fouls_avg = new.fouls_avg, " \
            "wins_recent = new.wins_recent, wins_avg = new.wins_avg, " \
            "double_double_recent = new.double_double_recent, double_double_avg = new.double_double_avg, " \
            "triple_double_recent = new.triple_double_recent, triple_double_avg = new.triple_double_avg, " \
            "quadruple_double_recent = new.quadruple_double_recent, quadruple_double_avg = new.quadruple_double_avg, " \
            "five_double_recent = new.five_double_recent, five_double_avg = new.five_double_avg, is_current = TRUE" \
            "".format(
                id, full_name, first_name, last_name, jersey, team,
                stats['PTS'], stats['PTS'], stats['FG3M'], stats['FG3M'],
                stats['DREB'], stats['DREB'], stats['OREB'], stats['OREB'],
                stats['AST'], stats['AST'], stats['STL'], stats['STL'], stats['BLK'], stats['BLK'],
                stats['FGA'] - stats['FGM'], stats['FGA'] - stats['FGM'], stats['FTA'] - stats['FTM'],
                stats['FTA'] - stats['FTM'],
                stats['TOV'], stats['TOV'], stats['PF'], stats['PF'], win_rate, win_rate,
                dd_rate, dd_rate, td_rate, td_rate,
                0.0, 0.0, 0.0, 0.0
            )
        cursor.execute(query)
        db_conn.commit()
        db_conn.close()
    except Exception as err:
        print(f"Failed player id: {id}, db error {err}")

        if db_conn is not None:
            db_conn.close()
        return

    print(f"Upserted player id: {id}, name: {full_name}.")


def get_player(player_id):
    """
    Fetches the player with the specified ID from the vgn.players MySQL table, and returns a tuple with their data.

    Args:
        player_id: An integer representing the ID of the player to fetch.

    Returns:
        A tuple representing the data of the player with the specified ID, or None if no player is found.

    Raises:
        None.

    This function executes a SELECT statement on the vgn.players MySQL table with the specified player ID,
    and returns the result as a tuple. If no player is found with the specified ID, the function returns None.
    If an error occurs while fetching the data, the function returns None and prints an error message to the
    console.
    """
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "SELECT * from vgn.players WHERE id={}".format(player_id)
        cursor.execute(query)
        result = cursor.fetchall()
        db_conn.close()
        return result[0]
    except Exception:
        return None


def get_players_stats(player_ids, order_by=None):
    try:
        db_conn = CNX_POOL.get_connection()
        query = \
            "SELECT *, points_recent as points, three_pointers_recent as threePointersMade, " \
            "defensive_rebounds_recent as reboundsDefensive, offensive_rebounds_recent as reboundsOffensive, " \
            "assists_recent as assists, steals_recent as steals, blocks_recent as blocks, " \
            "field_goal_misses_recent as fieldGoalsMissed, free_throw_misses_recent as freeThrowsMissed, " \
            "turnovers_recent as turnovers, fouls_recent as foulsPersonal, wins_recent as win, " \
            "double_double_recent as doubleDouble, triple_double_recent as tripleDouble, " \
            "quadruple_double_avg as quadrupleDouble, five_double_recent as fiveDouble" \
            " from vgn.players WHERE id IN ({}) " \
                .format(', '.join([str(player_id) for player_id in player_ids]))

        if order_by is not None:
            query += " ORDER BY {} ".format(', '.join([o[0] + " " + o[1] + " " for o in order_by]))

        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        players = df.to_dict('records')

        db_conn.close()

        return players
    except Exception:
        return None


def get_all_team_players(current_only = True):
    try:
        db_conn = CNX_POOL.get_connection()
        query = \
            "SELECT id, current_team FROM vgn.players WHERE current_team IS NOT NULL AND current_team <> ''"

        if current_only:
            query += " AND is_current = TRUE"

        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        records = df.to_dict('records')

        db_conn.close()

        players = []
        teams = {}
        for player in records:
            pid = player['id']
            team = player['current_team']

            if team not in teams:
                teams[team] = []

            teams[team].append(pid)
            players.append(pid)

        return teams, players
    except Exception:
        return {}, []


def get_empty_players_stats(player_ids, order_by=None):
    try:
        db_conn = CNX_POOL.get_connection()
        query = \
            "SELECT id, full_name as name, current_salary as current_salary, " \
            "0 as points, 0 as threePointersMade, 0 as reboundsDefensive, " \
            "0 as reboundsOffensive, 0 as assists, 0 as steals, 0 as blocks, " \
            "0 as fieldGoalsMade, 0 as fieldGoalsAttempted, 0 as fieldGoalsMissed, " \
            "0 as freeThrowsMade, 0 as freeThrowsAttempted, 0 as freeThrowsMissed, " \
            "0 as threePointersAttempted, 0 as turnovers, 0 as foulsPersonal, 0 as win, " \
            "0 as doubleDouble, 0 as tripleDouble, 0 as quadrupleDouble, 0 as fiveDouble" \
            " from vgn.players WHERE id IN ({}) " \
                .format(', '.join([str(player_id) for player_id in player_ids]))

        if order_by is not None:
            query += " ORDER BY {} ".format(', '.join([o[0] + " " + o[1] + " " for o in order_by]))

        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        loaded = df.to_dict('records')

        db_conn.close()

        player_stats = {}
        for player in loaded:
            player_stats[player['id']] = player
            player_stats[player['id']]['reboundsTotal'] = player['reboundsDefensive'] + player['reboundsOffensive']
            player_stats[player['id']]['gameInfo'] = {
                'awayTeam': 'N/A',
                'homeTeam': 'N/A',
                'homeScore': 0,
                'awayScore': 0,
                'statusText': 'N/A',
            }

        return player_stats
    except Exception as err:
        return None


def reformat_dashboard(raw_player_stats):
    result = []
    for ps in raw_player_stats:
        games_play = float(ps['GP'])

        result.append((
            int(ps['PLAYER_ID']), ps['PLAYER_NAME'], ps['TEAM_ABBREVIATION'],
            ps['PTS'], ps['PTS'], ps['FG3M'], ps['FG3M'],
            ps['DREB'], ps['DREB'], ps['OREB'], ps['OREB'],
            ps['AST'], ps['AST'], ps['STL'], ps['STL'], ps['BLK'], ps['BLK'],
            ps['FGM'], ps['FGM'], ps['FTM'], ps['FTM'],
            ps['TOV'], ps['TOV'], ps['PF'], ps['PF'], ps['W_PCT'], ps['W_PCT'],
            round(float(ps['DD2']) / games_play, 2), round(float(ps['DD2']) / games_play, 2),
            round(float(ps['TD3']) / games_play, 2), round(float(ps['TD3']) / games_play, 2),
            0.0, 0.0, 0.0, 0.0,
            ps['MIN'], ps['MIN'], ps['PFD'], ps['PFD'],
         ))

    return result


def update_player_stats_from_dashboard(player_ids):
    player_stats = reformat_dashboard(get_player_stats_dashboard())
    err_ids = []

    for player in player_stats:
        try:
            db_conn = CNX_POOL.get_connection()
            cursor = db_conn.cursor()
            query = \
                "INSERT INTO vgn.players (id, full_name, current_team," \
                "points_recent, points_avg, three_pointers_recent, three_pointers_avg," \
                "defensive_rebounds_recent, defensive_rebounds_avg, offensive_rebounds_recent, offensive_rebounds_avg," \
                "assists_recent, assists_avg, steals_recent, steals_avg, blocks_recent, blocks_avg," \
                "field_goal_misses_recent, field_goal_misses_avg, free_throw_misses_recent, free_throw_misses_avg," \
                "turnovers_recent, turnovers_avg, fouls_recent, fouls_avg, wins_recent, wins_avg," \
                "double_double_recent, double_double_avg, triple_double_recent, triple_double_avg," \
                "quadruple_double_recent, quadruple_double_avg, five_double_recent, five_double_avg," \
                "minutes_recent, minutes_avg, fouls_drawn_recent, fouls_drawn_avg, is_current) " \
                "VALUES(%s, %s, %s," \
                "%s, %s, %s, %s," \
                "%s, %s, %s, %s," \
                "%s, %s, %s, %s, %s, %s," \
                "%s, %s, %s, %s," \
                "%s, %s, %s, %s, %s, %s," \
                "%s, %s, %s, %s," \
                "%s, %s, %s, %s," \
                "%s, %s, %s, %s, TRUE" \
                ") AS new ON DUPLICATE KEY UPDATE full_name = new.full_name, current_team = new.current_team, " \
                "points_recent = new.points_recent, points_avg = new.points_avg, " \
                "three_pointers_recent = new.three_pointers_recent, three_pointers_avg = new.three_pointers_avg, " \
                "defensive_rebounds_recent = new.defensive_rebounds_recent, defensive_rebounds_avg = new.defensive_rebounds_avg, " \
                "offensive_rebounds_recent = new.offensive_rebounds_recent, offensive_rebounds_avg = new.offensive_rebounds_avg, " \
                "assists_recent = new.assists_recent, assists_avg = new.assists_avg, " \
                "steals_recent = new.steals_recent, steals_avg = new.steals_avg, " \
                "blocks_recent = new.blocks_recent, blocks_avg = new.blocks_avg, " \
                "field_goal_misses_recent = new.field_goal_misses_recent, field_goal_misses_avg = new.field_goal_misses_avg, " \
                "free_throw_misses_recent = new.free_throw_misses_recent, free_throw_misses_avg = new.free_throw_misses_avg, " \
                "turnovers_recent = new.turnovers_recent, turnovers_avg = new.turnovers_avg, " \
                "fouls_recent = new.fouls_recent, fouls_avg = new.fouls_avg, " \
                "wins_recent = new.wins_recent, wins_avg = new.wins_avg, " \
                "double_double_recent = new.double_double_recent, double_double_avg = new.double_double_avg, " \
                "triple_double_recent = new.triple_double_recent, triple_double_avg = new.triple_double_avg, " \
                "quadruple_double_recent = new.quadruple_double_recent, quadruple_double_avg = new.quadruple_double_avg, " \
                "five_double_recent = new.five_double_recent, five_double_avg = new.five_double_avg," \
                "minutes_recent = new.minutes_recent, minutes_avg = new.minutes_avg," \
                "fouls_drawn_recent = new.fouls_drawn_recent, fouls_drawn_avg = new.fouls_drawn_avg, is_current = TRUE"
            cursor.execute(query, player)
            db_conn.commit()
            db_conn.close()

            if player[0] in player_ids:
                player_ids.remove(player[0])
        except Exception as err:
            err_ids.append(player[0])
            print(f"DB error: {err}, player: {player[0]} {player[1]}")

            if db_conn is not None:
                db_conn.close()

    print(f"Upserted {len(player_stats) - len(err_ids)} players.")
    print(f"Failed players: {err_ids}")

    return player_ids


def reset_is_current(player_ids):
    if len(player_ids) == 0:
        return

    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = f"UPDATE vgn.players SET is_current = FALSE WHERE id IN ({', '.join([str(p) for p in player_ids])})"

        # Execute SQL query and store results in a pandas dataframe
        cursor.execute(query)
        db_conn.commit()
        db_conn.close()

        print(f"Players reset: {player_ids}")

        return
    except Exception as err:
        print(err)
        return


def reload_players():
    _, db_player_ids = get_all_team_players()
    _, current_player_ids = fresh_team_players()
    player_ids = [int(pid) for pid in current_player_ids]
    player_ids = update_player_stats_from_dashboard(player_ids)
    print(f"Players not upserted: {player_ids}")
    random.shuffle(player_ids)
    for player_id in player_ids:
        upsert_player_with_stats(player_id)
        time.sleep(1.0)

    current_player_ids = [int(pid) for pid in current_player_ids]
    non_current_ids = list(filter(lambda p: p not in current_player_ids, db_player_ids))
    reset_is_current(non_current_ids)


if __name__ == '__main__':
    reload_players()
