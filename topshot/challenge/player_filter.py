from typing import List, Set

from topshot.ts_info import TS_PLAYER_ID_MOMENTS


class PlayerFilter:
    def filter_players(self, player_ids: Set[int]) -> Set[int]:
        pass


class TopshotFilter(PlayerFilter):
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
            if player_id not in TS_PLAYER_ID_MOMENTS:
                continue

            for tag in self.tags:
                if not TS_PLAYER_ID_MOMENTS[player_id][tag]:
                    continue

            filtered.add(player_id)

        return filtered


class PlayerIDFilter(PlayerFilter):
    def __init__(self, ids: List[str]):
        """
        Initialize a new instance of the TopshotFilter class.

        Args:
            ids (List[str]): A list of tags used to filter players.
        """
        self.ids = [int(i) for i in ids]

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
            if player_id not in self.ids:
                continue

            if player_id not in TS_PLAYER_ID_MOMENTS:
                continue

            filtered.add(player_id)

        return filtered
