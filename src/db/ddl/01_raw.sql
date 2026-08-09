CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.customers (
    customer_id   VARCHAR,
    name          VARCHAR,
    email         VARCHAR,
    signup_date   VARCHAR,
    country       VARCHAR,
    _loaded_at    TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS raw.products (
    product_id    VARCHAR,
    product_name  VARCHAR,
    category      VARCHAR,
    price         VARCHAR,
    _loaded_at    TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS raw.transactions (
    transaction_id  VARCHAR,
    customer_id     VARCHAR,
    product_id      VARCHAR,
    quantity        VARCHAR,
    unit_price      VARCHAR,
    total_amount    VARCHAR,
    transaction_ts  VARCHAR,
    payment_method  VARCHAR,
    status          VARCHAR,
    _loaded_at      TIMESTAMP DEFAULT current_timestamp
);
