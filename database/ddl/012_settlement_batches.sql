DROP TABLE IF EXISTS settlement_batches;


CREATE TABLE settlement_batches (
    id BIGSERIAL PRIMARY KEY,

    /*
     * Processor-side settlement batch reference.
     * Represents the processor's grouping of settlement activity.
     */
    settlement_batch_id VARCHAR(80) NOT NULL,

    /*
     * Processor responsible for the settlement.
     */
    processor_fk BIGINT NOT NULL,

    /*
     * Date on which the processor reports the batch as settled.
     */
    settlement_date DATE NOT NULL,

    /*
     * All settlement financials in this project are normalized to USD.
     */
    settlement_currency CHAR(3) NOT NULL,

    /*
     * Operational state of the processor settlement batch.
     */
    batch_status VARCHAR(30) NOT NULL,

    /*
     * Batch-level financial totals.
     */
    gross_amount_usd NUMERIC(20, 2) NOT NULL,
    fee_amount_usd   NUMERIC(20, 2) NOT NULL,
    net_amount_usd   NUMERIC(20, 2) NOT NULL,

    /*
     * Number of settlement entries belonging to this batch.
     */
    entry_count INTEGER NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,


    -- ============================================================
    -- Business / uniqueness constraints
    -- ============================================================

    CONSTRAINT uq_settlement_batch_reference
        UNIQUE (
            processor_fk,
            settlement_batch_id
        ),


    -- ============================================================
    -- Relationships
    -- ============================================================

    CONSTRAINT fk_settlement_batch_processor
        FOREIGN KEY (processor_fk)
        REFERENCES processors(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,


    -- ============================================================
    -- Domain constraints
    -- ============================================================

    CONSTRAINT chk_settlement_batch_currency
        CHECK (
            settlement_currency = 'USD'
        ),

    CONSTRAINT chk_settlement_batch_status
        CHECK (
            batch_status IN (
                'SETTLED',
                'PARTIALLY_SETTLED',
                'REVERSED'
            )
        ),


    -- ============================================================
    -- Financial integrity
    -- ============================================================

    CONSTRAINT chk_settlement_batch_gross
        CHECK (
            gross_amount_usd >= 0
        ),

    CONSTRAINT chk_settlement_batch_fee
        CHECK (
            fee_amount_usd >= 0
        ),

    CONSTRAINT chk_settlement_batch_fee_not_greater_than_gross
        CHECK (
            fee_amount_usd <= gross_amount_usd
        ),

    CONSTRAINT chk_settlement_batch_net
        CHECK (
            net_amount_usd >= 0
        ),

    CONSTRAINT chk_settlement_batch_arithmetic
        CHECK (
            ABS(
                net_amount_usd
                - (gross_amount_usd - fee_amount_usd)
            ) <= 0.01
        ),

    CONSTRAINT chk_settlement_batch_entry_count
        CHECK (
            entry_count >= 0
        )
);


-- ================================================================
-- Indexes
-- ================================================================

CREATE INDEX idx_settlement_batches_processor
    ON settlement_batches(processor_fk);

CREATE INDEX idx_settlement_batches_date
    ON settlement_batches(settlement_date);

CREATE INDEX idx_settlement_batches_status
    ON settlement_batches(batch_status);