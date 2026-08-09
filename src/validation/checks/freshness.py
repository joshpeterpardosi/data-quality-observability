"""Staleness check on transaction_ts, raw layer."""
from src.validation.checks.base import CheckResult

MAX_STALENESS_DAYS = 2


def run(con, schema="raw") -> list[CheckResult]:
    total = con.execute(f"SELECT count(*) FROM {schema}.transactions").fetchone()[0]
    latest_ts, staleness_days = con.execute(f"""
        SELECT max(try_cast(transaction_ts AS TIMESTAMP)) AS latest,
               date_diff('second', max(try_cast(transaction_ts AS TIMESTAMP)), current_localtimestamp()) / 86400.0
        FROM {schema}.transactions
    """).fetchone()

    if latest_ts is None:
        passed, failed = False, total
        message = "no valid transaction_ts values found"
    else:
        passed = staleness_days <= MAX_STALENESS_DAYS
        failed = 0 if passed else total
        message = f"latest transaction {staleness_days:.1f}d old, threshold {MAX_STALENESS_DAYS}d"

    return [CheckResult(
        table_name="transactions", column_name="transaction_ts", dimension="timeliness",
        check_name="max_staleness_days", passed=passed, total_rows=total, failed_rows=failed,
        threshold=MAX_STALENESS_DAYS, severity="warning" if passed else "high", message=message,
    )]
