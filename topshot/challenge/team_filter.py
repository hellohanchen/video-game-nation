from nba_api.live.nba.endpoints import boxscore
from typing import List, Set


from utils import get_lead_team


EAST = {"MIL", "BOS", "PHI", "CLE", "NYK", "BKN", "MIA", "ATL", "TOR", "CHI", "WAS", "IND", "ORL", "CHA", "DET"}
WEST = {"DEN", "MEM", "SAC", "PHX", "LAC", "GSW", "MIN", "NOP", "LAL", "OKC", "DAL", "UTA", "POR", "SAS", "HOU"}


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
        if self.tag == "WIN":
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
            else:
                if lead_team in teams:
                    return {lead_team}
                else:
                    return set()

        if self.tag == "EC":
            return teams.intersection(EAST)

        if self.tag == "WC":
            return teams.intersection(WEST)

        return teams
