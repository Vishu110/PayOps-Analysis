from database.connection import get_connection


def fetch_transaction_dependencies() -> dict:
    """
    Fetch all master-data dependencies required by the
    transaction generator.

    Returns:
        dict containing customers, merchants, products,
        payment methods, and processors.
    """

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            # ----------------------------------------------------------
            # Customers
            # ----------------------------------------------------------

            cursor.execute(
                """
                SELECT
                    id,
                    customer_id,
                    country_code,
                    country_name,
                    preferred_currency,
                    risk_segment,
                    customer_status,
                    signup_date,
                    timezone
                FROM customers
                ORDER BY id;
                """
            )

            customer_rows = cursor.fetchall()

            customers = [
                {
                    "id": row[0],
                    "customer_id": row[1],
                    "country_code": row[2],
                    "country_name": row[3],
                    "preferred_currency": row[4],
                    "risk_segment": row[5],
                    "customer_status": row[6],
                    "signup_date": row[7],
                    "timezone": row[8],
                }
                for row in customer_rows
            ]

            # ----------------------------------------------------------
            # Merchants
            # ----------------------------------------------------------

            cursor.execute(
                """
                SELECT
                    id,
                    merchant_id,
                    merchant_name,
                    merchant_category,
                    size_segment,
                    country_code,
                    country_name,
                    default_currency,
                    preferred_processor_fk,
                    settlement_cycle,
                    risk_segment,
                    merchant_status,
                    onboarded_date
                FROM merchants
                ORDER BY id;
                """
            )

            merchant_rows = cursor.fetchall()

            merchants = [
                {
                    "id": row[0],
                    "merchant_id": row[1],
                    "merchant_name": row[2],
                    "merchant_category": row[3],
                    "size_segment": row[4],
                    "country_code": row[5],
                    "country_name": row[6],
                    "default_currency": row[7],
                    "preferred_processor_fk": row[8],
                    "settlement_cycle": row[9],
                    "risk_segment": row[10],
                    "merchant_status": row[11],
                    "onboarded_date": row[12],
                }
                for row in merchant_rows
            ]

            # ----------------------------------------------------------
            # Products
            # ----------------------------------------------------------

            cursor.execute(
                """
                SELECT
                    id,
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
                FROM products
                ORDER BY id;
                """
            )

            product_rows = cursor.fetchall()

            products = [
                {
                    "id": row[0],
                    "product_id": row[1],
                    "merchant_fk": row[2],
                    "product_name": row[3],
                    "product_category": row[4],
                    "base_price": row[5],
                    "currency": row[6],
                    "refundable": row[7],
                    "refund_probability": row[8],
                    "chargeback_probability": row[9],
                    "product_status": row[10],
                }
                for row in product_rows
            ]

            # ----------------------------------------------------------
            # Payment methods
            # ----------------------------------------------------------

            cursor.execute(
                """
                SELECT
                    id,
                    payment_method_id,
                    customer_fk,
                    issuing_bank_fk,
                    payment_method_type,
                    card_network,
                    card_type,
                    expiry_month,
                    expiry_year,
                    is_default,
                    payment_method_status
                FROM payment_methods
                ORDER BY id;
                """
            )

            payment_method_rows = cursor.fetchall()

            payment_methods = [
                {
                    "id": row[0],
                    "payment_method_id": row[1],
                    "customer_fk": row[2],
                    "issuing_bank_fk": row[3],
                    "payment_method_type": row[4],
                    "card_network": row[5],
                    "card_type": row[6],
                    "expiry_month": row[7],
                    "expiry_year": row[8],
                    "is_default": row[9],
                    "payment_method_status": row[10],
                }
                for row in payment_method_rows
            ]

            # ----------------------------------------------------------
            # Processors
            # ----------------------------------------------------------

            cursor.execute(
                """
                SELECT
                    id,
                    processor_id,
                    processor_name,
                    supported_regions,
                    supported_card_networks,
                    processor_status
                FROM processors
                ORDER BY id;
                """
            )

            processor_rows = cursor.fetchall()

            processors = [
                {
                    "id": row[0],
                    "processor_id": row[1],
                    "processor_name": row[2],
                    "supported_regions": row[3],
                    "supported_card_networks": row[4],
                    "processor_status": row[5],
                }
                for row in processor_rows
            ]

            return {
                "customers": customers,
                "merchants": merchants,
                "products": products,
                "payment_methods": payment_methods,
                "processors": processors,
            }

    finally:
        connection.close()