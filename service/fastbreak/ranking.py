import datetime

from nba_api.live.nba.endpoints import boxscore

from provider.nba.nba_provider import NBAProvider, NBA_PROVIDER
from provider.topshot.fb_provider import FB_PROVIDER
from repository.fb_lineups import get_lineups
from repository.vgn_players import get_empty_players_stats
from service.fastbreak.fastbreak import FastBreak
from service.fastbreak.lineup import Lineup, LINEUP_SERVICE
from service.fastbreak.service import FastBreakService
from utils import get_game_info


class RankingService(FastBreakService):
    def __init__(self):
        super(RankingService, self).__init__()
        self.current_game_date = ""
        self.lineups = {}
        self.games = []

        self.status = "PRE_GAME"
        self.player_stats = {}

        self.update()

    def __load_lineups(self):
        if self.fb is None:
            return

        game_day_players = []
        for game_id, game in NBA_PROVIDER.get_games_on_date(self.current_game_date).items():
            for team in [game['homeTeam'], game['awayTeam']]:
                for player in NBA_PROVIDER.get_players_for_team(team):
                    game_day_players.append(player)

        loaded = get_lineups(self.current_game_date)
        player_ids = []
        for lineup in loaded:
            new_lineup = Lineup(lineup, self)
            if new_lineup.is_valid():
                self.lineups[lineup['user_id']] = new_lineup

        if len(self.lineups) > 0:
            for user_id in self.lineups:
                player_ids.extend(self.lineups[user_id].player_ids)

            player_ids = list(set(player_ids))
            if None in player_ids:
                player_ids.remove(None)
            self.player_stats = get_empty_players_stats(player_ids)

    def reload(self):
        self.fb = FastBreak(FB_PROVIDER.get_fb(self.current_game_date))
        self.lineups = {}
        self.__load_lineups()

    def update(self):
        scoreboard = NBAProvider.get_scoreboard()
        new_status = self.get_status(scoreboard['games'])
        if new_status == "NO_GAME" or new_status == "PRE_GAME":
            if self.status == "POST_GAME":
                self.__update_stats()

                NBA_PROVIDER.reload()
                LINEUP_SERVICE.reload()

            self.status = "PRE_GAME"
        elif self.status == "PRE_GAME":
            self.current_game_date = datetime.datetime.strptime(scoreboard['gameDate'], '%Y-%m-%d').strftime('%m/%d/%Y')
            self.games = [game['gameId'] for game in scoreboard['games']]
            # noinspection PyBroadException
            try:
                self.reload()
                self.status = new_status
                LINEUP_SERVICE.reload()
            except Exception:
                return
        else:
            self.status = new_status

        self.__update_stats()

    def __update_stats(self):
        player_stats = {}
        for game_id in self.games:
            # noinspection PyBroadException
            try:
                game_stats = boxscore.BoxScore(game_id=game_id).get_dict()['game']
            except Exception:
                continue

            if game_stats['gameStatus'] == 1:
                continue

            game_info = get_game_info(game_stats)

            for player in game_stats['homeTeam']['players']:
                if player['status'] == 'ACTIVE':
                    player_id = player['personId']
                    player_stats[player_id] = self.enrich_stats(player['statistics'])
                    player_stats[player_id]['name'] = player['name']
                    player_stats[player_id]['gameInfo'] = game_info

            for player in game_stats['awayTeam']['players']:
                if player['status'] == 'ACTIVE':
                    player_id = player['personId']
                    player_stats[player_id] = self.enrich_stats(player['statistics'])
                    player_stats[player_id]['name'] = player['name']
                    player_stats[player_id]['gameInfo'] = game_info

        for player_id in player_stats:
            self.player_stats[player_id] = player_stats[player_id]

    def formatted_user_score(self, user_id):
        if self.status == "NO_GAME" or self.status == "PRE_GAME":
            return ["Games are not started yet."]

        if user_id not in self.lineups:
            return ["User lineup not found."]
        lineup = self.lineups[user_id]

        message = "🏀 ***{} GAMES***\n".format(self.current_game_date)
        if self.fb is not None:
            message += self.fb.get_formatted()

        message += self.fb.formatted_scores(lineup.player_ids[0:self.fb.count], self.player_stats)

        return message

    @staticmethod
    def enrich_stats(player_stats):
        player_stats['fieldGoalsMissed'] = player_stats['fieldGoalsAttempted'] - player_stats['fieldGoalsMade']
        player_stats['freeThrowsMissed'] = player_stats['freeThrowsAttempted'] - player_stats['freeThrowsMade']

        doubles = 0
        for stats in ['points', 'reboundsTotal', 'assists', 'steals', 'blocks']:
            if player_stats[stats] >= 10:
                doubles += 1

        player_stats['doubleDouble'] = 1.0 if doubles > 1 else 0
        player_stats['tripleDouble'] = 1.0 if doubles > 2 else 0
        player_stats['quadrupleDouble'] = 1.0 if doubles > 3 else 0
        player_stats['fiveDouble'] = 1.0 if doubles > 4 else 0

        return player_stats

    @staticmethod
    def get_status(games):
        if len(games) == 0:
            return "NO_GAME"

        started = False
        final = True
        for game in games:
            if game['gameStatus'] > 1:
                started = True
            if game['gameStatus'] < 3:
                final = False

        if not started and not final:
            return "PRE_GAME"
        if started and not final:
            return "IN_GAME"
        if started and final:
            return "POST_GAME"


RANK_SERVICE = RankingService()
