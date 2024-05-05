from typing import List, Dict, Optional

from constants import INVALID_ID, ERROR_MESSAGE
from provider.games.rr_provider import RR_PROVIDER
from provider.nba.nba_provider import NBA_PROVIDER
from provider.topshot.cadence.flow_collections import get_account_plays_with_lowest_serial
from provider.topshot.ts_provider import TS_PROVIDER
from repository.rr_lineups import get_lineups, upsert_lineup, submit_lineup, get_user_losses, get_user_results, \
    get_user_slate_result
from repository.vgn_players import get_player_ids_names
from repository.vgn_users import get_user_new
from service.redemptionrun.redemption_run import RRSelection, RedemptionRun
from service.redemptionrun.utils import build_rr_collection
from vgnlog.channel_logger import ADMIN_LOGGER


class AbstractLineupService:
    def __init__(self):
        super(AbstractLineupService, self).__init__()
        self.current_game_date: str = ""
        self.formatted_games: str = ""
        self.players: Dict[int, Dict[str, any]] = {}
        self.rr: RedemptionRun = RedemptionRun.get_empty_rr()

    def load_players(self):
        player_ids_to_load: List[int] = []

        for game_id, game in NBA_PROVIDER.get_games_on_date(self.current_game_date).items():
            for team in [game['homeTeam'], game['awayTeam']]:
                for player_id in NBA_PROVIDER.get_players_for_team(team):
                    player_ids_to_load.append(player_id)

        players, _ = get_player_ids_names(player_ids_to_load)
        self.players = players


class LineupService(AbstractLineupService):
    def __init__(self):
        super(LineupService, self).__init__()
        self.lineups: Dict[int, Lineup] = {}
        self.reload()

    def __load_lineups(self):
        lineups = get_lineups(self.current_game_date)
        for lineup in lineups:
            self.lineups[lineup['user_id']] = Lineup(lineup, self)

    def reload(self):
        coming_game_date = RR_PROVIDER.get_coming_game_date()
        if self.current_game_date != coming_game_date:
            self.current_game_date = coming_game_date
            self.players = {}
            self.lineups = {}

            self.formatted_games = self.__formatted_schedule()

        self.load_players()
        rr_info = RR_PROVIDER.get_rr(self.current_game_date)
        self.rr = RedemptionRun(rr_info['buckets'], self.players, rr_info['threshold'])
        self.__load_lineups()

    def __create_lineup(self, user_id: int):
        self.lineups[user_id] = Lineup(
            {
                "user_id": user_id,
                "game_date": self.current_game_date,
                "topshot_username": "",
                "bucket_1": None,
                "bucket_2": None,
                "bucket_3": None,
                "bucket_4": None,
                "bucket_5": None,
                "bucket_6": None,
                "bucket_7": None,
                "bucket_8": None,
                "is_submitted": False
            },
            self
        )

    def get_or_create_lineup(self, user_id: int) -> 'Lineup':
        if user_id not in self.lineups:
            self.__create_lineup(user_id)

        return self.lineups[user_id]

    def get_coming_games(self) -> List[Dict[str, str]]:
        return NBA_PROVIDER.get_games_on_date(self.current_game_date).items()

    def __formatted_schedule(self) -> str:
        message = f"**Games on {self.current_game_date}**\n"

        for _, game in self.get_coming_games():
            message += f"{game['awayTeam']} at {game['homeTeam']}\n"

        return message


