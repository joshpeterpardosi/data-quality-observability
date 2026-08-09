SELECT a.*, r.dataset
FROM dq.anomalies a
JOIN dq.validation_runs r USING (run_id)
ORDER BY a.detected_at DESC
