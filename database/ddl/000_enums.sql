--001_customers.sql ENUMS
DROP TYPE IF EXISTS customer_status_enum CASCADE;
DROP TYPE IF EXISTS risk_segment_enum CASCADE;

CREATE TYPE customer_status_enum as ENUM (
    'ACTIVE',
    'BLOCKED',
    'CLOSED'
);

CREATE TYPE risk_segment_enum as ENUM (
    'LOW',
    'MEDIUM',
    'HIGH'
);



--002_processors.sql ENUMS
DROP TYPE IF EXISTS processor_status_enum CASCADE;

CREATE TYPE processor_status_enum as ENUM (
    'ACTIVE',
    'DEGRADED',
    'DOWN'
);



--003_issuing_banks.sql
DROP TYPE IF EXISTS bank_status_enum CASCADE;

CREATE TYPE bank_status_enum AS ENUM (
    'ACTIVE',
    'DEGRADED',
    'DOWN'
);



--004_merchants.sql ENUMS
DROP TYPE IF EXISTS merchant_category_enum CASCADE;
DROP TYPE IF EXISTS merchant_status_enum CASCADE;

--Enums
CREATE TYPE merchant_category_enum AS ENUM (
    'ECOMMERCE',
    'SAAS',
    'MARKETPLACE',
    'DIGITAL_GOODS'
);

CREATE TYPE merchant_status_enum AS ENUM (
    'ACTIVE',
    'SUSPENDED',
    'TERMINATED'
);


--005_products.sql ENUMS
DROP TYPE IF EXISTS product_status_enum CASCADE;
DROP TYPE IF EXISTS product_category_enum CASCADE;

--Enums
CREATE TYPE product_category_enum AS ENUM(
    'ELECTRONICS',
    'CLOTHING',
    'DIGITAL_GOODS',
    'SUBSCRIPTION',
    'HOME_APPLIANCES'
);

CREATE TYPE product_status_enum AS ENUM(
    'ACTIVE',
    'DISCONTINUED'
);



--006_payment_methods.sql ENUMS
DROP TYPE IF EXISTS payment_method_type_enum CASCADE;
DROP TYPE IF EXISTS card_network_enum CASCADE;
DROP TYPE IF EXISTS card_type_enum CASCADE;
DROP TYPE IF EXISTS payment_method_status_enum CASCADE;


--Enums
CREATE TYPE payment_method_type_enum AS ENUM (
    'CARD',
    'BANK_ACCOUNT',
    'WALLET'
);

CREATE TYPE card_network_enum AS ENUM (
    'VISA',
    'MASTERCARD',
    'AMEX'
);

CREATE TYPE card_type_enum AS ENUM (
    'CREDIT',
    'DEBIT'
);

CREATE TYPE payment_method_status_enum AS ENUM (
    'ACTIVE',
    'EXPIRED',
    'BLOCKED'
);