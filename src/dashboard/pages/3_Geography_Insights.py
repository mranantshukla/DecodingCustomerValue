"""Geography Insights — regional opportunity map and quadrant classification."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from src.dashboard.data_access import load_view
from src.dashboard.theme import style_fig

st.set_page_config(page_title="Geography Insights", page_icon="🗺️", layout="wide")
st.title("🗺️ Geography Insights")

# US state name -> 2-letter code, so we can draw a choropleth.
STATE_ABBR = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
}

region = load_view("region_scorecard")
if region.empty:
    st.warning("Run `python -m src.pipeline` to generate region data.")
    st.stop()

region["state_code"] = region["location"].map(STATE_ABBR)
metric = st.selectbox(
    "Map metric", ["region_quality", "organic_demand", "promo_dependency", "avg_clv", "total_clv"]
)

fig = px.choropleth(
    region.dropna(subset=["state_code"]),
    locations="state_code",
    locationmode="USA-states",
    color=metric,
    scope="usa",
    color_continuous_scale="Blues",
    hover_name="location",
    title=f"{metric.replace('_', ' ').title()} by state",
)
st.plotly_chart(style_fig(fig), use_container_width=True)

st.divider()
st.subheader("Regional opportunity quadrant")
st.caption("Crossing region quality with promo dependency (vs medians) classifies each market.")
mq, mp = region["region_quality"].median(), region["promo_dependency"].median()


def quadrant(r):
    if r.region_quality >= mq and r.promo_dependency < mp:
        return "INVEST (healthy)"
    if r.region_quality >= mq and r.promo_dependency >= mp:
        return "FIX (good but subsidised)"
    if r.region_quality < mq and r.promo_dependency < mp:
        return "WATCH (low engagement)"
    return "HARVEST/RATIONALISE"


region["quadrant"] = region.apply(quadrant, axis=1)
fig = px.scatter(
    region,
    x="promo_dependency",
    y="region_quality",
    size="total_clv",
    color="quadrant",
    hover_name="location",
    size_max=30,
    labels={"promo_dependency": "Promo dependency", "region_quality": "Region quality"},
)
fig.add_vline(x=mp, line_dash="dash", line_color="grey")
fig.add_hline(y=mq, line_dash="dash", line_color="grey")
st.plotly_chart(style_fig(fig), use_container_width=True)

st.dataframe(region.sort_values("region_quality", ascending=False), use_container_width=True)
