import pandas as pd

from repository.config import CNX_POOL
from repository.common import rw_db


def insert_user(discord_id, topshot_username, flow_address):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "INSERT INTO vgn.users (id, topshot_username, flow_address) VALUES({}, '{}' ,'{}')".format(discord_id,
                                                                                                           topshot_username,
                                                                                                           flow_address)
        cursor.execute(query)
        db_conn.commit()
        db_conn.close()
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return f"insertUser:{err}"

    return f"Put new user id: {discord_id}, topshot username: {topshot_username}."


def insert_and_get_user(discord_id, topshot_username, flow_address):
    write = f"INSERT INTO vgn.users (id, topshot_username, flow_address) " \
            f"VALUES({discord_id}, '{topshot_username}' ,'{flow_address}') ON DUPLICATE KEY UPDATE " \
            f"topshot_username = VALUES(topshot_username), flow_address = VALUES(flow_address)"
    read = f"SELECT * from vgn.users WHERE id={discord_id}"
    record, err = rw_db(CNX_POOL, write, read)

    if err is not None:
        return None, err

    return record[0], None


def get_user(discord_id):
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "SELECT * from vgn.users WHERE id={}".format(discord_id)
        cursor.execute(query)
        result = cursor.fetchall()
        db_conn.close()

        if len(result) == 0:
            return None
        return result[0]

    except Exception:
        return None


def get_user_new(discord_id):
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = f"SELECT * from vgn.users WHERE id={discord_id}"

        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        result = df.to_dict('records')

        db_conn.commit()
        db_conn.close()

        if len(result) == 0:
            return None, None
        return result[0], None

    except Exception as err:
        return None, err


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
