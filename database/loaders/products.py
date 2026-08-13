from database.connection import get_connection


PRODUCT_INSERT_SQL = """
INSERT INTO products (
    product_id,
    merchant_fk,
    product_name,
    product_category,
    base_price,
    currency,
    refundable,
    refund_probability,
    chargeback_probability,
    product_status
)
VALUES (
    %(product_id)s,
    %(merchant_fk)s,
    %(product_name)s,
    %(product_category)s,
    %(base_price)s,
    %(currency)s,
    %(refundable)s,
    %(refund_probability)s,
    %(chargeback_probability)s,
    %(product_status)s
);
"""


def load_products(products: list[dict]) -> int:
    """
    Insert generated product records into PostgreSQL.

    Returns the number of successfully inserted records.
    """

    if not products:
        return 0

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.executemany(
                PRODUCT_INSERT_SQL,
                products,
            )

        connection.commit()

        return len(products)

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()