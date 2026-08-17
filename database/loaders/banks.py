from psycopg2.extras import Json

from database.connection import get_connection


BANK_INSERT_SQL = """
INSERT INTO issuing_banks (
    bank_id,
    bank_name,
    bank_code,
    country_code,
    country_name,
    supported_card_networks,
    bank_status
)
VALUES (
    %(bank_id)s,
    %(bank_name)s,
    %(bank_code)s,
    %(country_code)s,
    %(country_name)s,
    %(supported_card_networks)s,
    %(bank_status)s
);
"""


def load_banks(banks: list[dict]) -> int:
    """
    Insert generated issuing-bank records into PostgreSQL.

    Returns the number of inserted records.
    """

    if not banks:
        return 0

    records = []

    for bank in banks:

        record = bank.copy()

        record["supported_card_networks"] = Json(
            bank["supported_card_networks"]
        )

        records.append(record)

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.executemany(
                BANK_INSERT_SQL,
                records,
            )

        connection.commit()

        return len(records)

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def fetch_banks() -> list[dict]:
    """
    Fetch existing issuing banks from PostgreSQL.

    These records are used as dependencies by
    downstream payment-method generation.
    """

    query = """
        SELECT
            id,
            bank_id,
            bank_name,
            bank_code,
            country_code,
            country_name,
            supported_card_networks,
            bank_status
        FROM issuing_banks
        ORDER BY id;
    """

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(query)

            rows = cursor.fetchall()

            columns = [
                "id",
                "bank_id",
                "bank_name",
                "bank_code",
                "country_code",
                "country_name",
                "supported_card_networks",
                "bank_status",
            ]

            return [
                dict(zip(columns, row))
                for row in rows
            ]

    finally:

        connection.close()
