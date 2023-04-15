from awsmysql.collections_repo import get_collections
from awsmysql.lineups_repo import get_lineups, upsert_lineup, submit_lineup
from awsmysql.players_repo import get_players_stats
from nba.provider import NBA_PROVIDER
from utils import compute_vgn_score, truncate_message, compute_vgn_scores


class LineupProvider:
    def __init__(self):
        self.coming_game_date = ""
        self.team_to_opponent = {}
        self.team_to_players = {}
        self.player_to_team = {}
        self.players = {}
        self.player_ids = []
        self.lineups = {}
        self.collections = {}
        self.reload()

    def __load_players(self):
        self.player_ids = []
        players_to_load = []

        for game_id, game in NBA_PROVIDER.get_games_on_date(self.coming_game_date).items():
            for team in [game['homeTeam'], game['awayTeam']]:
                self.team_to_opponent[team] = game['homeTeam'] if team == game['awayTeam'] else game['awayTeam']
                self.team_to_players[team] = []
                for player in NBA_PROVIDER.get_players_for_team(team):
                    self.player_to_team[player] = team
                    players_to_load.append(player)

        loaded = get_players_stats(players_to_load, [("points_avg", "DESC")])

        index = 0
        for player in loaded:
            player_id = player['id']
            index += 1

            self.players[player_id] = player
            self.players[player_id]['index'] = index
            self.players[player_id]['formatted'], self.players[player_id]['score'] = self.formatted_player(player, None)
            self.player_ids.append(player_id)

            self.team_to_players[self.player_to_team[player_id]].append(player_id)

    def __load_lineups(self):
        loaded = get_lineups(self.coming_game_date)
        for lineup in loaded:
            self.lineups[lineup['user_id']] = Lineup(lineup, self)

        if len(self.lineups) > 0:
            self.collections = get_collections(self.lineups.keys())

    def reload(self):
        if self.coming_game_date != NBA_PROVIDER.get_coming_game_date():
            self.coming_game_date = NBA_PROVIDER.get_coming_game_date()
            self.__load_players()

        self.__load_lineups()

    def __create_lineup(self, user_id):
        self.lineups[user_id] = Lineup(
            {
                "user_id": user_id,
                "game_date": self.coming_game_date,
                "captain_1": None,
                "starter_2": None,
                "starter_3": None,
                "starter_4": None,
                "starter_5": None,
                "bench_6": None,
                "bench_7": None,
                "bench_8": None,
                "submitted": False
            },
            self
        )

    def get_lineup(self, user_id):
        return self.lineups[user_id]

    def check_lineup(self, user_id):
        if user_id not in self.lineups:
            self.__create_lineup(user_id)

        return self.get_lineup(user_id)

    def load_user_collection(self, user_id):
        collection = get_collections([user_id])

        if collection is not None:
            self.collections[user_id] = collection[user_id]

    def get_opponent(self, player_id):
        return self.team_to_opponent[self.player_to_team[player_id]]

    def formatted_player(self, player, collection):
        score = compute_vgn_score(player, collection)
        return \
            "***{}.*** **{} +{:.2f}v {}#{}** vs *{}*\n" \
            "{:.2f}pts {:.2f}reb {:.2f}ast {:.2f}stl {:.2f}blk\n".format(
                player['index'],
                player['full_name'],
                score,
                self.player_to_team[player['id']],
                player['jersey_number'],
                self.get_opponent(player['id']),
                player['points_recent'],
                player['defensive_rebounds_recent'] + player['offensive_rebounds_recent'],
                player['assists_recent'],
                player['steals_recent'],
                player['blocks_recent']
            ), \
            score

    def formatted_all_players(self):
        messages = []
        message = ""

        for player_id in self.players:
            new_message = self.players[player_id]['formatted']
            message, _ = truncate_message(messages, message, new_message, 1950)

        if message != "":
            messages.append(message)

        return messages

    def formatted_team_players(self, team):
        if team not in self.team_to_players:
            return ["{} is not playing on {}.".format(team, self.coming_game_date)]

        messages = []
        message = ""

        for player_id in self.team_to_players[team]:
            new_message = self.players[player_id]['formatted']
            message, _ = truncate_message(messages, message, new_message, 1950)

        if message != "":
            messages.append(message)

        return messages

    def detailed_player(self, player, collection):
        scores, total, bonus = compute_vgn_scores(player, collection)
        return \
            "***{}.*** **{} {} {}** vs *{}*\n" \
            "{:.2f} PTS {:.2f}v (+{:.2f}) " \
            "point-bonus {:.2f}v (+{:.2f})\n" \
            "{:.2f} 3PT {:.2f}v (+{:.2f})\n" \
            "{:.2f} DRB {:.2f}v (+{:.2f})\n" \
            "{:.2f} ORB {:.2f}v (+{:.2f})\n" \
            "{:.2f} AST {:.2f}v (+{:.2f})\n" \
            "{:.2f} STL {:.2f}v (+{:.2f})\n" \
            "{:.2f} BLK {:.2f}v (+{:.2f})\n" \
            "{:.2f} FGM {:.2f}v (+{:.2f})\n" \
            "{:.2f} FTM {:.2f}v (+{:.2f})\n" \
            "{:.2f} TOV {:.2f}v (+{:.2f})\n" \
            "{:.2f} PFS {:.2f}v (+{:.2f}) " \
            "foul-out {:.2f}v\n" \
            "{:.2f} WIN {:.2f}v (+{:.2f})\n" \
            "{:.2f} 2DD {:.2f}v\n" \
            "{:.2f} 3TD {:.2f}v\n" \
            "{:.2f} 4QD {:.2f}v\n" \
            "{:.2f} 5FD {:.2f}v\n" \
            "**sum: {:.2f}v (+{:.2f})**\n\n" \
            "".format(
                player['index'], player['full_name'], player['jersey_number'],
                self.player_to_team[player['id']], self.get_opponent(player['id']),
                player['points'], scores['points']['score'], scores['points']['bonus'],
                scores['pointBonus']['score'], scores['pointBonus']['bonus'],
                player['threePointersMade'], scores['threePointersMade']['score'], scores['threePointersMade']['bonus'],
                player['defensive_rebounds_recent'], scores['reboundsDefensive']['score'],
                scores['reboundsDefensive']['bonus'],
                player['offensive_rebounds_recent'], scores['reboundsOffensive']['score'],
                scores['reboundsOffensive']['bonus'],
                player['assists'], scores['assists']['score'], scores['assists']['bonus'],
                player['steals'], scores['steals']['score'], scores['steals']['bonus'],
                player['blocks'], scores['blocks']['score'], scores['blocks']['bonus'],
                player['fieldGoalsMissed'], scores['fieldGoalsMissed']['score'], scores['fieldGoalsMissed']['bonus'],
                player['freeThrowsMissed'], scores['freeThrowsMissed']['score'], scores['freeThrowsMissed']['bonus'],
                player['turnovers'], scores['turnovers']['score'], scores['turnovers']['bonus'],
                player['foulsPersonal'], scores['foulsPersonal']['score'], scores['foulsPersonal']['bonus'],
                scores['foulOut']['score'],
                player['win'], scores['win']['score'], scores['win']['bonus'],
                player['doubleDouble'], scores['doubleDouble']['score'],
                player['tripleDouble'], scores['tripleDouble']['score'],
                player['quadrupleDouble'], scores['quadrupleDouble']['score'],
                player['fiveDouble'], scores['fiveDouble']['score'],
                total, bonus
            )

    def detailed_players(self, players, user_id):
        if user_id not in self.collections:
            self.load_user_collection(user_id)

        collection = self.collections.get(user_id)
        if collection is None:
            return ["Fail to load user collection."]

        messages = []
        message = ""

        for dbPlayer in players:
            player_id = dbPlayer['id']
            if player_id not in self.players:
                new_message = "Player **{}** is not playing the coming games.\n".format(dbPlayer['full_name'])
            else:
                new_message = self.detailed_player(self.players[player_id], collection.get(player_id))
            message, _ = truncate_message(messages, message, new_message, 1950)

        if message != "":
            messages.append(message)

        return messages


