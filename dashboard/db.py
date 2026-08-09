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
    return get_connection()


def load_query(name: str):
    with open(os.path.join(QUERIES_DIR, f"{name}.sql")) as f:
        sql = f.read()
    return get_con().execute(sql).df()
