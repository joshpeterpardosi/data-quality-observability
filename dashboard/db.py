"""Connection + named-query loader shared by every dashboard page.

Per ADR 0002: the dashboard only ever reads dq.* (plus curated.* for row
counts) -- never raw.* -- so a broken ingestion run can't corrupt what's
rendered here.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st

from src.db.connection import get_connection

QUERIES_DIR = os.path.join(os.path.dirname(__file__), "queries")


@st.cache_resource
def get_con():
    con = get_connection()
    _bootstrap_if_empty(con)
    return con


def _bootstrap_if_empty(con):
    """First run on a fresh deploy (e.g. Streamlit Cloud): no CLI step ran the
    pipeline first, so do it here, once, before any page queries dq.*."""
    if con.execute("SELECT count(*) FROM raw.customers").fetchone()[0] > 0:
        return

    import glob

    from src.curation.build_curated import build_curated
    from src.ingestion.load_raw import load_raw
    from src.validation.runner import run_curated_validation, run_raw_validation

    raw_dir = os.path.join(_ROOT, "data", "raw")
    if not glob.glob(os.path.join(raw_dir, "*.csv")):
        from scripts.generate_synthetic_data import main as generate_data
        generate_data()

    load_raw(con)
    valid_frames, _status = run_raw_validation(con)
    build_curated(con, valid_frames)
    run_curated_validation(con)


def load_query(name: str):
    with open(os.path.join(QUERIES_DIR, f"{name}.sql")) as f:
        sql = f.read()
    return get_con().execute(sql).df()
