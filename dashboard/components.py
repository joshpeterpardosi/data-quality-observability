"""Small reusable HTML/CSS pieces: stat tile. Kept plain per dataviz skill's Tier 1 spec."""
import streamlit as st

from dashboard.palette import CHROME

_CSS = f"""
<style>
.dq-stat-tile {{
    background: {CHROME["surface"]};
    border: 1px solid {CHROME["gridline"]};
    border-radius: 10px;
    padding: 16px 18px;
}}
.dq-stat-label {{
    font-size: 0.8rem;
    color: {CHROME["muted"]};
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}
.dq-stat-value {{
    font-size: 1.9rem;
    font-weight: 600;
    color: {CHROME["ink"]};
    line-height: 1.1;
}}
.dq-stat-sub {{
    font-size: 0.82rem;
    color: {CHROME["ink_secondary"]};
    margin-top: 2px;
}}
</style>
"""


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)


def stat_tile(label: str, value: str, sub: str = ""):
    sub_html = f'<div class="dq-stat-sub">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="dq-stat-tile"><div class="dq-stat-label">{label}</div>'
        f'<div class="dq-stat-value">{value}</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )
