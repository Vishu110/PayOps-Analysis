-- ============================================================
-- 015_reconciliation_settlements.sql
--
-- Persistent reconciliation result dataset.
--
-- Purpose:
--   Store the mechanical reconciliation outcome between:
--     1. Internal expected settlements
--     2. Processor-reported settlement entries
--
-- Design principles:
--   - Reconciliation results are persisted rather than recomputed
--     for every analyst query.
--   - Expected and actual settlement values remain independent.
--   - Mechanical reconciliation status is stored here.
--   - Root-cause investigation remains an analyst/SQL layer.
--   - Processor-only records are supported for unmatched entries.
--
-- Scope:
--   Captured payment settlement reconciliation only.
-- ============================================================


CREATE TABLE IF NOT EXISTS reconciliation_settlements (

    -- --------------------------------------------------------
    -- Identity
    -- --------------------------------------------------------

    id BIGSERIAL PRIMARY KEY,

    simulation_date DATE NOT NULL,

    transaction_fk BIGINT NULL,

    settlement_entry_fk BIGINT NULL,


    -- --------------------------------------------------------
    -- Business identifiers
    -- --------------------------------------------------------

    transaction_id VARCHAR(100) NULL,

    settlement_entry_id VARCHAR(150) NULL,

    processor_transaction_reference VARCHAR(200) NULL,


    -- --------------------------------------------------------
    -- Expected / internal settlement
    -- --------------------------------------------------------

    expected_processor_fk BIGINT NULL,

    expected_merchant_fk BIGINT NULL,

    transaction_date DATE NULL,

    expected_settlement_date DATE NULL,

    expected_gross_amount_usd NUMERIC(20, 2) NULL,

    expected_fee_amount_usd NUMERIC(20, 2) NULL,

    expected_net_amount_usd NUMERIC(20, 2) NULL,


    -- --------------------------------------------------------
    -- Actual / processor settlement
    -- --------------------------------------------------------

    actual_processor_fk BIGINT NULL,

    actual_settlement_date DATE NULL,

    actual_gross_amount_usd NUMERIC(20, 2) NULL,

    actual_fee_amount_usd NUMERIC(20, 2) NULL,

    actual_net_amount_usd NUMERIC(20, 2) NULL,

    processor_status VARCHAR(30) NULL,


    -- --------------------------------------------------------
    -- Reconciliation result
    -- --------------------------------------------------------

    reconciliation_status VARCHAR(40) NOT NULL,

    amount_mismatch_reason VARCHAR(40) NULL,


    -- --------------------------------------------------------
    -- Audit timestamps
    -- --------------------------------------------------------

    reconciled_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,


    -- ========================================================
    -- Foreign keys
    -- ========================================================

    CONSTRAINT fk_reconciliation_transaction
        FOREIGN KEY (transaction_fk)
        REFERENCES transactions(id),

    CONSTRAINT fk_reconciliation_settlement_entry
        FOREIGN KEY (settlement_entry_fk)
        REFERENCES settlement_entries(id),

    CONSTRAINT fk_reconciliation_expected_processor
        FOREIGN KEY (expected_processor_fk)
        REFERENCES processors(id),

    CONSTRAINT fk_reconciliation_actual_processor
        FOREIGN KEY (actual_processor_fk)
        REFERENCES processors(id),

    CONSTRAINT fk_reconciliation_merchant
        FOREIGN KEY (expected_merchant_fk)
        REFERENCES merchants(id),


    -- ========================================================
    -- Uniqueness
    --
    -- A transaction can have only one reconciliation result
    -- for a given simulation date.
    -- ========================================================

    CONSTRAINT uq_reconciliation_transaction_date
        UNIQUE (simulation_date, transaction_fk),


    -- ========================================================
    -- Reconciliation status
    -- ========================================================

    CONSTRAINT chk_reconciliation_status
        CHECK (
            reconciliation_status IN (
                'MATCHED',
                'AMOUNT_MISMATCH',
                'MISSING_SETTLEMENT',
                'TIMING_EXCEPTION',
                'STATUS_MISMATCH',
                'PROCESSOR_MISMATCH',
                'UNMATCHED_PROCESSOR_ENTRY'
            )
        ),


    -- ========================================================
    -- Amount mismatch reason
    -- ========================================================

    CONSTRAINT chk_amount_mismatch_reason
        CHECK (
            amount_mismatch_reason IS NULL
            OR amount_mismatch_reason IN (
                'PROCESSOR_FEE_VARIANCE',
                'PARTIAL_SETTLEMENT',
                'FX_DIFFERENCE',
                'ROUNDING_DIFFERENCE',
                'UNEXPLAINED_DIFFERENCE'
            )
        ),


    -- ========================================================
    -- Amount mismatch reason only applies to amount mismatches
    -- ========================================================

    CONSTRAINT chk_amount_reason_status
        CHECK (
            amount_mismatch_reason IS NULL
            OR reconciliation_status = 'AMOUNT_MISMATCH'
        ),


    -- ========================================================
    -- Expected-side integrity
    --
    -- A normal transaction-side reconciliation must have:
    -- transaction + merchant + processor + transaction date +
    -- expected settlement date + expected financials.
    --
    -- Processor-only exceptions are allowed to have these NULL.
    -- ========================================================

    CONSTRAINT chk_expected_financials
        CHECK (
            (
                transaction_fk IS NULL
                AND expected_processor_fk IS NULL
                AND expected_merchant_fk IS NULL
                AND transaction_date IS NULL
                AND expected_settlement_date IS NULL
                AND expected_gross_amount_usd IS NULL
                AND expected_fee_amount_usd IS NULL
                AND expected_net_amount_usd IS NULL
            )
            OR
            (
                transaction_fk IS NOT NULL
                AND expected_processor_fk IS NOT NULL
                AND expected_merchant_fk IS NOT NULL
                AND transaction_date IS NOT NULL
                AND expected_settlement_date IS NOT NULL
                AND expected_gross_amount_usd IS NOT NULL
                AND expected_fee_amount_usd IS NOT NULL
                AND expected_net_amount_usd IS NOT NULL
            )
        ),


    -- ========================================================
    -- Actual-side integrity
    --
    -- Processor settlement fields must either all be present
    -- or all be absent.
    -- ========================================================

    CONSTRAINT chk_actual_financials
        CHECK (
            (
                settlement_entry_fk IS NULL
                AND actual_processor_fk IS NULL
                AND actual_settlement_date IS NULL
                AND actual_gross_amount_usd IS NULL
                AND actual_fee_amount_usd IS NULL
                AND actual_net_amount_usd IS NULL
                AND processor_status IS NULL
            )
            OR
            (
                settlement_entry_fk IS NOT NULL
                AND actual_processor_fk IS NOT NULL
                AND actual_settlement_date IS NOT NULL
                AND actual_gross_amount_usd IS NOT NULL
                AND actual_fee_amount_usd IS NOT NULL
                AND actual_net_amount_usd IS NOT NULL
                AND processor_status IS NOT NULL
            )
        ),


    -- ========================================================
    -- Status-specific presence rules
    -- ========================================================

    CONSTRAINT chk_missing_settlement
        CHECK (
            reconciliation_status <> 'MISSING_SETTLEMENT'
            OR settlement_entry_fk IS NULL
        ),

    CONSTRAINT chk_unmatched_processor_entry
        CHECK (
            reconciliation_status <> 'UNMATCHED_PROCESSOR_ENTRY'
            OR transaction_fk IS NULL
        ),


    -- ========================================================
    -- Expected financial arithmetic
    -- ========================================================

    CONSTRAINT chk_expected_amounts_non_negative
        CHECK (
            expected_gross_amount_usd IS NULL
            OR (
                expected_gross_amount_usd >= 0
                AND expected_fee_amount_usd >= 0
                AND expected_net_amount_usd >= 0
            )
        ),

    CONSTRAINT chk_expected_fee_not_above_gross
        CHECK (
            expected_gross_amount_usd IS NULL
            OR expected_fee_amount_usd <= expected_gross_amount_usd
        ),

    CONSTRAINT chk_expected_net_arithmetic
        CHECK (
            expected_gross_amount_usd IS NULL
            OR expected_net_amount_usd =
               expected_gross_amount_usd - expected_fee_amount_usd
        ),


    -- ========================================================
    -- Actual financial arithmetic
    -- ========================================================

    CONSTRAINT chk_actual_amounts_non_negative
        CHECK (
            actual_gross_amount_usd IS NULL
            OR (
                actual_gross_amount_usd >= 0
                AND actual_fee_amount_usd >= 0
                AND actual_net_amount_usd >= 0
            )
        ),

    CONSTRAINT chk_actual_fee_not_above_gross
        CHECK (
            actual_gross_amount_usd IS NULL
            OR actual_fee_amount_usd <= actual_gross_amount_usd
        ),

    CONSTRAINT chk_actual_net_arithmetic
        CHECK (
            actual_gross_amount_usd IS NULL
            OR actual_net_amount_usd =
               actual_gross_amount_usd - actual_fee_amount_usd
        ),


    -- ========================================================
    -- Date integrity
    -- ========================================================

    CONSTRAINT chk_expected_settlement_date
        CHECK (
            expected_settlement_date IS NULL
            OR transaction_date IS NULL
            OR expected_settlement_date >= transaction_date
        ),

    CONSTRAINT chk_actual_settlement_date
        CHECK (
            actual_settlement_date IS NULL
            OR transaction_date IS NULL
            OR actual_settlement_date >= transaction_date
        )
);


