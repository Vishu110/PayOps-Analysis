DROP TABLE IF EXISTS products CASCADE;


--Table
CREATE TABLE products(
    id BIGSERIAL,
    product_id VARCHAR(50) NOT NULL,
    merchant_fk BIGINT NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    product_category product_category_enum NOT NULL,
    base_price NUMERIC(12,2) NOT NULL,
    currency CHAR(3) NOT NULL,
    refundable BOOLEAN NOT NULL DEFAULT TRUE,
    refund_probability NUMERIC(5,2) NOT NULL,
    chargeback_probability NUMERIC(5,2) NOT NULL,
    product_status product_status_enum NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    --Constraints
    CONSTRAINT pk_products
    PRIMARY KEY(id),

    CONSTRAINT uq_products_product_id
    UNIQUE(product_id),

    CONSTRAINT fk_products_merchants
    FOREIGN KEY(merchant_fk)
    REFERENCES merchants(id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

    CONSTRAINT chk_products_price
    CHECK(base_price > 0),

    CONSTRAINT chk_products_refund_probability
    CHECK(refund_probability BETWEEN 0 AND 100),

    CONSTRAINT chk_products_chargeback_probability
    CHECK(chargeback_probability BETWEEN 0 AND 100)
);


--Indexes
CREATE INDEX idx_products_merchant
ON products(merchant_fk);

CREATE INDEX idx_products_category
ON products(product_category);

CREATE INDEX idx_products_status
ON products(product_status);