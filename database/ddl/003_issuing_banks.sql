DROP TABLE IF EXISTS issuing_banks CASCADE;


--Table
CREATE TABLE issuing_banks(
    id BIGSERIAL,
    bank_id VARCHAR(50) NOT NULL,
    bank_name VARCHAR(150) NOT NULL,
    bank_code VARCHAR(20) NOT NULL,
    country_code CHAR(2) NOT NULL,
    country_name VARCHAR(100) NOT NULL,
    supported_card_networks JSONB NOT NULL,
    bank_status bank_status_enum NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    --Constraints
    CONSTRAINT pk_issuing_banks
    PRIMARY KEY(id),

    CONSTRAINT uq_issuing_banks_bank_id
    UNIQUE(bank_id),

    CONSTRAINT uq_issuing_banks_bank_code
    UNIQUE(bank_code)
);

--Indexes
CREATE INDEX idx_issuing_banks_country
ON issuing_banks(country_code);

CREATE INDEX idx_issuing_banks_status
ON issuing_banks(bank_status);