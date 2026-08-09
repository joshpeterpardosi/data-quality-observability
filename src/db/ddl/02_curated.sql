CREATE SCHEMA IF NOT EXISTS curated;

CREATE TABLE IF NOT EXISTS curated.customers (
    customer_id   VARCHAR PRIMARY KEY,
    name          VARCHAR NOT NULL,
    email         VARCHAR,
    signup_date   DATE,
    country       VARCHAR
);

CREATE TABLE IF NOT EXISTS curated.products (
    product_id    VARCHAR PRIMARY KEY,
    product_name  VARCHAR NOT NULL,
    category      VARCHAR,
    price         DECIMAL(10,2)
);

CREATE TABLE IF NOT EXISTS curated.transactions (
    transaction_id  VARCHAR PRIMARY KEY,
    customer_id     VARCHAR,
    product_id      VARCHAR,
    quantity        INTEGER,
    unit_price      DECIMAL(10,2),
    total_amount    DECIMAL(12,2),
    transaction_ts  TIMESTAMP NOT NULL,
    payment_method  VARCHAR,
    status          VARCHAR
);
