import pandas as pd

from repository.common import rw_db
from repository.config import CNX_POOL
from utils import list_to_str


def create_giveaway(guild_id, channel_id, creator_id, name, description, winners, duration):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "INSERT INTO vgn.ts_giveaways (guild_id, channel_id, creator_id, " \
                "name, description, winners, duration) " \
                f"VALUES({guild_id}, {channel_id}, {creator_id}, '{name}', '{description}', {winners}, {duration})"
        cursor.execute(query)
        giveaway_id = cursor.lastrowid
        db_conn.commit()
        db_conn.close()
    except Exception as err:
        if db_conn is not None:
            db_conn.close()
        return None, err

    return giveaway_id, None


def submit_giveaway(gid, duration, fav_teams, team_set_weights, thumbnail_url):
    write = f"UPDATE vgn.ts_giveaways SET is_submitted = TRUE, submitted_at = NOW(), " \
            f"end_at = ADDTIME(NOW(), '{duration}:00:00.000000') "

    if fav_teams is not None and len(fav_teams) > 0:
        write += f", fav_teams='{fav_teams}'"
    if team_set_weights is not None and len(team_set_weights) > 0:
        write += f", team_set_weights='{team_set_weights}'"
    if thumbnail_url is not None and len(thumbnail_url) > 0:
        write += f", thumbnail_url='{thumbnail_url}'"

    write += f" WHERE id = {gid} AND is_submitted = FALSE"

    read = f"SELECT * FROM vgn.ts_giveaways WHERE id = {gid}"

    record, err = rw_db(CNX_POOL, write, read)

    if err is not None:
        return None, err
    if record is None or len(record) == 0:
        return None, "giveaway not found"

    return record[0], None


def message_giveaway(gid, mid):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = f"UPDATE vgn.ts_giveaways SET message_id = {mid} WHERE id = {gid}"

        cursor.execute(query)
        db_conn.commit()
        db_conn.close()
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return False, err

    return True, None


def get_giveaway(gid, uid):
    try:
        db_conn = CNX_POOL.get_connection()
        query = f"SELECT * from vgn.ts_giveaways WHERE id = {gid} AND creator_id = {uid}"
        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        loaded = df.to_dict('records')

        db_conn.close()

        if len(loaded) == 0:
            return None, None

        return loaded[0], None

    except Exception as err:
        return None, err


def get_ongoing_giveaways():
    try:
        db_conn = CNX_POOL.get_connection()
        query = f"SELECT * from vgn.ts_giveaways WHERE is_submitted = TRUE AND is_ended = FALSE"
        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        loaded = df.to_dict('records')

        db_conn.close()

        return loaded, None

    except Exception as err:
        return None, err


def get_drafts_for_user(uid, guild_ids, channel_ids):
    if len(guild_ids) == 0 or len(channel_ids) == 0:
        return {}, None

    try:
        db_conn = CNX_POOL.get_connection()
        query = f"SELECT * from vgn.ts_giveaways WHERE creator_id = {uid} " \
                f"AND is_submitted = FALSE AND is_ended = FALSE AND created_at >= SUBTIME(NOW(), '24:00:00.000000') " \
                f"AND guild_id IN ({list_to_str(guild_ids)}) AND channel_id IN ({list_to_str(channel_ids)}) " \
                f"ORDER BY created_at"
        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        loaded = df.to_dict('records')

        db_conn.close()

        giveaways = {}
        for giveaway in loaded:
            giveaways[str(giveaway['id'])] = giveaway

        return giveaways, None

    except Exception as err:
        return None, err


def get_user_giveaway_accesses(uid, all_guilds, role_id=None):
    try:
        db_conn = CNX_POOL.get_connection()
        query = f"SELECT * from vgn.ts_giveaway_creators where user_id = {uid}"
        if role_id is not None:
            query += f" OR role_id = {role_id}"
        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        loaded = df.to_dict('records')

        db_conn.close()

        guilds = {}
        guild_ids = []
        channel_ids = []
        for access in loaded:
            gid = access['guild_id']
            if gid not in all_guilds:
                continue

            if gid not in guilds:
                guilds[gid] = {}
                guilds[gid]['guild'] = all_guilds[gid]['guild']
                guilds[gid]['channels'] = {}
                guild_ids.append(gid)

            cid = access['channel_id']
            if cid == 0:
                guilds[gid]['channels'] = all_guilds[gid]['channels']
                channel_ids.extend(list(all_guilds[gid]['channels'].keys()))
            elif cid in all_guilds[gid]['channels']:
                guilds[gid]['channels'][cid] = all_guilds[gid]['channels'][cid]
                channel_ids.append(cid)

        return guilds, guild_ids, channel_ids, None

    except Exception as err:
        return None, None, None, err


