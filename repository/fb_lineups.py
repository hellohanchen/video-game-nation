from typing import Dict, Optional

import pandas as pd

from constants import INVALID_ID
from provider.topshot.fb_provider import FB_PROVIDER
from repository.common import rw_db
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
    db_conn = None
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
    write = "INSERT INTO vgn.fb_lineups (user_id, game_date, player_1, player_2, player_3, " \
            "player_4, player_5, player_6, player_7, player_8, is_ranked) " \
            "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE) ON DUPLICATE KEY UPDATE " \
            "player_1=VALUES(player_1), player_2=VALUES(player_2), player_3=VALUES(player_3), " \
            "player_4=VALUES(player_4), player_5=VALUES(player_5), player_6=VALUES(player_6), " \
            "player_7=VALUES(player_7), player_8=VALUES(player_8), is_ranked=FALSE"
    read = "SELECT * FROM vgn.fb_lineups WHERE user_id = {} AND game_date = '{}'".format(lineup[0], lineup[1])

    return rw_db(CNX_POOL, write, read, lineup)


def get_usages(game_date):
    if game_date not in FB_PROVIDER.date_contests:
        return {}, None

    contest_dates = FB_PROVIDER.get_dates(game_date)

    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT * FROM vgn.fb_lineups WHERE game_date IN ({}) " \
                "AND game_date != '{}'" \
            .format(', '.join("'" + d + "'" for d in contest_dates), game_date)

        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        db_lineups = df.to_dict('records')

        db_conn.commit()
        db_conn.close()
    except Exception as err:
        print("DB error: {}".format(err))

        if db_conn is not None:
            db_conn.close()
        return {}, err

    user_usages = {}
    for db_l in db_lineups:
        uid = db_l['user_id']
        if uid not in user_usages:
            user_usages[uid] = {}

        for key in ['player_1', 'player_2', 'player_3', 'player_4', 'player_5']:
            player_id = db_l[key]
            if player_id is not None and player_id != INVALID_ID:
                if player_id not in user_usages[uid]:
                    user_usages[uid][player_id] = 1
                else:
                    user_usages[uid][player_id] = user_usages[uid][player_id] + 1

    return user_usages, None


def submit_lineup(lineup, uid, cid):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        update_query = "INSERT INTO vgn.fb_lineups (user_id, topshot_username, game_date, " \
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
        cursor.execute(update_query, lineup)

        submit_query = "INSERT INTO vgn.fb_submissions (user_id, topshot_username, game_date, contest_id) " \
                       "VALUES(%s, %s, %s, %s) ON DUPLICATE KEY UPDATE topshot_username=VALUES(topshot_username)"
        cursor.execute(submit_query, (uid, lineup[1], lineup[2], cid))

        read = "SELECT * FROM vgn.fb_lineups WHERE user_id = {} AND game_date = '{}'".format(lineup[0], lineup[2])
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


def upsert_score(uid, cid, game_date, score, rate, rank, passed):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "UPDATE vgn.fb_submissions SET score = {}, rate = {}, `rank` = {}, is_passed = {} " \
                "WHERE user_id = {} AND contest_id = {} AND game_date = '{}'" \
            .format(score, rate, rank, passed, uid, cid, game_date)
        cursor.execute(query)
        db_conn.commit()
        db_conn.close()
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return err

    return None


def get_slate_ranks(cid, game_dates, count):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT user_id, topshot_username as username, SUM(IF(is_passed, 1, 0)) as wins, " \
                "SUM(rate) * IF(COUNT(*) = {}, 1.1, 1) as total_score, COUNT(*) = {} AS all_checked_in " \
                "FROM vgn.fb_submissions WHERE contest_id = {} AND game_date in ({}) " \
                "GROUP BY user_id, topshot_username ORDER BY wins DESC, total_score DESC LIMIT {}" \
            .format(len(game_dates), len(game_dates), cid, ', '.join("'" + date + "'" for date in game_dates), count)

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


def get_user_results(uid, cid, game_dates):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT game_date, is_passed, score, rate, `rank` FROM vgn.fb_submissions " \
                "WHERE game_date IN ({}) AND user_id = {} AND contest_id = {}" \
            .format(', '.join("'" + date + "'" for date in game_dates), uid, cid)

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


def get_submissions(uid, game_date) -> [Dict[int, Dict[str, any]], Optional[Exception]]:
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT * FROM vgn.fb_submissions WHERE user_id = {} AND game_date = '{}'" \
            .format(uid, game_date)

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
        results[row['contest_id']] = row

    return results, None


def get_user_slate_result(uid, cid, game_dates):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        slate_len = len(game_dates)
        query = "SELECT r.user_id, r.wins, r.total_score, r.all_checked_in, r.`rank` " \
                "FROM (" \
                "   SELECT user_id, SUM(IF(l.is_passed, 1, 0)) as wins, " \
                "       SUM(l.rate) * IF(COUNT(*) = {}, 1.1, 1) as total_score, COUNT(*) = {} AS all_checked_in, " \
                "       rank() over (" \
                "           ORDER BY SUM(IF(l.is_passed, 1, 0)) DESC, " \
                "           SUM(l.rate) * IF(COUNT(*) = {}, 1.1, 1) DESC) as `rank`" \
                "   FROM vgn.fb_submissions AS l " \
                "   WHERE game_date IN ({}) AND contest_id = {}" \
                "   GROUP BY l.user_id) r " \
                "WHERE r.user_id = {}"\
            .format(slate_len, slate_len, slate_len, ', '.join("'" + date + "'" for date in game_dates), cid, uid)

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
        query = "SELECT DISTINCT user_id FROM vgn.fb_lineups WHERE is_ranked = TRUE"

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


if __name__ == '__main__':
    # get_lineups("04/11/2023")
    get_lineup("100", "04/11/2023")
