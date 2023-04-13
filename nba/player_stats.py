import json
import os
import pathlib

from nba_api.stats.endpoints import CommonPlayerInfo, PlayerDashboardByYearOverYear, LeagueDashPlayerBioStats
from nba_api.stats.library.parameters import Season


def get_player_avg_stats(player_id):
    try:
        # Create a CommonPlayerInfo instance to get the player's name
        player_profile = CommonPlayerInfo(player_id=str(player_id), timeout=30)
        player_info = player_profile.common_player_info.get_data_frame()[['DISPLAY_FIRST_LAST', 'FIRST_NAME', 'LAST_NAME', 'JERSEY', 'TEAM_ABBREVIATION']]

        # Create a PlayerDashboardByYearOverYear instance to get the player's seasonal average stats
        player_stats = PlayerDashboardByYearOverYear(player_id=str(player_id), per_mode_detailed='PerGame')
        player_avg_stats = player_stats.get_data_frames()[1].iloc[0]
    except Exception as err:
        print(err)
        return None, None

    return player_info, player_avg_stats


def fresh_team_players():
    season = Season.default
    players = LeagueDashPlayerBioStats(season=season).get_data_frames()[0]

    result = {}
    for i in range(0, len(players)):
        player = players.iloc[i]
        team = player['TEAM_ABBREVIATION']

        if team not in result:
            result[team] = []

        result[team].append(int(player['PLAYER_ID']))

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "results/team_players.json"), 'w') as file:
        json.dump(result, file, indent=2)


if __name__ == '__main__':
    fresh_team_players()
