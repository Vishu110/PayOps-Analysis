from database.connection import get_connection


PAYMENT_METHOD_INSERT_SQL = """
INSERT INTO payment_methods (
    payment_method_id,
    customer_fk,
    issuing_bank_fk,
    payment_method_type,
    card_network,
    card_type,
    card_last_four,
    expiry_month,
    expiry_year,
    is_default,
    payment_method_status
)
VALUES (
    %(payment_method_id)s,
    %(customer_fk)s,
    %(issuing_bank_fk)s,
    %(payment_method_type)s,
    %(card_network)s,
    %(card_type)s,
    %(card_last_four)s,
    %(expiry_month)s,
    %(expiry_year)s,
    %(is_default)s,
    %(payment_method_status)s
);
"""


def load_payment_methods(
    payment_methods: list[dict],
) -> int:
    """
    Insert generated payment-method records
    into PostgreSQL.

    Returns the number of inserted records.
    """

    if not payment_methods:
        return 0

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.executemany(
                PAYMENT_METHOD_INSERT_SQL,
                payment_methods,
            )

        connection.commit()

        return len(payment_methods)

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()