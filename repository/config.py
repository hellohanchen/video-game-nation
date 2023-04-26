import mysql.connector.pooling

from repository import DB_USERNAME, DB_PASSWORD, MYSQL_ENDPOINT_URL

config = {
    'user': DB_USERNAME,
    'password': DB_PASSWORD,
    'host': MYSQL_ENDPOINT_URL,
    'database': 'vgn'
}

CNX_POOL = mysql.connector.pooling.MySQLConnectionPool(pool_name='vgnPool', pool_size=5, **config)
