"""Loyalty Simulator — re-weight the loyalty model and see who moves.

Lets a stakeholder interrogate the margin-aware loyalty definition: "what if we
cared less about satisfaction and more about frequency?" The score recomputes
live and we show how top-tier membership and its CLV shift — making the model's
assumptions tangible and challengeable.
"""

from __future__ import annotations

import numpy as np
import plotly.express as px
import streamlit as st

from src.dashboard.data_access import load_features
from src.dashboard.theme import ACCENT, NAVY, style_fig
from src.feature_engineering.loyalty import V2_WEIGHTS

st.set_page_config(page_title="Loyalty Simulator", page_icon="🎚️", layout="wide")
st.title("🎚️ Loyalty Simulator")
st.caption(
    "Adjust the weights of the margin-aware loyalty model (Definition B) and watch "
    "the champion tier and its value re-form. Defaults match production."
)

df = load_features()
prev_norm = (df["previous_purchases"] - df["previous_purchases"].min()) / (
    df["previous_purchases"].max() - df["previous_purchases"].min()
)

with st.sidebar:
    st.header("Loyalty weights")
    w_prev = st.slider("Previous purchases", 0.0, 1.0, V2_WEIGHTS["prev"], 0.05)
    w_freq = st.slider("Frequency", 0.0, 1.0, V2_WEIGHTS["freq"], 0.05)
    w_sub = st.slider("Subscription", 0.0, 1.0, V2_WEIGHTS["sub"], 0.05)
    w_sat = st.slider("Satisfaction", 0.0, 1.0, V2_WEIGHTS["sat"], 0.05)
    w_ndr = st.slider("Full-price ratio", 0.0, 1.0, V2_WEIGHTS["ndr"], 0.05)

weights = np.array([w_prev, w_freq, w_sub, w_sat, w_ndr])
if weights.sum() == 0:
    st.warning("All weights are zero — set at least one above zero.")
    st.stop()
weights = weights / weights.sum()  # renormalise so the score stays in [0,1]

sim = (
    weights[0] * prev_norm
    + weights[1] * df["freq_rank_norm"]
    + weights[2] * df["subscription_status_flag"].astype(float)
    + weights[3] * df["satisfaction_norm"]
    + weights[4] * df["non_discount_purchase_ratio"]
).clip(0, 1)

base = df["loyalty_score"]
top_n = max(1, len(df) // 5)
base_top = set(df.nlargest(top_n, "loyalty_score").index)
sim_top = set(sim.nlargest(top_n).index)
overlap = len(base_top & sim_top) / len(base_top | sim_top)

c1, c2, c3 = st.columns(3)
c1.metric("Mean loyalty", f"{sim.mean():.3f}", f"{sim.mean()-base.mean():+.3f}")
c2.metric("Champion-tier overlap vs prod", f"{overlap:.0%}")
c3.metric(
    "CLV in new champion tier", f"${df.loc[list(sim_top), 'estimated_clv_proxy'].sum()/1e6:.2f}M"
)

fig = px.histogram(
    x=base, nbins=40, opacity=0.5, title="Loyalty distribution: production vs simulated"
)
fig.add_histogram(x=sim, nbinsx=40, opacity=0.5, name="Simulated", marker_color=ACCENT)
fig.data[0].name = "Production"
fig.data[0].marker.color = NAVY
fig.update_layout(barmode="overlay", legend_title_text="")
st.plotly_chart(style_fig(fig), use_container_width=True)

st.info(
    "**Robustness read-out.** A high overlap (≥ ~70%) means the champion list is stable to "
    "re-weighting — the model is robust. A sharp drop signals the conclusion is sensitive to a "
    "single assumption and should be treated with caution."
)
