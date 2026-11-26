"""Decoding Customer Value — executive Streamlit application (home page).

Run from the repo root:
    streamlit run src/dashboard/app.py

This page is the executive cockpit. Reusable UI helpers live in ``ui.py`` and a
persistent global filter is shared across all pages via ``st.session_state``.
"""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from src.dashboard.data_access import kpis, load_features, load_report_text, load_view
from src.dashboard.theme import ACCENT, NAVY, PERSONA_COLORS, style_fig
from src.dashboard.ui import (
    apply_filter,
    caveat,
    global_filter_sidebar,
    inject_css,
    kpi_row,
    section,
)

st.set_page_config(page_title="Decoding Customer Value", page_icon="📊", layout="wide")
inject_css()

df = load_features()
filter_state = global_filter_sidebar(df)
view_df = apply_filter(df, filter_state)
k = kpis(view_df) if len(view_df) else kpis(df)

st.title("📊 Decoding Customer Value")
st.caption("A SQL-driven retention & loyalty intelligence platform for a D2C fashion brand.")

# --- KPI strip ---------------------------------------------------------------
kpi_row(
    [
        {
            "label": "Customers in view",
            "value": f"{k['customers']:,}",
            "help": "Population after the global filter (left).",
        },
        {
            "label": "Projected CLV",
            "value": f"${k['total_clv']/1e6:.1f}M",
            "help": "Forward 1–5yr CLV proxy. See FEATURE_GLOSSARY for the formula.",
        },
        {
            "label": "Top-20% value share",
            "value": f"{k['top20_share']:.0f}%",
            "help": "Concentration: % of CLV held by the top quintile of customers.",
        },
        {
            "label": "Avg loyalty",
            "value": f"{k['avg_loyalty']:.2f}",
            "help": "Canonical (margin-aware) loyalty score, 0–1.",
        },
        {
            "label": "Satisfied",
            "value": f"{k['pct_satisfied']:.0f}%",
            "help": "Share rating ≥ 3.8 (the configured CX floor).",
        },
    ]
)

caveat(
    "Discount, subscription, and gender are structurally entangled in the source — "
    "promo metrics are directional, not causal. See LIMITATIONS_AND_ETHICS for detail."
)

# --- Customer pyramid + promo×retention matrix ------------------------------
left, right = st.columns([1, 1])

with left:
    section("Customer value pyramid", "% of projected CLV by tier")
    tier = load_view("revenue_tier_contribution")
    if not tier.empty:
        order = ["Platinum", "Gold", "Silver", "Bronze"]
        tier["tier"] = tier["tier"].astype("category")
        tier = tier.set_index("tier").reindex(order).reset_index()
        fig = px.bar(
            tier,
            x="pct_clv",
            y="tier",
            orientation="h",
            text="pct_clv",
            color="tier",
            color_discrete_sequence=[NAVY, ACCENT, "#5FA8D3", "#A9C5DD"],
            labels={"pct_clv": "% of projected CLV", "tier": ""},
        )
        fig.update_traces(
            texttemplate="%{text:.0f}%",
            showlegend=False,
            hovertemplate="<b>%{y}</b><br>%{x:.1f}% of CLV<extra></extra>",
        )
        st.plotly_chart(style_fig(fig), use_container_width=True)
        st.caption(
            "A handful of Platinum customers carry a disproportionate share — protect them first."
        )

with right:
    section("Promo dependency × retention", "the strategic 2×2")
    m = load_view("promo_retention_matrix")
    if not m.empty:
        fig = px.scatter(
            m,
            x="promo_band",
            y="loyalty_band",
            size="total_clv",
            color="avg_clv",
            size_max=70,
            color_continuous_scale=["#C1483B", "#E0A458", "#3A8B5C"],
            labels={
                "promo_band": "Promo reliance",
                "loyalty_band": "Loyalty (retention proxy)",
                "avg_clv": "Avg CLV",
            },
        )
        fig.update_traces(
            hovertemplate="<b>%{y} · %{x}</b><br>Customers: %{customdata[0]:,}"
            "<br>Total CLV: $%{marker.size:,.0f}<extra></extra>",
            customdata=m[["customers"]].values,
        )
        st.plotly_chart(style_fig(fig), use_container_width=True)
        st.caption(
            "Bubble = total CLV. High-Loy / Low-Promo is the healthy core; "
            "High-Loy / High-Promo is margin at risk."
        )

# --- Persona contribution ---------------------------------------------------
section("Where the value sits", "persona-level CLV share")
ps = load_view("persona_scorecard")
if not ps.empty:
    fig = px.bar(
        ps.sort_values("pct_of_clv"),
        x="pct_of_clv",
        y="customer_persona",
        orientation="h",
        color="customer_persona",
        color_discrete_map=PERSONA_COLORS,
        hover_data=["customers", "avg_clv", "avg_promo_dependency", "pct_satisfied"],
        labels={"pct_of_clv": "% of projected CLV", "customer_persona": ""},
    )
    fig.update_layout(showlegend=False)
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>%{x:.1f}% of CLV"
        "<br>Customers: %{customdata[0]:,}"
        "<br>Avg CLV: $%{customdata[1]:,.0f}"
        "<br>Promo dep.: %{customdata[2]:.2f}"
        "<br>Satisfied: %{customdata[3]:.0%}<extra></extra>"
    )
    st.plotly_chart(style_fig(fig), use_container_width=True)

with st.expander("📄 Executive summary (auto-generated)"):
    txt = load_report_text("executive_summary.md")
    st.markdown(txt or "_Run `python -m src.pipeline` to generate the summary._")

st.sidebar.markdown("### Navigation")
st.sidebar.success(
    "Use the pages above to explore customers, segments, geography, " "and run the simulators."
)
