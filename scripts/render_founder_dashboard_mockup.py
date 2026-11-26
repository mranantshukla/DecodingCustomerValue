"""Render the Founder Dashboard mockup PNG (closest substitute for a .pbix).

Produces `assets/founder_dashboard_mockup.png` — a single 2×2 image containing
the four panels mandated by the Problem Statement PDF. Matplotlib only (already
in `requirements.txt`); no Plotly / no Power BI Desktop needed.

Run:
    python scripts/render_founder_dashboard_mockup.py

The script reads the SQL view exports under `reports/sql_exports/`. Run
`python -m src.pipeline` first if those files are absent.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import get_settings  # noqa: E402

# House palette (matches src/dashboard/theme.py and powerbi/theme.json).
NAVY = "#16324F"
ACCENT = "#2E86AB"
LIGHT_BLUE = "#5FA8D3"
PALE_BLUE = "#A9C5DD"
GOLD = "#E0A458"
RISK = "#C1483B"
GOOD = "#3A8B5C"
GREY = "#8A99A8"

PERSONA_COLORS = {
    "Premium Loyalist": GOOD,
    "Loyal Full-Price": ACCENT,
    "Promo-Dependent High-Value": GOLD,
    "At-Risk Premium": RISK,
    "High-Value Low-Frequency": "#6C5B7B",
    "Promo Hunter": "#B5651D",
    "Standard": GREY,
}


def _load(name: str) -> pd.DataFrame:
    settings = get_settings()
    path = settings.reports_path / "sql_exports" / f"{name}.csv"
    if not path.exists():
        sys.exit(f"Missing {path} — run `python -m src.pipeline` first.")
    return pd.read_csv(path)


def _panel_pyramid(ax: plt.Axes) -> None:
    """Panel ① — Customer Pyramid: 100% stacked bar by value tier."""
    tier = _load("revenue_tier_contribution")
    order = ["Platinum", "Gold", "Silver", "Bronze"]
    tier = tier.set_index("tier").reindex(order).reset_index()
    colours = [NAVY, ACCENT, LIGHT_BLUE, PALE_BLUE]
    y_pos = list(range(len(tier)))
    ax.barh(y_pos, tier["pct_clv"], color=colours, height=0.65, edgecolor="white")
    for i, v in enumerate(tier["pct_clv"]):
        ax.text(v + 1.2, i, f"{v:.0f}%", va="center", fontsize=10, color=NAVY, fontweight="600")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(tier["tier"], fontsize=10)
    ax.invert_yaxis()
    ax.set_xlim(0, tier["pct_clv"].max() * 1.15)
    ax.set_xlabel("% of projected CLV", fontsize=9, color=GREY)
    ax.set_title(
        "① Customer Value Pyramid", loc="left", fontsize=12, color=NAVY, fontweight="600", pad=10
    )
    ax.text(
        0,
        -0.95,
        f"Platinum (top 25% of customers) holds {tier['pct_clv'].iloc[0]:.0f}% of CLV",
        fontsize=9,
        color=GREY,
        style="italic",
    )
    _strip_chart(ax)


def _panel_promo_retention(ax: plt.Axes) -> None:
    """Panel ② — Promo Dependency × Retention, BY SEGMENT (persona scatter)."""
    df = _load("promo_retention_by_persona")
    sizes = (df["customers"] / df["customers"].max()) * 1800 + 80
    colours = [PERSONA_COLORS.get(p, GREY) for p in df["customer_persona"]]
    ax.scatter(
        df["avg_promo_dependency"],
        df["avg_loyalty"],
        s=sizes,
        c=colours,
        alpha=0.75,
        edgecolors="white",
        linewidth=1.2,
    )
    # Quadrant lines.
    avg_loy = df["avg_loyalty"].mean()
    ax.axvline(0.5, ls="--", color=GREY, lw=0.8, alpha=0.6)
    ax.axhline(avg_loy, ls="--", color=GREY, lw=0.8, alpha=0.6)
    # Persona labels on each bubble.
    for _, r in df.iterrows():
        ax.annotate(
            r["customer_persona"],
            (r["avg_promo_dependency"], r["avg_loyalty"]),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=7.5,
            color=NAVY,
            fontweight="500",
        )
    # Quadrant labels.
    ax.text(
        0.02,
        0.97,
        "Healthy core",
        transform=ax.transAxes,
        fontsize=8,
        color=GOOD,
        fontweight="600",
        va="top",
    )
    ax.text(
        0.98,
        0.97,
        "Margin at risk",
        transform=ax.transAxes,
        fontsize=8,
        color=RISK,
        fontweight="600",
        va="top",
        ha="right",
    )
    ax.text(0.02, 0.03, "Dormant", transform=ax.transAxes, fontsize=8, color=GREY, fontweight="600")
    ax.text(
        0.98,
        0.03,
        "Promo hunters",
        transform=ax.transAxes,
        fontsize=8,
        color=GOLD,
        fontweight="600",
        ha="right",
    )
    ax.set_xlabel("Promo dependency", fontsize=9, color=GREY)
    ax.set_ylabel("Loyalty (retention proxy)", fontsize=9, color=GREY)
    ax.set_title(
        "② Promo Dependency × Retention — by persona",
        loc="left",
        fontsize=12,
        color=NAVY,
        fontweight="600",
        pad=10,
    )
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(df["avg_loyalty"].min() * 0.85, df["avg_loyalty"].max() * 1.08)
    _strip_chart(ax)


def _panel_geo(ax: plt.Axes) -> None:
    """Panel ③ — Geographic Opportunity: top-10 states by region quality.

    A real Power BI page uses a US choropleth; matplotlib without `geopandas`
    can't render that, so we surface the same insight as a ranked horizontal
    bar — same data, same takeaway.
    """
    df = _load("region_scorecard").sort_values("region_quality", ascending=False).head(10)
    df = df.iloc[::-1]  # so the highest rank ends up at the top of the bar chart
    colours = [GOOD if q >= df["region_quality"].median() else ACCENT for q in df["region_quality"]]
    y_pos = list(range(len(df)))
    ax.barh(y_pos, df["region_quality"], color=colours, height=0.65, edgecolor="white")
    for i, v in enumerate(df["region_quality"]):
        ax.text(v + 0.003, i, f"{v:.2f}", va="center", fontsize=8, color=NAVY)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(df["location"], fontsize=9)
    ax.set_xlabel("Region quality index (loyalty + organic demand + value)", fontsize=9, color=GREY)
    ax.set_xlim(0, df["region_quality"].max() * 1.18)
    ax.set_title(
        "③ Geographic Opportunity — top 10 states",
        loc="left",
        fontsize=12,
        color=NAVY,
        fontweight="600",
        pad=10,
    )
    ax.text(
        0,
        -1.2,
        "Healthy markets: high spend AND low promo dependency",
        fontsize=9,
        color=GREY,
        style="italic",
    )
    _strip_chart(ax)


def _panel_funnel(ax: plt.Axes) -> None:
    """Panel ④ — Category Funnel: ordered by % low-history (entry → retention)."""
    df = _load("entry_point_categories").sort_values("pct_low_history", ascending=False)
    n = len(df)
    max_w = 100.0
    # True funnel: bar widths shrink top → bottom, centred horizontally.
    widths = [df["pct_low_history"].iloc[i] / df["pct_low_history"].max() * max_w for i in range(n)]
    colours = [GOLD, ACCENT, LIGHT_BLUE, GOOD][:n]
    for i, (cat, w, c) in enumerate(zip(df["category"], widths, colours)):
        left = (max_w - w) / 2
        ax.barh(n - i - 1, w, left=left, height=0.6, color=c, edgecolor="white")
        ax.text(
            50,
            n - i - 1,
            f"{cat}",
            ha="center",
            va="center",
            fontsize=11,
            color="white",
            fontweight="600",
        )
        ax.text(
            left + w + 2,
            n - i - 1,
            f"{df['pct_low_history'].iloc[i]:.0f}% low-history",
            va="center",
            fontsize=8,
            color=NAVY,
        )
    ax.set_xlim(-15, max_w + 35)
    ax.set_ylim(-0.7, n - 0.3)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.text(
        50,
        n - 0.1,
        "ENTRY-POINT (high % new customers)",
        ha="center",
        fontsize=8,
        color=GOLD,
        fontweight="600",
    )
    ax.text(
        50,
        -0.6,
        "RETENTION (sticky / repeat)",
        ha="center",
        fontsize=8,
        color=GOOD,
        fontweight="600",
    )
    ax.set_title(
        "④ Category Funnel — entry-point vs retention",
        loc="left",
        fontsize=12,
        color=NAVY,
        fontweight="600",
        pad=10,
    )
    for spine in ax.spines.values():
        spine.set_visible(False)


def _strip_chart(ax: plt.Axes) -> None:
    """Common chart styling — no top/right spines, light grid."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", labelsize=9, colors=NAVY)
    ax.grid(axis="x", color="#ECEFF3", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def render() -> Path:
    exec_kpis = _load("exec_kpis").iloc[0]

    fig = plt.figure(figsize=(15.5, 10.5), facecolor="white")
    # 2 rows × 2 cols for panels, with a thin KPI header row on top.
    gs = fig.add_gridspec(
        nrows=3,
        ncols=2,
        height_ratios=[0.55, 4.0, 4.0],
        hspace=0.40,
        wspace=0.20,
        left=0.05,
        right=0.97,
        top=0.88,
        bottom=0.06,
    )

    # --- Title + KPI strip ---------------------------------------------------
    fig.text(
        0.05,
        0.955,
        "DECODING CUSTOMER VALUE  —  Founder Dashboard",
        fontsize=15.5,
        color=NAVY,
        fontweight="700",
    )
    fig.text(
        0.05,
        0.925,
        "One page · four panels · designed for the founding team.",
        fontsize=9.5,
        color=GREY,
        style="italic",
    )

    kpi_ax = fig.add_subplot(gs[0, :])
    kpi_ax.axis("off")
    kpis = [
        ("Customers", f"{int(exec_kpis['total_customers']):,}"),
        ("Projected CLV", f"${exec_kpis['total_projected_clv']/1e6:.1f}M"),
        ("Avg loyalty", f"{exec_kpis['avg_loyalty']:.2f}"),
        ("% discounted", f"{exec_kpis['pct_discounted']:.0f}%"),
        ("% satisfied", f"{exec_kpis['pct_satisfied']:.0f}%"),
        ("% premium", f"{exec_kpis['pct_premium']:.0f}%"),
    ]
    n = len(kpis)
    for i, (label, value) in enumerate(kpis):
        x0 = i / n + 0.012
        rect = mpatches.FancyBboxPatch(
            (x0, 0.05),
            1 / n - 0.024,
            0.9,
            boxstyle="round,pad=0.012,rounding_size=0.05",
            linewidth=1,
            edgecolor="#E6EAF0",
            facecolor="white",
            transform=kpi_ax.transAxes,
        )
        kpi_ax.add_patch(rect)
        kpi_ax.text(
            x0 + (1 / n - 0.024) / 2,
            0.68,
            value,
            ha="center",
            va="center",
            fontsize=18,
            color=NAVY,
            fontweight="700",
            transform=kpi_ax.transAxes,
        )
        kpi_ax.text(
            x0 + (1 / n - 0.024) / 2,
            0.22,
            label.upper(),
            ha="center",
            va="center",
            fontsize=8.5,
            color=GREY,
            fontweight="600",
            transform=kpi_ax.transAxes,
        )

    # --- Four panels (2×2) ---------------------------------------------------
    _panel_pyramid(fig.add_subplot(gs[1, 0]))
    _panel_promo_retention(fig.add_subplot(gs[1, 1]))
    _panel_geo(fig.add_subplot(gs[2, 0]))
    _panel_funnel(fig.add_subplot(gs[2, 1]))

    # --- Footnote with the data caveat (always visible) ----------------------
    fig.text(
        0.05,
        0.015,
        "⚠  Discount / subscription / gender are structurally entangled in the source data — promo metrics are directional, not causal. "
        "See docs/LIMITATIONS_AND_ETHICS.md.",
        fontsize=7.5,
        color=GREY,
        style="italic",
    )

    out = ROOT / "assets" / "founder_dashboard_mockup.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


if __name__ == "__main__":
    path = render()
    print(f"Wrote {path}")
