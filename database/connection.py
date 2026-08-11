import psycopg2

from config.database import (
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
    validate_database_config,
)


def get_connection():
    """
    Create and return a postgreSQL database connection.
    """

    validate_database_config()

    return psycopg2.connect(
        host = DB_HOST,
        port = DB_PORT,
        dbname = DB_NAME,
        user = DB_USER,
        password = DB_PASSWORD
    )