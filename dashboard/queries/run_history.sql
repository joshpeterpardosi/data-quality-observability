SELECT run_id, dataset, status, started_at, finished_at
FROM dq.validation_runs
ORDER BY started_at
