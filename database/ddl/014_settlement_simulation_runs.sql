DROP TABLE IF EXISTS settlement_simulation_runs;

CREATE TABLE settlement_simulation_runs (
    simulation_date DATE PRIMARY KEY,

    simulation_seed BIGINT NOT NULL,

    simulation_status VARCHAR(20) NOT NULL,

    candidate_count INTEGER NOT NULL DEFAULT 0,
    expected_settlement_count INTEGER NOT NULL DEFAULT 0,
    processor_entry_count INTEGER NOT NULL DEFAULT 0,
    missing_settlement_count INTEGER NOT NULL DEFAULT 0,
    settlement_batch_count INTEGER NOT NULL DEFAULT 0,

    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_settlement_simulation_status
        CHECK (
            simulation_status IN (
                'RUNNING',
                'COMPLETE'
            )
        ),

    CONSTRAINT chk_settlement_simulation_candidate_count
        CHECK (candidate_count >= 0),

    CONSTRAINT chk_settlement_simulation_expected_count
        CHECK (expected_settlement_count >= 0),

    CONSTRAINT chk_settlement_simulation_processor_entry_count
        CHECK (processor_entry_count >= 0),

    CONSTRAINT chk_settlement_simulation_missing_count
        CHECK (missing_settlement_count >= 0),

    CONSTRAINT chk_settlement_simulation_batch_count
        CHECK (settlement_batch_count >= 0),

    CONSTRAINT chk_settlement_simulation_completed_at
        CHECK (
            completed_at IS NULL
            OR completed_at >= started_at
        ),

    CONSTRAINT chk_settlement_simulation_counts
        CHECK (
            expected_settlement_count = candidate_count
        ),

    CONSTRAINT chk_settlement_simulation_entry_counts
        CHECK (
            processor_entry_count
            + missing_settlement_count
            = expected_settlement_count
        ),

    CONSTRAINT chk_settlement_simulation_complete_timestamp
        CHECK (
            simulation_status <> 'COMPLETE'
            OR completed_at IS NOT NULL
        )
);

CREATE INDEX idx_settlement_simulation_status
    ON settlement_simulation_runs(simulation_status);

CREATE INDEX idx_settlement_simulation_started_at
    ON settlement_simulation_runs(started_at);