-- ============================================================
-- Indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_reconciliation_status
    ON reconciliation_settlements (
        reconciliation_status
    );


CREATE INDEX IF NOT EXISTS idx_reconciliation_simulation_date
    ON reconciliation_settlements (
        simulation_date
    );


CREATE INDEX IF NOT EXISTS idx_reconciliation_transaction
    ON reconciliation_settlements (
        transaction_fk
    );


CREATE INDEX IF NOT EXISTS idx_reconciliation_transaction_id
    ON reconciliation_settlements (
        transaction_id
    );


CREATE INDEX IF NOT EXISTS idx_reconciliation_settlement_entry
    ON reconciliation_settlements (
        settlement_entry_fk
    );


CREATE INDEX IF NOT EXISTS idx_reconciliation_merchant
    ON reconciliation_settlements (
        expected_merchant_fk
    );


CREATE INDEX IF NOT EXISTS idx_reconciliation_expected_processor
    ON reconciliation_settlements (
        expected_processor_fk
    );


CREATE INDEX IF NOT EXISTS idx_reconciliation_actual_processor
    ON reconciliation_settlements (
        actual_processor_fk
    );


CREATE INDEX IF NOT EXISTS idx_reconciliation_transaction_date
    ON reconciliation_settlements (
        transaction_date
    );


CREATE INDEX IF NOT EXISTS idx_reconciliation_expected_date
    ON reconciliation_settlements (
        expected_settlement_date
    );


CREATE INDEX IF NOT EXISTS idx_reconciliation_actual_date
    ON reconciliation_settlements (
        actual_settlement_date
    );


CREATE INDEX IF NOT EXISTS idx_reconciliation_status_simulation
    ON reconciliation_settlements (
        reconciliation_status,
        simulation_date
    );


CREATE INDEX IF NOT EXISTS idx_reconciliation_status_expected_date
    ON reconciliation_settlements (
        reconciliation_status,
        expected_settlement_date
    );


CREATE INDEX IF NOT EXISTS idx_reconciliation_status_actual_date
    ON reconciliation_settlements (
        reconciliation_status,
        actual_settlement_date
    );