"""Shared glue between Pandera DataFrameModels and dq.check_results rows.

Pandera excludes null values from column-level Checks on nullable fields by
design, so a tolerated null-rate (e.g. "email null <=5% is fine") can't be
expressed as a per-row Check — it's an aggregate stat over the whole column.
completeness on strict (non-nullable) columns is Pandera's own `not_nullable`
check; completeness on tolerant columns is computed directly here instead.
"""
import pandas as pd
import pandera.pandas as pa

from src.validation.checks.base import CheckResult

# stable, version-independent names for Pandera's own built-in checks
CHECK_DIMENSIONS = {
    "not_nullable": "completeness",
    "field_uniqueness": "uniqueness",
}
SEVERITY_BY_DIMENSION = {
    "completeness": "high",
    "uniqueness": "critical",
    "validity": "medium",
}


def null_rate_results(table, df, thresholds: dict) -> list[CheckResult]:
    total = len(df)
    results = []
    for col, threshold in thresholds.items():
        nulls = int(df[col].isna().sum())
        rate = nulls / total if total else 0.0
        passed = rate <= threshold
        results.append(CheckResult(
            table_name=table, column_name=col, dimension="completeness",
            check_name="null_rate", passed=passed, total_rows=total, failed_rows=nulls,
            threshold=threshold, severity="warning" if passed else "high",
            message=f"{nulls}/{total} null ({rate:.2%}), threshold {threshold:.0%}",
        ))
    return results


def schema_check_results(table, df, model, registry) -> tuple[list[CheckResult], "pd.Index"]:
    """Validate df against a Pandera model. Returns (results, structurally_valid_row_index).

    Uniqueness (`field_uniqueness`) failures are reported but excluded from
    the invalidated-row set: a duplicate key isn't malformed data, it's
    resolved by dedup (keep-first) in the curation step, not by discarding
    every copy.
    """
    total = len(df)
    try:
        model.validate(df, lazy=True)
        failures = None
    except pa.errors.SchemaErrors as e:
        failures = e.failure_cases

    results = []
    bad_index = set()
    for column, check_name in registry:
        if failures is not None:
            mask = (failures["column"] == column) & (failures["check"] == check_name)
            failed_idx = failures.loc[mask, "index"].dropna().astype(int)
        else:
            failed_idx = []
        failed = len(failed_idx)
        dimension = CHECK_DIMENSIONS.get(check_name, "validity")
        if dimension != "uniqueness":
            bad_index.update(failed_idx)
        passed = failed == 0
        results.append(CheckResult(
            table_name=table, column_name=column, dimension=dimension, check_name=check_name,
            passed=passed, total_rows=total, failed_rows=failed, threshold=0.0,
            severity="warning" if passed else SEVERITY_BY_DIMENSION.get(dimension, "medium"),
            message=f"{failed}/{total} rows failed {check_name}",
        ))
    valid_index = df.index.difference(bad_index)
    return results, valid_index
