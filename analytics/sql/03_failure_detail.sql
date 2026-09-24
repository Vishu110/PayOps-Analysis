WITH failure_detail AS (

    SELECT
        DATE_TRUNC(
            'month',
            t.simulation_date
        )::date AS month,

        pa.failure_reason,

        p.processor_name,

        COUNT(*) AS failed_attempts,

        COUNT(DISTINCT pa.transaction_fk)
            AS failed_transactions,

        ROUND(
            SUM(
                t.amount * f.fx_rate
            ),
            2
        ) AS failed_attempt_value_usd

    FROM payment_attempts pa

    INNER JOIN transactions t
        ON pa.transaction_fk = t.id

    INNER JOIN processors p
        ON pa.processor_fk = p.id

    LEFT JOIN fx_rates f
        ON t.simulation_date = f.rate_date
       AND t.currency = f.source_currency
       AND f.target_currency = 'USD'

    WHERE pa.attempt_status = 'FAILED'

    GROUP BY
        DATE_TRUNC(
            'month',
            t.simulation_date
        )::date,
        pa.failure_reason,
        p.processor_name
)

SELECT
    month,
    failure_reason,
    processor_name,
    failed_attempts,
    failed_transactions,
    failed_attempt_value_usd

FROM failure_detail

ORDER BY
    month,
    failed_attempts DESC;