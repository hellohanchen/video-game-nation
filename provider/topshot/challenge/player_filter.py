from typing import List, Set

from provider.topshot.ts_provider import TS_PROVIDER


class PlayerFilter:
    def filter_players(self, player_ids: Set[int]) -> Set[int]:
        pass


class TopshotFilter(PlayerFilter):
    def __init__(self, series: List[str], tags: List[str]):
        """
        Initialize a new instance of the TopshotFilter class.

        Args:
            tags (List[str]): A list of tags used to filter players.
        """
        self.series = series
        self.badges = tags

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
            if player_id not in TS_PROVIDER.player_moments:
                continue

            matched = True
            for series in self.series:
                matched = False
                all_badges = True
                for badge in self.badges:
                    if badge not in TS_PROVIDER.player_moments[player_id]['badges'][series] or \
                            not TS_PROVIDER.player_moments[player_id]['badges'][series][badge]:
                        all_badges = False
                        break
                if all_badges:
                    matched = True
                    break

            if matched:
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

            if player_id not in TS_PROVIDER.player_moments:
                continue

            filtered.add(player_id)

        return filtered


class TopshotSetFilter(PlayerFilter):
    def __init__(self, set: str):
        """
        Initialize a new instance of the TopshotSetFilter class.

        Args:
            set (str): flow id of TS set
        """
        self.set = int(set)

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
            if player_id not in TS_PROVIDER.player_moments:
                continue

            if self.set not in TS_PROVIDER.player_moments[player_id]['sets']:
                continue

            filtered.add(player_id)

        return filtered
