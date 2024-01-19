import pandas as pd


def rw_db(pool, write_query, read_query, write_objs=None, is_many=False):
    db_conn = None
    try:
        db_conn = pool.get_connection()
        cursor = db_conn.cursor()

        if write_objs is not None:
            if is_many:
                cursor.executemany(write_query, write_objs)
            else:
                cursor.execute(write_query, write_objs)
        else:
            cursor.execute(write_query)

        # Execute SQL query and store results in a pandas dataframe
        df = pd.read_sql(read_query, db_conn)

        # Convert dataframe to a dictionary with headers
        loaded = df.to_dict('records')

        db_conn.commit()
        db_conn.close()
    except Exception as err:
        if db_conn is not None:
            db_conn.close()

        return None, err

    return loaded, None
