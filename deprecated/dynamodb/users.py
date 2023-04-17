import logging

import boto3
from botocore.exceptions import ClientError

from deprecated.dynamodb.table import Table

logger = logging.getLogger(__name__)


class Users(Table):
    """Encapsulates an Amazon DynamoDB table of user data."""
    def __init__(self, dyn_resource):
        """
        :param dyn_resource: A Boto3 DynamoDB resource.
        """
        super().__init__(dyn_resource, "users")

    def put_user(self, user_id, topshot_username):
        """
        Adds a user to the table.
        :param user_id: The discord snowflake id of user
        :param topshot_username: The username of user's topshot account
        """
        try:
            self.table.put_item(
                Item={
                    'id': user_id,
                    'topshot_username': topshot_username
                }
            )
        except ClientError as err:
            logger.error(
                "Couldn't add user %s to table %s. Here's why: %s: %s",
                topshot_username, self.table_name,
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise


def run_scenario(dyn_resource):
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    print('-'*88)
    print("Welcome to the Amazon DynamoDB getting started demo.")
    print('-'*88)

    users = Users(dyn_resource)


if __name__ == '__main__':
    try:
        session = boto3.Session(profile_name='ddrw01')
        run_scenario(session.resource('dynamodb'))
    except Exception as e:
        print(f"Something went wrong with the demo! Here's what: {e}")
