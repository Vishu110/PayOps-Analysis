DROP TABLE IF EXISTS payment_attempts CASCADE;

CREATE TABLE payment_attempts (
    id BIGSERIAL,

    attempt_id VARCHAR(50) NOT NULL,

    transaction_fk BIGINT NOT NULL,

    attempt_number SMALLINT NOT NULL,

    processor_fk BIGINT NOT NULL,

    attempt_status transaction_status_enum NOT NULL,

    failure_reason transaction_failure_reason_enum,

    initiated_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_payment_attempts
        PRIMARY KEY (id),

    CONSTRAINT uq_payment_attempts_attempt_id
        UNIQUE (attempt_id),

    CONSTRAINT fk_payment_attempts_transaction
        FOREIGN KEY (transaction_fk)
        REFERENCES transactions(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_payment_attempts_processor
        FOREIGN KEY (processor_fk)
        REFERENCES processors(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT uq_payment_attempt_number
        UNIQUE (transaction_fk, attempt_number),

    CONSTRAINT chk_payment_attempt_number
        CHECK (attempt_number >= 1),

    CONSTRAINT chk_payment_attempt_completed_at
        CHECK (
            completed_at IS NULL
            OR completed_at >= initiated_at
        ),

    CONSTRAINT chk_payment_attempt_failure_reason
        CHECK (
            (attempt_status = 'FAILED' AND failure_reason IS NOT NULL)
            OR
            (attempt_status <> 'FAILED' AND failure_reason IS NULL)
        )
);

CREATE INDEX idx_payment_attempts_transaction
ON payment_attempts(transaction_fk);

CREATE INDEX idx_payment_attempts_processor
ON payment_attempts(processor_fk);

CREATE INDEX idx_payment_attempts_status
ON payment_attempts(attempt_status);

CREATE INDEX idx_payment_attempts_initiated_at
ON payment_attempts(initiated_at);