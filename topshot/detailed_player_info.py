import asyncio
import json
import os.path
import pathlib

from topshot.tsgql.listing_tiers import get_listing_tiers

SERIES_MAP = {
    1: "S1",
    2: "S2",
    3: "S3",
    4: "S3",
    5: "S4"
}

TIER_MAP = {
    "SET_VISUAL_COMMON": "C",
    "SET_VISUAL_RARE": "R",
    "SET_VISUAL_FANDOM": "F",
    "SET_VISUAL_LEGENDARY": "L",
    "SET_VISUAL_ANTHOLOGY": "A"
}


async def load_player_data():
    result = {}
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/players.json"), 'r') as player_file:
        data = json.load(player_file)
        for player in data['players']:
            result[player['playerID']] = {
                "displayName": player['label']
            }

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/players_2.json"), 'r') as player_file:
        data = json.load(player_file)
        for player in data['players']:
            if int(player['id']) not in result:
                continue

            result[int(player['id'])]['originalName'] = player['name']

    for player_id in result:
        for s_id in SERIES_MAP:
            result[player_id][SERIES_MAP[s_id]] = False
            result[player_id][SERIES_MAP[s_id] + "C"] = False
            result[player_id][SERIES_MAP[s_id] + "F"] = False
            result[player_id][SERIES_MAP[s_id] + "R"] = False
            result[player_id][SERIES_MAP[s_id] + "L"] = False
            result[player_id][SERIES_MAP[s_id] + "Rookie"] = False

            try:
                tiers = await get_listing_tiers(s_id, player_id)
                if len(tiers) > 0:
                    result[player_id][SERIES_MAP[s_id]] = True
                    for t in tiers:
                        result[player_id][SERIES_MAP[s_id] + TIER_MAP[t]] = True
            except:
                with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/detailed_players.json"),'w') as output:
                    json.dump(result, output, indent=2)

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/detailed_players.json"), 'w') as output:
        json.dump(result, output, indent=2)


asyncio.run(load_player_data())
