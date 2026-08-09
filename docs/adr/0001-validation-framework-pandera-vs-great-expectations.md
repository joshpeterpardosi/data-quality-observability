# ADR 0001: Validation Framework — Pandera vs. Great Expectations

## Status
Accepted — 2026-08-09

## Context

We're building a Data Quality & Observability Platform on an e-commerce
transaction dataset (`customers`, `products`, `transactions`). The platform
must run the following checks on a schedule and surface results in a
Streamlit dashboard backed by DuckDB:

- **Completeness** — null percentage per column, against per-column thresholds
- **Uniqueness** — duplicate row / duplicate primary-key detection
- **Referential integrity** — orphan foreign keys (e.g. `transactions.customer_id`
  not present in `customers.customer_id`)
- **Freshness** — staleness of the latest record vs. an expected load SLA
- **Anomaly detection** — statistical drift in volume/value columns
  (e.g. z-score or IQR on daily transaction count or revenue)

Stack constraints: DuckDB as the engine, Streamlit as the UI, Docker as the
runtime, single maintainer, portfolio timeline (weeks, not months). The
result needs to read as well-engineered code, not just passing checks — this
is a hiring artifact as much as a working tool.

Two candidate validation libraries were evaluated: **Pandera** and
**Great Expectations (GE)**.

## Decision Drivers

1. **Coverage of the five check dimensions above**, and how much has to be
   hand-rolled regardless of library choice.
2. **Integration friction with DuckDB** — validation should run close to the
   data (DuckDB relations / Arrow / pandas), not require a separate heavy
   context.
3. **Dependency weight and startup cost** — matters for Docker image size
   and cold-start time in a demo environment.
4. **Time-to-working-demo** — portfolio project, solo maintainer, limited
   time budget.
5. **Code legibility as a portfolio artifact** — schemas/checks should read
   as clear, reviewable Python, since reviewers will read the source.
6. **API stability** — risk of breaking changes disrupting the build.

## Options Considered

### Option A: Great Expectations

GE is a full data-quality framework: `ExpectationSuite`s, a `DataContext`,
pluggable `Datasource`s/`Checkpoint`s, a validation store, and auto-generated
HTML "Data Docs."

**Pros**
- Very large built-in expectation library (`expect_column_values_to_not_be_null`,
  `expect_column_values_to_be_unique`, `expect_column_pair_values_A_to_be_greater_than_B`, etc.)
- Ships its own HTML report generation (Data Docs) — free reporting UI
- Strong brand recognition; widely used in enterprise data platforms
- Checkpoints give a built-in notion of a "validation run" with history

**Cons**
- Heavier setup: a `DataContext` (YAML/JSON project config), datasource
  wiring, and expectation suite JSON files before the first check runs.
  This is overhead the project doesn't need since Streamlit is the
  reporting layer, not Data Docs.
- No native orphan-FK / cross-table check — cross-table referential
  integrity still has to be hand-written as SQL or a custom expectation.
- No native freshness-vs-SLA or statistical anomaly-detection expectation
  out of the box either — both need custom expectations or external code.
- History of breaking API changes across major versions (0.13 → 0.15 → 0.18
  → 1.0 config/API reshuffles), which is a real risk against a fixed
  portfolio timeline — debugging library churn instead of building features.
- Larger dependency footprint (pydantic, jinja2, sqlalchemy-adjacent
  tooling, its own CLI) — larger Docker image, slower cold start.
- Suite definitions in JSON/YAML are harder to read/review as "clean code"
  than a Python class; less natural fit for a code-sample-driven portfolio.

### Option B: Pandera

Pandera defines schemas as Python objects (`DataFrameSchema` or a
`pandera.DataFrameModel` class), validated against pandas/DuckDB-Arrow
DataFrames, with `Check` objects for arbitrary column- or dataframe-level
logic.

**Pros**
- Schema-as-code: a `DataFrameModel` class with typed fields reads like a
  dataclass/pydantic model — self-documenting, good portfolio code sample.
- Built-in checks cover completeness (`nullable=False`), uniqueness
  (`unique=True` / `Check` on duplicated rows), dtype/range/regex validation
  directly.
- `Check(...)` and `Check(element_wise=...)` make custom logic (freshness,
  anomaly z-score, orphan-FK against a second DataFrame via closure) trivial
  to express in a few lines of plain Python — same amount of custom code GE
  would need for these, but without a config layer around it.
