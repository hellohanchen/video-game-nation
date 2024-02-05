from typing import List, Dict, Tuple

import pandas as pd

from constants import RoleValidationType, NBA_TEAMS
from repository.config import CNX_POOL
from utils import list_to_str


def get_role_validations(guild_ids: List[int]):
    db_conn = None
    try:
        db_conn = CNX_POOL.get_connection()
        query = f"SELECT * from vgn.discord_roles WHERE guild_id=({', '.join(list_to_str(guild_ids))})"
        df = pd.read_sql(query, db_conn)
        result = df.to_dict('records')
        db_conn.close()

        if len(result) == 0:
            return {}, None

        validation_rules = {}
        for row in result:
            guild_id = row['guild_id']
            if guild_id not in validation_rules:
                validation_rules[guild_id] = []

            rule = parse_validation_rule(row)
            if len(rule) > 0:
                validation_rules[guild_id].append(rule)

        return validation_rules

    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return {}, err


def parse_validation_rule(db_row: Dict[str, str]) -> Dict[str, int | RoleValidationType | Tuple[str, str]]:
    vt = RoleValidationType(db_row['validation_type'])
    if vt == RoleValidationType.SET and db_row['validation_info'].isnumeric():
        return {
            'role_id': db_row['role_id'],
            'type': vt,
            'info': int(db_row['validation_info'])
        }
    if vt == RoleValidationType.TEAM and len(db_row['validation_info']) == 4:
        team = db_row['validation_info'][0:3].upper()
        if team in NBA_TEAMS:
            series = db_row['validation_info'][3:]
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
    if vt == RoleValidationType.FAV_TEAM:
        team = db_row['validation_info'][0:3].upper()
        if team in NBA_TEAMS:
            return {
                'role_id': db_row['role_id'],
                'type': vt,
                'info': team
            }

    return {}
