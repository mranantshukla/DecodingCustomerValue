"""Shared theming and chart helpers for the Streamlit app.

Centralising the palette and Plotly defaults here keeps every page on-brand and
keeps the page modules focused on narrative, not styling. Consistent theming is
what separates an executive dashboard from a collection of charts.
"""

from __future__ import annotations

# Restrained, executive palette: one accent, one warning, neutral greys.
NAVY = "#16324F"
ACCENT = "#2E86AB"
GOLD = "#E0A458"
RISK = "#C1483B"
GOOD = "#3A8B5C"
GREY = "#8A99A8"
SEQ = [NAVY, ACCENT, "#5FA8D3", GOLD, GREY]

PERSONA_COLORS = {
    "Premium Loyalist": GOOD,
    "Loyal Full-Price": ACCENT,
    "Promo-Dependent High-Value": GOLD,
    "At-Risk Premium": RISK,
    "High-Value Low-Frequency": "#6C5B7B",
    "Promo Hunter": "#B5651D",
    "Standard": GREY,
}

PLOTLY_LAYOUT = {
    "template": "plotly_white",
    "font": {"family": "Segoe UI, Helvetica, Arial", "size": 13, "color": NAVY},
    "title": {"font": {"size": 17, "color": NAVY}},
    "margin": {"l": 40, "r": 20, "t": 50, "b": 40},
    "colorway": SEQ,
    "hoverlabel": {"font_size": 12},
}


def style_fig(fig):
    """Apply the house layout to a Plotly figure and return it."""
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig


def metric_help() -> dict[str, str]:
    """Tooltips so every KPI on the dashboard is self-explaining."""
    return {
        "clv": "Forward 1–5yr value proxy: basket × annual frequency × tenure × margin factor.",
        "loyalty": "Canonical (margin-aware) loyalty score, 0–1. Rewards full-price repeat buying.",
        "promo": "Promo dependency, 0–1. Blends a customer's discount use with their micro-segment's.",
        "premium": "Share of customers in the top 20% of projected CLV.",
    }
