import os

from dotenv import load_dotenv


load_dotenv()
DB_USERNAME = os.getenv('MYSQL_DB_USERNAME')
DB_PASSWORD = os.getenv('MYSQL_DB_PASSWORD')

MYSQL_ENDPOINT_URL = 'vgn-db-01.cd6mswkom4ku.us-west-1.rds.amazonaws.com'
