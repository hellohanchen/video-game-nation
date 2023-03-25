import time

from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

def get_low_asks(result_dict):
    price_data = result_dict['searchMomentListings']['data']['searchSummary']['data']['data']
    res = {}

    for price in price_data:
        res[int(price['play']['flowID'])] = int(float(price['priceRange']['min']))

    return res


async def get_listing_prices(set_id, player_ids, team_ids):
    # Select your transport with a defined url endpoint
    transport = AIOHTTPTransport(url="https://public-api.nbatopshot.com/graphql")

    # Create a GraphQL client using the defined transport
    client = Client(transport=transport, fetch_schema_from_transport=True)

    print("{}: Set: {}, Plays: {}...".format(time.strftime("%H:%M:%S", time.localtime()), set_id, ','.join(player_ids)))

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
                        priceRange {
                          min
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
      "byPrice": { "min": None, "max": None },
      "byPower": { "min": None, "max": None },
      "bySerialNumber": { "min": None, "max": None },
      "byGameDate": { "start": None, "end": None },
      "byCreatedAt": { "start": None, "end": None },
      "byPrimaryPlayerPosition": [],
      "bySets": [ set_id ],
      "bySeries": [  ],
      "bySetVisuals": [ ],
      "byPlayStyle": [ ],
      "bySkill": [],
      "byPlayers": player_ids,
      "byTagNames": [],
      "byTeams": team_ids,
      "byListingType": [ "BY_USERS" ],
      "searchInput": { "pagination": { "cursor": "", "direction": "RIGHT", "limit": 12 } },
      "orderBy": "UPDATED_AT_DESC"
    }
    result = await client.execute_async(query, variable_values=input_variables)

    prices = get_low_asks(result)

    return prices


if __name__ == '__main__':
    print(get_listing_prices("208ae30a-a4fe-42d4-9e51-e6fd1ad2a7a9", ["203482"]))
