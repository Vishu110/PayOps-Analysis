/*
===============================================================================
01_payment_operations.sql

Purpose
-------
Power BI source queries for the Payment Operations overview.

The file contains three independent result sets. Run/load each SELECT as a
separate Power BI query because PostgreSQL clients used by Power BI expect one
result set per query.

Result sets
-----------
1. Monthly Payment Operations
   Grain: one row per simulation month.

2. Monthly Retry & Transaction Latency
   Grain: one row per simulation month, built from transaction-level attempt
   counts and transaction lifecycle timestamps.

3. Monthly Payment Funnel & Event Latency
   Grain: one row per simulation month, built from payment-attempt event
   history. Event sequence_number is intentionally not used to identify stages;
   event_status existence is used instead.

Validated business definitions
-------------------------------
- Retry: transaction with more than one payment attempt.
- Retry recovery: retried transaction whose final transaction status is
  CAPTURED.
- Authorization: payment attempt reached the AUTHORIZED event.
- Capture: payment attempt reached the CAPTURED event.
- Payment conversion: captured attempts / all payment attempts.
- Authentication required: payment attempt reached REQUIRES_ACTION.
- Authentication recovery: authentication-required attempt that subsequently
  reached CAPTURED / authentication-required attempts.
- Event latency is calculated from event_at timestamps.

Important modeling note
-----------------------
Transactions, payment attempts, and payment events have different grains.
The queries aggregate each source to its intended grain before the monthly
aggregation so that joins do not multiply business metrics.
===============================================================================
*/


/* ============================================================================
1. MONTHLY PAYMENT OPERATIONS
   Grain: one row per simulation month.
============================================================================ */

SELECT
    DATE_TRUNC('month', t.simulation_date)::date AS month,

    COUNT(*) AS transaction_volume,

    COUNT(*) FILTER (
        WHERE t.current_status = 'CAPTURED'
    ) AS captured_transactions,

    ROUND(
        SUM(
            CASE
                WHEN t.current_status = 'CAPTURED'
                    THEN t.amount * f.fx_rate
                ELSE 0
            END
        ),
        2
    ) AS gpv_usd,

    ROUND(
        SUM(
            CASE
                WHEN t.current_status = 'CAPTURED'
                    THEN t.amount * f.fx_rate
                ELSE 0
            END
        )
        / NULLIF(
            COUNT(*) FILTER (
                WHERE t.current_status = 'CAPTURED'
            ),
            0
        ),
        2
    ) AS avg_captured_transaction_value_usd,

    ROUND(
        COUNT(*) FILTER (
            WHERE t.current_status = 'CAPTURED'
        )::numeric
        / NULLIF(COUNT(*), 0)
        * 100,
        2
    ) AS success_rate,

    COUNT(*) FILTER (
        WHERE t.current_status = 'FAILED'
    ) AS failed_transactions,

    ROUND(
        COUNT(*) FILTER (
            WHERE t.current_status = 'FAILED'
        )::numeric
        / NULLIF(COUNT(*), 0)
        * 100,
        2
    ) AS failure_rate,

    COUNT(*) FILTER (
        WHERE t.current_status = 'CANCELED'
    ) AS canceled_transactions,

    ROUND(
        COUNT(*) FILTER (
            WHERE t.current_status = 'CANCELED'
        )::numeric
        / NULLIF(COUNT(*), 0)
        * 100,
        2
    ) AS cancellation_rate

FROM transactions t

LEFT JOIN fx_rates f
    ON t.simulation_date = f.rate_date
   AND t.currency = f.source_currency
   AND f.target_currency = 'USD'

GROUP BY
    DATE_TRUNC('month', t.simulation_date)::date

ORDER BY
    month;


/* ============================================================================
2. MONTHLY RETRY & TRANSACTION LATENCY
   Grain: one row per simulation month.

   Retry is transaction-level, not attempt-level.
============================================================================ */

WITH transaction_attempt_summary AS (

    SELECT
        pa.transaction_fk,
        COUNT(*) AS attempt_count

    FROM payment_attempts pa

    GROUP BY
        pa.transaction_fk
),

