import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import plotly.graph_objects as go
import streamlit as st

from dashboard.components import inject_css
from dashboard.db import load_query
from dashboard.palette import CHROME, DIMENSION_ORDER, STATUS

st.set_page_config(page_title="Overview - Data Quality", page_icon="◆", layout="wide")
inject_css()
st.title("Overview")

checks = load_query("check_results_latest")
metrics = load_query("metrics_timeseries")
curated_counts = load_query("curated_row_counts")

dataset = st.radio("Layer", ["raw", "curated"], horizontal=True)
subset = checks[checks["dataset"] == dataset]

st.subheader(f"Checks by dimension — {dataset}")
by_dim = (
    subset.groupby(["dimension", "passed"]).size().unstack(fill_value=0)
    .reindex(DIMENSION_ORDER).fillna(0)
)
for col in (True, False):
    if col not in by_dim.columns:
        by_dim[col] = 0

fig = go.Figure()
fig.add_bar(
    name="Passed", x=by_dim.index, y=by_dim[True],
    marker_color=STATUS["passed"], hovertemplate="%{x}: %{y} passed<extra></extra>",
)
fig.add_bar(
    name="Failed", x=by_dim.index, y=by_dim[False],
    marker_color=STATUS["failed"], hovertemplate="%{x}: %{y} failed<extra></extra>",
)
fig.update_layout(
    barmode="stack",
    plot_bgcolor=CHROME["surface"],
    paper_bgcolor=CHROME["surface"],
    font_color=CHROME["ink"],
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    yaxis=dict(gridcolor=CHROME["gridline"], title="checks"),
    xaxis=dict(title=None),
    margin=dict(t=10, b=10, l=10, r=10),
    height=360,
)
st.plotly_chart(fig, width="stretch")

st.divider()
st.subheader("Curation gate: raw → curated row counts")

raw_counts = (
    metrics[(metrics["dataset"] == "raw") & (metrics["metric_name"] == "row_count")]
    .sort_values("captured_at")
    .groupby("table_name")
    .last()["metric_value"]
)
gate = curated_counts.set_index("table_name")["row_count"].to_frame("curated")
gate["raw"] = raw_counts
gate["dropped"] = gate["raw"] - gate["curated"]
gate["dropped_pct"] = (gate["dropped"] / gate["raw"] * 100).round(1)

fig2 = go.Figure()
fig2.add_bar(name="Curated", x=gate.index, y=gate["curated"], marker_color=STATUS["passed"])
fig2.add_bar(name="Dropped", x=gate.index, y=gate["dropped"], marker_color=STATUS["failed"])
fig2.update_layout(
    barmode="stack",
    plot_bgcolor=CHROME["surface"],
    paper_bgcolor=CHROME["surface"],
    font_color=CHROME["ink"],
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    yaxis=dict(gridcolor=CHROME["gridline"], title="rows"),
    margin=dict(t=10, b=10, l=10, r=10),
    height=340,
)
st.plotly_chart(fig2, width="stretch")
st.dataframe(gate.reset_index().rename(columns={"table_name": "table"}), hide_index=True, width="stretch")
