from nba_api.stats.endpoints import CommonPlayerInfo, PlayerDashboardByYearOverYear


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


if __name__ == '__main__':
    get_player_avg_stats(1628932)
