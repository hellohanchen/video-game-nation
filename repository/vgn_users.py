import pandas as pd

from repository.config import CNX_POOL


def insert_user(discord_id, topshot_username, flow_address):
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "INSERT INTO vgn.users (id, topshot_username, flow_address) VALUES({}, '{}' ,'{}')".format(discord_id, topshot_username, flow_address)
        cursor.execute(query)
        db_conn.commit()
        db_conn.close()
    except Exception as err:
        return "DB error: {}".format(err)

    return "Put new user id: {}, topshot username: {}.".format(discord_id, topshot_username)


def get_user(discord_id):
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "SELECT * from vgn.users WHERE id={}".format(discord_id)
        cursor.execute(query)
        result = cursor.fetchall()
        db_conn.close()
        return result[0]
    except Exception:
        return None


def get_users(discord_ids):
    if discord_ids is None or len(discord_ids) == 0:
        return []

    try:
        db_conn = CNX_POOL.get_connection()
        query = "SELECT * from vgn.users WHERE id IN ({})".format(', '.join([str(user_id) for user_id in discord_ids]))
        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        loaded = df.to_dict('records')

        db_conn.close()

        users = {}
        for user in loaded:
            users[user['id']] = user

        return users

    except Exception:
        return None
