import pandas as pd

from repository.config import CNX_POOL


def get_lineup(user_id, game_date):
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT * FROM vgn.fb_lineups WHERE user_id = {} AND game_date = '{}'".format(user_id, game_date)
        df = pd.read_sql(query, db_conn)
        lineups = df.to_dict('records')
        db_conn.commit()
        db_conn.close()

        if len(lineups) == 0:
            return {}, None
        return lineups[0], None
    except Exception as err:
        return None, err


def get_lineups(game_date):
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT * FROM vgn.fb_lineups WHERE game_date = '{}' ".format(game_date)

        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        lineups = df.to_dict('records')

        db_conn.commit()
        db_conn.close()
    except Exception as err:
        print("DB error: {}".format(err))

        if db_conn is not None:
            db_conn.close()
        return {}

    return lineups


def upsert_lineup(lineup):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "INSERT INTO vgn.fb_lineups (user_id, game_date, player_1, player_2, player_3, " \
                "player_4, player_5, player_6, player_7, player_8, is_ranked) " \
                "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE) ON DUPLICATE KEY UPDATE " \
                "player_1=VALUES(player_1), player_2=VALUES(player_2), player_3=VALUES(player_3), " \
                "player_4=VALUES(player_4), player_5=VALUES(player_5), player_6=VALUES(player_6), " \
                "player_7=VALUES(player_7), player_8=VALUES(player_8), is_ranked=FALSE"
        cursor.execute(query, lineup)
        db_conn.commit()
        db_conn.close()

        return True, "Updated"
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return False, "DB error: {}".format(err)


def submit_lineup(lineup):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "INSERT INTO vgn.fb_lineups (user_id, topshot_username, game_date, " \
                "player_1, player_1_serial, player_2, player_2_serial, " \
                "player_3, player_3_serial, player_4, player_4_serial, " \
                "player_5, player_5_serial, is_ranked, sum_serial) " \
                "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s) ON DUPLICATE KEY UPDATE " \
                "topshot_username=VALUES(topshot_username), " \
                "player_1=VALUES(player_1), player_1_serial=VALUES(player_1_serial), " \
                "player_2=VALUES(player_2), player_2_serial=VALUES(player_2_serial), " \
                "player_3=VALUES(player_3), player_3_serial=VALUES(player_3_serial), " \
                "player_4=VALUES(player_4), player_4_serial=VALUES(player_4_serial), " \
                "player_5=VALUES(player_5), player_5_serial=VALUES(player_5_serial), " \
                "is_ranked=TRUE, sum_serial=VALUES(sum_serial)"
        cursor.execute(query, lineup)
        db_conn.commit()
        db_conn.close()

        return True, "Updated"
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return False, "DB error: {}".format(err)


def upsert_score(user_id, game_date, score, passed):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "UPDATE vgn.fb_lineups SET score = {}, is_passed = {} " \
                "WHERE user_id = {} AND game_date = '{}'".format(score, passed, user_id, game_date)
        cursor.execute(query)
        db_conn.commit()
        db_conn.close()
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return err

    return None


def get_weekly_ranks(game_dates, count):
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT u.topshot_username as username, SUM(IF(l.is_passed, 1, 0)) as wins, " \
                "SUM(l.score) * IF(COUNT(*) = {}, 1.1, 1) as total_score, COUNT(*) = {} AS all_checked_in FROM " \
                "(SELECT * FROM vgn.fb_lineups WHERE game_date IN ({}) AND is_ranked = TRUE) l " \
                "JOIN vgn.users u ON l.user_id = u.id " \
                "GROUP BY u.id ORDER BY wins DESC, total_score DESC LIMIT {}"\
            .format(len(game_dates), len(game_dates), ', '.join("'" + date + "'" for date in game_dates), count)

        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        leaderboard = df.to_dict('records')

        db_conn.commit()
        db_conn.close()
    except Exception as err:
        print("DB error: {}".format(err))

        if db_conn is not None:
            db_conn.close()
        return {}

    return leaderboard


def get_user_results(uid, game_dates):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT game_date, is_passed FROM vgn.fb_lineups WHERE game_date IN ({}) AND user_id = {}" \
            .format(', '.join("'" + date + "'" for date in game_dates), uid)

        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        loaded = df.to_dict('records')

        db_conn.commit()
        db_conn.close()
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return {}, err

    results = {}
    for row in loaded:
        results[row['game_date']] = 1 if row['is_passed'] else 0
    for d in game_dates:
        if d not in results:
            results[d] = -1

    return results, None


if __name__ == '__main__':
    # get_lineups("04/11/2023")
    get_lineup("100", "04/11/2023")
