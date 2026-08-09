CREATE SCHEMA IF NOT EXISTS dq;

CREATE TABLE IF NOT EXISTS dq.validation_runs (
    run_id        UUID PRIMARY KEY,
    started_at    TIMESTAMP NOT NULL,
    finished_at   TIMESTAMP,
    dataset       VARCHAR NOT NULL,
    status        VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS dq.check_results (
    id            BIGINT PRIMARY KEY,
    run_id        UUID NOT NULL,
    table_name    VARCHAR NOT NULL,
    column_name   VARCHAR,
    dimension     VARCHAR NOT NULL,
    check_name    VARCHAR NOT NULL,
    passed        BOOLEAN NOT NULL,
    total_rows    BIGINT,
    failed_rows   BIGINT,
    failure_rate  DOUBLE,
    threshold     DOUBLE,
    severity      VARCHAR,
    message       VARCHAR
);

CREATE TABLE IF NOT EXISTS dq.metrics_timeseries (
    run_id        UUID NOT NULL,
    table_name    VARCHAR NOT NULL,
    metric_name   VARCHAR NOT NULL,
    metric_value  DOUBLE NOT NULL,
    captured_at   TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS dq.anomalies (
    id                BIGINT PRIMARY KEY,
    run_id            UUID NOT NULL,
    table_name        VARCHAR NOT NULL,
    metric_name       VARCHAR NOT NULL,
    observed_value    DOUBLE,
    expected_low      DOUBLE,
    expected_high     DOUBLE,
    z_score           DOUBLE,
    detected_at       TIMESTAMP NOT NULL
);
