import asyncio
import random
import time

from provider.topshot.cadence.flow_collections import get_collection_for_trade
from provider.topshot.graphql.get_account import get_flow_address
from provider.topshot.graphql.get_price import get_listing_prices
from provider.topshot.ts_provider import TS_PROVIDER


def remove_dupes(c1, c2, series_or_set):
    c1_sets_to_remove = []
    c2_sets_to_remove = []

    if series_or_set > 0:
        c1_sets_to_remove = list(c1.keys())
        if series_or_set in c1_sets_to_remove:
            c1_sets_to_remove.remove(series_or_set)
        c2_sets_to_remove = list(c2.keys())
        if series_or_set in c2_sets_to_remove:
            c2_sets_to_remove.remove(series_or_set)
    elif series_or_set < 0:
        c1_sets_to_remove = [set_id for set_id in c1 if TS_PROVIDER.set_info[int(set_id)]['flowSeriesNumber'] != -series_or_set]
        c2_sets_to_remove = [set_id for set_id in c2 if TS_PROVIDER.set_info[int(set_id)]['flowSeriesNumber'] != -series_or_set]

    for set_id in c1_sets_to_remove:
        c1.pop(set_id)

    for set_id in c2_sets_to_remove:
        c2.pop(set_id)

    c1_sets_to_remove = []
    c2_sets_to_remove = []

    for set_id in c1:
        if set_id not in c2:
            continue

        common_plays = []

        for play_id in c1[set_id]:
            if play_id in c2[set_id]:
                common_plays.append(play_id)

        for play_id in common_plays:
            c1[set_id].pop(play_id)
            c2[set_id].pop(play_id)

        if len(c1[set_id]) == 0:
            c1_sets_to_remove.append(set_id)

        if len(c2[set_id]) == 0:
            c2_sets_to_remove.append(set_id)

    for set_id in c2_sets_to_remove:
        c2.pop(set_id)


async def get_lowest_listing_price(collection):
    for set_id in collection:
        set_uuid = TS_PROVIDER.set_info[int(set_id)]["id"]
        play_ids = list(collection[set_id].keys())

        while len(play_ids) > 0:
            unresolved_play_ids = []
            start = 0
            while start < len(play_ids):
                upper_bound = min(start + 12, len(play_ids))

                player_ids = [TS_PROVIDER.play_info[int(play_id)][0]['playerId'] for play_id in play_ids[start:upper_bound]]

                team_ids = []

                if None in player_ids:
                    player_ids = [player_id for player_id in player_ids if player_id is not None]
                    if len(player_ids) == 0:  # only team moments
                        team_ids = [
                            str(TS_PROVIDER.team_name_to_id[collection[set_id][play_id]['FullName']]['id'])
                            for play_id in play_ids[start:upper_bound]
                        ]

                time.sleep(0.3)
                listing_prices = await get_listing_prices(set_uuid, player_ids, team_ids)

                if len(listing_prices) == 0:
                    print("Empty response, retry after 0.3s")
                    time.sleep(0.25)
                    continue

                for play_id in play_ids[start:upper_bound]:
                    play_id_int = int(play_id)
                    if play_id_int in listing_prices:
                        collection[set_id][play_id]['LowAsk'] = listing_prices[play_id_int]
                    else:
                        unresolved_play_ids.append(play_id)

                start = start + 12

            if len(unresolved_play_ids) == len(play_ids):
                play_ids = []
                for play_id in unresolved_play_ids:
                    play_ids.append(play_id)
                    play_ids.append(play_id)
            else:
                random.shuffle(unresolved_play_ids)
                play_ids = unresolved_play_ids


async def get_account_collection(topshot_username):
    address = await get_flow_address(topshot_username)

    if address is None:
        raise NameError("Can't find topshot user {}".format(topshot_username))

    return await get_collection_for_trade(address)


async def compare_moments(ts_user1, ts_user2, series_or_set):
    c1, c2 = await asyncio.gather(*[get_account_collection(ts_user1), get_account_collection(ts_user2)])
    remove_dupes(c1, c2, series_or_set)
    await asyncio.gather(*[get_lowest_listing_price(c1)])
    await asyncio.gather(*[get_lowest_listing_price(c2)])

    return c1, c2


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    c1, c2 = loop.run_until_complete(compare_moments("MingDynastyVase", "ubabu", 4))
    loop.close()

    print(c1)
    print("-"*88)
    print(c2)
