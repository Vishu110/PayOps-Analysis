DROP TABLE IF EXISTS payment_events CASCADE;

CREATE TABLE payment_events (
    id BIGSERIAL,

    event_id VARCHAR(50) NOT NULL,

    payment_attempt_fk BIGINT NOT NULL,

    event_status transaction_status_enum NOT NULL,

    event_at TIMESTAMPTZ NOT NULL,

    sequence_number SMALLINT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_payment_events
        PRIMARY KEY (id),

    CONSTRAINT uq_payment_events_event_id
        UNIQUE (event_id),

    CONSTRAINT fk_payment_events_attempt
        FOREIGN KEY (payment_attempt_fk)
        REFERENCES payment_attempts(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT uq_payment_event_sequence
        UNIQUE (payment_attempt_fk, sequence_number),

    CONSTRAINT chk_payment_event_sequence
        CHECK (sequence_number >= 1)
);

CREATE INDEX idx_payment_events_attempt
ON payment_events(payment_attempt_fk);

CREATE INDEX idx_payment_events_status
ON payment_events(event_status);

CREATE INDEX idx_payment_events_event_at
ON payment_events(event_at);