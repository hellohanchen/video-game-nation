import pandas as pd

from repository.common import rw_db
from repository.config import CNX_POOL


def get_lineup(user_id, game_date):
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT * FROM vgn.rr_lineups WHERE user_id = {} AND game_date = '{}'".format(user_id, game_date)
        df = pd.read_sql(query, db_conn)
        lineups = df.to_dict('records')
        db_conn.commit()
        db_conn.close()

        if len(lineups) == 0:
            return {}, None
        return lineups[0], None
    except Exception as err:
        return None, err


def get_lineups(game_date, is_submitted=False):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT * FROM vgn.rr_lineups WHERE game_date = '{}' ".format(game_date)

        if is_submitted:
            query += "AND is_submitted = TRUE"

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
    write = "INSERT INTO vgn.rr_lineups (user_id, game_date, bucket_1, bucket_2, bucket_3, " \
            "bucket_4, bucket_5, bucket_6, bucket_7, bucket_8, is_submitted) " \
            "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE) ON DUPLICATE KEY UPDATE " \
            "bucket_1=VALUES(bucket_1), bucket_2=VALUES(bucket_2), bucket_3=VALUES(bucket_3), " \
            "bucket_4=VALUES(bucket_4), bucket_5=VALUES(bucket_5), bucket_6=VALUES(bucket_6), " \
            "bucket_7=VALUES(bucket_7), bucket_8=VALUES(bucket_8), is_submitted=FALSE"
    read = "SELECT * FROM vgn.rr_lineups WHERE user_id = {} AND game_date = '{}'".format(lineup[0], lineup[1])

    return rw_db(CNX_POOL, write, read, lineup)


def submit_lineup(uid, ts_name, gd):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        update_query = f"UPDATE vgn.rr_lineups SET topshot_username = '{ts_name}', is_submitted = TRUE " \
                       f"WHERE user_id = {uid} AND game_date = '{gd}'"
        cursor.execute(update_query)

        read = "SELECT * FROM vgn.rr_lineups WHERE user_id = {} AND game_date = '{}'".format(uid, gd)
        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(read, db_conn)

        # Convert dataframe to a dictionary with headers
        db_lineups = df.to_dict('records')

        db_conn.commit()
        db_conn.close()

        if len(db_lineups) == 0:
            return False, [], "submitted lineup not found"

        return True, db_lineups, "submitted"
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return False, [], "DB error: {}".format(err)


def upsert_score(uid, game_date, wins, score, rank, win):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "UPDATE vgn.rr_lineups SET points = {}, raw_score = {}, `rank` = {}, win = {} " \
                "WHERE user_id = {} AND game_date = '{}'" \
            .format(wins, score, rank, win, uid, game_date)
        cursor.execute(query)
        db_conn.commit()
        db_conn.close()
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return err

    return None


def get_slate_ranks(game_dates, top_n):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT user_id, topshot_username as username, SUM(IF(win, 1, 0)) as wins, " \
                "SUM(points) as total_points, SUM(raw_score) as total_score, COUNT(*) - SUM(IF(win, 1, 0)) as losses " \
                "FROM vgn.rr_lineups WHERE game_date in ({}) " \
                "GROUP BY user_id, topshot_username ORDER BY wins DESC, total_points DESC, " \
                "losses, total_score DESC LIMIT {}" \
            .format(', '.join("'" + date + "'" for date in game_dates), top_n)

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
        return []

    return leaderboard


def get_user_results(uid, game_dates):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT game_date, points, raw_score, `rank`, win FROM vgn.rr_lineups " \
                "WHERE game_date IN ({}) AND user_id = {} ORDER BY game_date" \
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
        results[row['game_date']] = row
    for d in game_dates:
        if d not in results:
            results[d] = None

    return results, None


def get_user_losses(uid, game_dates, current_game_date):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT COUNT(*) - SUM(IF(win, 1, 0)) as losses " \
                "FROM vgn.rr_lineups WHERE game_date in ({}) " \
                "AND user_id = {} AND game_date != '{}'" \
                "GROUP BY user_id" \
            .format(', '.join("'" + date + "'" for date in game_dates), uid, current_game_date)

        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        loaded = df.to_dict('records')

        db_conn.commit()
        db_conn.close()
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return None, err

    if len(loaded) == 0:
        return 0, None

    return loaded[0]['losses'], None


def get_user_slate_result(uid, game_dates):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT r.user_id, r.wins, r.total_points, r.total_score, r.losses, r.`rank` " \
                "FROM (" \
                "   SELECT user_id, SUM(IF(l.win, 1, 0)) as wins, " \
                "       SUM(points) as total_points, SUM(raw_score) as total_score, " \
                "       COUNT(*) - SUM(IF(win, 1, 0)) as losses, " \
                "       rank() over (" \
                "           ORDER BY SUM(IF(l.win, 1, 0)) DESC, " \
                "           SUM(points) DESC, " \
                "           COUNT(*) - SUM(IF(win, 1, 0)), " \
                "           SUM(raw_score) " \
                "       ) as `rank`" \
                "   FROM vgn.rr_lineups AS l " \
                "   WHERE game_date IN ({})" \
                "   GROUP BY l.user_id) r " \
                "WHERE r.user_id = {}" \
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

        return None, err

    if len(loaded) == 0:
        return None, None

    return loaded[0], None


def get_submitted_users():
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT DISTINCT user_id FROM vgn.rr_lineups WHERE is_submitted = TRUE"

        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        users = df.to_dict('records')

        db_conn.commit()
        db_conn.close()
    except Exception as err:
        if db_conn is not None:
            db_conn.close()
        return [], err

    return users, None


def get_submission_count(game_date):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT COUNT(*) AS submissions FROM vgn.rr_lineups " \
                "WHERE game_date = '{}' AND is_submitted = TRUE".format(game_date)

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
        return None, err

    return submissions, None


if __name__ == '__main__':
    get_lineups("04/11/2023")
