SELECT m.run_id, m.table_name, m.metric_name, m.metric_value, m.captured_at, r.dataset
FROM dq.metrics_timeseries m
JOIN dq.validation_runs r USING (run_id)
ORDER BY m.captured_at
