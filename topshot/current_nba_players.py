import asyncio
import json
import os
import pathlib
import time

from topshot.ts_info import TS_PLAYER_ID_MOMENTS
from topshot.tsgql.get_stats import get_player_stats


async def filter_current_nba_players():
    result = {}

    player_ids = list(TS_PLAYER_ID_MOMENTS.keys())
    for player in player_ids:
        player_id = int(player)

        if await get_player_stats(player_id) is None:
            result[player_id] = False
        else:
            result[player_id] = True

        time.sleep(0.3)

    return result


if __name__ == '__main__':
    players = asyncio.run(filter_current_nba_players())

    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/current_nba_players.json"),
              'w') as output_file:
        json.dump(players, output_file, indent=2)

