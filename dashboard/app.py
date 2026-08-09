import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st

from dashboard.components import inject_css, stat_tile
from dashboard.db import load_query

st.set_page_config(page_title="Data Quality Observability", page_icon="◆", layout="wide")
inject_css()

st.title("Data Quality Observability")
st.caption("E-commerce transaction pipeline: raw → curated, validated end to end.")

runs = load_query("latest_runs")
checks = load_query("check_results_latest")

col1, col2, col3, col4 = st.columns(4)
with col1:
    raw_run = runs[runs["dataset"] == "raw"]
    status = raw_run.iloc[0]["status"] if not raw_run.empty else "n/a"
    stat_tile("Latest raw run", status.upper(), sub="Pandera + SQL checks")
with col2:
    curated_run = runs[runs["dataset"] == "curated"]
    status = curated_run.iloc[0]["status"] if not curated_run.empty else "n/a"
    stat_tile("Latest curated run", status.upper(), sub="Post-gate verification")
with col3:
    total = len(checks)
    failed = int((~checks["passed"]).sum()) if total else 0
    stat_tile("Checks (latest runs)", f"{total - failed}/{total} passed", sub=f"{failed} failing")
with col4:
    anomalies = load_query("anomalies_recent")
    stat_tile("Open anomalies", str(len(anomalies)), sub="z-score > 3 on daily volume")

st.divider()

st.subheader("Run status by layer")
st.dataframe(
    runs.assign(status=runs["status"].map(lambda s: s.upper()))[
        ["dataset", "status", "started_at", "finished_at"]
    ],
    hide_index=True,
    width="stretch",
)

st.divider()
st.markdown(
    "Use the sidebar: **Overview** for pass/fail by dimension, **Check Drilldown** "
    "for the failing rows, **Trends & Anomalies** for volume drift and history over time."
)
