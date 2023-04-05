import asyncio
import json
import os
import pathlib

from topshot.cadence.play_info import get_all_plays

BADGES = {
    "Top Shot Debut": "TSD",
    "Rookie Year": "RY",
    "Rookie Premiere": "RP",
    "MVP Year": "MVP",
    "Championship Year": "CY",
}

cadence_plays = asyncio.run(get_all_plays())

with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/graphql_plays.json"), 'r', encoding='utf-8') as graphql_result:
    graphql_plays = json.load(graphql_result)['data']['searchPlays']['searchSummary']['data']['data']

play_details = {}
for play in graphql_plays:
    player_name = play["stats"]['playerName'] if 'playerName' in play['stats'] and play["stats"]['playerName'] is not None else play["stats"]['teamAtMoment']

    try:
        if 'dateOfMoment' in play['stats'] and play["stats"]['dateOfMoment'] is not None:
            play_date = play["stats"]['dateOfMoment'][:10]
        else:
            play_date = ""

        play_id = cadence_plays[player_name][play_date][play["stats"]['playCategory']]
    except Exception as err:
        play_id = -1

    detail = {
        "flowID": play_id,
        "playID": play['id'],
        "playerName": player_name,
        "playerID": int(play["stats"]['playerID']) if play['stats']['playerID'] is not None else 0,
        "playType": play["stats"]['playCategory'],
        "playDate": play_date,
        "TSD": False,
        "RY": False,
        "RP": False,
        "MVP": False,
        "CY": False,
        "TEAM": play['stats']['playerID'] is None
    }

    if play['tags'] is not None:
        for tag in play['tags']:
            if tag['title'] in BADGES:
                detail[BADGES[tag['title']]] = True

    play_details[play['id']] = detail

with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/detailed_plays.json"), 'w') as output_file:
    json.dump(play_details, output_file, indent=2)
