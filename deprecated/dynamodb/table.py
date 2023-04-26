import logging

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class Table:
    """Encapsulates an Amazon DynamoDB table of user data."""
    def __init__(self, dyn_resource, table_name):
        """
        :param dyn_resource: A Boto3 DynamoDB resource.
        """
        self.dyn_resource = dyn_resource
        self.table = None
        self.table_name = table_name
        self.exist = self.__exists()

    def __exists(self):
        """
        Determines whether a table exists. As a side effect, stores the table in
        a member variable.
        :return: True when the table exists; otherwise, False.
        """
        try:
            table = self.dyn_resource.Table(self.table_name)
            table.load()
            exists = True
        except ClientError as err:
            if err.response['Error']['Code'] == 'ResourceNotFoundException':
                exists = False
            else:
                logger.error(
                    "Couldn't check for existence of %s. Here's why: %s: %s",
                    self.table_name,
                    err.response['Error']['Code'], err.response['Error']['Message'])
                raise
        else:
            self.table = table
        return exists
