import pandas as pd

from repository.common import rw_db
from repository.config import CNX_POOL
from utils import list_to_str


def create_giveaway(guild_id, channel_id, creator_id, name, description, winners, duration):
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
        return None, err

    return giveaway_id, None


def submit_giveaway(gid, duration, fav_teams, team_set_weights):
    write = f"UPDATE vgn.ts_giveaways SET is_submitted = TRUE, submitted_at = NOW(), " \
            f"end_at = ADDTIME(NOW(), '{duration}:00:00.000000') "

    if fav_teams is not None and len(fav_teams) > 0:
        write += f", fav_teams='{fav_teams}'"
    if team_set_weights is not None and len(team_set_weights) > 0:
        write += f", team_set_weights='{team_set_weights}'"

    write += f" WHERE id = {gid} AND is_submitted = FALSE"

    read = f"SELECT * FROM vgn.ts_giveaways WHERE id = {gid}"

    record, err = rw_db(CNX_POOL, write, read)

    if err is not None:
        return None, err
    if record is None or len(record) == 0:
        return None, "giveaway not found"

    return record[0], None


def message_giveaway(gid, mid):
    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = f"UPDATE vgn.ts_giveaways SET message_id = {mid} WHERE id = {gid}"

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

        giveaways = {}
        for giveaway in loaded:
            giveaways[giveaway['id']] = giveaway

        return giveaways, None

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


def get_user_giveaway_accesses(uid, all_guilds):
    try:
        db_conn = CNX_POOL.get_connection()
        query = f"SELECT * from vgn.ts_giveaway_creators where user_id = {uid}"
        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(query, db_conn)

        # Convert dataframe to a dictionary with headers
        loaded = df.to_dict('records')

        db_conn.close()

        guilds = {}
        guild_ids = []
        channel_ids = []
        for giveaway in loaded:
            gid = giveaway['guild_id']
            if gid not in all_guilds:
                continue

            if gid not in guilds:
                guilds[gid] = {}
                guilds[gid]['guild'] = all_guilds[gid]['guild']
                guilds[gid]['channels'] = []
                guild_ids.append(gid)

            cid = giveaway['channel_id']
            if cid == 0:
                guilds[gid]['channels'] = all_guilds[gid]['channels']
                channel_ids.extend(list(all_guilds[gid]['channels'].keys()))
            elif cid in all_guilds[gid]['channels']:
                guilds[gid]['channels'].append(cid)
                channel_ids.append(cid)

        return guilds, guild_ids, channel_ids, None

    except Exception as err:
        return None, None, None, err


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


def get_submission(gid, uid):
    try:
        db_conn = CNX_POOL.get_connection()
        query = f"SELECT * from vgn.ts_giveaway_submissions WHERE giveaway_id = {gid} AND user_id = {uid}"
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


def join_giveaway(gid, user, fav_team):
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
        return False, err

    return True, None
