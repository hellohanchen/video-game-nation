import asyncio
import json
import os
import pathlib

from flow_py_sdk import flow_client, Script


async def get_all_plays():
    script = Script(
        code="""
                import TopShot from 0x0b2a3299cc857e29

                pub fun main(): {UInt32:{String:String}} {
                    let plays = TopShot.getAllPlays()

                    let res: {UInt32:{String:String}} = {}                        

                    for play in plays {
                        res.insert(key: play.playID, {})
                        
                        let metadata = TopShot.getPlayMetaData(playID: play.playID)!
                        
                        res[play.playID]!.insert(key: "FullName", metadata["FullName"] ?? metadata["TeamAtMoment"]!)
                        res[play.playID]!.insert(key: "DateOfMoment", metadata["DateOfMoment"] ?? "")
                        res[play.playID]!.insert(key: "PlayCategory", metadata["PlayCategory"] ?? "")
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

        player_plays = {}

        for play_item in complex_script.value:
            for field in play_item.value.value:
                if field.key.value == "FullName":
                    player_name = field.value.value
                if field.key.value == "DateOfMoment":
                    date = field.value.value[:10]
                if field.key.value == "PlayCategory":
                    category = field.value.value

            if player_name not in player_plays:
                player_plays[player_name] = {}

            if date not in player_plays[player_name]:
                player_plays[player_name][date] = {}

            player_plays[player_name][date][category] = play_item.key.value

        with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "result/cadence_plays.json"), 'w') as output_file:
            json.dump(player_plays, output_file, indent=2)

        return player_plays


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(get_all_plays())
    loop.close()
