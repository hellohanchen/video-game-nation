def build_fb_collections(ts_provider, plays, player_ids):
    """
        Builds a collection of plays for NBA players or teams, given a dictionary of play IDs and their sets with
        the lowest serial number of each set.

        Args:
            plays: A dictionary where keys are play IDs and values are the number of times the play was performed.

        Returns:
            A tuple containing two elements: a dictionary of player IDs mapped to dictionaries of their play statistics,
            and a list of play IDs that were not found in the TS_ENRICHED_PLAYS dictionary.

        Raises:
            None.

        This function iterates through a dictionary of play IDs and their counts, and computes statistics for each NBA
        player or team based on the plays they were involved in. If a play ID cannot be found in the TS_ENRICHED_PLAYS
        dictionary, it is added to the not_found_plays list.

        The function returns a tuple containing two elements: a dictionary of player IDs mapped to dictionaries of
        their play statistics, and a list of play IDs that were not found in the TS_ENRICHED_PLAYS dictionary.
        If a play corresponds to an NBA player, the play statistics are added to the player's dictionary in the
        player_collections dictionary. If a play corresponds to a team, the team statistics are added to the team's
        dictionary in the team_collections dictionary. Note that the team collections part of the function is not
        implemented yet.
        :param player_ids: list of player ids to scan
        :param plays: play_id --> (set_id, lowest_serial)
        :param ts_provider: detailed ts moment info
        """

    player_collections = {}
    not_found_plays = []

    for play_id in plays:
        if play_id not in ts_provider.play_info:
            not_found_plays.append(play_id)
            continue

        for set_id in plays[play_id]:
            play = None
            for play_with_set_info in ts_provider.play_info[play_id]:
                if play_with_set_info['setFlowId'] == set_id:
                    play = play_with_set_info
                    break
            if play is None:
                not_found_plays.append(play_id * 10000 + set_id)
                continue

            serial = plays[play_id][set_id]
            player_id = play['playerId']
            tier = play['tier']
            is_tsd = 'TSD' in play['badges']

            if player_id is not None and player_id != 0:
                if player_id not in player_ids:
                    continue

                if player_id not in player_collections:
                    player_collections[player_id] = {
                        'tier': tier,
                        'serial': serial,
                        'tsd': is_tsd
                    }
                else:
                    existing_tier = player_collections[player_id]['tier']
                    if existing_tier == 'Common' or existing_tier == 'Fandom':
                        if serial < player_collections[player_id]['serial'] or \
                                tier == 'Rare' or tier == 'Legendary':
                            player_collections[player_id]['tier'] = tier
                            player_collections[player_id]['serial'] = serial

                        player_collections[player_id]['tsd'] |= is_tsd
                    elif existing_tier == 'Rare':
                        if tier == 'Legendary' or \
                                (tier == 'Rare' and serial < player_collections[player_id]['serial']):
                            player_collections[player_id]['tier'] = tier
                            player_collections[player_id]['serial'] = serial
                    elif tier == 'Legendary' and serial < player_collections[player_id]['serial']:
                        player_collections[player_id]['serial'] = serial

                    if player_collections[player_id]['tier'] == tier:
                        player_collections[player_id]['tsd'] |= is_tsd

    return player_collections, not_found_plays
