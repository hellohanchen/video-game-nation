from typing import List, Dict, Tuple

import pandas as pd

from constants import RoleVerificationType, NBA_TEAMS
from repository.config import CNX_POOL
from utils import list_to_str


def get_role_verifications(guild_ids: List[int]):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        query = f"SELECT * from vgn.discord_roles WHERE guild_id IN ({list_to_str(guild_ids)})"
        df = pd.read_sql(query, db_conn)
        result = df.to_dict('records')
        db_conn.close()

        if len(result) == 0:
            return {}, None

        verify_rules = {}
        for row in result:
            guild_id = row['guild_id']
            if guild_id not in verify_rules:
                verify_rules[guild_id] = []

            rule = parse_verification(row)
            if len(rule) > 0:
                verify_rules[guild_id].append(rule)

        return verify_rules, None

    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return {}, err


def parse_verification(db_row: Dict[str, str]) -> Dict[str, int | RoleVerificationType | Tuple[str, str]]:
    vt = RoleVerificationType(db_row['verify_type'])
    if vt == RoleVerificationType.LINKED:
        return {
            'role_id': db_row['role_id'],
            'type': vt,
        }
    if vt == RoleVerificationType.SET and db_row['verify_info'].isnumeric():
        return {
            'role_id': db_row['role_id'],
            'type': vt,
            'info': int(db_row['verify_info'])
        }
    if vt == RoleVerificationType.TEAM and len(db_row['verify_info']) == 4:
        team = db_row['verify_info'][0:3].upper()
        if team in NBA_TEAMS:
            series = db_row['verify_info'][3:]
            if series.isnumeric():
                return {
                    'role_id': db_row['role_id'],
                    'type': vt,
                    'info': (team, series)
                }
            if series == "C":
                return {
                    'role_id': db_row['role_id'],
                    'type': vt,
                    'info': (team, "C")
                }
            if series == "A":
                return {
                    'role_id': db_row['role_id'],
                    'type': vt,
                    'info': (team, "A")
                }

    return {}