class Lineup:
    def __init__(self, db_lineup: Dict[str, int | bool | str], service: AbstractLineupService):
        self.user_id: int = INVALID_ID
        self.username: str = ""
        self.selections: List[Optional[RRSelection]] = []
        self.is_submitted: bool = False
        self.service: AbstractLineupService = service
        self.reload(db_lineup)

    def reload(self, db_lineup: Dict[str, int | bool | str]):
        self.user_id = db_lineup['user_id']
        self.username = db_lineup['topshot_username']
        self.selections: List[Optional[RRSelection]] = [
            None if db_lineup['bucket_1'] is None else RRSelection.from_db_str(db_lineup['bucket_1']),
            None if db_lineup['bucket_2'] is None else RRSelection.from_db_str(db_lineup['bucket_2']),
            None if db_lineup['bucket_3'] is None else RRSelection.from_db_str(db_lineup['bucket_3']),
            None if db_lineup['bucket_4'] is None else RRSelection.from_db_str(db_lineup['bucket_4']),
            None if db_lineup['bucket_5'] is None else RRSelection.from_db_str(db_lineup['bucket_5']),
            None if db_lineup['bucket_6'] is None else RRSelection.from_db_str(db_lineup['bucket_6']),
            None if db_lineup['bucket_7'] is None else RRSelection.from_db_str(db_lineup['bucket_7']),
            None if db_lineup['bucket_8'] is None else RRSelection.from_db_str(db_lineup['bucket_8']),
        ]
        self.is_submitted = db_lineup['is_submitted']

    def formatted(self) -> str:
        message = self.service.formatted_games + "\n"

        message += f"Your selections for **{self.service.current_game_date}**"
        if self.is_submitted:
            message += f" is **SUBMITTED**.\n\n"
        else:
            message += f" is **NOT** submitted.\n\n"

        for i in range(len(self.service.rr.buckets)):
            selection = self.selections[i]
            bucket = self.service.rr.buckets[i]
            if selection is None:
                message += bucket.get_formatted()
            else:
                message += selection.format_with_bucket(bucket)
            message += '\n'
        message += f"**Survival Rate: {int(self.service.rr.threshold * 100.0)}%**"

        return message

    def __upsert(self):
        return upsert_lineup(
            (
                self.user_id, self.service.current_game_date,
                None if self.selections[0] is None else self.selections[0].to_db_str(),
                None if self.selections[1] is None else self.selections[1].to_db_str(),
                None if self.selections[2] is None else self.selections[2].to_db_str(),
                None if self.selections[3] is None else self.selections[3].to_db_str(),
                None if self.selections[4] is None else self.selections[4].to_db_str(),
                None if self.selections[5] is None else self.selections[5].to_db_str(),
                None if self.selections[6] is None else self.selections[6].to_db_str(),
                None if self.selections[7] is None else self.selections[7].to_db_str(),
            )
        )

    async def select(self, bucket_idx, selected) -> str:
        bucket = self.service.rr.buckets[bucket_idx]
        selected_name = bucket.options[0][1] if selected == bucket.options[0][0] else bucket.options[1][1]

        new_selection = RRSelection(selected, 0, 'Unknown')
        self.selections[bucket_idx] = new_selection

        updated_lineup, err = self.__upsert()
        if err is None:
            message = self.formatted()
            message += f"\nSelected **{selected_name}**."
            if self.is_submitted:
                message += "\n**You need to SUBMIT again to save your changes to join leaderboard.**"
            self.reload(updated_lineup[0])
            return message
        else:
            await ADMIN_LOGGER.error(f"RRLineup:Select:{self.user_id}:{bucket_idx}:{err}")
            return ERROR_MESSAGE

    async def submit(self) -> str:
        for i in range(len(self.service.rr.buckets)):
            if self.selections[i] is None:
                return "You need to make all selections before submission."

        user, err = get_user_new(self.user_id)
        if user is None:
            await ADMIN_LOGGER.error(f"RRLineup:Submit:GetUser:{err}")
            return ERROR_MESSAGE

        losses, err = get_user_losses(self.user_id, RR_PROVIDER.rr_details.keys(), self.service.current_game_date)
        if err is not None:
            await ADMIN_LOGGER.error(f"RRLineup:Submit:GetLosses:{self.user_id}:{err}")
            return ERROR_MESSAGE

        try:
            plays = await get_account_plays_with_lowest_serial(user['flow_address'])
            collection, _, rr_moments = build_rr_collection(
                TS_PROVIDER, plays, self.service.rr, RR_PROVIDER.eligible_team_ids)
            if losses > rr_moments:
                return f"You've lost {losses} lives and have {rr_moments} 23-24 redemption/playoff moments."

            for i in range(len(self.service.rr.buckets)):
                selection = self.selections[i]
                identifier = selection.selected
                if identifier not in collection:
                    return f"Missing {self.service.rr.buckets[i].moment_types} moments of " \
                           f"{self.service.rr.buckets[i].get_option_name(identifier)}"
                selection.tier = collection[identifier]['tier']
                selection.serial = collection[identifier]['serial']
        except Exception as err:
            await ADMIN_LOGGER.error(f"RRLineup:Collection:{self.user_id}:{err}")
            return ERROR_MESSAGE

        _, err = self.__upsert()
        if err is not None:
            await ADMIN_LOGGER.error(f"RRLineup:Submit:Upsert:{self.user_id}:{err}")
            return ERROR_MESSAGE

        successful, updated_lineup, err = submit_lineup(
            self.user_id, user['topshot_username'], self.service.current_game_date)
        if not successful:
            await ADMIN_LOGGER.error(f"RRLineup:Submit:{err}")
            return ERROR_MESSAGE
        self.reload(updated_lineup[0])

        message = f"You've submitted selections for *{self.service.current_game_date}*:\n\n"
        for i in range(len(self.service.rr.buckets)):
            bucket = self.service.rr.buckets[i]
            selection = self.selections[i]
            selected_name = bucket.options[0][1] if selection.selected == bucket.options[0][0] else bucket.options[1][1]

            message += f"🏀 **{selected_name}** " \
                       f"{selection.serial}, {selection.tier}\n"

        return message


RR_LINEUP_SERVICE = LineupService()
