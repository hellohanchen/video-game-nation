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
    try:
        result = await client.execute_async(query, variable_values={"input": {"username": topshot_username}})
    except TransportQueryError:
        return None, None, None

    return result['getUserProfileByUsername']['publicInfo']['username'], \
           result['getUserProfileByUsername']['publicInfo']['flowAddress'], \
           result['getUserProfileByUsername']['publicInfo']['favoriteTeamID']


if __name__ == '__main__':
    print(get_flow_address('MingDynastyVase'))