transaction_level AS (

    SELECT
        t.id AS transaction_id,
        t.simulation_date,
        t.current_status,
        COALESCE(ta.attempt_count, 0) AS attempt_count,

        CASE
            WHEN COALESCE(ta.attempt_count, 0) > 1
                THEN 1
            ELSE 0
        END AS retried_flag,

        CASE
            WHEN COALESCE(ta.attempt_count, 0) > 1
             AND t.current_status = 'CAPTURED'
                THEN 1
            ELSE 0
        END AS retry_recovered_flag,

        EXTRACT(
            EPOCH FROM (
                t.completed_at - t.initiated_at
            )
        ) AS processing_seconds

    FROM transactions t

    LEFT JOIN transaction_attempt_summary ta
        ON t.id = ta.transaction_fk
)

SELECT
    DATE_TRUNC('month', simulation_date)::date AS month,

    COUNT(*) AS transaction_volume,

    SUM(retried_flag) AS transactions_with_retry,

    ROUND(
        SUM(retried_flag)::numeric
        / NULLIF(COUNT(*), 0)
        * 100,
        2
    ) AS retry_rate,

    SUM(retry_recovered_flag) AS retry_recovered_transactions,

    ROUND(
        SUM(retry_recovered_flag)::numeric
        / NULLIF(SUM(retried_flag), 0)
        * 100,
        2
    ) AS retry_recovery_rate,

    ROUND(
        AVG(attempt_count),
        2
    ) AS avg_attempts_per_transaction,

    MAX(attempt_count) AS max_attempts,

    ROUND(
        AVG(processing_seconds),
        2
    ) AS avg_processing_seconds,

    ROUND(
        (
            PERCENTILE_CONT(0.95)
            WITHIN GROUP (
                ORDER BY processing_seconds
            )
        )::numeric,
        2
    ) AS p95_processing_seconds,

    ROUND(
        (
            PERCENTILE_CONT(0.99)
            WITHIN GROUP (
                ORDER BY processing_seconds
            )
        )::numeric,
        2
    ) AS p99_processing_seconds

FROM transaction_level

GROUP BY
    DATE_TRUNC('month', simulation_date)::date

ORDER BY
    month;


/* ============================================================================
3. MONTHLY PAYMENT FUNNEL & EVENT LATENCY
   Grain: one row per simulation month.

   Event stages are identified by event_status existence, not sequence_number.
   This is required because REQUIRES_ACTION changes the sequence positions of
   subsequent events.
============================================================================ */

WITH attempt_events AS (

    SELECT
        pe.payment_attempt_fk,

        MAX(pe.event_at) FILTER (
            WHERE pe.event_status = 'PENDING'
        ) AS pending_at,

        MAX(pe.event_at) FILTER (
            WHERE pe.event_status = 'REQUIRES_ACTION'
        ) AS requires_action_at,

        MAX(pe.event_at) FILTER (
            WHERE pe.event_status = 'AUTHORIZED'
        ) AS authorized_at,

        MAX(pe.event_at) FILTER (
            WHERE pe.event_status = 'CAPTURED'
        ) AS captured_at

    FROM payment_events pe

    WHERE pe.event_status IN (
        'PENDING',
        'REQUIRES_ACTION',
        'AUTHORIZED',
        'CAPTURED'
    )

    GROUP BY
        pe.payment_attempt_fk
),

