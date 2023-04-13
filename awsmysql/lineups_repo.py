import pandas as pd

from awsmysql.mysql_connection_pool import CNX_POOL


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


def get_lineups(game_date):
    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT * FROM vgn.lineups WHERE game_date = '{}'".format(game_date)

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
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "INSERT INTO vgn.lineups (user_id, game_date, captain_1, starter_2, starter_3, " \
                "starter_4, starter_5, bench_6, bench_7, bench_8) " \
                "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE " \
                "captain_1=VALUES(captain_1), starter_2=VALUES(starter_2), starter_3=VALUES(starter_3), " \
                "starter_4=VALUES(starter_4), starter_5=VALUES(starter_5), bench_6=VALUES(bench_6), " \
                "bench_7=VALUES(bench_7), bench_8=VALUES(bench_8)"
        cursor.execute(query, lineup)
        db_conn.commit()
        db_conn.close()

        return True, "Updated"
    except Exception as err:
        return False, "DB error: {}".format(err)


if __name__ == '__main__':
    # get_lineups("04/11/2023")
    get_lineup("100", "04/11/2023")
