DROP TABLE IF EXISTS customers CASCADE;


--TABLE
CREATE TABLE customers (
    id BIGSERIAL,
    customer_id VARCHAR(50) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(25),
    country_code CHAR(2) NOT NULL,
    country_name VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    city VARCHAR(100),
    timezone VARCHAR(100) NOT NULL,
    preferred_currency CHAR(3) NOT NULL,
    risk_segment risk_segment_enum NOT NULL,
    customer_status customer_status_enum NOT NULL,
    signup_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    --Constraints
    CONSTRAINT pk_customers
    PRIMARY KEY (id),

    CONSTRAINT uq_customers_customer_id
    UNIQUE (customer_id),

    CONSTRAINT uq_customers_email
    UNIQUE (email)
);


--Indexes
CREATE INDEX idx_customers_country
ON customers(country_code);

CREATE INDEX idx_customers_risk
ON customers(risk_segment);

CREATE INDEX idx_customers_status
ON customers(customer_status);

CREATE INDEX idx_customers_signup
ON customers(signup_date);
