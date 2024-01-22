import asyncio

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

                    for momentId in collectionRef.getIDs() {
                        // Borrow a reference to the specified moment
                        let moment = collectionRef.borrowMoment(id: momentId)
                            ?? panic("Could not borrow a reference to the specified moment")

                        // Get the moment's metadata to access its play and Set IDs
                        let data = moment.data

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
            set_id = int(str(set_item.key))
            sets[set_id] = {}

            for play_item in set_item.value.value:
                play_id = int(str(play_item.key))
                sets[set_id][play_id] = {}

                for play_info in play_item.value.value:
                    sets[set_id][play_id][str(play_info.key)] = str(play_info.value)

    return sets


async def get_account_plays(address):
    script = Script(
        code="""
                import TopShot from 0x0b2a3299cc857e29

                pub fun main(account: Address): {UInt32:{UInt32:UInt32}} {
                    let acct = getAccount(account)

                    let collectionRef = acct.getCapability(/public/MomentCollection)
                                            .borrow<&{TopShot.MomentCollectionPublic}>()!

                    let res: {UInt32:{UInt32:UInt32}} = {}                        

                    for id in collectionRef.getIDs() {
                        // Borrow a reference to the specified moment
                        let token = collectionRef.borrowMoment(id: id)
                            ?? panic("Could not borrow a reference to the specified moment")

                        // Get the moment's metadata to access its play and Set IDs
                        let data = token.data
                        
                        if res.containsKey(data.playID) == false {
                            let playCountPerSet: {UInt32:UInt32} = {}
                            playCountPerSet.insert(key: data.setID, 1)
                            res.insert(key: data.playID, playCountPerSet)
                        } else {
                            let playCountPerSet: {UInt32:UInt32} = res[data.playID]!
                            if playCountPerSet.containsKey(data.setID) == false {
                                playCountPerSet.insert(key: data.setID, 1)
                            } else {
                                var count: UInt32 = playCountPerSet[data.setID]!
                                count = count + 1
                                playCountPerSet.insert(key: data.setID, count)
                            }
                            
                            res.insert(key: data.playID, playCountPerSet)
                        }
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
        plays = {}

        for play in complex_script.value:
            play_count_per_set = {}
            for set in play.value.value:
                play_count_per_set[set.key.value] = set.value.value

            plays[play.key.value] = play_count_per_set

    return plays


async def get_account_plays_with_lowest_serial(address):
    script = Script(
        code="""
                import TopShot from 0x0b2a3299cc857e29

                pub fun main(account: Address): {UInt32:{UInt32:UInt32}} {
                    let acct = getAccount(account)

                    let collectionRef = acct.getCapability(/public/MomentCollection)
                                            .borrow<&{TopShot.MomentCollectionPublic}>()!

                    let res: {UInt32:{UInt32:UInt32}} = {}                        

                    for id in collectionRef.getIDs() {
                        // Borrow a reference to the specified moment
                        let token = collectionRef.borrowMoment(id: id)
                            ?? panic("Could not borrow a reference to the specified moment")

                        // Get the moment's metadata to access its play and Set IDs
                        let data = token.data
                        
                        if res.containsKey(data.playID) == false {
                            let playLowestSerial: {UInt32:UInt32} = {}
                            playLowestSerial.insert(key: data.setID, data.serialNumber)
                            res.insert(key: data.playID, playLowestSerial)
                        } else {
                            let playLowestSerial: {UInt32:UInt32} = res[data.playID]!
                            if playLowestSerial.containsKey(data.setID) == false {
                                playLowestSerial.insert(key: data.setID, data.serialNumber)
                            } else {
                                var low: UInt32 = playLowestSerial[data.setID]!
                                if data.serialNumber < low {
                                    playLowestSerial.insert(key: data.setID, data.serialNumber)
                                }
                            }
                            
                            res.insert(key: data.playID, playLowestSerial)
                        }
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
        plays = {}

        for play in complex_script.value:
            play_lowest_serial_per_set = {}
            for set_info in play.value.value:
                play_lowest_serial_per_set[set_info.key.value] = set_info.value.value

            plays[play.key.value] = play_lowest_serial_per_set

    return plays


if __name__ == '__main__':
    result = asyncio.run(get_account_plays_with_lowest_serial("0xad955e5d8047ef82"))
    print(result)
