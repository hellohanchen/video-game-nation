import pandas as pd

from repository.config import CNX_POOL


def create_listing(uid, d_username, ts_username, lf_sid, lf_info, ft_sid, ft_info, note):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "INSERT INTO vgn.ts_listings (user_id, discord_username, topshot_username, " \
                "lf_set_id, lf_info, ft_set_id, ft_info, note, created_at, updated_at) " \
                f"VALUES({uid}, '{d_username}', '{ts_username}', " \
                f"{lf_sid}, '{lf_info}', {ft_sid}, '{ft_info}', '{note}', NOW(), NOW())"
        cursor.execute(query)
        listing_id = cursor.lastrowid
        db_conn.commit()
        db_conn.close()
    except Exception as err:
        if db_conn is not None:
            db_conn.close()
        return None, err

    return listing_id, None


def get_ongoing_listings():
    try:
        db_conn = CNX_POOL.get_connection()
        query = f"SELECT * from vgn.ts_listings WHERE updated_at >= SUBTIME(NOW(), '168:00:00.000000') " \
                f"ORDER BY updated_at DESC"
        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        loaded = df.to_dict('records')

        db_conn.close()

        return loaded, None

    except Exception as err:
        return None, err


def update_listing(lid, lf_sid, lf_info, ft_sid, ft_info, note):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = f"UPDATE vgn.ts_listings SET lf_set_id = {lf_sid}, lf_info = '{lf_info}', " \
                f"ft_set_id = {ft_sid}, ft_info = '{ft_info}', note = '{note}', updated_at = NOW() " \
                f"WHERE id = {lid}"
        cursor.execute(query)
        db_conn.commit()
        db_conn.close()
    except Exception as err:
        if db_conn is not None:
            db_conn.close()
        return False, err

    return True, None
