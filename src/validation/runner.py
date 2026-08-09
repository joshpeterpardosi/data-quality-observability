"""Run all DQ checks against a schema layer, persist to dq.* tables.

Per ADR 0001/0002: row/column-level checks (completeness, uniqueness,
validity) run through Pandera schemas in validation/schemas/*.py against
raw.* (the only layer with real messy data to validate). Cross-table and
aggregate checks (orphan FK, freshness, volume anomaly) run as SQL in
validation/checks/*.py and are parameterizable across schema layers.

Pandera + the raw-layer SQL checks land under one dq.validation_runs row
(dataset='raw') -- the dashboard's "latest run per dataset" query picks a
single run_id per dataset, so splitting them across two runs would make one
set of results invisible as soon as the other run.
"""
import uuid
from datetime import datetime, timezone

from src.db.connection import get_connection
from src.validation.checks import anomaly, freshness, orphan_fk
from src.validation.checks.base import insert_results, log_table_metrics
from src.validation.schemas import customers_schema, products_schema, transactions_schema

PANDERA_MODULES = {
    "customers": customers_schema,
    "products": products_schema,
    "transactions": transactions_schema,
}


def _new_run(con, dataset):
    run_id = str(uuid.uuid4())
    con.execute(
        "INSERT INTO dq.validation_runs (run_id, started_at, dataset, status) VALUES (?, ?, ?, 'running')",
        [run_id, datetime.now(timezone.utc).replace(tzinfo=None), dataset],
    )
    return run_id


def _finish_run(con, run_id, all_results):
    failed = [r for r in all_results if not r.passed]
    blocking = [r for r in failed if r.severity in ("critical", "high")]
    status = "failed" if blocking else ("warning" if failed else "passed")
    con.execute(
        "UPDATE dq.validation_runs SET finished_at = ?, status = ? WHERE run_id = ?",
        [datetime.now(timezone.utc).replace(tzinfo=None), status, run_id],
    )
    return status


def run_raw_validation(con=None):
    """Pandera (completeness/uniqueness/validity) + SQL (orphan FK, freshness, anomaly) against raw.*.

    One dq.validation_runs row. Returns (valid_frames, status); valid_frames
    feeds curation (only Pandera-valid rows get built into curated.*).
    """
    own_con = con is None
    if own_con:
        con = get_connection()

    run_id = _new_run(con, "raw")
    all_results = []
    valid_indices = {}
    for table, module in PANDERA_MODULES.items():
        df = con.execute(f"SELECT * FROM raw.{table}").df()
        results, valid_index = module.validate(df)
        all_results.extend(results)
        valid_indices[table] = df.loc[valid_index]

    all_results.extend(orphan_fk.run(con, schema="raw"))
    all_results.extend(freshness.run(con, schema="raw"))

    insert_results(con, run_id, all_results)
    log_table_metrics(con, run_id, all_results)
    anomaly_rows = anomaly.run(con, run_id, schema="raw")

    status = _finish_run(con, run_id, all_results)
    _print_summary(run_id, "raw", all_results, anomaly_rows)

    if own_con:
        con.close()
    return valid_indices, status


def run_curated_validation(con=None, schema="curated"):
    """Cross-table/aggregate SQL checks (orphan FK, freshness, anomaly) against curated.*.

    Proves the dedupe/FK gate in curation worked -- no Pandera here, curated
    is already typed/cleaned, not raw messy data.
    """
    own_con = con is None
    if own_con:
        con = get_connection()

    run_id = _new_run(con, schema)
    all_results = []
    all_results.extend(orphan_fk.run(con, schema=schema))
    all_results.extend(freshness.run(con, schema=schema))
    insert_results(con, run_id, all_results)
    log_table_metrics(con, run_id, all_results)
    anomaly_rows = anomaly.run(con, run_id, schema=schema)

    status = _finish_run(con, run_id, all_results)
    _print_summary(run_id, schema, all_results, anomaly_rows)

    if own_con:
        con.close()
    return run_id, status


def _print_summary(run_id, label, results, anomaly_rows):
    failed = [r for r in results if not r.passed]
    print(f"[{label}] run_id={run_id} checks={len(results)} failed={len(failed)} anomalies={len(anomaly_rows)}")
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        col = f".{r.column_name}" if r.column_name else ""
        print(f"  [{mark}] {r.dimension:<13} {r.table_name}{col:<24} {r.check_name:<26} {r.message}")
    for row in anomaly_rows:
        print(f"  [ANOMALY] {row[2]}.{row[3]} day observed={row[4]:.0f} expected=[{row[5]:.1f},{row[6]:.1f}] z={row[7]:.2f}")


if __name__ == "__main__":
    from src.curation.build_curated import build_curated

    con = get_connection()
    valid_frames, _status = run_raw_validation(con)
    build_curated(con, valid_frames)
    run_curated_validation(con)
    con.close()
