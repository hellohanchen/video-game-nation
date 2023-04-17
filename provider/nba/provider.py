import datetime
import json
import os.path
import pathlib

from nba_api.live.nba.endpoints import scoreboard, boxscore

from provider.nba.schedule import download_schedule


class NBAProvider:
    def __init__(self):
        self.game_schedule = {}
        self.game_teams = {}
        self.team_players = {}
        self.latest_date = ""
        self.coming_date = ""

        self.__load_schedule()
        self.__load_team_players()

    def __load_schedule(self):
        new_schedule = json.load(open(os.path.join(pathlib.Path(__file__).parent.resolve(), 'data/game_dates.json'), 'r'))

        for date in new_schedule:
            self.game_schedule[date] = new_schedule[date]
            for game_id in new_schedule[date]:
                self.game_teams[game_id] = new_schedule[date][game_id]

        self.latest_date = date
        self.set_coming_game_date()

    def __load_team_players(self):
        self.team_players = json.load(
            open(os.path.join(pathlib.Path(__file__).parent.resolve(), 'data/team_players.json'), 'r'))

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

        :param date: game date, example 01/01/2023
        :return: list of game ids
        """
        return self.game_schedule[date]

    def get_teams_for_games(self, games):
        """
        Get teams' tri codes for a list of games.

        :param games: list of game id
        :return: a dictionary of {game_id, [teamTriCodes]}
        """
        return {game_id: self.get_teams_for_game(game_id) for game_id in games}

    def get_teams_for_game(self, game_id):
        """
        Return 2 teams' tri code for a game.

        :param game_id: game id
        :return: [homeTeamTriCode, awayTeamTriCode]
        """
        return {self.game_teams[game_id]['homeTeam'], self.game_teams[game_id]['awayTeam']}

    @staticmethod
    def get_players_for_games(games_teams):
        """
        Get players' ids set of each game in a list.

        :param games_teams: games and teams in each game
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

    def get_coming_game_date(self):
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
            self.coming_date = datetime.datetime.strptime(current_date, '%Y-%m-%d').strftime('%m/%d/%Y')
        else:
            cur_date = datetime.datetime.strptime(current_date, '%Y-%m-%d')
            max_date = datetime.datetime.strptime(self.latest_date, '%m/%d/%Y')

            while cur_date < max_date:
                cur_date = cur_date + datetime.timedelta(days=1)

                if cur_date.strftime('%m/%d/%Y') in self.game_schedule:
                    self.coming_date = cur_date.strftime('%m/%d/%Y')
                    return

            self.coming_date = "N/A"

    def fresh_schedule(self):
        download_schedule()
        self.__load_schedule()


NBA_PROVIDER = NBAProvider()


if __name__ == '__main__':
    print(NBA_PROVIDER.get_coming_game_date())
