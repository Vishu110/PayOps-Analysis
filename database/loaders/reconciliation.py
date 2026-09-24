from __future__ import annotations

from datetime import date

from database.connection import get_connection


class ReconciliationLoader:
    """
    Persist settlement reconciliation results for one simulation date.

    Design:
        1. Identify the latest captured attempt for each transaction.
        2. Materialize the expected settlement population into a temporary table.
        3. Materialize the processor settlement feed into a temporary table.
        4. Index both temporary tables for fast reconciliation joins.
        5. Insert the reconciliation result into the persistent table.
        6. Validate the fundamental reconciliation invariant.

    The temporary tables deliberately exist only for the duration of the
    transaction. They prevent repeated evaluation of large CTEs and give
    PostgreSQL explicit indexes on the two keys used by reconciliation.

    Matching rule:
        actual.merchant_reference = expected.transaction_id

    Processor identity is deliberately NOT part of the matching key.
    A processor mismatch is itself a reconciliation exception and therefore
    must remain observable.
    """

    def __init__(self, connection=None):
        """
        Initialize the loader.

        Args:
            connection:
                Optional existing PostgreSQL connection.

                If supplied, the caller owns the transaction.

                If omitted, reconcile_date() creates and commits its own
                database transaction.
        """

        self.connection = connection

    # ==================================================================
    # Public API
    # ==================================================================

    def reconcile_date(
        self,
        simulation_date: date,
    ) -> dict:
        """
        Reconcile settlement activity for one simulation date.

        The operation is idempotent:
        existing reconciliation results for the supplied simulation date
        are deleted and rebuilt atomically.

        Args:
            simulation_date:
                Simulation date to reconcile.

        Returns:
            Dictionary containing reconciliation statistics.

        Raises:
            TypeError:
                If simulation_date is not a datetime.date.
        """

        if not isinstance(simulation_date, date):
            raise TypeError(
                "simulation_date must be a datetime.date instance."
            )

        owns_connection = self.connection is None

        connection = (
            get_connection()
            if owns_connection
            else self.connection
        )

        try:
            with connection.cursor() as cursor:

                # ======================================================
                # 1. Remove previous results
                # ======================================================

                cursor.execute(
                    """
                    DELETE FROM reconciliation_settlements
                    WHERE simulation_date = %s;
                    """,
                    (simulation_date,),
                )

                deleted_count = cursor.rowcount

                # ======================================================
                # 2. Build expected settlement population
                # ======================================================
                #
                # IMPORTANT:
                #
                # This is deliberately materialized into a temporary
                # table rather than kept as a CTE.
                #
                # The expected population is used by both sides of the
                # reconciliation logic. Materializing it means:
                #
                #   transactions
                #       +
                #   latest captured attempts
                #       +
                #   merchant
                #       +
                #   processor
                #       +
                #   FX
                #
                # are evaluated exactly once.
                #
                # The direct calendar mapping guarantees one settlement
                # date for every settlement cycle.
                # ======================================================

                cursor.execute(
                    """
                    CREATE TEMP TABLE tmp_reconciliation_expected
                    ON COMMIT DROP
                    AS
                    WITH latest_captures AS (
                        SELECT DISTINCT ON (pa.transaction_fk)
                            pa.transaction_fk,
                            pa.processor_fk,
                            pa.completed_at
                        FROM payment_attempts pa
                        INNER JOIN transactions t
                            ON t.id = pa.transaction_fk
                        WHERE pa.attempt_status = 'CAPTURED'
                          AND t.simulation_date = %s
                        ORDER BY
                            pa.transaction_fk,
                            pa.completed_at DESC,
                            pa.id DESC
                    ),

                    settlement_calendar AS (
                        /*
                         * T+0:
                         *     transaction date itself, including weekends.
                         *
                         * T+1 onward:
                         *     Monday-Friday business days only.
                         *
                         * This produces exactly one calendar date for
                         * every settlement-cycle value.
                         */

                        SELECT
                            %s::date AS calendar_date,
                            0 AS business_days_after_transaction

                        UNION ALL

                        SELECT
                            business_date AS calendar_date,
                            ROW_NUMBER() OVER (
                                ORDER BY business_date
                            ) AS business_days_after_transaction
                        FROM (
                            SELECT
                                calendar_date AS business_date
                            FROM generate_series(
                                %s::date + INTERVAL '1 day',
                                %s::date + INTERVAL '45 days',
                                INTERVAL '1 day'
                            ) AS calendar_dates(calendar_date)
                            WHERE EXTRACT(
                                ISODOW FROM calendar_date
                            ) BETWEEN 1 AND 5
                        ) business_days
                    )

                    SELECT
                        t.id AS transaction_fk,
                        t.transaction_id,
                        t.merchant_fk,
                        lc.processor_fk,
                        t.simulation_date,
                        t.simulation_date AS transaction_date,
                        sc.calendar_date AS expected_settlement_date,

                        /*
                         * Expected gross.
                         */
                        ROUND(
                            (
                                t.amount * fx.fx_rate
                            )::numeric,
                            2
                        ) AS expected_gross_amount_usd,

                        /*
                         * Expected fee.
                         *
                         * Fee is calculated from the rounded USD gross,
                         * matching the settlement expected-value logic.
                         */
                        ROUND(
                            (
                                ROUND(
                                    (
                                        t.amount * fx.fx_rate
                                    )::numeric,
                                    2
                                )
                                * p.default_processing_fee_percentage
                                / 100
                            )::numeric,
                            2
                        ) AS expected_fee_amount_usd,

                        /*
                         * Expected net.
                         */
                        ROUND(
                            (
                                ROUND(
                                    (
                                        t.amount * fx.fx_rate
                                    )::numeric,
                                    2
                                )
                                -
                                ROUND(
                                    (
                                        ROUND(
                                            (
                                                t.amount * fx.fx_rate
                                            )::numeric,
                                            2
                                        )
                                        * p.default_processing_fee_percentage
                                        / 100
                                    )::numeric,
                                    2
                                )
                            )::numeric,
                            2
                        ) AS expected_net_amount_usd

                    FROM transactions t

                    INNER JOIN latest_captures lc
                        ON lc.transaction_fk = t.id

                    INNER JOIN merchants m
                        ON m.id = t.merchant_fk

                    INNER JOIN processors p
                        ON p.id = lc.processor_fk

                    INNER JOIN fx_rates fx
                        ON fx.rate_date = t.simulation_date
                       AND fx.source_currency = t.currency
                       AND fx.target_currency = 'USD'

                    INNER JOIN settlement_calendar sc
                        ON sc.business_days_after_transaction =
                           m.settlement_cycle

                    WHERE t.simulation_date = %s;
                    """,
                    (
                        simulation_date,
                        simulation_date,
                        simulation_date,
                        simulation_date,
                        simulation_date,
                    ),
                )

                # This is a small per-date table compared with the
                # underlying transaction/attempt population.
                cursor.execute(
                    """
                    CREATE UNIQUE INDEX tmp_reconciliation_expected_txn_idx
                    ON tmp_reconciliation_expected (transaction_id);
                    """
                )

                # ======================================================
                # 3. Capture expected population count
                # ======================================================

                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM tmp_reconciliation_expected;
                    """
                )

                captured_transaction_count = cursor.fetchone()[0]

                # ======================================================
                # 4. Build actual processor population
                # ======================================================
                #
                # Restrict to:
                #
                #     journal_type = SETTLED
                #     transaction_date = simulation_date
                #
                # This prevents unrelated processor history from entering
                # the reconciliation workload.
                # ======================================================

                cursor.execute(
                    """
                    CREATE TEMP TABLE tmp_reconciliation_actual
                    ON COMMIT DROP
                    AS
                    SELECT
                        se.id AS settlement_entry_fk,
                        se.settlement_entry_id,
                        se.merchant_reference,
                        se.processor_transaction_reference,
                        se.processor_fk,
                        se.transaction_date,
                        se.expected_settlement_date,
                        se.actual_settlement_date,
                        se.gross_amount_usd,
                        se.fee_amount_usd,
                        se.net_amount_usd,
                        se.processor_status
                    FROM settlement_entries se
                    WHERE se.journal_type = 'SETTLED'
                      AND se.transaction_date = %s;
                    """,
                    (simulation_date,),
                )

                cursor.execute(
                    """
                    CREATE INDEX tmp_reconciliation_actual_reference_idx
                    ON tmp_reconciliation_actual (merchant_reference);
                    """
                )

                # PostgreSQL temporary tables do not automatically receive
                # useful optimizer statistics immediately after creation.
                # ANALYZE is cheap because these tables contain only one
                # simulation date.
                cursor.execute(
                    """
                    ANALYZE tmp_reconciliation_expected;
                    """
                )

                cursor.execute(
                    """
                    ANALYZE tmp_reconciliation_actual;
                    """
                )

                # ======================================================
                # 5. Reconcile and persist
                # ======================================================
                #
                # Two logical populations are inserted:
                #
                # A. Internal transaction side
                #
                #    expected LEFT JOIN actual
                #
                #    This identifies:
                #       MATCHED
                #       AMOUNT_MISMATCH
                #       MISSING_SETTLEMENT
                #       TIMING_EXCEPTION
                #       STATUS_MISMATCH
                #       PROCESSOR_MISMATCH
                #
                # B. Processor-only side
                #
                #    actual LEFT JOIN expected
                #
                #    This identifies:
                #       UNMATCHED_PROCESSOR_ENTRY
                #
                # Processor is intentionally not part of the join.
                # ======================================================

                reconciliation_sql = """
                    INSERT INTO reconciliation_settlements (

                        simulation_date,

                        transaction_fk,
                        settlement_entry_fk,

                        transaction_id,
                        settlement_entry_id,
                        processor_transaction_reference,

                        expected_processor_fk,
                        expected_merchant_fk,

                        transaction_date,
                        expected_settlement_date,

                        expected_gross_amount_usd,
                        expected_fee_amount_usd,
                        expected_net_amount_usd,

                        actual_processor_fk,
                        actual_settlement_date,

                        actual_gross_amount_usd,
                        actual_fee_amount_usd,
                        actual_net_amount_usd,

                        processor_status,

                        reconciliation_status,
                        amount_mismatch_reason
                    )

                    SELECT
                        %s,

                        e.transaction_fk,
                        a.settlement_entry_fk,

                        e.transaction_id,
                        a.settlement_entry_id,
                        a.processor_transaction_reference,

                        e.processor_fk,
                        e.merchant_fk,

                        e.transaction_date,
                        e.expected_settlement_date,

                        e.expected_gross_amount_usd,
                        e.expected_fee_amount_usd,
                        e.expected_net_amount_usd,

                        a.processor_fk,
                        a.actual_settlement_date,

                        a.gross_amount_usd,
                        a.fee_amount_usd,
                        a.net_amount_usd,

                        a.processor_status,

                        CASE

                            WHEN a.settlement_entry_fk IS NULL
                                THEN 'MISSING_SETTLEMENT'

                            WHEN a.processor_fk <> e.processor_fk
                                THEN 'PROCESSOR_MISMATCH'

                            WHEN a.processor_status = 'REVERSED'
                                THEN 'STATUS_MISMATCH'

                            WHEN (
                                a.gross_amount_usd
                                    <> e.expected_gross_amount_usd
                                OR a.fee_amount_usd
                                    <> e.expected_fee_amount_usd
                                OR a.net_amount_usd
                                    <> e.expected_net_amount_usd
                            )
                                THEN 'AMOUNT_MISMATCH'

                            WHEN a.actual_settlement_date
                                    <> e.expected_settlement_date
                                THEN 'TIMING_EXCEPTION'

                            ELSE 'MATCHED'

                        END AS reconciliation_status,

                        CASE

                            WHEN a.settlement_entry_fk IS NULL
                                THEN NULL

                            WHEN NOT (
                                a.gross_amount_usd
                                    <> e.expected_gross_amount_usd
                                OR a.fee_amount_usd
                                    <> e.expected_fee_amount_usd
                                OR a.net_amount_usd
                                    <> e.expected_net_amount_usd
                            )
                                THEN NULL

                            /*
                             * Same gross, different fee.
                             */
                            WHEN (
                                a.gross_amount_usd
                                    = e.expected_gross_amount_usd
                                AND a.fee_amount_usd
                                    <> e.expected_fee_amount_usd
                            )
                                THEN 'PROCESSOR_FEE_VARIANCE'

                            /*
                             * Gross is lower while expected fee is
                             * preserved.
                             */
                            WHEN (
                                a.gross_amount_usd
                                    < e.expected_gross_amount_usd
                                AND a.fee_amount_usd
                                    = e.expected_fee_amount_usd
                            )
                                THEN 'PARTIAL_SETTLEMENT'

                            /*
                             * Gross and fee changed but net is effectively
                             * unchanged.
                             */
                            WHEN (
                                a.gross_amount_usd
                                    <> e.expected_gross_amount_usd
                                AND a.fee_amount_usd
                                    <> e.expected_fee_amount_usd
                                AND ABS(
                                    a.net_amount_usd
                                    - e.expected_net_amount_usd
                                ) <= 0.01
                            )
                                THEN 'FX_DIFFERENCE'

                            /*
                             * Small financial difference.
                             */
                            WHEN (
                                ABS(
                                    a.gross_amount_usd
                                    - e.expected_gross_amount_usd
                                ) <= 0.01
                                AND ABS(
                                    a.fee_amount_usd
                                    - e.expected_fee_amount_usd
                                ) <= 0.01
                            )
                                THEN 'ROUNDING_DIFFERENCE'

                            ELSE 'UNEXPLAINED_DIFFERENCE'

                        END AS amount_mismatch_reason

                    FROM tmp_reconciliation_expected e

                    LEFT JOIN tmp_reconciliation_actual a
                        ON a.merchant_reference = e.transaction_id

                    UNION ALL

                    SELECT
                        %s,

                        NULL,
                        a.settlement_entry_fk,

                        NULL,
                        a.settlement_entry_id,
                        a.processor_transaction_reference,

                        NULL,
                        NULL,

                        a.transaction_date,
                        a.expected_settlement_date,

                        NULL,
                        NULL,
                        NULL,

                        a.processor_fk,
                        a.actual_settlement_date,

                        a.gross_amount_usd,
                        a.fee_amount_usd,
                        a.net_amount_usd,

                        a.processor_status,

                        'UNMATCHED_PROCESSOR_ENTRY',
                        NULL

                    FROM tmp_reconciliation_actual a

                    LEFT JOIN tmp_reconciliation_expected e
                        ON e.transaction_id = a.merchant_reference

                    WHERE e.transaction_fk IS NULL;
                """

                cursor.execute(
                    reconciliation_sql,
                    (
                        simulation_date,
                        simulation_date,
                    ),
                )

                inserted_count = cursor.rowcount

                # ======================================================
                # 6. Validate fundamental row-count invariant
                # ======================================================
                #
                # The persistent table has a unique constraint on:
                #
                #     (simulation_date, transaction_fk)
                #
                # Therefore duplicate transaction-side rows cannot be
                # committed. The expected temporary table also has a
                # unique transaction_id index.
                #
                # We therefore do not perform an expensive GROUP BY scan
                # just to prove something already protected by schema.
                # ======================================================

                cursor.execute(
                    """
                    SELECT
                        COUNT(*) AS total_count,

                        COUNT(*) FILTER (
                            WHERE reconciliation_status = 'MATCHED'
                        ) AS matched_count,

                        COUNT(*) FILTER (
                            WHERE reconciliation_status = 'AMOUNT_MISMATCH'
                        ) AS amount_mismatch_count,

                        COUNT(*) FILTER (
                            WHERE reconciliation_status =
                                  'MISSING_SETTLEMENT'
                        ) AS missing_settlement_count,

                        COUNT(*) FILTER (
                            WHERE reconciliation_status =
                                  'TIMING_EXCEPTION'
                        ) AS timing_exception_count,

                        COUNT(*) FILTER (
                            WHERE reconciliation_status =
                                  'STATUS_MISMATCH'
                        ) AS status_mismatch_count,

                        COUNT(*) FILTER (
                            WHERE reconciliation_status =
                                  'PROCESSOR_MISMATCH'
                        ) AS processor_mismatch_count,

                        COUNT(*) FILTER (
                            WHERE reconciliation_status =
                                  'UNMATCHED_PROCESSOR_ENTRY'
                        ) AS unmatched_processor_entry_count

                    FROM reconciliation_settlements
                    WHERE simulation_date = %s;
                    """,
                    (simulation_date,),
                )

                (
                    total_count,
                    matched_count,
                    amount_mismatch_count,
                    missing_settlement_count,
                    timing_exception_count,
                    status_mismatch_count,
                    processor_mismatch_count,
                    unmatched_processor_entry_count,
                ) = cursor.fetchone()

                transaction_side_count = (
                    total_count
                    - unmatched_processor_entry_count
                )

                # Every captured transaction must produce exactly one
                # transaction-side reconciliation result.
                if transaction_side_count != captured_transaction_count:
                    raise RuntimeError(
                        "Transaction-side reconciliation count does not "
                        "match captured transaction count. "
                        f"Reconciliation={transaction_side_count}, "
                        f"Captured={captured_transaction_count}."
                    )

                # The inserted population must contain at least every
                # expected transaction. Processor-only entries may increase
                # the total.
                if inserted_count < captured_transaction_count:
                    raise RuntimeError(
                        "Reconciliation row count is smaller than the "
                        "captured transaction population. "
                        f"Inserted={inserted_count}, "
                        f"Captured={captured_transaction_count}."
                    )

                # ======================================================
                # 7. Commit
                # ======================================================

                if owns_connection:
                    connection.commit()

                return {
                    "simulation_date": simulation_date,
                    "deleted_count": deleted_count,
                    "captured_transaction_count":
                        captured_transaction_count,
                    "reconciliation_count": total_count,
                    "matched_count": matched_count,
                    "amount_mismatch_count":
                        amount_mismatch_count,
                    "missing_settlement_count":
                        missing_settlement_count,
                    "timing_exception_count":
                        timing_exception_count,
                    "status_mismatch_count":
                        status_mismatch_count,
                    "processor_mismatch_count":
                        processor_mismatch_count,
                    "unmatched_processor_entry_count":
                        unmatched_processor_entry_count,
                }

        except Exception:

            if owns_connection:
                connection.rollback()

            raise

        finally:

            if owns_connection:
                connection.close()


# ======================================================================
# Convenience function
# ======================================================================


def reconcile_settlements(
    simulation_date: date,
) -> dict:
    """
    Convenience wrapper for one-date reconciliation.

    Creates its own database connection and commits the reconciliation
    transaction when successful.
    """

    loader = ReconciliationLoader()

    return loader.reconcile_date(
        simulation_date=simulation_date
    )


# ======================================================================
# CLI
# ======================================================================


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Build settlement reconciliation results "
            "for one simulation date."
        )
    )

    parser.add_argument(
        "simulation_date",
        help="Simulation date in YYYY-MM-DD format.",
    )

    args = parser.parse_args()

    reconciliation_date = date.fromisoformat(
        args.simulation_date
    )

    result = reconcile_settlements(
        reconciliation_date
    )

    print()
    print("=" * 72)
    print("RECONCILIATION COMPLETE")
    print("=" * 72)

    print(
        f"Simulation date                  : "
        f"{result['simulation_date']}"
    )

    print(
        f"Captured transactions             : "
        f"{result['captured_transaction_count']:,}"
    )

    print(
        f"Reconciliation rows              : "
        f"{result['reconciliation_count']:,}"
    )

    print(
        f"Matched                          : "
        f"{result['matched_count']:,}"
    )

    print(
        f"Amount mismatches                : "
        f"{result['amount_mismatch_count']:,}"
    )

    print(
        f"Missing settlements              : "
        f"{result['missing_settlement_count']:,}"
    )

    print(
        f"Timing exceptions                : "
        f"{result['timing_exception_count']:,}"
    )

    print(
        f"Status mismatches               : "
        f"{result['status_mismatch_count']:,}"
    )

    print(
        f"Processor mismatches            : "
        f"{result['processor_mismatch_count']:,}"
    )

    print(
        f"Unmatched processor entries     : "
        f"{result['unmatched_processor_entry_count']:,}"
    )

    print("=" * 72)