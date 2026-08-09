SELECT run_id, dataset, status, started_at, finished_at
FROM dq.validation_runs
QUALIFY row_number() OVER (PARTITION BY dataset ORDER BY started_at DESC) = 1
ORDER BY dataset
