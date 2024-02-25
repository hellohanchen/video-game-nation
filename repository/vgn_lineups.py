import pandas as pd

from repository.config import CNX_POOL


def get_lineup(user_id, game_date):
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "SELECT * FROM vgn.lineups WHERE user_id = {} AND game_date = '{}'".format(user_id, game_date)
        cursor.execute(query)
        result = cursor.fetchone()
        db_conn.commit()
        db_conn.close()

        return result
    except Exception as err:
        return "DB error: {}".format(err)


def get_lineups(game_date, submitted=False):
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT * FROM vgn.lineups WHERE game_date = '{}' ".format(game_date)
        if submitted:
            query += " AND submitted = true"

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


def get_submission_count(game_date):
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT COUNT(*) AS submissions FROM vgn.lineups " \
                "WHERE game_date = '{}' AND submitted = TRUE".format(game_date)

        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        submissions = df.to_dict('records')[0]['submissions']

        db_conn.commit()
        db_conn.close()
    except Exception as err:
        print("DB error: {}".format(err))

        if db_conn is not None:
            db_conn.close()
        return {}

    return submissions


def get_weekly_ranks(game_dates, count):
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT u.topshot_username as username, SUM(l.score) as total_score FROM " \
                "(SELECT * FROM vgn.lineups WHERE game_date IN ({})) l JOIN vgn.users u ON l.user_id = u.id " \
                "GROUP BY u.id ORDER BY total_score DESC LIMIT {}"\
            .format(', '.join("'" + date + "'" for date in game_dates), count)

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


def get_weekly_score(game_dates, user_id):
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT SUM(l.score) as total_score FROM " \
                "(SELECT * FROM vgn.lineups WHERE game_date IN ({})) l JOIN " \
                "(SELECT * FROM vgn.users WHERE id = {}) u ON l.user_id = u.id " \
            .format(', '.join("'" + date + "'" for date in game_dates), user_id)

        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        score = df.to_dict('records')

        db_conn.commit()
        db_conn.close()
    except Exception as err:
        print("DB error: {}".format(err))

        if db_conn is not None:
            db_conn.close()
        return {}

    if len(score) > 0:
        return score[0]['total_score']
    return 0


def upsert_lineup(lineup):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "INSERT INTO vgn.lineups (user_id, game_date, captain_1, starter_2, starter_3, " \
                "starter_4, starter_5, bench_6, bench_7, bench_8, backup_9) " \
                "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE " \
                "captain_1=VALUES(captain_1), starter_2=VALUES(starter_2), starter_3=VALUES(starter_3), " \
                "starter_4=VALUES(starter_4), starter_5=VALUES(starter_5), bench_6=VALUES(bench_6), " \
                "bench_7=VALUES(bench_7), bench_8=VALUES(bench_8), backup_9=VALUES(backup_9)"
        cursor.execute(query, lineup)
        db_conn.commit()
        db_conn.close()

        return True, "Updated"
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return False, "DB error: {}".format(err)


def upsert_score(user_id, game_date, score):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "UPDATE vgn.lineups SET score = {} " \
                "WHERE user_id = {} AND game_date = '{}'".format(score, user_id, game_date)
        cursor.execute(query)
        db_conn.commit()
        db_conn.close()
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        print("DB error: {}".format(err))


def submit_lineup(user_id, game_date):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "UPDATE vgn.lineups SET submitted = true " \
                "WHERE user_id = {} AND game_date = '{}'".format(user_id, game_date)
        cursor.execute(query)
        db_conn.commit()
        db_conn.close()

        return True, "Updated"
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return False, "DB error: {}".format(err)


if __name__ == '__main__':
    # get_lineups("04/11/2023")
    get_lineup("100", "04/11/2023")
