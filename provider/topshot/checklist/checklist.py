import asyncio

from provider.topshot.cadence.flow_collections import get_account_plays
from provider.topshot.ts_info import TS_SET_CHECKLISTS, TS_TEAM_CHECKLISTS


def check_sets_and_teams(plays):
    complete_sets = []
    complete_teams = []

    for set in TS_SET_CHECKLISTS:
        set_id = int(set)
        count = 0
        for play in TS_SET_CHECKLISTS[set]['moments']:
            play_id = int(play)
            if play_id in plays and set_id in plays[play_id]:
                count += 1
        if count == TS_SET_CHECKLISTS[set]['count']:
            complete_sets.append(TS_SET_CHECKLISTS[set]['name'])

    for team in TS_TEAM_CHECKLISTS:
        complete_team_sets = []
        for series in TS_TEAM_CHECKLISTS[team]['series']:
            count = 0
            for player in TS_TEAM_CHECKLISTS[team]['series'][series]['players']:
                found = False
                for play_id in TS_TEAM_CHECKLISTS[team]['series'][series]['players'][player]['plays']:
                    if play_id in plays:
                        found = True
                        break
                if found:
                    count += 1

            if count == TS_TEAM_CHECKLISTS[team]['series'][series]['count']:
                complete_team_sets.append(f"{team} {series}")

        count = 0
        for player in TS_TEAM_CHECKLISTS[team]['contemporary']['players']:
            found = False
            for play_id in TS_TEAM_CHECKLISTS[team]['contemporary']['players'][player]['plays']:
                if play_id in plays:
                    found = True
                    break
            if found:
                count += 1

        if count == TS_TEAM_CHECKLISTS[team]['contemporary']['count']:
            complete_team_sets.append(f"{team} contemporary")

        count = 0
        for player in TS_TEAM_CHECKLISTS[team]['all']['players']:
            found = False
            for play_id in TS_TEAM_CHECKLISTS[team]['all']['players'][player]['plays']:
                if play_id in plays:
                    found = True
                    break
            if found:
                count += 1

        if count == TS_TEAM_CHECKLISTS[team]['all']['count']:
            complete_team_sets.append(f"{team} all")

        if len(complete_team_sets) > 0:
            complete_teams.extend(complete_team_sets)

    return complete_sets, complete_teams


if __name__ == '__main__':
    plays = asyncio.run(get_account_plays('0xad955e5d8047ef82'))
    sets, teams = check_sets_and_teams(plays)
    for set in sets:
        print(set)
    for team in teams:
        print(team)
