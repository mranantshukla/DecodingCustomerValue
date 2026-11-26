"""Reusable Streamlit UI helpers + a small CSS pass.

Pulled out of ``app.py`` and the pages so every screen looks the same. Keep this
file small — its job is consistency, not feature creep. Anything fancier than
what's here is almost certainly the wrong tradeoff for an executive dashboard.
"""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import contextmanager

import streamlit as st

from src.dashboard.theme import ACCENT, GOOD, GREY, NAVY, RISK

# ---------------------------------------------------------------------------
# CSS — a tight, restrained pass for an executive feel
# ---------------------------------------------------------------------------
_CSS = f"""
<style>
/* Tighter top padding so KPI cards sit at eye-level. */
.block-container {{ padding-top: 1.4rem; padding-bottom: 2.5rem; }}

/* KPI card — bordered tile with subtle hover lift. */
div[data-testid="stMetric"] {{
    background: #FFFFFF;
    border: 1px solid #E6EAF0;
    border-radius: 10px;
    padding: 14px 16px 12px 16px;
    transition: box-shadow 120ms ease, transform 120ms ease;
}}
div[data-testid="stMetric"]:hover {{
    box-shadow: 0 4px 14px rgba(22,50,79,0.08);
    transform: translateY(-1px);
}}
div[data-testid="stMetricLabel"] p {{ color: {GREY}; font-size: 0.78rem; letter-spacing: 0.02em; }}
div[data-testid="stMetricValue"] {{ color: {NAVY}; font-weight: 600; }}

/* Section headers above charts. */
.dcv-section {{
    display: flex; align-items: baseline; gap: 12px;
    margin: 22px 0 10px 0; padding-bottom: 6px; border-bottom: 1px solid #ECEFF3;
}}
.dcv-section h3 {{
    color: {NAVY}; margin: 0; font-size: 1.05rem; font-weight: 600;
}}
.dcv-section span {{
    color: {GREY}; font-size: 0.85rem;
}}
.dcv-caveat {{
    background: #FFF7E8; border-left: 3px solid {RISK}; padding: 8px 12px;
    border-radius: 4px; color: {NAVY}; font-size: 0.85rem; margin: 4px 0 10px 0;
}}
/* Subtle sidebar grouping. */
section[data-testid="stSidebar"] h3 {{
    color: {NAVY}; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em;
    margin-top: 1rem; border-bottom: 1px solid #ECEFF3; padding-bottom: 4px;
}}
</style>
"""


def inject_css() -> None:
    """Add the house CSS once per page."""
    st.markdown(_CSS, unsafe_allow_html=True)


def section(title: str, sub: str = "") -> None:
    """Render a section header with optional sub-text."""
    sub_html = f"<span>{sub}</span>" if sub else ""
    st.markdown(
        f"<div class='dcv-section'><h3>{title}</h3>{sub_html}</div>", unsafe_allow_html=True
    )


def caveat(text: str) -> None:
    """Render the standard data-caveat callout (subtle, always visible)."""
    st.markdown(f"<div class='dcv-caveat'>⚠ {text}</div>", unsafe_allow_html=True)


def kpi_row(items: Iterable[dict]) -> None:
    """Render a row of KPI cards from a list of dicts.

    Each dict accepts: ``label``, ``value`` (str), optional ``delta``, ``help``.
    """
    items = list(items)
    cols = st.columns(len(items))
    for col, it in zip(cols, items):
        col.metric(
            label=it["label"],
            value=it["value"],
            delta=it.get("delta"),
            help=it.get("help"),
        )


# ---------------------------------------------------------------------------
# Global filter state — persistent across pages via st.session_state
# ---------------------------------------------------------------------------
_FILTER_KEY = "dcv_global_filter"


def init_global_filter(df) -> None:
    """Initialise the shared filter state once."""
    if _FILTER_KEY not in st.session_state:
        st.session_state[_FILTER_KEY] = {
            "personas": [],
            "categories": [],
            "locations": [],
            "min_loyalty": 0.0,
            "premium_only": False,
        }


def global_filter_sidebar(df) -> dict:
    """Render the persistent global filter in the sidebar; return the state."""
    init_global_filter(df)
    state = st.session_state[_FILTER_KEY]
    with st.sidebar:
        st.markdown("### Global filter")
        state["personas"] = st.multiselect(
            "Persona", sorted(df["customer_persona"].unique()), default=state["personas"]
        )
        state["categories"] = st.multiselect(
            "Category", sorted(df["category"].unique()), default=state["categories"]
        )
        state["locations"] = st.multiselect(
            "Location", sorted(df["location"].unique()), default=state["locations"]
        )
        state["min_loyalty"] = st.slider(
            "Min loyalty score", 0.0, 1.0, float(state["min_loyalty"]), 0.05
        )
        state["premium_only"] = st.checkbox("Premium only", value=state["premium_only"])
        if st.button("Reset filter"):
            st.session_state[_FILTER_KEY] = {
                "personas": [],
                "categories": [],
                "locations": [],
                "min_loyalty": 0.0,
                "premium_only": False,
            }
            st.rerun()
    return st.session_state[_FILTER_KEY]


def apply_filter(df, state: dict):
    """Apply the global filter state to a feature DataFrame."""
    f = df
    if state["personas"]:
        f = f[f["customer_persona"].isin(state["personas"])]
    if state["categories"]:
        f = f[f["category"].isin(state["categories"])]
    if state["locations"]:
        f = f[f["location"].isin(state["locations"])]
    f = f[f["loyalty_score"] >= state["min_loyalty"]]
    if state["premium_only"]:
        f = f[f["premium_customer_flag"] == 1]
    return f


@contextmanager
def card(border: bool = True):
    """Simple chart container — Streamlit native + a light wrapper for spacing."""
    container = st.container(border=border)
    with container:
        yield container


# Re-export colour palette for page convenience.
__all__ = [
    "inject_css",
    "section",
    "caveat",
    "kpi_row",
    "card",
    "init_global_filter",
    "global_filter_sidebar",
    "apply_filter",
    "NAVY",
    "ACCENT",
    "GOOD",
    "RISK",
]
