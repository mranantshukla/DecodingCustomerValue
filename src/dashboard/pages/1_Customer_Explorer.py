"""Customer Explorer — filter, inspect, and export the customer base."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from src.dashboard.data_access import load_features
from src.dashboard.theme import style_fig
from src.dashboard.ui import (
    apply_filter,
    global_filter_sidebar,
    inject_css,
    kpi_row,
    section,
)

st.set_page_config(page_title="Customer Explorer", page_icon="🔎", layout="wide")
inject_css()
st.title("🔎 Customer Explorer")

df = load_features()
state = global_filter_sidebar(df)
f = apply_filter(df, state)

# Per-page refinements that don't belong in the global filter.
with st.sidebar:
    st.markdown("### Local refinements")
    sort_by = st.selectbox(
        "Sort by",
        ["estimated_clv_proxy", "loyalty_score", "review_rating"],
        index=0,
    )
    show_n = st.slider(
        "Rows shown",
        50,
        1000,
        200,
        50,
        help="Paginated for responsiveness on the full 3,900-row table.",
    )

kpi_row(
    [
        {"label": "Customers in view", "value": f"{len(f):,}"},
        {
            "label": "Avg CLV",
            "value": f"${f['estimated_clv_proxy'].mean():,.0f}" if len(f) else "—",
        },
        {"label": "Avg loyalty", "value": f"{f['loyalty_score'].mean():.2f}" if len(f) else "—"},
        {
            "label": "Avg promo dep.",
            "value": f"{f['promo_dependency_score'].mean():.2f}" if len(f) else "—",
        },
    ]
)

section("Customer table", f"top {show_n:,} of {len(f):,} by {sort_by}")
left, right = st.columns([2, 1])
with left:
    cols = [
        "customer_id",
        "age",
        "gender",
        "category",
        "location",
        "loyalty_score",
        "promo_dependency_score",
        "estimated_clv_proxy",
        "revenue_contribution_tier",
        "customer_persona",
        "review_rating",
    ]
    sorted_f = f[cols].sort_values(sort_by, ascending=False)
    st.dataframe(sorted_f.head(show_n), use_container_width=True, height=460)
    st.download_button(
        "⬇ Download filtered customers (CSV)",
        sorted_f.to_csv(index=False),
        "customers_filtered.csv",
        "text/csv",
    )
with right:
    if len(f):
        fig = px.scatter(
            f,
            x="loyalty_score",
            y="estimated_clv_proxy",
            color="promo_dependency_score",
            color_continuous_scale="RdYlGn_r",
            labels={"loyalty_score": "Loyalty", "estimated_clv_proxy": "CLV proxy"},
            title="Loyalty vs value (colour = promo reliance)",
            hover_data=["customer_persona", "category", "location"],
        )
        st.plotly_chart(style_fig(fig), use_container_width=True)
