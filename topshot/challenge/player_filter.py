from topshot.player_info import TS_PLAYER_INFO
from typing import List, Set


class TopshotFilter:
    def __init__(self, tags: List[str]):
        """
        Initialize a new instance of the TopshotFilter class.

        Args:
            tags (List[str]): A list of tags used to filter players.
        """
        self.tags = tags

    def filter_players(self, player_ids: Set[int]) -> Set[int]:
        """
        Filter a set of player IDs based on the tags associated with the TopshotFilter object.

        Args:
            player_ids (Set[int]): A set of player IDs to filter.

        Returns:
            Set[int]: A set of player IDs that passed the filter.
        """
        filtered = set()
        for player_id in player_ids:
            if str(player_id) not in TS_PLAYER_INFO:
                continue

            for tag in self.tags:
                if not TS_PLAYER_INFO[str(player_id)][tag]:
                    continue

            filtered.add(player_id)

        return filtered
