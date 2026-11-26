"""Segment Explorer — persona economics and the behavioural-cluster overlay."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from src.dashboard.data_access import load_features, load_view
from src.dashboard.theme import PERSONA_COLORS, style_fig

st.set_page_config(page_title="Segment Explorer", page_icon="🧩", layout="wide")
st.title("🧩 Segment Explorer")

df = load_features()
ps = load_view("persona_scorecard")

st.subheader("Persona scorecard")
st.caption("Mutually-exclusive business personas — the segmentation leadership acts on.")
if not ps.empty:
    st.dataframe(ps, use_container_width=True)

c1, c2 = st.columns(2)
with c1:
    fig = px.scatter(
        df,
        x="promo_dependency_score",
        y="loyalty_score",
        size="estimated_clv_proxy",
        color="customer_persona",
        color_discrete_map=PERSONA_COLORS,
        size_max=18,
        opacity=0.6,
        title="Personas in promo × loyalty space",
        labels={"promo_dependency_score": "Promo dependency", "loyalty_score": "Loyalty"},
    )
    st.plotly_chart(style_fig(fig), use_container_width=True)
with c2:
    agg = (
        df.groupby("customer_persona")
        .agg(customers=("customer_id", "count"), avg_clv=("estimated_clv_proxy", "mean"))
        .reset_index()
    )
    fig = px.bar(
        agg.sort_values("avg_clv"),
        x="avg_clv",
        y="customer_persona",
        orientation="h",
        color="customer_persona",
        color_discrete_map=PERSONA_COLORS,
        title="Average CLV by persona",
        labels={"avg_clv": "Avg CLV", "customer_persona": ""},
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(style_fig(fig), use_container_width=True)

st.divider()
st.subheader("Behavioural cluster overlay (unsupervised validation)")
st.caption(
    "KMeans clusters (ordered low→high value) cross-tabbed against personas. "
    "Used to validate the rule-based personas, not to replace them."
)
ct = df.pivot_table(
    index="behaviour_cluster",
    columns="customer_persona",
    values="customer_id",
    aggfunc="count",
    fill_value=0,
)
fig = px.imshow(
    ct,
    text_auto=True,
    color_continuous_scale="Blues",
    aspect="auto",
    title="Cluster × persona counts",
)
st.plotly_chart(style_fig(fig), use_container_width=True)
