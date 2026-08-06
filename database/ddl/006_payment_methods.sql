DROP TABLE IF EXISTS payment_methods CASCADE;



--Table
CREATE TABLE payment_methods(
    id BIGSERIAL,
    payment_method_id VARCHAR(50) NOT NULL,
    customer_fk BIGINT NOT NULL,
    issuing_bank_fk BIGINT NOT NULL,
    payment_method_type payment_method_type_enum NOT NULL,
    card_network card_network_enum NOT NULL,
    card_type card_type_enum NOT NULL,
    card_last_four CHAR(4) NOT NULL,
    expiry_month SMALLINT NOT NULL,
    expiry_year SMALLINT NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    payment_method_status payment_method_status_enum NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    --Constraints
    CONSTRAINT pk_payment_methods
        PRIMARY KEY(id),

    CONSTRAINT uq_payment_methods_payment_method_id
        UNIQUE(payment_method_id),

    CONSTRAINT fk_payment_methods_customers
        FOREIGN KEY(customer_fk)
        REFERENCES customers(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_payment_methods_issuing_banks
        FOREIGN KEY(issuing_bank_fk)
        REFERENCES issuing_banks(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT chk_payment_methods_last_four
        CHECK(card_last_four ~ '^[0-9]{4}$'),

    CONSTRAINT chk_payment_methods_expiry_month
        CHECK(expiry_month BETWEEN 1 AND 12)--,

    --CONSTRAINT chk_payment_methods_expiry_year
        --CHECK(expiry_year >= 2020)
);


--Indexes
CREATE INDEX idx_payment_methods_customer
ON payment_methods(customer_fk);

CREATE INDEX idx_payment_methods_bank
ON payment_methods(issuing_bank_fk);

CREATE INDEX idx_payment_methods_network
ON payment_methods(card_network);

CREATE INDEX idx_payment_methods_status
ON payment_methods(payment_method_status);