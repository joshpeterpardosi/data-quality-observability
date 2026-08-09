# ADR 0002: DuckDB Schema & Project Folder Structure

## Status
Accepted — 2026-08-09

## Context
Follows [0001](0001-validation-framework-pandera-vs-great-expectations.md).
Need a DuckDB schema layout that separates raw/landed data from validated
data from the observability metadata the Streamlit dashboard reads, plus a
project folder structure that keeps ingestion, validation, and dashboard
code independently testable.

## Decision

### DuckDB schema layout

Three DuckDB schemas, not one flat namespace — landing, curated, and
observability metadata are different lifecycles and shouldn't share tables.

```
raw.*        -- landed as-is from source files, loosely typed, never mutated
curated.*    -- typed/cleaned tables, only populated from rows that pass
                schema-level validation
dq.*         -- observability metadata: run history, check results,
                metrics time series, anomaly log
```

**`raw` schema** (source-of-truth landing zone; intentionally permissive
types so validation has real messy data to catch):

```sql
CREATE SCHEMA raw;

CREATE TABLE raw.customers (
    customer_id   VARCHAR,
    name          VARCHAR,
    email         VARCHAR,
    signup_date   VARCHAR,   -- left as text; format/nullability is what we validate
    country       VARCHAR,
    _loaded_at    TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE raw.products (
    product_id    VARCHAR,
    product_name  VARCHAR,
    category      VARCHAR,
    price         VARCHAR,
    _loaded_at    TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE raw.transactions (
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
```

**`curated` schema** (typed, only rows that passed validation land here —
this is what a "healthy" downstream consumer would query):

```sql
CREATE SCHEMA curated;

CREATE TABLE curated.customers (
    customer_id   VARCHAR PRIMARY KEY,
    name          VARCHAR NOT NULL,
    email         VARCHAR,
    signup_date   DATE,
    country       VARCHAR
);

CREATE TABLE curated.products (
    product_id    VARCHAR PRIMARY KEY,
    product_name  VARCHAR NOT NULL,
    category      VARCHAR,
    price          DECIMAL(10,2)
);

CREATE TABLE curated.transactions (
    transaction_id  VARCHAR PRIMARY KEY,
    customer_id     VARCHAR,   -- FK enforced by dq checks, not a DuckDB constraint
    product_id      VARCHAR,
    quantity        INTEGER,
    unit_price      DECIMAL(10,2),
    total_amount    DECIMAL(12,2),
    transaction_ts  TIMESTAMP NOT NULL,
    payment_method  VARCHAR,
    status          VARCHAR
);
```

**`dq` schema** (what the Streamlit app reads — every check, from either
Pandera or SQL, writes here in the same shape):

```sql
CREATE SCHEMA dq;

CREATE TABLE dq.validation_runs (
    run_id        UUID PRIMARY KEY,
    started_at    TIMESTAMP NOT NULL,
    finished_at   TIMESTAMP,
    dataset       VARCHAR NOT NULL,     -- e.g. 'transactions'
    status        VARCHAR NOT NULL      -- 'running' | 'passed' | 'failed'
);

CREATE TABLE dq.check_results (
    id            BIGINT PRIMARY KEY,
    run_id        UUID NOT NULL,        -- FK -> dq.validation_runs.run_id
    table_name    VARCHAR NOT NULL,
    column_name   VARCHAR,              -- null for table/cross-table-level checks
    dimension     VARCHAR NOT NULL,     -- completeness | uniqueness | validity
                                         -- | consistency | timeliness | accuracy
    check_name    VARCHAR NOT NULL,     -- e.g. 'null_pct_email', 'orphan_fk_customer_id'
    passed        BOOLEAN NOT NULL,
    total_rows    BIGINT,
    failed_rows   BIGINT,
    failure_rate  DOUBLE,
    threshold     DOUBLE,
    severity      VARCHAR,              -- 'warn' | 'error'
    message       VARCHAR
);

CREATE TABLE dq.metrics_timeseries (
    run_id        UUID NOT NULL,
    table_name    VARCHAR NOT NULL,
    metric_name   VARCHAR NOT NULL,     -- 'null_pct', 'duplicate_pct',
                                         -- 'freshness_lag_hours', 'row_count'
    metric_value  DOUBLE NOT NULL,
    captured_at   TIMESTAMP NOT NULL
);

CREATE TABLE dq.anomalies (
    id                BIGINT PRIMARY KEY,
    run_id            UUID NOT NULL,
    table_name        VARCHAR NOT NULL,
    metric_name       VARCHAR NOT NULL, -- e.g. 'daily_transaction_count'
    observed_value    DOUBLE,
    expected_low       DOUBLE,
    expected_high      DOUBLE,
    z_score           DOUBLE,
    detected_at       TIMESTAMP NOT NULL
);
```

