"""Promo Impact Simulator — model the margin recovery and churn risk of a sunset.

The core decision-support tool for the promotional sunset plan. Pick which
promo-reliance tier(s) lose discounts, set assumptions (margin recovered per
discounted dollar, and the churn elasticity of discount-dependent customers),
and see the projected net P&L impact with a transparent calculation.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.dashboard.data_access import load_features
from src.dashboard.theme import GOOD, RISK, style_fig

st.set_page_config(page_title="Promo Impact Simulator", page_icon="✂️", layout="wide")
st.title("✂️ Promotional Sunset Simulator")
st.caption(
    "Estimate the net effect of withdrawing discounts from selected customer tiers. "
    "Assumptions are explicit and adjustable — this is a decision aid, not a forecast."
)

df = load_features()
discounted = df[df["discount_applied"] == "Yes"].copy()

with st.sidebar:
    st.header("Sunset scope & assumptions")
    tiers = st.multiselect(
        "Withdraw discounts from promo tiers",
        sorted(df["promo_reliance_tier"].dropna().unique()),
        default=["Full-Price Loyalist", "Occasional Discount"],
    )
    margin_pts = st.slider(
        "Gross margin recovered per discounted $",
        0.05,
        0.40,
        0.15,
        0.01,
        help="Assumed margin restored when a discount is removed.",
    )
    churn_elasticity = st.slider(
        "Churn rate among affected discount-dependent customers",
        0.0,
        0.6,
        0.25,
        0.05,
        help="Share of affected DISCOUNT-DEPENDENT customers expected to lapse.",
    )

affected = discounted[discounted["promo_reliance_tier"].isin(tiers)]
# Margin recovered = recovered margin points on the affected discounted spend (annualised proxy).
recovered_margin = (affected["annual_value"] * margin_pts).sum()

# Churn risk applies primarily to discount-dependent customers in scope.
dep = affected[affected["promo_reliance_tier"] == "Discount-Dependent"]
churned_clv = dep["estimated_clv_proxy"].sum() * churn_elasticity
net = recovered_margin - churned_clv

c1, c2, c3, c4 = st.columns(4)
c1.metric("Customers affected", f"{len(affected):,}")
c2.metric("Annual margin recovered", f"${recovered_margin/1e6:.2f}M")
c3.metric("CLV at churn risk", f"${churned_clv/1e6:.2f}M")
c4.metric(
    "Net projected impact", f"${net/1e6:.2f}M", delta=f"{'favourable' if net>0 else 'unfavourable'}"
)

fig = go.Figure(
    go.Waterfall(
        orientation="v",
        measure=["relative", "relative", "total"],
        x=["Margin recovered", "CLV at risk", "Net impact"],
        y=[recovered_margin, -churned_clv, 0],
        text=[f"+${recovered_margin/1e6:.2f}M", f"-${churned_clv/1e6:.2f}M", f"${net/1e6:.2f}M"],
        connector={"line": {"color": "#8A99A8"}},
        increasing={"marker": {"color": GOOD}},
        decreasing={"marker": {"color": RISK}},
        totals={"marker": {"color": "#16324F"}},
    )
)
fig.update_layout(title="Projected P&L impact of the sunset", showlegend=False)
st.plotly_chart(style_fig(fig), use_container_width=True)

st.success(
    "**Recommended sequencing:** start with Full-Price Loyalists and Occasional-Discount "
    "tiers (near-zero churn elasticity, pure margin recovery). Defer Discount-Dependent "
    "customers to a later wave with a softer landing (loyalty perks, not price)."
)

with st.expander("How this is calculated"):
    st.markdown(
        "- **Margin recovered** = Σ(annual_value × margin points) over affected customers.\n"
        "- **CLV at risk** = Σ(CLV of affected *discount-dependent* customers) × churn rate.\n"
        "- **Net impact** = margin recovered − CLV at risk.\n\n"
        "Full-price-leaning tiers contribute margin with little churn risk; discount-dependent "
        "customers carry the churn exposure, which is why the plan sequences them last."
    )
