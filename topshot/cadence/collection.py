from flow_py_sdk import flow_client, cadence, Script


async def get_collection_for_trade(address):
    script = Script(
        code="""
                import TopShot from 0x0b2a3299cc857e29

                pub fun main(account: Address): {UInt32:{UInt32:{String:String}}} {
                    let acct = getAccount(account)

                    let collectionRef = acct.getCapability(/public/MomentCollection)
                                            .borrow<&{TopShot.MomentCollectionPublic}>()!

                    let res: {UInt32:{UInt32:{String:String}}} = {}                        

                    for id in collectionRef.getIDs() {
                        // Borrow a reference to the specified moment
                        let token = collectionRef.borrowMoment(id: id)
                            ?? panic("Could not borrow a reference to the specified moment")

                        // Get the moment's metadata to access its play and Set IDs
                        let data = token.data

                        // Use the moment's play ID 
                        // to get all the metadata associated with that play
                        let metadata = TopShot.getPlayMetaData(playID: data.playID) ?? panic("Play doesn't exist")

                        if res.containsKey(data.setID) == false {
                            res.insert(key: data.setID, {})
                        }

                        if res[data.setID]!.containsKey(data.playID) == false {
                            res[data.setID]!.insert(key: data.playID, {})
                            res[data.setID]![data.playID]!.insert(key: "FullName", metadata["FullName"] ?? metadata["TeamAtMoment"]!)
                            res[data.setID]![data.playID]!.insert(key: "Count", "0")
                        }

                        var count: Int = Int.fromString(res[data.setID]![data.playID]!["Count"]!)!
                        count = count + 1
                        res[data.setID]![data.playID]!.insert(key: "Count", count.toString())
                    }

                    return res
                }
            """,
        arguments=[cadence.Address.from_hex(address)],
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
