from awsmysql.mysql_connection_pool import CNX_POOL
from topshot.tsgql.get_address import get_flow_address


async def add_user(discord_id, topshot_username):
    try:
        flow_address = await get_flow_address(topshot_username)
    except NameError as err:
        return str(err)

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


async def get_user(discord_id):
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "SELECT * from users WHERE id={}".format(discord_id)
        cursor.execute(query)
        result = cursor.fetchall()
        db_conn.close()
        return result[0]
    except Exception:
        return None
