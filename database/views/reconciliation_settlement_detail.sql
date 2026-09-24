/*
 * Settlement reconciliation detail
 *
 * Purpose:
 *   Provide one canonical, read-only reconciliation record for every
 *   captured transaction plus every processor settlement entry.
 *
 * The expected side is independently derived from the internal payment
 * data. Processor-reported amounts and dates are taken from
 * settlement_entries. No processor-reported "expected" fields are used
 * to calculate the internal expectation.
 *
 * This view identifies mechanical reconciliation outcomes. It is not an
 * investigation result and should not be treated as a source of truth for
 * root cause beyond the deterministic amount-mismatch classifications.
 *
 * Business-day assumption:
 *   Monday-Friday only. Holidays are intentionally not modelled, matching
 *   the settlement simulation.
 */

CREATE OR REPLACE VIEW reconciliation_settlement_detail AS

WITH captured_transactions AS (

    SELECT
        t.id AS transaction_db_id,
        t.transaction_id,
        t.simulation_date AS transaction_date,
        t.merchant_fk,
        t.amount AS original_amount,
        t.currency AS original_currency,

        m.merchant_id,
        m.country_code AS merchant_country_code,
        m.settlement_cycle,

        ca.processor_fk,
        p.processor_id,
        p.processor_name,
        p.default_processing_fee_percentage AS processor_fee_percentage,

        fx.fx_rate,

        /*
         * The latest CAPTURED attempt is the settlement-owning attempt.
         * This matches the settlement candidate logic.
         */
        ca.captured_at

    FROM transactions t

    INNER JOIN LATERAL (
        SELECT
            pa.processor_fk,
            pa.completed_at AS captured_at
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
),

expected_settlements AS (

    SELECT
        ct.transaction_db_id,
        ct.transaction_id,
        ct.transaction_date,
        ct.merchant_fk,
        ct.merchant_id,
        ct.merchant_country_code,
        ct.original_amount,
        ct.original_currency,
        ct.settlement_cycle,
        ct.processor_fk,
        ct.processor_id,
        ct.processor_name,
        ct.processor_fee_percentage,
        ct.fx_rate,
        ct.captured_at,

        /*
         * Add the merchant settlement cycle in business days.
         *
         * For weekday starts, the expression adds the required number of
         * weekdays plus two days for each weekend crossed.
         *
         * For Saturday/Sunday starts, the calculation first moves the
         * effective start to Monday and then adds the remaining business
         * days. A zero-day cycle always returns the transaction date.
         */
        CASE
            WHEN ct.settlement_cycle = 0 THEN
                ct.transaction_date

            WHEN EXTRACT(ISODOW FROM ct.transaction_date) = 6 THEN
                ct.transaction_date
                + ct.settlement_cycle
                + 1
                + (
                    2 * FLOOR(
                        (ct.settlement_cycle - 1) / 5.0
                    )
                )::integer

            WHEN EXTRACT(ISODOW FROM ct.transaction_date) = 7 THEN
                ct.transaction_date
                + ct.settlement_cycle
                + (
                    2 * FLOOR(
                        (ct.settlement_cycle - 1) / 5.0
                    )
                )::integer

            ELSE
                ct.transaction_date
                + ct.settlement_cycle
                + (
                    2 * FLOOR(
                        (
                            EXTRACT(ISODOW FROM ct.transaction_date)::integer
                            - 1
                            + ct.settlement_cycle
                        ) / 5.0
                    )
                )::integer
        END AS expected_settlement_date,

        ROUND(
            ct.original_amount * ct.fx_rate,
            2
        ) AS expected_gross_amount_usd

    FROM captured_transactions ct
),

expected_financials AS (

    SELECT
        es.*,

        ROUND(
            es.expected_gross_amount_usd
            * es.processor_fee_percentage
            / 100.0,
            2
        ) AS expected_fee_amount_usd

    FROM expected_settlements es
),

expected_final AS (

    SELECT
        ef.*,

        ROUND(
            ef.expected_gross_amount_usd
            - ef.expected_fee_amount_usd,
            2
        ) AS expected_net_amount_usd

    FROM expected_financials ef
),

processor_entries AS (

    SELECT
        se.id AS settlement_entry_db_id,
        se.settlement_entry_id,
        se.settlement_batch_fk,
        sb.settlement_batch_id,
        sb.batch_status,
        se.processor_fk AS actual_processor_fk,
        p.processor_id AS actual_processor_id,
        p.processor_name AS actual_processor_name,
        se.merchant_reference,
        se.processor_transaction_reference,
        se.transaction_date AS actual_transaction_date,
        se.expected_settlement_date AS processor_reported_expected_settlement_date,
        se.actual_settlement_date,
        se.settlement_currency,
        se.gross_amount_usd AS actual_gross_amount_usd,
        se.fee_amount_usd AS actual_fee_amount_usd,
        se.net_amount_usd AS actual_net_amount_usd,
        se.processor_status,
        se.journal_type

    FROM settlement_entries se

    INNER JOIN settlement_batches sb
        ON sb.id = se.settlement_batch_fk

    INNER JOIN processors p
        ON p.id = se.processor_fk
),

reconciliation_base AS (

    SELECT
        ef.transaction_db_id,
        pe.settlement_entry_db_id,

        COALESCE(
            ef.transaction_id,
            pe.merchant_reference
        ) AS transaction_id,

        ef.transaction_id AS expected_transaction_id,
        pe.merchant_reference AS processor_transaction_id,

        ef.merchant_fk,
        ef.merchant_id,
        ef.merchant_country_code,

        COALESCE(
            ef.processor_fk,
            pe.actual_processor_fk
        ) AS processor_fk,

        COALESCE(
            ef.processor_id,
            pe.actual_processor_id
        ) AS processor_id,

        COALESCE(
            ef.processor_name,
            pe.actual_processor_name
        ) AS processor_name,

        ef.transaction_date AS expected_transaction_date,
        pe.actual_transaction_date AS processor_transaction_date,

        ef.captured_at,
        ef.settlement_cycle,

        ef.expected_settlement_date,
        pe.processor_reported_expected_settlement_date,
        pe.actual_settlement_date,

        ef.settlement_cycle AS expected_settlement_cycle,

        ef.original_amount,
        ef.original_currency,
        ef.fx_rate,

        ef.processor_fee_percentage,

        ef.expected_gross_amount_usd,
        ef.expected_fee_amount_usd,
        ef.expected_net_amount_usd,

        pe.actual_gross_amount_usd,
        pe.actual_fee_amount_usd,
        pe.actual_net_amount_usd,

        pe.settlement_currency,
        pe.processor_status,
        pe.journal_type,
        pe.settlement_entry_id,
        pe.settlement_batch_fk,
        pe.settlement_batch_id,
        pe.batch_status,
        pe.processor_transaction_reference,

        CASE
            WHEN ef.transaction_id IS NULL THEN
                'UNMATCHED_PROCESSOR_ENTRY'

            WHEN pe.settlement_entry_id IS NULL THEN
                'MISSING_SETTLEMENT'

            WHEN pe.actual_processor_fk <> ef.processor_fk THEN
                'PROCESSOR_MISMATCH'

            WHEN pe.processor_status <> 'SETTLED' THEN
                'STATUS_MISMATCH'

            WHEN pe.actual_settlement_date <> ef.expected_settlement_date THEN
                'TIMING_EXCEPTION'

            WHEN pe.actual_gross_amount_usd <> ef.expected_gross_amount_usd
              OR pe.actual_fee_amount_usd <> ef.expected_fee_amount_usd
              OR pe.actual_net_amount_usd <> ef.expected_net_amount_usd THEN
                'AMOUNT_MISMATCH'

            ELSE
                'MATCHED'
        END AS reconciliation_status

    FROM expected_final ef

    FULL OUTER JOIN processor_entries pe
        ON pe.merchant_reference = ef.transaction_id
),

classified AS (

    SELECT
        rb.*,

        CASE
            WHEN rb.reconciliation_status <> 'AMOUNT_MISMATCH' THEN
                NULL

            WHEN rb.actual_gross_amount_usd = rb.expected_gross_amount_usd
             AND rb.actual_fee_amount_usd <> rb.expected_fee_amount_usd THEN
                'PROCESSOR_FEE_VARIANCE'

            WHEN rb.actual_gross_amount_usd = ROUND(
                rb.expected_gross_amount_usd * 0.75,
                2
            ) THEN
                'PARTIAL_SETTLEMENT'

            WHEN rb.actual_gross_amount_usd = rb.expected_gross_amount_usd
                + GREATEST(
                    0.01::numeric,
                    ROUND(
                        rb.expected_gross_amount_usd * 0.002,
                        2
                    )
                ) THEN
                'FX_DIFFERENCE'

            WHEN rb.actual_gross_amount_usd = rb.expected_gross_amount_usd
                + 0.02 THEN
                'ROUNDING_DIFFERENCE'

            ELSE
                'UNEXPLAINED_DIFFERENCE'
        END AS amount_mismatch_reason

    FROM reconciliation_base rb
)

SELECT
    transaction_db_id,
    settlement_entry_db_id,
    transaction_id,
    expected_transaction_id,
    processor_transaction_id,

    merchant_fk,
    merchant_id,
    merchant_country_code,

    processor_fk,
    processor_id,
    processor_name,

    expected_transaction_date,
    processor_transaction_date,
    captured_at,

    settlement_cycle,
    expected_settlement_cycle,
    expected_settlement_date,
    processor_reported_expected_settlement_date,
    actual_settlement_date,

    original_amount,
    original_currency,
    fx_rate,

    processor_fee_percentage,
    'USD' AS expected_settlement_currency,

    expected_gross_amount_usd,
    expected_fee_amount_usd,
    expected_net_amount_usd,

    actual_gross_amount_usd,
    actual_fee_amount_usd,
    actual_net_amount_usd,

    settlement_currency,
    processor_status,
    journal_type,

    settlement_entry_id,
    settlement_batch_fk,
    settlement_batch_id,
    batch_status,
    processor_transaction_reference,

    reconciliation_status,
    amount_mismatch_reason

FROM classified;
