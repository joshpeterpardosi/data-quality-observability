"""Shared result type and writer for dimension checks."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class CheckResult:
    table_name: str
    dimension: str
    check_name: str
    passed: bool
    total_rows: int
    failed_rows: int
    column_name: Optional[str] = None
    threshold: Optional[float] = None
    severity: str = "warning"
    message: str = ""

    @property
    def failure_rate(self) -> float:
        return round(self.failed_rows / self.total_rows, 4) if self.total_rows else 0.0


def insert_results(con, run_id, results):
    next_id = con.execute("SELECT coalesce(max(id), 0) FROM dq.check_results").fetchone()[0]
    for offset, r in enumerate(results, start=1):
        con.execute(
            """
            INSERT INTO dq.check_results
                (id, run_id, table_name, column_name, dimension, check_name,
                 passed, total_rows, failed_rows, failure_rate, threshold, severity, message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [next_id + offset, run_id, r.table_name, r.column_name, r.dimension, r.check_name,
             r.passed, r.total_rows, r.failed_rows, r.failure_rate, r.threshold, r.severity, r.message],
        )


def log_table_metrics(con, run_id, results):
    """Roll per-check results up into per-table row_count / check_failure_rate points."""
    agg = defaultdict(lambda: {"total_checks": 0, "failed_checks": 0, "total_rows": 0})
    for r in results:
        a = agg[r.table_name]
        a["total_checks"] += 1
        a["failed_checks"] += 0 if r.passed else 1
        a["total_rows"] = max(a["total_rows"], r.total_rows)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for table, a in agg.items():
        failure_rate = a["failed_checks"] / a["total_checks"] if a["total_checks"] else 0.0
        for metric_name, value in (("row_count", float(a["total_rows"])), ("check_failure_rate", failure_rate)):
            con.execute(
                "INSERT INTO dq.metrics_timeseries (run_id, table_name, metric_name, metric_value, captured_at) VALUES (?, ?, ?, ?, ?)",
                [run_id, table, metric_name, value, now],
            )
