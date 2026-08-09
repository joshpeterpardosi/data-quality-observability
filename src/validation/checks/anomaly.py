"""Daily transaction-volume anomaly detection (z-score).

Writes outlier days to dq.anomalies and the full daily series to
dq.metrics_timeseries -- the dashboard never queries raw.* directly (ADR
0002), so the complete series has to land in dq.* for the trends page to
plot an observed-vs-expected band over time.
"""


def run(con, run_id, schema="raw"):
    df = con.execute(f"""
        SELECT date_trunc('day', try_cast(transaction_ts AS TIMESTAMP)) AS day, count(*) AS cnt
        FROM {schema}.transactions
        WHERE try_cast(transaction_ts AS TIMESTAMP) IS NOT NULL
        GROUP BY 1
    """).df()
    if df.empty:
        return []

    mean = df["cnt"].mean()
    std = df["cnt"].std(ddof=0)
    if std == 0:
        return []

    df["z"] = (df["cnt"] - mean) / std

    for row in df.itertuples():
        con.execute(
            "INSERT INTO dq.metrics_timeseries (run_id, table_name, metric_name, metric_value, captured_at) VALUES (?, ?, ?, ?, ?)",
            [run_id, "transactions", "daily_transaction_count", float(row.cnt), row.day],
        )

    outliers = df[df["z"].abs() > 3]

    next_id = con.execute("SELECT coalesce(max(id), 0) FROM dq.anomalies").fetchone()[0]
    rows = []
    for offset, row in enumerate(outliers.itertuples(), start=1):
        rows.append([
            next_id + offset, run_id, "transactions", "daily_transaction_count",
            float(row.cnt), float(mean - 3 * std), float(mean + 3 * std), float(row.z),
        ])
        con.execute("""
            INSERT INTO dq.anomalies
                (id, run_id, table_name, metric_name, observed_value, expected_low, expected_high, z_score, detected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)
        """, rows[-1])
    return rows
