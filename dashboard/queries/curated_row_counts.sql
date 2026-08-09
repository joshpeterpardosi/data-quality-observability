SELECT 'customers' AS table_name, count(*) AS row_count FROM curated.customers
UNION ALL SELECT 'products', count(*) FROM curated.products
UNION ALL SELECT 'transactions', count(*) FROM curated.transactions
