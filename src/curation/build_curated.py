"""Build curated.* from rows that pass Pandera schema validation.

Per ADR 0002: curated is only populated from rows that pass schema-level
validation. Structural/type failures (from src/validation/schemas/*.py) are
excluded upstream; this step only dedupes surviving duplicate keys
(keep-first) and gates transactions on FK existence against already-loaded
curated parent tables.
"""
from src.db.connection import get_connection
from src.validation.runner import run_raw_validation


def build_curated(con, valid_frames=None):
    if valid_frames is None:
        valid_frames, _status = run_raw_validation(con)

    con.execute("DELETE FROM curated.transactions")
    con.execute("DELETE FROM curated.products")
    con.execute("DELETE FROM curated.customers")

    con.register("valid_customers", valid_frames["customers"])
    con.register("valid_products", valid_frames["products"])
    con.register("valid_transactions", valid_frames["transactions"])

    con.execute("""
        INSERT INTO curated.customers (customer_id, name, email, signup_date, country)
        SELECT customer_id, name, email, try_cast(signup_date AS DATE), country
        FROM (
            SELECT *, row_number() OVER (PARTITION BY customer_id ORDER BY _loaded_at) AS rn
            FROM valid_customers
        )
        WHERE rn = 1
    """)

    con.execute("""
        INSERT INTO curated.products (product_id, product_name, category, price)
        SELECT product_id, product_name, category, try_cast(trim(price, '$') AS DECIMAL(10,2))
        FROM (
            SELECT *, row_number() OVER (PARTITION BY product_id ORDER BY _loaded_at) AS rn
            FROM valid_products
        )
        WHERE rn = 1
    """)

    con.execute("""
        INSERT INTO curated.transactions
            (transaction_id, customer_id, product_id, quantity, unit_price,
             total_amount, transaction_ts, payment_method, status)
        SELECT d.transaction_id, d.customer_id, d.product_id,
               try_cast(d.quantity AS INTEGER), try_cast(d.unit_price AS DECIMAL(10,2)),
               try_cast(d.total_amount AS DECIMAL(12,2)), try_cast(d.transaction_ts AS TIMESTAMP),
               d.payment_method, d.status
        FROM (
            SELECT *, row_number() OVER (PARTITION BY transaction_id ORDER BY _loaded_at) AS rn
            FROM valid_transactions
        ) d
        WHERE d.rn = 1
          AND EXISTS (SELECT 1 FROM curated.customers c WHERE c.customer_id = d.customer_id)
          AND EXISTS (SELECT 1 FROM curated.products p WHERE p.product_id = d.product_id)
    """)

    con.unregister("valid_customers")
    con.unregister("valid_products")
    con.unregister("valid_transactions")

    for table in ("customers", "products", "transactions"):
        raw_n = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
        curated_n = con.execute(f"SELECT count(*) FROM curated.{table}").fetchone()[0]
        print(f"curated.{table}: {curated_n}/{raw_n} rows kept ({raw_n - curated_n} dropped)")


if __name__ == "__main__":
    con = get_connection()
    build_curated(con)
    con.close()
