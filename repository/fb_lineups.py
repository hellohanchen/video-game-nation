import pandas as pd

from repository.config import CNX_POOL


def get_lineup(user_id, game_date):
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "SELECT * FROM vgn.fb_lineups WHERE user_id = {} AND game_date = '{}'".format(user_id, game_date)
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
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "INSERT INTO vgn.fb_lineups (user_id, game_date, player_1, player_2, player_3, " \
                "player_4, player_5, player_6, player_7, player_8) " \
                "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE " \
                "player_1=VALUES(player_1), player_2=VALUES(player_2), player_3=VALUES(player_3), " \
                "player_4=VALUES(player_4), player_5=VALUES(player_5), player_6=VALUES(player_6), " \
                "player_7=VALUES(player_7), player_8=VALUES(player_8)"
        cursor.execute(query, lineup)
        db_conn.commit()
        db_conn.close()

        return True, "Updated"
    except Exception as err:
        return False, "DB error: {}".format(err)


if __name__ == '__main__':
    # get_lineups("04/11/2023")
    get_lineup("100", "04/11/2023")