class Lineup:
    def __init__(self, db_lineup, provider):
        self.user_id = db_lineup['user_id']
        self.game_date = db_lineup['game_date']
        self.player_ids = [
            db_lineup['captain_1'],
            db_lineup['starter_2'],
            db_lineup['starter_3'],
            db_lineup['starter_4'],
            db_lineup['starter_5'],
            db_lineup['bench_6'],
            db_lineup['bench_7'],
            db_lineup['bench_8'],
        ]
        self.submitted = db_lineup['submitted']
        self.provider = provider

    def get_formatted(self):
        message = "Your lineup for **{}** is **{}submitted**.\n"\
            .format(self.game_date, "" if self.submitted else "not ")
        message += "**" + "1️⃣" + ". Captain** {}\n".format(self.get_formatted_player(1))
        message += "**" + "2️⃣" + ".** Starter {}\n".format(self.get_formatted_player(2))
        message += "**" + "3️⃣" + ".** Starter {}\n".format(self.get_formatted_player(3))
        message += "**" + "4️⃣" + ".** Starter {}\n".format(self.get_formatted_player(4))
        message += "**" + "5️⃣" + ".** Starter {}\n".format(self.get_formatted_player(5))
        message += "**" + "6️⃣" + ".** *Bench*   {}\n".format(self.get_formatted_player(6))
        message += "**" + "7️⃣" + ".** *Bench*   {}\n".format(self.get_formatted_player(7))
        message += "**" + "8️⃣" + ".** *Bench*   {}\n".format(self.get_formatted_player(8))
        message += "A. **/player** command get all players\n"
        message += "B. **/team <teamName>** command check players for team\n"
        message += "C. **/add <playerId> <pos>** command to add player to position\n"
        message += "D. **/remove <pos>** command to remove player to position\n"
        message += "E. **/swap <pos1> <pos2>** command to swap 2 positions\n"
        message += "F. **/submit** command to submit your lineup\n"
        return message

    def get_formatted_player(self, position):
        player_id = self.player_ids[position - 1]

        if player_id is None:
            return "/add <playerId> {}".format(position)
        else:
            player = self.provider.players[player_id]
            return "**#{} {}** ***+{:.2f}v {}*** vs *{}*".format(
                player['index'],
                player['full_name'],
                player['score'],
                self.provider.player_to_team[player_id],
                self.provider.get_opponent(player_id)
            )

    def add_player(self, player_idx, position):
        if player_idx < 1 or player_idx > len(self.provider.player_ids):
            return "Player index should be between [1, {}]".format(len(self.provider.player_ids))

        player_id = self.provider.player_ids[player_idx - 1]
        if player_id in self.player_ids:
            return "Player **{}. {}** is already in the lineup.".format(
                self.provider.players[player_id]['index'],
                self.provider.players[player_id]['full_name'],
            )

        message = ""

        previous_player = self.player_ids[position - 1]
        if previous_player is not None:
            message += "Removed **{}. {}**. ".format(
                self.provider.players[previous_player]['index'],
                self.provider.players[previous_player]['full_name'],
            )
        self.player_ids[position - 1] = player_id

        successful, _ = upsert_lineup(
            (self.user_id, self.game_date, self.player_ids[0], self.player_ids[1], self.player_ids[2],
             self.player_ids[3], self.player_ids[4], self.player_ids[5], self.player_ids[6], self.player_ids[7])
        )
        if successful:
            message += "Added **{}. {}** to position {}. ".format(
                self.provider.players[self.player_ids[position - 1]]['index'],
                self.provider.players[self.player_ids[position - 1]]['full_name'],
                position
            )

            return message
        else:
            self.player_ids[position - 1] = previous_player
            return "Failed to update lineup, please retry."

    def remove_player(self, pos):
        if self.player_ids[pos - 1] is None:
            return "Nothing to remove."

        previous_player = self.player_ids[pos - 1]
        self.player_ids[pos - 1] = None

        successful, _ = upsert_lineup(
            (self.user_id, self.game_date, self.player_ids[0], self.player_ids[1], self.player_ids[2],
             self.player_ids[3], self.player_ids[4], self.player_ids[5], self.player_ids[6], self.player_ids[7])
        )

        if successful:
            return "Removed **{}. {}**. ".format(
                self.provider.players[previous_player]['index'],
                self.provider.players[previous_player]['full_name'],
            )
        else:
            self.player_ids[pos - 1] = previous_player
            return "Failed to update lineup, please retry."

    def swap_players(self, pos1, pos2):
        if self.player_ids[pos1 - 1] is None and self.player_ids[pos2 - 1] is None:
            return "Swapped."

        tmp = self.player_ids[pos1 - 1]
        self.player_ids[pos1 - 1] = self.player_ids[pos2 - 1]
        self.player_ids[pos2 - 1] = tmp

        successful, _ = upsert_lineup(
            (self.user_id, self.game_date, self.player_ids[0], self.player_ids[1], self.player_ids[2],
             self.player_ids[3], self.player_ids[4], self.player_ids[5], self.player_ids[6], self.player_ids[7])
        )

        if successful:
            return "Swapped."
        else:
            self.player_ids[pos2 - 1] = self.player_ids[pos1 - 1]
            self.player_ids[pos1 - 1] = tmp
            return "Failed to update lineup, please retry."

    def submit(self):
        if None in self.player_ids:
            return "Still have unfilled positions {}".format([i+1 for i in range(0, 8) if self.player_ids[i] is None])

        successful, _ = submit_lineup(self.user_id, self.game_date)
        if successful:
            self.submitted = True
            return "Submitted."
        else:
            return "Failed to update lineup, please retry."


LINEUP_PROVIDER = LineupProvider()
