from __future__ import annotations

from datetime import date

from database.connection import get_connection


def fetch_settlement_candidates(
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    """
    Fetch captured transactions that are eligible for settlement.

    This function is responsible only for retrieving the source data
    required by the settlement simulation.

    Settlement calculations, processor-feed mutations, and
    reconciliation logic belong to later layers.

    A transaction is settlement-eligible only when it has a
    CAPTURED payment attempt.

    The processor attached to that CAPTURED attempt is treated as
    the processor responsible for settlement. This is important for
    transactions that were retried through a different processor.

    Args:
        start_date:
            Optional inclusive transaction simulation date.

        end_date:
            Optional inclusive transaction simulation date.

    Returns:
        A list of dictionaries containing the source attributes
        required by the settlement generator.
    """

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            query = """
                SELECT
                    t.id AS transaction_db_id,
                    t.transaction_id,
                    t.simulation_date,
                    t.merchant_fk,
                    t.amount,
                    t.currency,

                    ca.processor_fk,
                    ca.completed_at AS captured_at,

                    m.merchant_id,
                    m.settlement_cycle,

                    p.processor_id,
                    p.default_processing_fee_percentage,

                    fx.fx_rate

                FROM transactions t

                INNER JOIN LATERAL (
                    SELECT
                        pa.processor_fk,
                        pa.completed_at
                    FROM payment_attempts pa
                    WHERE pa.transaction_fk = t.id
                      AND pa.attempt_status = 'CAPTURED'
                    ORDER BY
                        pa.completed_at DESC,
                        pa.id DESC
                    LIMIT 1
                ) ca ON TRUE

                INNER JOIN merchants m
                    ON m.id = t.merchant_fk

                INNER JOIN processors p
                    ON p.id = ca.processor_fk

                INNER JOIN fx_rates fx
                    ON fx.rate_date = t.simulation_date
                   AND fx.source_currency = t.currency
                   AND fx.target_currency = 'USD'

                WHERE 1 = 1
            """

            parameters = []

            if start_date is not None:
                query += """
                    AND t.simulation_date >= %s
                """
                parameters.append(start_date)

            if end_date is not None:
                query += """
                    AND t.simulation_date <= %s
                """
                parameters.append(end_date)

            query += """
                ORDER BY
                    t.simulation_date,
                    t.id
            """

            cursor.execute(
                query,
                parameters,
            )

            rows = cursor.fetchall()

            return [
                {
                    "transaction_db_id": row[0],
                    "transaction_id": row[1],
                    "simulation_date": row[2],
                    "merchant_fk": row[3],
                    "amount": row[4],
                    "currency": row[5],
                    "processor_fk": row[6],
                    "captured_at": row[7],
                    "merchant_id": row[8],
                    "settlement_cycle": row[9],
                    "processor_id": row[10],
                    "processor_fee_percentage": row[11],
                    "fx_rate": row[12],
                }
                for row in rows
            ]

    finally:
        connection.close()