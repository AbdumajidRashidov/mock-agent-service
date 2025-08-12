import os
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv
import logging
import urllib.parse

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "numeo_agents")
MAX_DB_CONNECTIONS = int(os.getenv("MAX_DB_CONNECTIONS", 50))
DB_PASSWORD_ENCODED = urllib.parse.quote(DB_PASSWORD)

_pool = None


def get_pool():
    global _pool
    if _pool is None:
        dsn = f"postgresql://{DB_USER}:{DB_PASSWORD_ENCODED}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        _pool = ThreadedConnectionPool(minconn=1, maxconn=MAX_DB_CONNECTIONS, dsn=dsn)
        logger.info("Database connection pool created.")
    return _pool


class get_connection:
    def __enter__(self):
        self.conn = get_pool().getconn()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        get_pool().putconn(self.conn)


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS migrations (
                    id VARCHAR PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """
            )
            conn.commit()
    logger.info("Database initialized.")


# if __name__ == "__main__":
#     init_db()
