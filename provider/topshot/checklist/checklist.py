import asyncio

from provider.topshot.cadence.flow_collections import get_account_plays
from provider.topshot.ts_provider import TS_PROVIDER, TS_PROVIDER


def check_sets_and_teams(plays):
    complete_sets = []
    complete_teams = []

    for set in TS_PROVIDER.set_checklists:
        set_id = int(set)
        count = 0
        for play in TS_PROVIDER.set_checklists[set]['moments']:
            play_id = int(play)
            if play_id in plays and set_id in plays[play_id]:
                count += 1
        if count == TS_PROVIDER.set_checklists[set]['count']:
            complete_sets.append(TS_PROVIDER.set_checklists[set]['name'])

    for team in TS_PROVIDER.team_checklists:
        complete_team_sets = []
        for series in TS_PROVIDER.team_checklists[team]['series']:
            count = 0
            for player in TS_PROVIDER.team_checklists[team]['series'][series]['players']:
                found = False
                for play_id in TS_PROVIDER.team_checklists[team]['series'][series]['players'][player]['plays']:
                    if play_id in plays:
                        found = True
                        break
                if found:
                    count += 1

            if count == TS_PROVIDER.team_checklists[team]['series'][series]['count']:
                complete_team_sets.append(f"{team} {series}")

        count = 0
        for player in TS_PROVIDER.team_checklists[team]['contemporary']['players']:
            found = False
            for play_id in TS_PROVIDER.team_checklists[team]['contemporary']['players'][player]['plays']:
                if play_id in plays:
                    found = True
                    break
            if found:
                count += 1

        if count == TS_PROVIDER.team_checklists[team]['contemporary']['count']:
            complete_team_sets.append(f"{team} contemporary")

        count = 0
        for player in TS_PROVIDER.team_checklists[team]['all']['players']:
            found = False
            for play_id in TS_PROVIDER.team_checklists[team]['all']['players'][player]['plays']:
                if play_id in plays:
                    found = True
                    break
            if found:
                count += 1

        if count == TS_PROVIDER.team_checklists[team]['all']['count']:
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
