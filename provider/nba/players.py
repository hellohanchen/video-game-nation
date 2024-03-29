import json
import os
import pathlib
from typing import Dict, List

from nba_api.stats.endpoints import CommonPlayerInfo, PlayerDashboardByYearOverYear, CommonAllPlayers, \
    LeagueDashPlayerStats


def get_player_avg_stats(player_id):
    player_info = None
    player_avg_stats = None
    try:
        # Create a CommonPlayerInfo instance to get the player's name
        player_profile = CommonPlayerInfo(player_id=str(player_id), timeout=30)
        player_info = player_profile.common_player_info.get_data_frame()[['DISPLAY_FIRST_LAST', 'FIRST_NAME', 'LAST_NAME', 'JERSEY', 'TEAM_ABBREVIATION']]

        # Create a PlayerDashboardByYearOverYear instance to get the player's seasonal average stats
        player_stats = PlayerDashboardByYearOverYear(player_id=str(player_id), per_mode_detailed='PerGame')
        player_avg_stats = player_stats.get_data_frames()[1].iloc[0]
    except Exception as err:
        print(f"Failed player id: {player_id}, fetch error {err}")
        return player_info, player_avg_stats

    return player_info, player_avg_stats


def get_player_stats_dashboard():
    player_avg_stats = None
    try:
        # Create a LeagueDashPlayerStats instance to get all player's seasonal average stats
        player_stats = LeagueDashPlayerStats(per_mode_detailed='PerGame')
        player_avg_stats = player_stats.get_data_frames()[0].iloc
    except Exception as err:
        print(err)
        return player_avg_stats

    return player_avg_stats


def fresh_team_players() -> tuple[Dict[str, List[int]], List[str]]:
    """
    Generates a JSON file containing a dictionary with team abbreviations as keys and a list of player IDs as values.

    This function retrieves data from an API that contains the biographical and statistical information of NBA players,
    and generates a JSON file containing a dictionary with team abbreviations as keys and a list of player IDs as values.
    The function saves the JSON file in a folder named 'data' within the same directory as this script. The JSON file is
    named 'team_players.json'. If the 'data' folder or the JSON file do not exist, the function creates them. If they
    already exist, the function overwrites them with the latest data. This function does not return anything.
    """
    players = CommonAllPlayers(is_only_current_season=1, timeout=60).get_data_frames()[0]

    if len(players) == 0:
        print("Team player data unavailable")
        return {}, []

    team_players = {}
    player_ids = {}
    for i in range(0, len(players)):
        player = players.iloc[i]
        team = player['TEAM_ABBREVIATION']

        if team == "":
            continue
        if team not in team_players:
            team_players[team] = []

        player_id = str(player['PERSON_ID'])
        team_players[team].append(int(player['PERSON_ID']))

        if player_id not in player_ids:
            player_ids[player_id] = True

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "data/team_players_23_24.json"), 'w') as file:
        json.dump(team_players, file, indent=2)

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "data/current_nba_players.json"), 'w') as output:
        json.dump(player_ids, output, indent=2)

    return team_players, list(player_ids.keys())


if __name__ == '__main__':
    get_player_stats_dashboard()
