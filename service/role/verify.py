from discord.abc import Snowflake

from constants import RoleVerificationType
from provider.topshot.checklist.checklist import check_for_set, check_for_team


def verify_roles(verifications, plays):
    roles = []
    for v in verifications:
        if v['type'] == RoleVerificationType.LINKED:
            roles.append(v['role'])
        elif v['type'] == RoleVerificationType.SET:
            verified, _ = check_for_set(v['info'], plays)
            if verified:
                roles.append(v['role'])
        elif v['type'] == RoleVerificationType.TEAM:
            verified, _ = check_for_team(v['info'][0], v['info'][1], plays)
            if verified:
                roles.append(v['role'])

    return roles
