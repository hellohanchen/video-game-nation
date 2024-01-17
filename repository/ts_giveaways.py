import pandas as pd

from repository.config import CNX_POOL


def create_giveaway(guild_id, channel_id, creator_id, name, description, winners, duration):
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "INSERT INTO vgn.ts_giveaways (guild_id, channel_id, creator_id, " \
                "name, description, winners, duration) " \
                f"VALUES({guild_id}, {channel_id}, {creator_id}, '{name}', '{description}', {winners}, {duration})"
        cursor.execute(query)
        db_conn.commit()
        db_conn.close()
    except Exception as err:
        return False, err

    return True, None


def submit_giveaway(gid, duration, fav_teams, team_set_weights):
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = f"UPDATE vgn.ts_giveaways SET is_submitted = TRUE, submitted_at = NOW(), " \
                f"end_at = ADDTIME(NOW(), '{duration}:00:00.000000')"

        if fav_teams is not None and len(fav_teams) > 0:
            query += f", fav_teams='{fav_teams}'"
        if team_set_weights is not None and len(team_set_weights) > 0:
            query += f", team_set_weights='{team_set_weights}'"

        query += f" WHERE id = {gid} AND is_submitted = FALSE"

        cursor.execute(query)
        db_conn.commit()
        db_conn.close()
    except Exception as err:
        return False, err

    return True, None


def message_giveaway(gid, mid):
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = f"UPDATE vgn.ts_giveaways SET message_id = {mid} WHERE guild_id = {gid} AND is_ended = FALSE"

        cursor.execute(query)
        db_conn.commit()
        db_conn.close()
    except Exception as err:
        return False, err

    return True, None


def get_giveaway(gid):
    try:
        db_conn = CNX_POOL.get_connection()
        query = f"SELECT * from vgn.ts_giveaways WHERE id = {gid}"
        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        loaded = df.to_dict('records')

        db_conn.close()

        users = {}
        for user in loaded:
            users[user['id']] = user

        return users, None

    except Exception as err:
        return None, err
