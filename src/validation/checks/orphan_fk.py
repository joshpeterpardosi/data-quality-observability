"""Foreign-key existence checks, raw layer."""
from src.validation.checks.base import CheckResult

FOREIGN_KEYS = [
    ("transactions", "customer_id", "customers", "customer_id"),
    ("transactions", "product_id", "products", "product_id"),
]


def run(con, schema="raw") -> list[CheckResult]:
    results = []
    for table, col, parent, parent_col in FOREIGN_KEYS:
        total = con.execute(f"SELECT count(*) FROM {schema}.{table}").fetchone()[0]
        orphans = con.execute(f"""
            SELECT count(*) FROM {schema}.{table} t
            WHERE t.{col} IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM {schema}.{parent} p WHERE p.{parent_col} = t.{col})
        """).fetchone()[0]
        passed = orphans == 0
        results.append(CheckResult(
            table_name=table, column_name=col, dimension="consistency",
            check_name="referential_integrity", passed=passed, total_rows=total,
            failed_rows=orphans, threshold=0.0, severity="warning" if passed else "high",
            message=f"{orphans} {col} values missing from {parent}.{parent_col}",
        ))
    return results
