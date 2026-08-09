"""Load CSVs from data/raw/ into raw.* tables, all-VARCHAR, as landed."""
import os

from src.db.connection import get_connection

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.path.join(_ROOT, "data", "raw")

TABLE_COLUMNS = {
    "customers": ["customer_id", "name", "email", "signup_date", "country"],
    "products": ["product_id", "product_name", "category", "price"],
    "transactions": [
        "transaction_id", "customer_id", "product_id", "quantity", "unit_price",
        "total_amount", "transaction_ts", "payment_method", "status",
    ],
}


def load_raw(con):
    for table, cols in TABLE_COLUMNS.items():
        csv_path = os.path.join(RAW_DIR, f"{table}.csv")
        con.execute(f"DELETE FROM raw.{table}")
        con.execute(f"""
            INSERT INTO raw.{table} ({", ".join(cols)})
            SELECT {", ".join(cols)} FROM read_csv_auto(?, ALL_VARCHAR=TRUE)
        """, [csv_path])
        n = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
        print(f"raw.{table}: {n} rows")


if __name__ == "__main__":
    con = get_connection()
    load_raw(con)
    con.close()
