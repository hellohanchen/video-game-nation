import asyncio

from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportQueryError


async def get_flow_address(topshot_username):
    # Select your transport with a defined url endpoint
    transport = AIOHTTPTransport(url="https://public-api.nbatopshot.com/graphql")

    # Create a GraphQL client using the defined transport
    client = Client(transport=transport, fetch_schema_from_transport=False)

    query = gql(
        """
        query ProfilePage_getUserProfileByUsername($input: getUserProfileByUsernameInput!) {
            getUserProfileByUsername(input: $input) {
                publicInfo {
                  ...UserFragment
                }
            }
        }
    
        fragment UserFragment on UserPublicInfo {
            username
            flowAddress
        }
    """
    )

    # Execute the query on the transport
    try:
        result = await client.execute_async(query, variable_values={"input": {"username": topshot_username}})
    except TransportQueryError:
        return None

    return result['getUserProfileByUsername']['publicInfo']['flowAddress']


async def get_flow_account_info(topshot_username):
    try:
        # Select your transport with a defined url endpoint
        transport = AIOHTTPTransport(url="https://public-api.nbatopshot.com/graphql")

        # Create a GraphQL client using the defined transport
        client = Client(transport=transport, fetch_schema_from_transport=False)

        query = gql(
            """
            query ProfilePage_getUserProfileByUsername($input: getUserProfileByUsernameInput!) {
                getUserProfileByUsername(input: $input) {
                    publicInfo {
                      ...UserFragment
                    }
                }
            }
        
            fragment UserFragment on UserPublicInfo {
                username
                flowAddress
                favoriteTeamID
            }
        """
        )

    # Execute the query on the transport
        result = await client.execute_async(query, variable_values={"input": {"username": topshot_username}})
    except Exception as err:
        return None, None, None, err

    return result['getUserProfileByUsername']['publicInfo']['username'], \
           result['getUserProfileByUsername']['publicInfo']['flowAddress'], \
           result['getUserProfileByUsername']['publicInfo']['favoriteTeamID'], \
           None


async def get_team_leaderboard_rank(address, tid):
    try:
        # Select your transport with a defined url endpoint
        transport = AIOHTTPTransport(url="https://public-api.nbatopshot.com/graphql")

        # Create a GraphQL client using the defined transport
        client = Client(transport=transport, fetch_schema_from_transport=False)

        query = gql(
            """
            query getLeaderboardEntry($input: GetLeaderboardEntryInput!) {
                getLeaderboardEntry(input: $input) {
                    entry {
                        rank
                    }
                }
            }
        """
        )

    # Execute the query on the transport
        result = await client.execute_async(query, variable_values={
            "input": {"kind": "TEAM", "id": tid, "flowAddress": address}
        })
    except Exception as err:
        return None, err

    return result['getLeaderboardEntry']['entry']['rank'], None


if __name__ == '__main__':
    print(asyncio.run(get_team_leaderboard_rank('ad955e5d8047ef82', 1610612741)))
