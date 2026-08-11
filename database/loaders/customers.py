from database.connection import get_connection

CUSTOMER_INSERT_SQL = """
INSERT INTO customers(
    customer_id,
    first_name,
    last_name,
    email,
    phone,
    country_code,
    country_name,
    state,
    city,
    timezone,
    preferred_currency,
    risk_segment,
    customer_status,
    signup_date
)

VALUES (
    %(customer_id)s,
    %(first_name)s,
    %(last_name)s,
    %(email)s,
    %(phone)s,
    %(country_code)s,
    %(country_name)s,
    %(state)s,
    %(city)s,
    %(timezone)s,
    %(preferred_currency)s,
    %(risk_segment)s,
    %(customer_status)s,
    %(signup_date)s
);
"""


def load_customers(customers: list[dict]) -> int:
    """
    Insert generated customer records into PostgreSQL.
    Returns the number of successfully inserted records.
    """

    if not customers:
        return 0

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.executemany(
                CUSTOMER_INSERT_SQL,
                customers,
            )

        connection.commit()
        return len(customers)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()