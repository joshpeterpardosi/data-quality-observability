"""Single entry point for opening the DuckDB warehouse. Applies DDL on connect."""
import glob
import os

import duckdb

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(_ROOT, "data", "duckdb", "warehouse.duckdb")
DDL_DIR = os.path.join(os.path.dirname(__file__), "ddl")


def get_connection(db_path: str = DB_PATH) -> duckdb.DuckDBPyConnection:
    if os.path.dirname(db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    con = duckdb.connect(db_path)
    for ddl_file in sorted(glob.glob(os.path.join(DDL_DIR, "*.sql"))):
        with open(ddl_file) as f:
            con.execute(f.read())
    return con
