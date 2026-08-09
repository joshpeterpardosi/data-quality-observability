WITH latest AS (
    SELECT run_id, dataset
    FROM dq.validation_runs
    QUALIFY row_number() OVER (PARTITION BY dataset ORDER BY started_at DESC) = 1
)
SELECT l.dataset, c.*
FROM dq.check_results c
JOIN latest l USING (run_id)
ORDER BY l.dataset, c.dimension, c.table_name, c.column_name