def add_giveaway_access(uid, gid, cid):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "INSERT INTO vgn.ts_giveaway_creators (user_id, guild_id, channel_id) " \
                f"VALUES({uid}, {gid}, {cid})"
        cursor.execute(query)
        db_conn.commit()
        db_conn.close()
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return False, err

    return True, None


def get_submission_count(gid):
    try:
        db_conn = CNX_POOL.get_connection()
        query = f"SELECT COUNT(*) as submission from vgn.ts_giveaway_submissions WHERE giveaway_id = {gid}"
        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        loaded = df.to_dict('records')

        db_conn.close()

        return loaded[0]['submission'], None

    except Exception as err:
        return None, err


def get_submission(gid, address):
    try:
        db_conn = CNX_POOL.get_connection()
        query = f"SELECT * from vgn.ts_giveaway_submissions WHERE giveaway_id = {gid} AND flow_address = '{address}'"
        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        loaded = df.to_dict('records')

        db_conn.close()

        if len(loaded) > 0:
            return loaded[0], None
        return None, None

    except Exception as err:
        return None, err


def get_submissions_with_flow_info(gid):
    try:
        db_conn = CNX_POOL.get_connection()
        query = f"SELECT u.id AS user_id, u.topshot_username AS topshot_username, u.flow_address AS flow_address, " \
                f"s.fav_team AS fav_team " \
                f"FROM vgn.ts_giveaway_submissions s JOIN vgn.users u ON s.user_id = u.id " \
                f"WHERE s.giveaway_id = {gid}"
        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        loaded = df.to_dict('records')

        db_conn.close()
        return loaded, None

    except Exception as err:
        return None, err


def get_submitted_fav_team(uid):
    try:
        db_conn = CNX_POOL.get_connection()
        query = f"SELECT fav_team FROM vgn.ts_giveaway_submissions WHERE user_id = {uid} AND giveaway_id IN " \
                f"(SELECT id FROM vgn.ts_giveaways WHERE is_submitted = TRUE AND is_ended = FALSE AND end_at > NOW()) " \
                f"AND fav_team IS NOT NULL LIMIT 1 "
        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        loaded = df.to_dict('records')

        db_conn.close()

        if len(loaded) > 0:
            return loaded[0]['fav_team'], None
        return None, None

    except Exception as err:
        return None, err


def join_giveaway(gid, user, fav_team):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()

        if fav_team is not None:
            query = "INSERT INTO vgn.ts_giveaway_submissions (giveaway_id, user_id, topshot_username, " \
                    "flow_address, fav_team) " \
                    f"VALUES({gid}, {user['id']}, '{user['topshot_username']}', '{user['flow_address']}', '{fav_team}')"
        else:
            query = "INSERT INTO vgn.ts_giveaway_submissions (giveaway_id, user_id, topshot_username, " \
                    "flow_address) " \
                    f"VALUES({gid}, {user['id']}, '{user['topshot_username']}', '{user['flow_address']}')"

        cursor.execute(query)
        db_conn.commit()
        db_conn.close()
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return False, err

    return True, None


def leave_giveaway(gid, uid):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()

        query = f"DELETE FROM vgn.ts_giveaway_submissions WHERE user_id = {uid} AND giveaway_id = {gid}"
        cursor.execute(query)

        db_conn.commit()
        db_conn.close()
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return False, err

    return True, None



def close_giveaway(gid):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()

        query = f"UPDATE vgn.ts_giveaways SET is_ended = TRUE WHERE id = {gid}"
        cursor.execute(query)

        db_conn.commit()
        db_conn.close()
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return False, err

    return True, None


def ban_user(uid):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()

        query = f"DELETE FROM vgn.ts_giveaway_submissions WHERE user_id = {uid}"
        cursor.execute(query)

        db_conn.commit()
        db_conn.close()
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return False, err

    return True, None

