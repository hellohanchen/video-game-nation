import asyncio

from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportQueryError


async def get_set_plays(set_id):
    # Select your transport with a defined url endpoint
    transport = AIOHTTPTransport(url="https://public-api.nbatopshot.com/graphql")

    # Create a GraphQL client using the defined transport
    client = Client(transport=transport, fetch_schema_from_transport=False)

    query = gql(
        """
        query getSet ($input: GetSetInput!) {
            getSet (input: $input) {
                set {
                    id
                    sortID
                    version
                    flowId
                    flowName
                    flowSeriesNumber
                    flowLocked
                    setVisualId
                    plays {
                        id
                        version
                        flowID
                        sortID
                        status
                        stats {
                            playerID
                            playerName
                            firstName
                            lastName
                            jerseyNumber
                            teamAtMoment
                            playCategory
                            quarter
                            dateOfMoment
                        }
                    }
                }
            }
        }
    """
    )

    # Execute the query on the transport
    try:
        result = await client.execute_async(query, variable_values={"input": {"setID": set_id}})
    except Exception as err:
        return None

    return result['getSet']['set']


if __name__ == '__main__':
    print(asyncio.run(get_set_plays('7e3d08f9-061e-4c37-b58f-7b551b6adaab')))
