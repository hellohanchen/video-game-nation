import logging

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from deprecated.dynamodb.table import Table

logger = logging.getLogger(__name__)


class Players(Table):
    """Encapsulates an Amazon DynamoDB table of user data."""
    def __init__(self, dyn_resource):
        """
        :param: dyn_resource: A Boto3 DynamoDB resource.
        """
        super().__init__(dyn_resource, "players")

    def put_player(self, player_id, full_name, attributes):
        """
        Adds a player to the table
        :param: player_id: The topshot player id
        :param: full_name: The player's full name without punctuation
        :param: attributes: Other player attributes including team, jersey, and salary
        """

        first_name, last_name = split_fullname(full_name)

        try:
            self.table.put_item(
                Item={
                    'id': player_id,
                    'full_name': full_name.lower(),
                    'first_name': first_name.lower(),
                    'last_name': last_name.lower(),
                    'current_team': attributes.get('current_team', ""),
                    'jersey_number': attributes.get('jersey_number', None),
                    'avg_salary': attributes.get('avg_salary', 0),
                    'vgn_salary': attributes.get('avg_salary', 0)
                }
            )
        except ClientError as err:
            logger.error(
                "Couldn't add user %s to table %s. Here's why: %s: %s",
                full_name, self.table_name,
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise

    def query_player_by_name(self, name):
        """
        Queries for players by full name or first/last name

        :param: name: The year to query.
        :return: The list of movies that were released in the specified year.
        """
        try:
            response = self.table.query(
                IndexName="full_name-index",
                KeyConditionExpression=Key('full_name').eq(name.lower())
            )
        except ClientError as err:
            logger.error(
                "Couldn't query for players with name %s. Here's why: %s: %s", name,
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise

        if response['Items'] is not None and len(response['Items']) > 0:
            return response['Items']

        results = []

        try:
            response = self.table.query(
                IndexName="first_name-index",
                KeyConditionExpression=Key('first_name').eq(name.lower())
            )
        except ClientError as err:
            logger.error(
                "Couldn't query for players with name %s. Here's why: %s: %s", name,
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise

        if response['Items'] is not None and len(response['Items']) > 0:
            results.extend(response['Items'])

        try:
            response = self.table.query(
                IndexName="last_name-index",
                KeyConditionExpression=Key('last_name').eq(name.lower())
            )
        except ClientError as err:
            logger.error(
                "Couldn't query for players with name %s. Here's why: %s: %s", name,
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise

        if response['Items'] is not None and len(response['Items']) > 0:
            results.extend(response['Items'])

        return results


def split_fullname(full_name):
    space1 = full_name.find(' ')
    space2 = full_name.find(' ', space1 + 1)

    if space2 == -1:
        return full_name[:space1], full_name[space1 + 1:]
    else:
        return full_name[:space1], full_name[space1 + 1:space2]


def run_scenario(dyn_resource):
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    players = Players(dyn_resource)

    # with open(os.path.abspath("C:\\workspace\\python\\video-game-nation\\topshot\\resource\\players.json"), 'r') as player_file:
    #     data = json.load(player_file)
    #
    #     for player in data["players"]:
    #         players.put_player(player['playerID'], player['label'], {})

    print(players.query_player_by_name("gordon"))


if __name__ == '__main__':
    try:
        session = boto3.Session(profile_name='ddrw01')
        run_scenario(session.resource('dynamodb'))
    except Exception as e:
        print(f"Something went wrong with the demo! Here's what: {e}")


