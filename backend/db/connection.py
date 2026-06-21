import os
from psycopg2 import pool
from contextlib import contextmanager

DB_DSN = os.environ.get("DB_DSN", "dbname=credexa user=adityajadhav host=localhost port=5432")

# Create a global connection pool
try:
    db_pool = pool.SimpleConnectionPool(1, 20, DB_DSN)
except Exception as e:
    print(f"Error creating DB pool: {e}")
    db_pool = None

@contextmanager
def get_db_connection():
    if not db_pool:
        import psycopg2
        conn = psycopg2.connect(DB_DSN)
        try:
            yield conn
        finally:
            conn.close()
    else:
        conn = db_pool.getconn()
        try:
            yield conn
        finally:
            db_pool.putconn(conn)