Why three schemas instead of one: `raw` has to stay loosely typed and
append-only so we can validate real messy input; `curated` has to stay
trustworthy (only validated rows); `dq` has to stay independent of both so
the dashboard can render results even when the current run failed and
`curated` wasn't refreshed. Mixing these into one schema would either force
`raw` to be strictly typed (defeats the point — validation would never
catch a malformed row) or let dashboard queries accidentally read
unvalidated data.

`transaction_id`/`customer_id`/`product_id` FKs are enforced by `dq` checks
(orphan-FK check → `dq.check_results`), not DuckDB `FOREIGN KEY`
constraints — DuckDB does support them, but a hard constraint would abort
the load on the first bad row, which is exactly the case we want to detect
and report on, not prevent from loading into `raw`.

### Folder structure

```
data-quality-observability/
├── data/
│   ├── raw/                        # source files (csv/parquet) — gitignored
│   └── duckdb/
│       └── warehouse.duckdb        # gitignored; created at runtime
│
├── src/
│   ├── ingestion/
│   │   └── load_raw.py             # source files -> raw.* tables
│   │
│   ├── validation/
│   │   ├── schemas/                # Pandera DataFrameModel classes
│   │   │   ├── customers_schema.py
│   │   │   ├── products_schema.py
│   │   │   └── transactions_schema.py
│   │   ├── checks/                 # cross-table / aggregate SQL checks
│   │   │   ├── orphan_fk.py
│   │   │   ├── freshness.py
│   │   │   └── anomaly.py
│   │   └── runner.py               # orchestrates a run, writes to dq.*
│   │
│   └── db/
│       ├── ddl/                    # CREATE SCHEMA/TABLE statements above
│       │   ├── 01_raw.sql
│       │   ├── 02_curated.sql
│       │   └── 03_dq.sql
│       └── connection.py           # single place that opens warehouse.duckdb
│
├── dashboard/                      # Streamlit app
│   ├── app.py
│   ├── pages/
│   │   ├── 1_overview.py           # latest run status per table
│   │   ├── 2_check_drilldown.py    # failed checks, failure_rate detail
│   │   └── 3_trends_anomalies.py   # metrics_timeseries + anomalies charts
│   └── queries/                    # named SQL used by dashboard pages
│
├── tests/
│   ├── test_schemas.py             # Pandera schemas against fixture data
│   └── test_checks.py              # orphan_fk/freshness/anomaly unit tests
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── docs/
│   └── adr/
│       ├── 0001-validation-framework-pandera-vs-great-expectations.md
│       └── 0002-duckdb-schema-and-project-layout.md
│
├── pyproject.toml
├── .gitignore
└── README.md
```

Rationale for the split:
- `validation/schemas` vs `validation/checks` mirrors the ADR 0001 decision
  directly — per-row/column checks are Pandera classes, cross-table/
  aggregate checks are SQL — so the file layout documents the architecture.
- `dashboard/` only ever reads `dq.*` (plus `curated.*` for row counts) —
  it never talks to `raw.*`, so a broken ingestion run can't corrupt what
  the dashboard renders.
- `db/ddl/*.sql` is applied once at startup (idempotent `CREATE SCHEMA/TABLE
  IF NOT EXISTS`) so the Docker container can initialize `warehouse.duckdb`
  from a clean volume.

## Consequences
- Every check — Pandera or SQL — normalizes into `dq.check_results`, so the
  dashboard has exactly one table to query regardless of check origin.
- `curated.*` being populated only from rows that pass validation means
  "row count in curated vs raw" is itself a free data-quality metric.
- Adding a new table (e.g. `refunds`) means adding one Pandera schema file,
  extending the 3 DDL files, and the orphan-FK/freshness checks pick it up
  through the existing `checks/` parameterization — no dashboard changes
  required unless a new chart is wanted.
