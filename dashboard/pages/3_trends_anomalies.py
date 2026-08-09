import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import plotly.graph_objects as go
import streamlit as st

from dashboard.components import inject_css
from dashboard.db import load_query
from dashboard.palette import CHROME, DIMENSION_COLOR, STATUS

st.set_page_config(page_title="Trends & Anomalies - Data Quality", page_icon="◆", layout="wide")
inject_css()
st.title("Trends & Anomalies")

metrics = load_query("metrics_timeseries")
anomalies = load_query("anomalies_recent")
runs = load_query("run_history")

st.subheader("Daily transaction volume vs. expected range")
daily = (
    metrics[metrics["metric_name"] == "daily_transaction_count"]
    .sort_values("captured_at")
    .drop_duplicates(subset="captured_at", keep="last")
)

if daily.empty:
    st.info("No transaction volume series recorded yet — run the validation pipeline.")
else:
    mean = daily["metric_value"].mean()
    std = daily["metric_value"].std(ddof=0)
    low, high = mean - 3 * std, mean + 3 * std

    fig = go.Figure()
    fig.add_scatter(
        x=list(daily["captured_at"]) + list(daily["captured_at"][::-1]),
        y=[high] * len(daily) + [low] * len(daily),
        fill="toself", fillcolor="rgba(195,194,183,0.35)",
        line=dict(color="rgba(0,0,0,0)"), hoverinfo="skip", showlegend=True, name="Expected range",
    )
    fig.add_scatter(
        x=daily["captured_at"], y=daily["metric_value"], mode="lines+markers", name="Observed",
        line=dict(color=DIMENSION_COLOR["timeliness"], width=2),
        marker=dict(size=7),
        hovertemplate="%{x|%Y-%m-%d}: %{y:.0f} transactions<extra></extra>",
    )
    anomaly_days = anomalies[anomalies["metric_name"] == "daily_transaction_count"]
    if not anomaly_days.empty:
        fig.add_scatter(
            x=daily.loc[daily["metric_value"].isin(anomaly_days["observed_value"]), "captured_at"],
            y=anomaly_days["observed_value"],
            mode="markers", name="Anomaly (|z| > 3)",
            marker=dict(size=12, color=STATUS["failed"], symbol="diamond", line=dict(width=1, color="white")),
            hovertemplate="%{y:.0f} transactions, flagged<extra></extra>",
        )
    fig.update_layout(
        plot_bgcolor=CHROME["surface"], paper_bgcolor=CHROME["surface"], font_color=CHROME["ink"],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        yaxis=dict(gridcolor=CHROME["gridline"], title="transactions / day"),
        xaxis=dict(title=None),
        margin=dict(t=10, b=10, l=10, r=10), height=380,
    )
    st.plotly_chart(fig, width="stretch")

st.divider()
st.subheader("Row count by table, across runs")
row_counts = metrics[metrics["metric_name"] == "row_count"].sort_values("captured_at")
if row_counts.empty:
    st.info("No row-count history yet.")
else:
    fig2 = go.Figure()
    for i, table in enumerate(sorted(row_counts["table_name"].unique())):
        sub = row_counts[row_counts["table_name"] == table]
        fig2.add_scatter(
            x=sub["captured_at"], y=sub["metric_value"], mode="lines+markers", name=table,
            line=dict(color=list(DIMENSION_COLOR.values())[i % len(DIMENSION_COLOR)], width=2),
        )
    fig2.update_layout(
        plot_bgcolor=CHROME["surface"], paper_bgcolor=CHROME["surface"], font_color=CHROME["ink"],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        yaxis=dict(gridcolor=CHROME["gridline"], title="rows"),
        margin=dict(t=10, b=10, l=10, r=10), height=340,
    )
    st.plotly_chart(fig2, width="stretch")

st.divider()
st.subheader("Run history")
st.dataframe(
    runs.assign(status=runs["status"].str.upper()),
    hide_index=True, width="stretch",
)
