import random
import time

import pandas as pd

from awsmysql.mysql_connection_pool import CNX_POOL
from nba.player_stats import get_player_avg_stats
from topshot.ts_info import TS_PLAYER_ID_MOMENTS


def add_player(id):
    """
    Adds a new player to the vgn.players MySQL table, given their ID.

    Args:
        id: An integer representing the ID of the player to add.

    Returns:
        None.

    Raises:
        None.

    Examples:
        >>> await add_player(201939)
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
        print(err)
        return

    if info is None or stats is None:
        print("Error fetching player: {}".format(id))
        return

    try:
        full_name = info['DISPLAY_FIRST_LAST'][0].lower().replace('\'', '\\\'')
        first_name = info['FIRST_NAME'][0].lower().replace('\'', '\\\'')
        last_name = info['LAST_NAME'][0].lower().replace('\'', '\\\'')

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
        print("Error parsing info: {}, err: {}".format(info, err))
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
            "quadruple_double_recent, quadruple_double_avg, five_double_recent, five_double_avg) " \
            "VALUES({}, '{}' ,'{}', '{}', {}, '{}'," \
            "{}, {}, {}, {}," \
            "{}, {}, {}, {}," \
            "{}, {}, {}, {}, {}, {}," \
            "{}, {}, {}, {}," \
            "{}, {}, {}, {}, {}, {}," \
            "{}, {}, {}, {}," \
            "{}, {}, {}, {}" \
            ")".format(
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
        print("DB error: {}".format(err))

        if db_conn is not None:
            db_conn.close()
        return

    print("Inserted new player id: {}, name: {}.".format(id, full_name))


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


def search_players_stats(name, order_by=None):
    try:
        db_conn = CNX_POOL.get_connection()
        query = \
            "SELECT * FROM vgn.players WHERE last_name='{}' OR first_name='{}'".format(name.lower(), name.lower())

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


def upload_players(player_ids):
    """
    Uploads player data to the vgn.players MySQL table, given a list of player IDs.

    Args:
        player_ids: An optional list of integers representing the IDs of the players to upload. If empty,
        all player IDs from the TS_PLAYER_ID_MOMENTS global variable will be used, shuffled randomly.

    Returns:
        None.

    Raises:
        None.

    Examples:
        >>> await upload_players([201939, 203081])
        Inserted new player id: 201939, name: curry, stephen.
        Inserted new player id: 203081, name: george, paul.

    This function uploads player data to the vgn.players MySQL table, by calling the `add_player` function for
    each player ID in the input list. If the input list is empty, the function uses all player IDs from the
    TS_PLAYER_ID_MOMENTS global variable, shuffles them randomly, and uploads their data. If a player is already
    in the database, their data is not uploaded again. To avoid overloading the database, the function waits for
    10 seconds between each upload.
    """

    if len(player_ids) == 0:
        player_ids = list(TS_PLAYER_ID_MOMENTS.keys())
        random.shuffle(player_ids)

    for player in player_ids:
        player_id = int(player)

        if get_player(player_id) is None:
            add_player(player_id)
            time.sleep(10.0)


def check_current_nba_players():
    """
    Checks if the current NBA players in the TS_PLAYER_ID_MOMENTS global variable are in the vgn.players MySQL table.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.

    This function checks if the current NBA players in the TS_PLAYER_ID_MOMENTS global variable are in the vgn.players
    MySQL table, by calling the `get_player` function for each player ID in the global variable. If a player is not
    found in the database, the function prints a message to the console indicating that the player was not found.
    This function is useful for checking if all current NBA players have been properly uploaded to the database.
    """
    for player_id in TS_PLAYER_ID_MOMENTS:
        if TS_PLAYER_ID_MOMENTS[player_id]['isNBA']:
            if get_player(player_id) is None:
                print("Player not found: {}".format(player_id))


if __name__ == '__main__':
    not_found_ids = [
        1627814, 202355, 1629312, 203944, 203994, 203482, 1626162, 201567,
        1626149, 1629021, 1628539, 203457, 1629651, 2555, 201587, 203999, 202696, 1630534,
        1628384, 1630168, 1629052, 201988, 1630202, 2210, 1626158,
        1626220, 1628380, 2216
    ]

    get_players_stats(not_found_ids)
