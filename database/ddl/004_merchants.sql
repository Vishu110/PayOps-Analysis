DROP TABLE IF EXISTS merchants CASCADE;


--Table
CREATE TABLE merchants (
    id BIGSERIAL,
    merchant_id VARCHAR(50) NOT NULL,
    merchant_name VARCHAR(150) NOT NULL,
    legal_name VARCHAR(200) NOT NULL,
    merchant_category merchant_category_enum NOT NULL,
    size_segment merchant_size_segment_enum NOT NULL,
    country_code CHAR(2) NOT NULL,
    country_name VARCHAR(100) NOT NULL,
    default_currency CHAR(3) NOT NULL,
    preferred_processor_fk BIGINT NOT NULL,
    settlement_cycle SMALLINT NOT NULL,
    default_processing_fee_percentage NUMERIC(5,2) NOT NULL,
    risk_segment risk_segment_enum NOT NULL,
    merchant_status merchant_status_enum NOT NULL,
    onboarded_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    --Constraints
    CONSTRAINT pk_merchants
    PRIMARY KEY(id),

    CONSTRAINT uq_merchants_merchant_id
    UNIQUE(merchant_id),

    CONSTRAINT uq_merchants_legal_name
    UNIQUE(legal_name),

    CONSTRAINT fk_merchants_processors
    FOREIGN KEY(preferred_processor_fk)
    REFERENCES processors(id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

    CONSTRAINT chk_settlement_cycle
    CHECK(settlement_cycle BETWEEN 0 AND 30),

    CONSTRAINT chk_merchants_processing_fee 
    CHECK(
        default_processing_fee_percentage >= 0 AND
        default_processing_fee_percentage <= 100
    )
);

--Indexes
CREATE INDEX idx_merchants_country
ON merchants(country_code);

CREATE INDEX idx_merchants_category
ON merchants(merchant_category);

CREATE INDEX idx_merchants_processor
ON merchants(preferred_processor_fk);

CREATE INDEX idx_merchants_status
ON merchants(merchant_status);