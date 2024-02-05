import asyncio

from constants import NBA_TEAM_NAMES
from provider.topshot.cadence.flow_collections import get_account_plays
from provider.topshot.ts_provider import TS_PROVIDER


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
            team_set = TS_PROVIDER.team_checklists[team]['series'][series]
            count = 0
            players = team_set['players']
            for player_id in players:
                found = False
                for play_id in players[player_id]['plays']:
                    if play_id in plays:
                        found = True
                        break
                if found:
                    count += 1

            if count == team_set['count']:
                complete_team_sets.append(f"{team} {series}")

        count = 0
        team_set = TS_PROVIDER.team_checklists[team]['contemporary']
        for player_id in team_set['players']:
            found = False
            for play_id in team_set[player_id]['plays']:
                if play_id in plays:
                    found = True
                    break
            if found:
                count += 1
        if count == team_set['count']:
            complete_team_sets.append(f"{team} contemporary")

        count = 0
        team_set = TS_PROVIDER.team_checklists[team]['all']
        for player_id in team_set['players']:
            found = False
            for play_id in team_set[player_id]['plays']:
                if play_id in plays:
                    found = True
                    break
            if found:
                count += 1
        if count == team_set['count']:
            complete_team_sets.append(f"{team} all")

        if len(complete_team_sets) > 0:
            complete_teams.extend(complete_team_sets)

    return complete_sets, complete_teams


def check_for_set(set_id, plays):
    if str(set_id) not in TS_PROVIDER.set_checklists:
        return False, []

    moments = TS_PROVIDER.set_checklists[str(set_id)]['moments']
    missed = []
    for pid in moments:
        play_id = int(pid)
        if play_id not in plays or set_id not in plays[play_id]:
            missed.append(f"{moments[pid]['player']} {moments[pid]['date']}")

    if len(missed) == 0:
        return True, []
    else:
        return False, missed


def check_for_team(team, series, plays):
    nba_team = NBA_TEAM_NAMES.get(team)
    if nba_team not in TS_PROVIDER.team_checklists:
        return False, []

    if series.isnumeric():
        if series not in TS_PROVIDER.team_checklists[nba_team]['series']:
            return False, []
        team_set = TS_PROVIDER.team_checklists[nba_team]['series'][series]
    elif series == "C":
        team_set = TS_PROVIDER.team_checklists[nba_team]['contemporary']
    elif series == "A":
        team_set = TS_PROVIDER.team_checklists[nba_team]['all']
    else:
        return False, []

    players = team_set['players']
    missed = []
    for player_id in players:
        found = False
        for play_id in players[player_id]['plays']:
            if play_id in plays:
                found = True
                break
        if not found:
            missed.append(players[player_id]['name'])

    if len(missed) == 0:
        return True, []
    else:
        return False, missed


if __name__ == '__main__':
    user_collection = asyncio.run(get_account_plays('0xad955e5d8047ef82'))
    print(check_for_set(134, user_collection))
    print(check_for_team('LAC', 'A', user_collection))
