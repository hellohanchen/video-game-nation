import asyncio
import random
import time

from flow_py_sdk import flow_client, cadence, Script

from topshot.ts_info import TOPSHOT_SET_INFO, get_player_flow_id_str, TOPSHOT_TEAM_INFO
from topshot.tsgql import flow_address, listing_price


async def get_all_plays():
    script = Script(
        code="""
                import TopShot from 0x0b2a3299cc857e29

                pub fun main(): {UInt32: String} {
                    let plays = TopShot.getAllPlays()

                    let res: {UInt32: String} = {}                        

                    for play in plays {
                        res.insert(key: play.playID, play.identifier)
                    }

                    return res
                }
            """,
        arguments=[],
    )

    async with flow_client(
            host="access.mainnet.nodes.onflow.org", port=9000
    ) as client:
        complex_script = await client.execute_script(
            script=script
            # , block_id
            # , block_height
        )
        sets = {}

        for set_item in complex_script.value:
            set_id = str(set_item.key)
            sets[set_id] = {}

            for play_item in set_item.value.value:
                play_id = str(play_item.key)
                sets[set_id][play_id] = {}

                for play_info in play_item.value.value:
                    sets[set_id][play_id][str(play_info.key)] = str(play_info.value)

    return sets


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    c1 = loop.run_until_complete(get_all_plays())
    loop.close()

    print(c1)

