from typing import List

from service.redemptionrun.redemption_run import RedemptionRun

RR_SETS = [141, 142, 143]
PLAYOFF_SETS = [
    16, 17, 18, 19, 20, 21,
    39, 40, 41,
    67, 68, 69, 104, 105, 110,
    141, 142, 143
]


def build_rr_collection(ts_provider, plays, rr: RedemptionRun, redemption_team_ids: List[int]):
    moment_types_of_ids = {}
    for b in rr.buckets:
        moment_types_of_ids[b.options[0][0]] = b.moment_types
        moment_types_of_ids[b.options[1][0]] = b.moment_types

    collection = {}
    not_found_plays = []
    rr_moment_count = 0

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
            tier = play['tier']

            # handle player id case
            player_id = play['playerId']
            if player_id in moment_types_of_ids:
                required_types = moment_types_of_ids[player_id]
                if 'Any' not in required_types and play['playType'] not in required_types:
                    continue

                if player_id not in collection:
                    collection[player_id] = {
                        'tier': tier,
                        'serial': serial,
                    }
                else:
                    existing_tier = collection[player_id]['tier']
                    if existing_tier == 'Common' or existing_tier == 'Fandom':
                        if tier == 'Rare':
                            collection[player_id]['tier'] = 'Rare'
                        elif tier in ['Legendary', 'Ultimate']:
                            collection[player_id]['tier'] = 'Legendary'
                    elif existing_tier == 'Rare' and tier in ['Legendary', 'Ultimate']:
                        collection[player_id]['tier'] = 'Legendary'

                    if collection[player_id]['serial'] > serial:
                        collection[player_id]['serial'] = serial

            team_id = play['teamId']
            if team_id in redemption_team_ids and set_id in RR_SETS:
                rr_moment_count += 1
            if team_id in moment_types_of_ids:
                required_types = moment_types_of_ids[team_id]
                if 'Any' not in required_types:
                    if 'Playoff' not in required_types and play['playType'] not in required_types:
                        continue
                    elif set_id not in PLAYOFF_SETS:
                        continue

                if team_id not in collection:
                    collection[team_id] = {
                        'tier': tier,
                        'serial': serial,
                    }
                else:
                    existing_tier = collection[team_id]['tier']
                    if existing_tier == 'Common' or existing_tier == 'Fandom':
                        if tier == 'Rare':
                            collection[team_id]['tier'] = 'Rare'
                        elif tier in ['Legendary', 'Ultimate']:
                            collection[team_id]['tier'] = 'Legendary'
                    elif existing_tier == 'Rare' and tier in ['Legendary', 'Ultimate']:
                        collection[team_id]['tier'] = 'Legendary'

                    if collection[team_id]['serial'] > serial:
                        collection[team_id]['serial'] = serial

    return collection, not_found_plays, rr_moment_count