- Validates pandas DataFrames directly, and DuckDB's `.df()` / `.arrow()`
  output plugs straight in — no adapter layer needed.
- Small dependency surface (pandas/numpy + pandera itself) — lighter Docker
  image, fast cold start.
- Stable, narrow API surface; low churn risk.
- Failure output (`SchemaErrors.failure_cases`) is a DataFrame — trivial to
  write into a DuckDB `dq` schema for the Streamlit dashboard to query.

**Cons**
- No built-in reporting UI — but the project is building a custom Streamlit
  dashboard anyway, so this isn't lost functionality, it's avoided
  duplication.
- Smaller built-in expectation catalog than GE — mitigated by the fact that
  the two hardest checks (orphan FK, freshness, anomaly detection) are
  custom in both libraries regardless.
- Less enterprise brand recognition than GE — acceptable trade-off; the
  reviewer signal we want is "wrote clear, testable validation code," which
  Pandera's style supports better than GE's config files.

## Comparison Summary

| Dimension                       | Great Expectations                        | Pandera                                  |
|----------------------------------|---------------------------------------------|-------------------------------------------|
| Null % / completeness            | Built-in expectation                        | Built-in (`nullable=False`, custom `Check`) |
| Duplicate detection               | Built-in expectation                        | Built-in (`unique=True`, custom `Check`)  |
| Orphan FK (cross-table)           | Custom (no native expectation)              | Custom (`Check` w/ closure over other df) |
| Freshness vs. SLA                 | Custom                                      | Custom                                    |
| Anomaly detection (z-score/IQR)   | Custom                                      | Custom                                    |
| DuckDB/pandas integration          | Requires Datasource/Batch wiring            | Direct — validates DataFrames as-is       |
| Setup overhead                    | DataContext + suites + checkpoints          | Import + define schema class              |
| Dependency weight / image size    | Heavy                                       | Light                                     |
| Reporting UI                      | Built-in Data Docs (redundant w/ Streamlit) | None (Streamlit is the UI)                |
| API stability                     | History of breaking changes                 | Stable, narrow surface                    |
| Code as portfolio artifact        | JSON/YAML suites                            | Readable Python classes                   |

## Decision

**Use Pandera.**

The two dimensions where GE would normally justify its weight —
a large built-in expectation catalog and free reporting — don't pay off
here: the hardest checks in this project's scope (orphan FK, freshness,
anomaly detection) are custom code in *either* library, and reporting is
being built explicitly in Streamlit, making GE's Data Docs redundant.
What's left is Pandera's advantage: less setup, a lighter runtime, a more
stable API, and schema definitions that read as clean, reviewable Python —
which matters for a portfolio piece.

Concretely: table schemas (`customers`, `products`, `transactions`) are
defined as `pandera.DataFrameModel` classes for structural/completeness/
uniqueness checks; freshness, orphan-FK, and anomaly checks are implemented
as plain DuckDB SQL queries (they're cross-table or aggregate checks, which
is DuckDB's job, not a per-row schema's) with their pass/fail results
normalized into the same result schema Pandera checks write to, so the
dashboard has one uniform `dq` results table regardless of which layer
produced the finding.

## Consequences

- All row/column-level checks (nulls, dtypes, ranges, duplicates) live in
  `src/validation/schemas/*.py` as Pandera models — versioned, testable,
  importable.
- Cross-table and aggregate checks (orphan FK, freshness, anomaly
  detection) live in `src/validation/checks/*.py` as parameterized DuckDB
  SQL, not inside Pandera, since Pandera operates on a single DataFrame.
- A single `dq.check_results` table (see folder/schema proposal) is the
  contract between both check types and the Streamlit dashboard — the
  dashboard doesn't need to know which layer produced a given result.
- If the project later needs GE-style shareable HTML reports for a
  non-technical audience, that's a reversible addition — it wouldn't
  replace Pandera, just add a reporting sink alongside the DuckDB one.

## Alternatives Rejected
- **Great Expectations** — see above; setup/dependency weight and API churn
  risk outweigh its expectation catalog and Data Docs for this scope.
- **Hand-rolled validation only (no library)** — rejected because Pandera's
  marginal cost over hand-rolled checks is near zero (a few lines per
  schema) while it buys typed schemas, reusable `Check` composition, and a
  consistent `SchemaErrors` failure format to standardize on.
