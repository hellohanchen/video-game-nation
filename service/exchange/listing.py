import json
import os
import pathlib
from typing import Dict, List

from constants import INVALID_ID
from repository.ts_listings import create_listing, get_ongoing_listings
from vgnlog.channel_logger import ADMIN_LOGGER

EXCHANGE_SETS = {}
EXCHANGE_SET_NAMES = {}
with open(os.path.join(
        pathlib.Path(__file__).parent.resolve(),
        'resource/sets.json'
), 'r') as json_file:
    EXCHANGE_SETS = json.load(json_file)
    for league in EXCHANGE_SETS:
        for series in EXCHANGE_SETS[league]:
            for tier in EXCHANGE_SETS[league][series]['tiers']:
                for set_id in EXCHANGE_SETS[league][series]['tiers'][tier]:
                    EXCHANGE_SET_NAMES[
                        int(set_id)] = f"{EXCHANGE_SETS[league][series]['tiers'][tier][set_id]} ({series})"


class Listing:
    def __init__(self, db_listing):
        self.id = db_listing['id']
        self.user_id: int = db_listing['user_id']
        self.d_username: str = db_listing['discord_username']
        self.ts_username: str = db_listing['topshot_username']
        self.lf_set_id: int = db_listing['lf_set_id']
        self.lf_info: str = db_listing['lf_info']
        self.ft_set_id: int = db_listing['ft_set_id']
        self.ft_info: str = db_listing['ft_info']
        self.note: str = db_listing['note']

    @staticmethod
    def new_empty(user_id, discord_username, topshot_username):
        return Listing(db_listing={
            'id': INVALID_ID,
            'user_id': user_id,
            'discord_username': discord_username,
            'topshot_username': topshot_username,
            'lf_set_id': INVALID_ID,
            'lf_info': "",
            'ft_set_id': INVALID_ID,
            'ft_info': "",
            'note': "",
        })

    def set_lf(self, sid, info):
        self.lf_set_id = sid
        self.lf_info = info

    def set_ft(self, sid, info):
        self.ft_set_id = sid
        self.ft_info = info

    def set_note(self, note):
        self.note = note

    def to_db(self):
        return self.user_id, self.d_username, self.ts_username, \
               self.lf_set_id, self.lf_info, self.ft_set_id, self.ft_info, self.note

    def __str__(self):
        message = f"{self.d_username}(ts@{self.ts_username})\n"
        if self.lf_set_id != INVALID_ID:
            message += f"**LF: {EXCHANGE_SET_NAMES[self.lf_set_id]}**"
            if len(self.lf_info) > 0:
                message += f" {self.lf_info}\n"
            else:
                message += f"\n"
        if self.ft_set_id != INVALID_ID:
            message += f"**FT: {EXCHANGE_SET_NAMES[self.ft_set_id]}**"
            if len(self.ft_info) > 0:
                message += f" {self.ft_info}\n"
            else:
                message += f"\n"
        if len(self.note) > 0:
            message += f"**Note:** {self.note}\n"
        else:
            message += f"**Note:** \n"

        return message


class ListingService:
    def __init__(self, trade_channels):
        super(ListingService, self).__init__()
        self.channels = trade_channels
        self.user_listings: Dict[int, List[Listing]] = {}
        self.lf_sets: Dict[int, Dict[int, Listing]] = {}
        self.ft_sets: Dict[int, Dict[int, Listing]] = {}
        self.reload()

    def reload(self):
        listings, err = get_ongoing_listings()
        if listings is not None:
            user_listings: Dict[int, List[Listing]] = {}
            lf_sets: Dict[int, Dict[int, Listing]] = {}
            ft_sets: Dict[int, Dict[int, Listing]] = {}

            for listing in listings:
                uid = listing['user_id']
                if uid not in user_listings:
                    user_listings[uid] = []
                if len(self.user_listings[uid]) < 5:
                    self.user_listings[uid].insert(0, listing)
                    self.add_to_sets(listing, lf_sets, ft_sets)

            self.user_listings = user_listings
            self.lf_sets = lf_sets
            self.ft_sets = ft_sets
            return "Reloaded"

        return f"Listing:Reload:{err}"

    async def post(self, listing: Listing):
        if listing.id == INVALID_ID:
            uid, d_username, ts_username, lf_sid, lf_info, ft_sid, ft_info, note = listing.to_db()
            lid, err = create_listing(uid, d_username, ts_username, lf_sid, lf_info, ft_sid, ft_info, note)
            if err is not None:
                await ADMIN_LOGGER.error(f"Listing:Post:{err}")
                return

            listing.id = lid
            if uid not in self.user_listings:
                self.user_listings[uid] = []
            if len(self.user_listings[uid]) < 5:
                self.user_listings[uid].append(listing)
            else:
                to_remove = self.user_listings[uid][0]
                self.user_listings.pop(0)
                self.user_listings[uid].append(listing)
                self.remove_from_sets(to_remove)

            self.add_to_sets(listing)

        for channel in self.channels:
            await channel.send(str(listing))

    def remove_from_sets(self, li: Listing):
        if li.id == INVALID_ID:
            return

        lid = li.id
        if li.lf_set_id in self.lf_sets and lid in self.lf_sets[li.lf_set_id]:
            del self.lf_sets[li.lf_set_id][lid]
        if li.ft_set_id in self.ft_sets and lid in self.ft_sets[li.ft_set_id]:
            del self.ft_sets[li.ft_set_id][lid]

    def add_to_sets(self, li: Listing, lf_sets=None, ft_sets=None):
        if li.id == INVALID_ID:
            return

        if lf_sets is None:
            lf_sets = self.lf_sets
        if ft_sets is None:
            ft_sets = self.ft_sets

        lid = li.id
        if li.lf_set_id != INVALID_ID:
            if li.lf_set_id not in lf_sets:
                lf_sets[li.lf_set_id] = {}
            lf_sets[li.lf_set_id][lid] = li
        if li.ft_set_id != INVALID_ID:
            if li.ft_set_id not in ft_sets:
                ft_sets[li.ft_set_id] = {}
            ft_sets[li.ft_set_id][lid] = li
