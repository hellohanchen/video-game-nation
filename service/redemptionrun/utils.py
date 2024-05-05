from typing import List

from service.redemptionrun.redemption_run import RedemptionRun


RR_SETS = [141, 142, 143]


def build_rr_collection(ts_provider, plays, rr: RedemptionRun, team_ids: List[int]):
    moment_types = {}
    for b in rr.buckets:
        moment_types[b.options[0][0]] = b.moment_types
        moment_types[b.options[1][0]] = b.moment_types

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

            if 'TEAM' in play['badges']:
                identifier = play['teamId']
            else:
                identifier = play['playerId']
            if identifier in team_ids and set_id in RR_SETS:
                rr_moment_count += 1

            if identifier not in moment_types:
                continue
            if 'Any' not in moment_types[identifier] and play['playType'] not in moment_types[identifier]:
                continue

            serial = plays[play_id][set_id]
            tier = play['tier']

            if identifier is not None and identifier != 0:
                if identifier not in collection:
                    collection[identifier] = {
                        'tier': tier,
                        'serial': serial,
                    }
                else:
                    existing_tier = collection[identifier]['tier']
                    if existing_tier == 'Common' or existing_tier == 'Fandom':
                        if tier == 'Rare':
                            collection[identifier]['tier'] = 'Rare'
                        elif tier in ['Legendary', 'Ultimate']:
                            collection[identifier]['tier'] = 'Legendary'
                    elif existing_tier == 'Rare' and tier in ['Legendary', 'Ultimate']:
                        collection[identifier]['tier'] = 'Legendary'

                    if collection[identifier]['serial'] > serial:
                        collection[identifier]['serial'] = serial

    return collection, not_found_plays, rr_moment_count
