from database.connection import get_connection


MERCHANT_INSERT_SQL = """
INSERT INTO merchants (
    merchant_id,
    merchant_name,
    legal_name,
    merchant_category,
    size_segment,
    country_code,
    country_name,
    default_currency,
    preferred_processor_fk,
    settlement_cycle,
    default_processing_fee_percentage,
    risk_segment,
    merchant_status,
    onboarded_date
)
VALUES (
    %(merchant_id)s,
    %(merchant_name)s,
    %(legal_name)s,
    %(merchant_category)s,
    %(size_segment)s,
    %(country_code)s,
    %(country_name)s,
    %(default_currency)s,
    %(preferred_processor_fk)s,
    %(settlement_cycle)s,
    %(default_processing_fee_percentage)s,
    %(risk_segment)s,
    %(merchant_status)s,
    %(onboarded_date)s
);
"""


def load_merchants(merchants: list[dict]) -> int:
    """
    Insert generated merchant records into PostgreSQL.

    Returns the number of successfully inserted records.
    """

    if not merchants:
        return 0

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.executemany(
                MERCHANT_INSERT_SQL,
                merchants,
            )

        connection.commit()

        return len(merchants)

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()


def fetch_merchants() -> list[dict]:
    """
    Fetch existing merchants from PostgreSQL.

    These records are used as dependencies by
    downstream product generation.
    """

    query = """
        SELECT
            id,
            merchant_id,
            merchant_name,
            merchant_category,
            size_segment,
            country_code,
            country_name,
            default_currency
        FROM merchants
        ORDER BY id;
    """

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(query)

            rows = cursor.fetchall()

            columns = [
                "id",
                "merchant_id",
                "merchant_name",
                "merchant_category",
                "size_segment",
                "country_code",
                "country_name",
                "default_currency",
            ]

            return [
                dict(zip(columns, row))
                for row in rows
            ]

    finally:

        connection.close()