attempt_level AS (

    SELECT
        pa.id AS payment_attempt_id,
        t.simulation_date,

        CASE
            WHEN ae.requires_action_at IS NOT NULL
                THEN 1
            ELSE 0
        END AS authentication_required_flag,

        CASE
            WHEN ae.authorized_at IS NOT NULL
                THEN 1
            ELSE 0
        END AS authorized_flag,

        CASE
            WHEN ae.captured_at IS NOT NULL
                THEN 1
            ELSE 0
        END AS captured_flag,

        CASE
            WHEN ae.requires_action_at IS NOT NULL
             AND ae.captured_at IS NOT NULL
                THEN 1
            ELSE 0
        END AS authentication_recovered_flag,

        EXTRACT(
            EPOCH FROM (
                ae.authorized_at - ae.requires_action_at
            )
        ) AS authentication_to_authorization_seconds,

        EXTRACT(
            EPOCH FROM (
                ae.authorized_at - ae.pending_at
            )
        ) AS authorization_latency_seconds,

        EXTRACT(
            EPOCH FROM (
                ae.captured_at - ae.authorized_at
            )
        ) AS capture_after_authorization_seconds,

        EXTRACT(
            EPOCH FROM (
                ae.captured_at - ae.pending_at
            )
        ) AS end_to_end_payment_latency_seconds

    FROM payment_attempts pa

    INNER JOIN transactions t
        ON pa.transaction_fk = t.id

    LEFT JOIN attempt_events ae
        ON ae.payment_attempt_fk = pa.id
)

SELECT
    DATE_TRUNC('month', simulation_date)::date AS month,

    COUNT(*) AS payment_attempts,

    SUM(authorized_flag) AS authorized_attempts,

    ROUND(
        SUM(authorized_flag)::numeric
        / NULLIF(COUNT(*), 0)
        * 100,
        2
    ) AS authorization_rate,

    SUM(captured_flag) AS captured_attempts,

    ROUND(
        SUM(captured_flag)::numeric
        / NULLIF(SUM(authorized_flag), 0)
        * 100,
        2
    ) AS capture_rate,

    ROUND(
        SUM(captured_flag)::numeric
        / NULLIF(COUNT(*), 0)
        * 100,
        2
    ) AS payment_conversion_rate,

    SUM(authentication_required_flag) AS authentication_required_attempts,

    ROUND(
        SUM(authentication_required_flag)::numeric
        / NULLIF(COUNT(*), 0)
        * 100,
        2
    ) AS authentication_required_rate,

    SUM(authentication_recovered_flag)
        AS authentication_recovered_attempts,

    ROUND(
        SUM(authentication_recovered_flag)::numeric
        / NULLIF(SUM(authentication_required_flag), 0)
        * 100,
        2
    ) AS authentication_recovery_rate,

    ROUND(
        AVG(authorization_latency_seconds)
            FILTER (
                WHERE authorization_latency_seconds IS NOT NULL
            ),
        2
    ) AS avg_authorization_latency_seconds,

    ROUND(
        (
            PERCENTILE_CONT(0.95)
            WITHIN GROUP (
                ORDER BY authorization_latency_seconds
            )
        )::numeric,
        2
    ) AS p95_authorization_latency_seconds,

    ROUND(
        AVG(authentication_to_authorization_seconds)
            FILTER (
                WHERE authentication_to_authorization_seconds IS NOT NULL
            ),
        2
    ) AS avg_authentication_to_authorization_seconds,

    ROUND(
        (
            PERCENTILE_CONT(0.95)
            WITHIN GROUP (
                ORDER BY authentication_to_authorization_seconds
            )
        )::numeric,
        2
    ) AS p95_authentication_to_authorization_seconds,

    ROUND(
        AVG(capture_after_authorization_seconds)
            FILTER (
                WHERE capture_after_authorization_seconds IS NOT NULL
            ),
        2
    ) AS avg_capture_after_authorization_seconds,

    ROUND(
        (
            PERCENTILE_CONT(0.95)
            WITHIN GROUP (
                ORDER BY capture_after_authorization_seconds
            )
        )::numeric,
        2
    ) AS p95_capture_after_authorization_seconds,

    ROUND(
        AVG(end_to_end_payment_latency_seconds)
            FILTER (
                WHERE end_to_end_payment_latency_seconds IS NOT NULL
            ),
        2
    ) AS avg_end_to_end_payment_latency_seconds,

    ROUND(
        (
            PERCENTILE_CONT(0.95)
            WITHIN GROUP (
                ORDER BY end_to_end_payment_latency_seconds
            )
        )::numeric,
        2
    ) AS p95_end_to_end_payment_latency_seconds

FROM attempt_level

GROUP BY
    DATE_TRUNC('month', simulation_date)::date

ORDER BY
    month;
