# Data Quality & Observability Platform

A small end-to-end pipeline that ingests messy e-commerce CSVs into DuckDB, validates them against explicit data-quality rules across five dimensions, curates only the rows that pass, and surfaces every result in a Streamlit dashboard.

Built as a portfolio piece: the design decisions are written down as ADRs, not just implemented.

## What it does

```
data/raw/*.csv
      │
      ▼
  raw.*  (DuckDB, all VARCHAR, landed as-is)
      │
      ├─► Pandera schemas ──► completeness / uniqueness / validity
      │        (src/validation/schemas/*.py)
      │
      ├─► SQL checks ────────► consistency (orphan FK) / timeliness (staleness)
      │        (src/validation/checks/*.py)
      │
      ├─► volume anomaly detection (z-score on daily transaction count)
      │
      ▼
  curated.*  (typed, deduped, orphan-FK rows dropped)
      │
      ├─► same SQL checks re-run against curated.* (proves the gate worked)
      │
      ▼
  dq.*  (validation_runs, check_results, metrics_timeseries, anomalies)
      │
      ▼
  Streamlit dashboard  (reads dq.* + curated.* only, never raw.*)
```

Every check result — pass or fail — lands in `dq.check_results`. The dashboard doesn't distinguish between a Pandera check and a SQL check; both write to the same table.

## Why Pandera + SQL, not one or the other

Full reasoning: [docs/adr/0001](docs/adr/0001-validation-framework-pandera-vs-great-expectations.md).

Row/column-level checks (completeness, uniqueness, validity) are Pandera `DataFrameModel` schemas — they read as typed, reviewable Python. Cross-table and aggregate checks (orphan foreign keys, freshness vs. SLA, volume anomaly) are plain DuckDB SQL, because Pandera validates one DataFrame at a time and these checks inherently need either a second table or an aggregate over the whole column.

Schema layout and the raw/curated/dq split are explained in [docs/adr/0002](docs/adr/0002-duckdb-schema-and-project-layout.md).

## Setup

```bash
pip install -e .
```

Requires Python 3.11+. Installs `pandas`, `duckdb`, `pandera`, `streamlit`, `plotly`.

## Running it

Generate synthetic source data (messy on purpose — duplicate keys, orphan FKs, malformed prices, stale timestamps, a volume spike):

```bash
python scripts/generate_synthetic_data.py
```

Run the full pipeline — load raw, validate, build curated, re-validate curated:

```bash
python -m src.ingestion.load_raw
python -m src.validation.runner
```

Launch the dashboard:

```bash
streamlit run dashboard/app.py
```

Opens at `http://localhost:8501` with three pages: **Overview** (pass/fail by dimension, curation gate effectiveness), **Check Drilldown** (every check, filterable), **Trends & Anomalies** (daily volume vs. expected range, run history).

## Tests

```bash
python -m pytest
```

20 tests: Pandera schemas against fixture data, SQL checks (orphan FK / freshness / anomaly) against an in-memory DuckDB, and the curation gate end to end (dedupe-keep-first, orphan-FK exclusion, type casting).

## Project layout

```
data/raw/            source CSVs (gitignored, generated)
data/duckdb/          warehouse.duckdb (gitignored, created at runtime)
src/ingestion/        CSV -> raw.*
src/validation/
  schemas/            Pandera DataFrameModels (completeness/uniqueness/validity)
  checks/             SQL checks (orphan FK, freshness, anomaly) + shared CheckResult type
  runner.py           orchestrates a run, writes to dq.*
src/curation/          raw.* -> curated.*, gated on Pandera-valid rows
src/db/ddl/            schema DDL (raw / curated / dq), applied on connect
dashboard/             Streamlit app: pages, named SQL queries, palette/components
tests/                 pytest suite
docs/adr/              architecture decision records
```

## Known gaps

- No scheduler — the pipeline runs on demand, not on a cron.
- No Docker image yet.
- `dq.metrics_timeseries` grows unbounded across reruns (fine at this scale, would need pruning for continuous use).
- The `timeliness` check fails by design on the synthetic dataset (seeded data caps out at 5 days old, threshold is 2) — that's the fixture doing its job, not a bug.
