DROP TABLE IF EXISTS settlement_entries;


CREATE TABLE settlement_entries (
    id BIGSERIAL PRIMARY KEY,

    /*
     * Unique identifier for this processor settlement-feed line.
     */
    settlement_entry_id VARCHAR(100) NOT NULL,

    /*
     * Parent processor settlement batch.
     */
    settlement_batch_fk BIGINT NOT NULL,

    /*
     * Processor that produced this settlement entry.
     *
     * This is intentionally stored separately from the batch
     * processor so that the relationship can be validated.
     */
    processor_fk BIGINT NOT NULL,

    /*
     * Business reference used to match the processor record
     * back to our internal transaction.
     *
     * This is intentionally NOT a foreign key.
     *
     * A processor-only record may have a reference that does
     * not exist in our transactions table.
     */
    merchant_reference VARCHAR(100),

    /*
     * Processor's own payment / transaction reference.
     *
     * Useful when investigating an exception with the processor.
     */
    processor_transaction_reference VARCHAR(150) NOT NULL,

    /*
     * Type of processor journal entry.
     *
     * Current project scope covers captured payment settlements.
     */
    journal_type VARCHAR(30) NOT NULL,

    /*
     * Original payment transaction date reported by the processor.
     */
    transaction_date DATE NOT NULL,

    /*
     * Settlement date expected/reported by the processor feed.
     *
     * Nullable because an unmatched or malformed processor
     * record may not contain this information.
     */
    expected_settlement_date DATE,

    /*
     * Actual settlement date reported by the processor.
     */
    actual_settlement_date DATE NOT NULL,

    /*
     * Currency of the financial amounts in this entry.
     *
     * The current project normalizes settlement financials to USD.
     */
    settlement_currency CHAR(3) NOT NULL,

    /*
     * Processor-reported settlement amounts.
     */
    gross_amount_usd NUMERIC(20, 2) NOT NULL,
    fee_amount_usd   NUMERIC(20, 2) NOT NULL,
    net_amount_usd   NUMERIC(20, 2) NOT NULL,

    /*
     * Status reported by the processor.
     */
    processor_status VARCHAR(30) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,


    -- ============================================================
    -- Business / uniqueness constraints
    -- ============================================================

    CONSTRAINT uq_settlement_entry_id
        UNIQUE (settlement_entry_id),

    CONSTRAINT uq_settlement_processor_reference
        UNIQUE (
            processor_fk,
            processor_transaction_reference
        ),


    -- ============================================================
    -- Relationships
    -- ============================================================

    CONSTRAINT fk_settlement_entries_batch
        FOREIGN KEY (settlement_batch_fk)
        REFERENCES settlement_batches(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_settlement_entries_processor
        FOREIGN KEY (processor_fk)
        REFERENCES processors(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,


    -- ============================================================
    -- Domain constraints
    -- ============================================================

    CONSTRAINT chk_settlement_entry_journal_type
        CHECK (
            journal_type = 'SETTLED'
        ),

    CONSTRAINT chk_settlement_entry_processor_status
        CHECK (
            processor_status IN (
                'SETTLED',
                'REVERSED'
            )
        ),

    CONSTRAINT chk_settlement_entry_currency
        CHECK (
            settlement_currency = 'USD'
        ),


    -- ============================================================
    -- Financial integrity
    -- ============================================================

    CONSTRAINT chk_settlement_entry_gross
        CHECK (
            gross_amount_usd >= 0
        ),

    CONSTRAINT chk_settlement_entry_fee
        CHECK (
            fee_amount_usd >= 0
        ),

    CONSTRAINT chk_settlement_entry_fee_not_greater_than_gross
        CHECK (
            fee_amount_usd <= gross_amount_usd
        ),

    CONSTRAINT chk_settlement_entry_net
        CHECK (
            net_amount_usd >= 0
        ),

    CONSTRAINT chk_settlement_entry_arithmetic
        CHECK (
            ABS(
                net_amount_usd
                - (gross_amount_usd - fee_amount_usd)
            ) <= 0.01
        ),


    -- ============================================================
    -- Date integrity
    -- ============================================================

    CONSTRAINT chk_settlement_entry_transaction_date
        CHECK (
            actual_settlement_date >= transaction_date
        ),

    CONSTRAINT chk_settlement_entry_expected_date
        CHECK (
            expected_settlement_date IS NULL
            OR expected_settlement_date >= transaction_date
        )
);


-- ================================================================
-- Indexes
-- ================================================================

CREATE INDEX idx_settlement_entries_batch
    ON settlement_entries(settlement_batch_fk);

CREATE INDEX idx_settlement_entries_processor
    ON settlement_entries(processor_fk);

CREATE INDEX idx_settlement_entries_merchant_reference
    ON settlement_entries(merchant_reference);

CREATE INDEX idx_settlement_entries_actual_date
    ON settlement_entries(actual_settlement_date);

CREATE INDEX idx_settlement_entries_status
    ON settlement_entries(processor_status);

CREATE INDEX idx_settlement_entries_journal_type
    ON settlement_entries(journal_type);