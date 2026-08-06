DROP TABLE IF EXISTS processors CASCADE;


--Table
CREATE TABLE processors (
    id BIGSERIAL,
    processor_id VARCHAR(50) NOT NULL,
    processor_name VARCHAR(100) NOT NULL,
    headquarters_country_code CHAR(2) NOT NULL,
    headquarters_country_name VARCHAR(100) NOT NULL,
    supported_regions JSONB NOT NULL,
    supported_card_networks JSONB NOT NULL,
    default_processing_fee_percentage NUMERIC(5,2) NOT NULL,
    processor_status processor_status_enum NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    --Constraints
    CONSTRAINT pk_processors
    PRIMARY KEY (id),

    CONSTRAINT uq_processors_processor_id
    UNIQUE (processor_id),

    CONSTRAINT uq_processors_name
    UNIQUE (processor_name),

    CONSTRAINT chk_processors_default_processing_fee
    CHECK (
        default_processing_fee_percentage >= 0
        AND default_processing_fee_percentage <= 100
    )
);


--Indexes
CREATE INDEX idx_processors_status
ON processors(processor_status);