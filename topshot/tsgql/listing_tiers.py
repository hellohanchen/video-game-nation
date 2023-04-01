import asyncio

from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport


def get_tiers(graphql_response):
    listing_data = graphql_response['searchMomentListings']['data']['searchSummary']['data']['data']
    res = []

    for listing in listing_data:
        res.append(listing['set']['setVisualId'])

    return res


async def get_listing_tiers(series, player_id):
    # Select your transport with a defined url endpoint
    transport = AIOHTTPTransport(url="https://public-api.nbatopshot.com/graphql")

    # Create a GraphQL client using the defined transport
    client = Client(transport=transport, fetch_schema_from_transport=True)

    query = gql("""
        query SearchMomentListingsDefault($byPlayers: [ID], $byTagNames: [String!], $byTeams: [ID], $byPrice: PriceRangeFilterInput, $orderBy: MomentListingSortType, $byGameDate: DateRangeFilterInput, $byCreatedAt: DateRangeFilterInput, $byListingType: [MomentListingType], $bySets: [ID], $bySeries: [ID], $bySetVisuals: [VisualIdType], $byPrimaryPlayerPosition: [PlayerPosition], $bySerialNumber: IntegerRangeFilterInput, $searchInput: BaseSearchInput!) {
          searchMomentListings(input: {filters: {byPlayers: $byPlayers, byTagNames: $byTagNames, byGameDate: $byGameDate, byCreatedAt: $byCreatedAt, byTeams: $byTeams, byPrice: $byPrice, byListingType: $byListingType, byPrimaryPlayerPosition: $byPrimaryPlayerPosition, bySets: $bySets, bySeries: $bySeries, bySetVisuals: $bySetVisuals, bySerialNumber: $bySerialNumber}, sortBy: $orderBy, searchInput: $searchInput}) {
            data {
              searchSummary {
                data {
                  ... on MomentListings {
                    data {
                      ... on MomentListing {
                        play {
                          flowID
                          stats {
                            playerName
                            playerID
                          }
                        }
                        set {
                          setVisualId
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
    """
                )

    # Execute the query on the transport
    input_variables = {
        "byPrice": {"min": None, "max": None},
        "byPower": {"min": None, "max": None},
        "bySerialNumber": {"min": None, "max": None},
        "byGameDate": {"start": None, "end": None},
        "byCreatedAt": {"start": None, "end": None},
        "byPrimaryPlayerPosition": [],
        "bySets": [],
        "bySeries": [series],
        "bySetVisuals": [],
        "byPlayStyle": [],
        "bySkill": [],
        "byPlayers": [player_id],
        "byTagNames": [],
        "byTeams": [],
        "byListingType": ["BY_USERS"],
        "searchInput": {"pagination": {"cursor": "", "direction": "RIGHT", "limit": 12}},
        "orderBy": "UPDATED_AT_DESC"
    }
    result = await client.execute_async(query, variable_values=input_variables)

    tiers = get_tiers(result)

    return tiers


if __name__ == '__main__':
    t = asyncio.run(get_listing_tiers(5, 1629029))
    print(t)
