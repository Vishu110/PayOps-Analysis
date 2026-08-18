DROP TABLE IF EXISTS transactions CASCADE;

CREATE TABLE transactions (
    id BIGSERIAL,

    transaction_id VARCHAR(50) NOT NULL,

    customer_fk BIGINT NOT NULL,
    merchant_fk BIGINT NOT NULL,
    product_fk BIGINT NOT NULL,
    payment_method_fk BIGINT NOT NULL,

    transaction_type transaction_type_enum NOT NULL,

    amount NUMERIC(18,2) NOT NULL,
    currency CHAR(3) NOT NULL,
    quantity SMALLINT NOT NULL,

    current_status transaction_status_enum NOT NULL,

    initiated_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_transactions
        PRIMARY KEY (id),

    CONSTRAINT uq_transactions_transaction_id
        UNIQUE (transaction_id),

    CONSTRAINT fk_transactions_customer
        FOREIGN KEY (customer_fk)
        REFERENCES customers(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_transactions_merchant
        FOREIGN KEY (merchant_fk)
        REFERENCES merchants(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_transactions_product
        FOREIGN KEY (product_fk)
        REFERENCES products(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_transactions_payment_method
        FOREIGN KEY (payment_method_fk)
        REFERENCES payment_methods(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT chk_transactions_amount
        CHECK (amount > 0),

    CONSTRAINT chk_transactions_quantity
        CHECK (quantity > 0),

    CONSTRAINT chk_transactions_completed_at
        CHECK (
            completed_at IS NULL
            OR completed_at >= initiated_at
        )
);

CREATE INDEX idx_transactions_customer
ON transactions(customer_fk);

CREATE INDEX idx_transactions_merchant
ON transactions(merchant_fk);

CREATE INDEX idx_transactions_product
ON transactions(product_fk);

CREATE INDEX idx_transactions_payment_method
ON transactions(payment_method_fk);

CREATE INDEX idx_transactions_status
ON transactions(current_status);

CREATE INDEX idx_transactions_initiated_at
ON transactions(initiated_at);