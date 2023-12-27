import datetime
import json
import os.path
import pathlib
from typing import Optional

from nba_api.live.nba.endpoints import scoreboard, boxscore

from provider.nba.injuries import load_injuries
from provider.nba.schedule import download_schedule
from utils import parse_dash_date, to_slash_date, parse_slash_date


EAST_CONFERENCE = {"MIL", "BOS", "PHI", "CLE", "NYK", "BKN", "MIA", "ATL",
                   "TOR", "CHI", "WAS", "IND", "ORL", "CHA", "DET"}
WEST_CONFERENCE = {"DEN", "MEM", "SAC", "PHX", "LAC", "GSW", "MIN", "NOP",
                   "LAL", "OKC", "DAL", "UTA", "POR", "SAS", "HOU"}
INJURIES = {
    "Day-To-Day": "DTD",
    "Game-Time-Decision": "GTD",
    "Game Time Decision": "GTD",
    "Out": "OUT",
}


class NBAProvider:
    def __init__(self):
        self.game_schedule = {}
        self.game_dates = {}
        self.game_teams = {}
        self.team_players = {}
        self.latest_date = ""
        self.coming_date = ""
        self.injuries = {}

        self.__load_schedule()
        self.__load_team_players()
        self.__load_injuries()

    def __load_schedule(self):
        with open(os.path.join(pathlib.Path(__file__).parent.resolve(), 'data/game_dates.json'), 'r') as f:
            new_schedule = json.load(f)

        self.game_schedule.update(new_schedule)
        self.game_dates.update({game_id: date for date, games in new_schedule.items() for game_id in games})
        self.game_teams.update({game_id: games[game_id] for date, games in new_schedule.items() for game_id in games})
        self.latest_date = list(new_schedule.keys())[-1]
        self.set_coming_game_date()

    def __load_team_players(self):
        self.team_players = json.load(
            open(os.path.join(pathlib.Path(__file__).parent.resolve(), 'data/team_players_23_24.json'), 'r'))

    def __load_injuries(self):
        self.injuries = load_injuries()

    @staticmethod
    def get_scoreboard():
        """
        Get latest scoreboard.

        :return: scoreboard in dictionary
        """
        return scoreboard.ScoreBoard().get_dict()['scoreboard']

    def get_games_on_date(self, date):
        """
        Get all game ids for a provided date.

        :param: date: game date, example 01/01/2023
        :return: list of game ids
        """
        return self.game_schedule.get(date, {})

    def get_date_for_game(self, game_id: str) -> Optional[str]:
        """
        Get the date for a given game ID.

        :param: game_id: a string representing the game ID
        :return: a string representing the date of the game, or None if the game ID is invalid or the date cant be found
        """
        return self.game_dates.get(game_id)

    def get_teams_for_games(self, games):
        """
        Get teams' tri codes for a list of games.

        :param: games: list of game id
        :return: a dictionary of {game_id, [teamTriCodes]}
        """
        return {game_id: self.get_teams_for_game(game_id) for game_id in games}

    def get_teams_for_game(self, game_id):
        """
        Return 2 teams' tri code for a game.

        :param: game_id: game id
        :return: [homeTeamTriCode, awayTeamTriCode]
        """
        return {self.game_teams[game_id]['homeTeam'], self.game_teams[game_id]['awayTeam']}

    @staticmethod
    def get_players_for_games(games_teams):
        """
        Get players' ids set of each game in a list.

        :param: games_teams: games and teams in each game
        :return: a dictionary of {game_id, {player_ids}}
        """

        result = {}

        for game_id in games_teams:
            try:
                game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
            except Exception:
                continue

            if game_stats['gameStatus'] == 1:
                continue

            player_ids = []
            if game_stats['homeTeam']['teamTricode'] in games_teams[game_id]:
                player_ids.extend([player['personId'] for player in game_stats['homeTeam']['players']])
            if game_stats['awayTeam']['teamTricode'] in games_teams[game_id]:
                player_ids.extend([player['personId'] for player in game_stats['awayTeam']['players']])

            if len(player_ids) > 0:
                result[game_id] = set(player_ids)

        return result

    def get_players_for_team(self, team):
        return self.team_players[team]

    def get_all_player_ids(self):
        players = []
        for team in self.team_players:
            players.extend(self.team_players[team])
        return players

    def get_player_injury(self, player_name):
        injury = self.injuries.get(player_name)
        if injury is None:
            return None

        short_injury = INJURIES.get(injury)
        if short_injury is None:
            return injury

        return short_injury

    def get_coming_game_date(self):
        self.set_coming_game_date()
        return self.coming_date

    def set_coming_game_date(self):
        sb = NBAProvider.get_scoreboard()
        current_date = sb['gameDate']

        started = False
        if len(sb['games']) == 0:
            started = True
        else:
            for game in sb['games']:
                if game['gameStatus'] > 1:
                    started = True
                    break

        if not started:
            self.coming_date = to_slash_date(parse_dash_date(current_date))
        else:
            cur_date = parse_dash_date(current_date)
            max_date = parse_slash_date(self.latest_date)

            while cur_date < max_date:
                cur_date = cur_date + datetime.timedelta(days=1)

                if to_slash_date(cur_date) in self.game_schedule:
                    self.coming_date = to_slash_date(cur_date)
                    return

            self.coming_date = "N/A"

    def reload(self):
        download_schedule()
        self.__load_schedule()
        self.__load_team_players()
        self.__load_injuries()

    @staticmethod
    def get_scoreboard_message(headline):
        message = "-" * 40
        message += "\n🏀 ***{}***\n".format(headline)

        score_board = NBAProvider.get_scoreboard()

        if len(score_board['games']) > 0:
            message += "**Games on {}**\n\n".format(score_board['gameDate'])

            for game in score_board['games']:
                message += "**{}** {} : {} **{}** {}\n".format(
                    game['awayTeam']['teamTricode'],
                    game['awayTeam']['score'],
                    game['homeTeam']['score'],
                    game['homeTeam']['teamTricode'],
                    game['gameStatusText']
                )

            message += "\n\n"

        return message


NBA_PROVIDER = NBAProvider()


if __name__ == '__main__':
    print(NBA_PROVIDER.get_coming_game_date())
