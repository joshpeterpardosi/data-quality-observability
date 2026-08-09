"""Cross-table / aggregate SQL checks: orphan FK, freshness, anomaly."""
import datetime
import uuid

from src.validation.checks import anomaly, freshness, orphan_fk


def _seed(con, customers, products, transactions):
    con.execute("DELETE FROM raw.transactions")
    con.execute("DELETE FROM raw.products")
    con.execute("DELETE FROM raw.customers")
    for cid in customers:
        con.execute("INSERT INTO raw.customers (customer_id) VALUES (?)", [cid])
    for pid in products:
        con.execute("INSERT INTO raw.products (product_id) VALUES (?)", [pid])
    for row in transactions:
        con.execute(
            "INSERT INTO raw.transactions (transaction_id, customer_id, product_id, transaction_ts) VALUES (?, ?, ?, ?)",
            row,
        )


def test_orphan_fk_detects_missing_customer(con):
    _seed(
        con, customers=["C0001"], products=["P001"],
        transactions=[
            ["T1", "C0001", "P001", "2026-08-01 10:00:00"],
            ["T2", "C9999", "P001", "2026-08-01 10:00:00"],
        ],
    )
    results = orphan_fk.run(con, schema="raw")
    cust_check = next(r for r in results if r.column_name == "customer_id")
    assert not cust_check.passed
    assert cust_check.failed_rows == 1


def test_orphan_fk_passes_when_all_fks_resolve(con):
    _seed(
        con, customers=["C0001"], products=["P001"],
        transactions=[["T1", "C0001", "P001", "2026-08-01 10:00:00"]],
    )
    results = orphan_fk.run(con, schema="raw")
    assert all(r.passed for r in results)


def test_freshness_fails_on_stale_data(con):
    _seed(
        con, customers=["C0001"], products=["P001"],
        transactions=[["T1", "C0001", "P001", "2020-01-01 00:00:00"]],
    )
    [result] = freshness.run(con, schema="raw")
    assert not result.passed


def test_freshness_passes_on_recent_data(con):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _seed(
        con, customers=["C0001"], products=["P001"],
        transactions=[["T1", "C0001", "P001", now]],
    )
    [result] = freshness.run(con, schema="raw")
    assert result.passed


def test_anomaly_flags_volume_spike(con):
    base = datetime.datetime(2026, 1, 1)
    rows = []
    tid = 1
    for day in range(10):  # 10 normal days, 5 transactions each
        for _ in range(5):
            ts = (base + datetime.timedelta(days=day)).strftime("%Y-%m-%d %H:%M:%S")
            rows.append([f"T{tid}", "C0001", "P001", ts])
            tid += 1
    spike_day = (base + datetime.timedelta(days=10)).strftime("%Y-%m-%d")  # spike: 200 in one day
    for _ in range(200):
        rows.append([f"T{tid}", "C0001", "P001", f"{spike_day} 10:00:00"])
        tid += 1

    _seed(con, customers=["C0001"], products=["P001"], transactions=rows)
    outliers = anomaly.run(con, run_id=str(uuid.uuid4()), schema="raw")

    assert len(outliers) == 1
    assert outliers[0][4] == 200.0  # observed_value


def test_anomaly_no_outliers_on_flat_series(con):
    base = datetime.datetime(2026, 1, 1)
    rows = []
    tid = 1
    for day in range(10):
        for _ in range(5):
            ts = (base + datetime.timedelta(days=day)).strftime("%Y-%m-%d %H:%M:%S")
            rows.append([f"T{tid}", "C0001", "P001", ts])
            tid += 1

    _seed(con, customers=["C0001"], products=["P001"], transactions=rows)
    outliers = anomaly.run(con, run_id=str(uuid.uuid4()), schema="raw")

    assert outliers == []
