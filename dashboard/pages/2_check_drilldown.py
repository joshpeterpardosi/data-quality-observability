import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st

from dashboard.components import inject_css
from dashboard.db import load_query
from dashboard.palette import DIMENSION_ORDER, SEVERITY

st.set_page_config(page_title="Check Drilldown - Data Quality", page_icon="◆", layout="wide")
inject_css()
st.title("Check Drilldown")
st.caption("Every check from the latest run, per layer. Filter down to what's failing.")

checks = load_query("check_results_latest")

col1, col2, col3 = st.columns(3)
with col1:
    dataset = st.selectbox("Layer", sorted(checks["dataset"].unique()))
with col2:
    dims = st.multiselect("Dimension", DIMENSION_ORDER, default=DIMENSION_ORDER)
with col3:
    only_failed = st.checkbox("Show failing only", value=True)

view = checks[(checks["dataset"] == dataset) & (checks["dimension"].isin(dims))]
if only_failed:
    view = view[~view["passed"]]

st.write(f"{len(view)} checks")

display_cols = [
    "table_name", "column_name", "dimension", "check_name", "passed",
    "total_rows", "failed_rows", "failure_rate", "threshold", "severity", "message",
]
view = view[display_cols].sort_values(["passed", "severity"])


def _row_style(row):
    if row["passed"]:
        return [""] * len(row)
    color = SEVERITY.get(row["severity"], SEVERITY["medium"])
    return [f"background-color: {color}22"] * len(row)


st.dataframe(
    view.style.apply(_row_style, axis=1).format({"failure_rate": "{:.2%}", "threshold": "{:.2%}"}),
    hide_index=True,
    width="stretch",
    height=560,
)
