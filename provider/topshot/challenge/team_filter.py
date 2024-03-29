from typing import Set

from nba_api.live.nba.endpoints import boxscore

from provider.nba.nba_provider import EAST_CONFERENCE, WEST_CONFERENCE
from utils import get_lead_team


class TeamFilter:
    def __init__(self, tag: str):
        """
        Initialize a new instance of the TeamFilter class.

        Args:
            tag (str): A string representing the filter tag.
        """
        self.tag = tag

    def filter_teams(self, game_id: int, teams: Set[str]) -> Set[str]:
        """
        Filter a set of team IDs based on the tag associated with the TeamFilter object.

        Args:
            game_id (int): An integer representing the game ID.
            teams (Set[str]): A set of team IDs to filter.

        Returns:
            Set[str]: A set of team IDs that passed the filter.
        """
        if self.tag == "WIN" or self.tag == "LOSE":
            try:
                game_boxscore = boxscore.BoxScore(game_id=game_id).get_dict()['game']
            except:
                return set()

            lead_team = get_lead_team(
                game_boxscore['awayTeam']['teamTricode'],
                game_boxscore['awayTeam']['score'],
                game_boxscore['homeTeam']['teamTricode'],
                game_boxscore['homeTeam']['score']
            )
            if lead_team == "TIE":
                return teams

            if self.tag == 'WIN':
                if lead_team in teams:
                    return {lead_team}
                else:
                    return set()
            else:
                if lead_team in teams:
                    return set(teams) - {lead_team}
                else:
                    return set(teams)

        if self.tag == "EC":
            return teams.intersection(EAST_CONFERENCE)

        if self.tag == "WC":
            return teams.intersection(WEST_CONFERENCE)

        if self.tag in EAST_CONFERENCE or self.tag in WEST_CONFERENCE:
            if self.tag in teams:
                return {self.tag}
            else:
                return set()

        return teams
