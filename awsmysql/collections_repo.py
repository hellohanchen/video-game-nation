import asyncio

from awsmysql.mysql_connection_pool import CNX_POOL
from topshot.cadence.flow_collections import get_account_plays
from topshot.ts_info import TS_ENRICHED_PLAYS, TS_PLAYER_ID_MOMENTS

TIERS = {'Common': 2, 'Fandom': 5, 'Rare': 10, 'Legendary': 25}
TYPES = {
    'Dunk': 'dunk', '3 Pointer': 'three_pointer', 'Assist': 'assist', 'Steal': 'steal', 'Block': 'block_shot',
    'Jump Shot': 'jump_shot', 'Hook Shot': 'hook_shot', 'Handles': 'handle', 'Layup': 'layup', 'Reel': 'reel'
}


async def upsert_collection(user_id, plays):
    """
    Upserts the collection of plays for a given user into the vgn.collections table in the database.

    Args:
        user_id: The ID of the user whose collection is being updated.
        plays: A list of play IDs representing the plays in the user's collection.

    Returns:
        A string indicating the status of the update operation. If the operation was successful, the string "Updated
        successfully!" is returned. If there was an error while executing the SQL query, a string in the format "DB
        error: <error message>" is returned. If some play IDs could not be found, a string in the format "Updated
        with not found play ids: <comma-separated list of play IDs>" is returned.

    Raises:
        None.

    Examples:
        >>> result = await upsert_collection(1234, [5678, 9012, 3456])
        >>> print(result)
        "Updated successfully!"

        >>> result = await upsert_collection(5678, [1234, 5678, 9012, 3456])
        >>> print(result)
        "Updated with not found play ids: 1234"

        >>> result = await upsert_collection(9012, [])
        >>> print(result)
        "Updated successfully!"
    """
    coll, not_found_plays = build_vgn_collection(plays)

    sql_records = [
        (user_id, player_id, coll[player_id]['dunk'], coll[player_id]['three_pointer'],
         coll[player_id]['badge'], coll[player_id]['debut'], coll[player_id]['assist'], coll[player_id]['steal'],
         coll[player_id]['block_shot'], coll[player_id]['jump_shot'], coll[player_id]['hook_shot'],
         coll[player_id]['handle'], coll[player_id]['layup'], coll[player_id]['reel'], coll[player_id]['team'])
        for player_id in coll
    ]

    try:
        db_conn = CNX_POOL.get_connection()
        cursor = db_conn.cursor()
        query = "INSERT INTO vgn.collections (user_id, player_id, dunk, three_pointer, " \
                "badge, debut, assist, steal, block_shot, " \
                "jump_shot, hook_shot, handle, layup, reel, team) " \
                "VALUES(%s, %s , %s, %s, %s , %s, %s, %s , %s, %s, %s , %s, %s, %s , %s) ON DUPLICATE KEY UPDATE " \
                "dunk=VALUES(dunk), three_pointer=VALUES(three_pointer), " \
                "badge=VALUES(badge), debut=VALUES(debut), assist=VALUES(assist), steal=VALUES(steal), " \
                "block_shot=VALUES(block_shot), jump_shot=VALUES(jump_shot), hook_shot=VALUES(hook_shot), " \
                "handle=VALUES(handle), layup=VALUES(layup), reel=VALUES(reel), team=VALUES(team)"
        cursor.executemany(query, sql_records)
        db_conn.commit()
        db_conn.close()
    except Exception as err:
        return "DB error: {}.".format(err)

    if len(not_found_plays) > 0:
        return "Updated with not found play ids: {}.".format(', '.join([str(play) for play in not_found_plays]))

    return "Updated successfully!"


def build_vgn_collection(plays):
    """
        Builds a collection of plays for NBA players or teams, given a dictionary of play IDs and their counts.

        Args:
            plays: A dictionary where keys are play IDs and values are the number of times the play was performed.

        Returns:
            A tuple containing two elements: a dictionary of player IDs mapped to dictionaries of their play statistics,
            and a list of play IDs that were not found in the TS_ENRICHED_PLAYS dictionary.

        Raises:
            None.

        This function iterates through a dictionary of play IDs and their counts, and computes statistics for each NBA
        player or team based on the plays they were involved in. If a play ID cannot be found in the TS_ENRICHED_PLAYS
        dictionary, it is added to the not_found_plays list.

        The function returns a tuple containing two elements: a dictionary of player IDs mapped to dictionaries of
        their play statistics, and a list of play IDs that were not found in the TS_ENRICHED_PLAYS dictionary.
        If a play corresponds to an NBA player, the play statistics are added to the player's dictionary in the
        player_collections dictionary. If a play corresponds to a team, the team statistics are added to the team's
        dictionary in the team_collections dictionary. Note that the team collections part of the function is not
        implemented yet.
        """

    player_collections = {}
    team_collections = {}
    not_found_plays = []

    for play_id in plays:
        if play_id not in TS_ENRICHED_PLAYS:
            not_found_plays.append(play_id)
            continue

        count = plays[play_id]
        play = TS_ENRICHED_PLAYS[play_id]

        player_id = play['playerID']

        if player_id != 0:
            if not TS_PLAYER_ID_MOMENTS[player_id]['isNBA']:
                continue

            if player_id not in player_collections:
                player_collections[player_id] = {
                    'dunk': 0,
                    'three_pointer': 0,
                    'badge': 0,
                    'debut': 0,
                    'assist': 0,
                    'steal': 0,
                    'block_shot': 0,
                    'jump_shot': 0,
                    'hook_shot': 0,
                    'handle': 0,
                    'layup': 0,
                    'reel': 0,
                    'team': 0  # TODO: cache a player_id -> team mapping
                }

            points = TIERS[play['tier']] * count
            player_collections[player_id][TYPES[play['playType']]] += points

            if play['RM'] or play['RY'] or play['RP'] or play['CY'] or play['MVP'] or play['CR']:
                player_collections[player_id]['badge'] += points
            if play['TSD']:
                player_collections[player_id]['debut'] += points
        else:
            # TODO build team collection
            pass

    return player_collections, not_found_plays


if __name__ == '__main__':
    plays = asyncio.run(get_account_plays('ad955e5d8047ef82'))
    print(asyncio.run(upsert_collection(723723650909601833, plays)))
