def truncate_message(msgs, msg, add, limit):
    if len(msg) + len(add) >= limit:
        msgs.append(msg)
        return add, ""
    else:
        return msg + add, ""


def get_lead_team(team1, team1_score, team2, team2_score):
    if team1_score == team2_score:
        return "TIE"
    if team1_score > team2_score:
        return team1
    return team2
