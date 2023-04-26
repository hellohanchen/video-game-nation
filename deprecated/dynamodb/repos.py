import boto3

from deprecated.dynamodb.users import Users


def get_user_repo():
    session = boto3.Session(profile_name='ddrw01')
    return Users(session.resource('dynamodb'))
