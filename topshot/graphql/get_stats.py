import asyncio

from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportQueryError


async def get_player_stats(player_id):
    # Select your transport with a defined url endpoint
    transport = AIOHTTPTransport(url="https://public-api.nbatopshot.com/graphql")

    # Create a GraphQL client using the defined transport
    client = Client(transport=transport, fetch_schema_from_transport=True)

    query = gql(
        """
        query getPlayerDataWithCurrentStats ($input: GetPlayerDataWithCurrentStatsInput) {
            getPlayerDataWithCurrentStats (input: $input) {
                playerData {
                    jerseyNumber
                    position
                    height
                    weight
                    currentTeamName
                    currentTeamId
                    firstName
                    lastName
                    birthplace
                    birthdate
                    yearsExperience
                    teamsPlayedFor
                }
                playerSeasonAverageScores {
                    minutes
                    blocks
                    points
                    steals
                    assists
                    rebounds
                    turnovers
                    plusMinus
                    flagrantFouls
                    personalFouls
                    technicalFouls
                    twoPointsMade
                    blockedAttempts
                    fieldGoalsMade
                    freeThrowsMade
                    threePointsMade
                    defensiveRebounds
                    offensiveRebounds
                    pointsOffTurnovers
                    twoPointsAttempted
                    assistTurnoverRatio
                    fieldGoalsAttempted
                    freeThrowsAttempted
                    twoPointsPercentage
                    fieldGoalsPercentage
                    freeThrowsPercentage
                    threePointsAttempted
                    threePointsPercentage
                    efficiency
                    true_shooting_attempts
                    points_in_paint_made
                    points_in_paint_attempted
                    points_in_paint
                    fouls_drawn
                    offensive_fouls
                    fast_break_points
                    fast_break_points_attempted
                    fast_break_points_made
                    second_chance_points
                    second_chance_points_attempted
                    second_chance_points_made
                }
            }
        }
    """
    )

    # Execute the query on the transport
    try:
        result = await client.execute_async(query, variable_values={"input": {"nbaPlayerID": player_id}})
    except:
        return None

    return result['getPlayerDataWithCurrentStats']


if __name__ == '__main__':
    print(asyncio.run(get_player_stats('1629029')))
