"""Reference-palette color roles shared across dashboard pages.

Values from the dataviz skill's validated default palette (light-surface
steps; this dashboard runs Streamlit's light theme, see .streamlit/config.toml).
"""

STATUS = {
    "passed": "#0ca30c",
    "warning": "#fab219",
    "failed": "#d03b3b",
    "running": "#898781",
}

SEVERITY = {
    "critical": "#d03b3b",
    "high": "#ec835a",
    "medium": "#fab219",
    "warning": "#0ca30c",
}

CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]

DIMENSION_ORDER = ["completeness", "uniqueness", "validity", "consistency", "timeliness"]
DIMENSION_COLOR = dict(zip(DIMENSION_ORDER, CATEGORICAL))

CHROME = {
    "surface": "#fcfcfb",
    "page": "#f9f9f7",
    "ink": "#0b0b0b",
    "ink_secondary": "#52514e",
    "muted": "#898781",
    "gridline": "#e1e0d9",
    "baseline": "#c3c2b7",
}
