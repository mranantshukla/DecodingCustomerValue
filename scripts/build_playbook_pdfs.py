"""build_playbook_pdfs.py - Generate three professional PDF documents:

  1. Deliverables/05_Summary/Executive_Summary.pdf            (2-3 pages)
  2. Deliverables/04_Playbook/01_Promotional_Sunset_Plan.pdf  (8-10 pages)
  3. Deliverables/04_Playbook/02_Ideal_Customer_Profile.pdf   (6-8 pages)

Each PDF is built independently with a shared style library, a shared chart
factory, and a per-document header/footer.

Image-rendering fix from the previous (combined) version:
  - Source charts are now rendered at *exactly* the embed width (6.4 inches),
    so ReportLab does not need to rescale at PDF time. Text stays crisp.
  - bbox_inches="tight" replaced with explicit subplots_adjust padding so
    saved canvases are predictable.
  - DPI raised to 180 (was 150) for sharper line work.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ─────────────────────────────────────────────────────────────────────────────
# Paths + brand
# ─────────────────────────────────────────────────────────────────────────────

ROOT = Path("e:/Cagiitg")
SQL_EXPORTS = ROOT / "reports" / "sql_exports"
PLAYBOOK_DIR = ROOT / "Deliverables" / "04_Playbook"
SUMMARY_DIR = ROOT / "Deliverables" / "05_Summary"
CHART_DIR = PLAYBOOK_DIR / "charts"

EXEC_PDF = SUMMARY_DIR / "Executive_Summary.pdf"
SUNSET_PDF = PLAYBOOK_DIR / "01_Promotional_Sunset_Plan.pdf"
ICP_PDF = PLAYBOOK_DIR / "02_Ideal_Customer_Profile.pdf"

NAVY = "#16324F"
ACCENT = "#2E86AB"
GOLD = "#E0A458"
RISK = "#C1483B"
GOOD = "#3A8B5C"
GREY = "#8A99A8"
BG = "#F7F9FB"

NAVY_RL = colors.HexColor(NAVY)
ACCENT_RL = colors.HexColor(ACCENT)
GOLD_RL = colors.HexColor(GOLD)
RISK_RL = colors.HexColor(RISK)
GOOD_RL = colors.HexColor(GOOD)
GREY_RL = colors.HexColor(GREY)
BG_RL = colors.HexColor(BG)

EMBED_WIDTH_IN = 6.4
DPI = 180


# ─────────────────────────────────────────────────────────────────────────────
# Chart factory — render at exact embed width so no PDF-time rescaling
# ─────────────────────────────────────────────────────────────────────────────


def setup_mpl() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titleweight": "bold",
            "axes.titlesize": 11.5,
            "axes.titlecolor": NAVY,
            "axes.labelcolor": NAVY,
            "axes.edgecolor": GREY,
            "axes.linewidth": 0.6,
            "xtick.color": NAVY,
            "ytick.color": NAVY,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def _save(fig, name: str) -> Path:
    out = CHART_DIR / name
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    return out


def chart_pareto() -> Path:
    df = pd.read_csv(SQL_EXPORTS / "revenue_concentration.csv").sort_values("value_decile")
    fig, ax1 = plt.subplots(figsize=(EMBED_WIDTH_IN, 3.4))
    ax2 = ax1.twinx()

    bars = ax1.bar(df["value_decile"], df["decile_clv"] / 1e6, color=ACCENT, edgecolor="white")
    ax1.set_ylabel("Decile CLV ($ millions)", color=NAVY)
    ax1.set_xlabel("Customer value decile (1 = lowest, 10 = highest)", color=NAVY)
    ax1.set_xticks(df["value_decile"])
    for b in bars:
        h = b.get_height()
        ax1.annotate(
            f"${h:.2f}M" if h >= 0.1 else f"${h*1000:.0f}k",
            xy=(b.get_x() + b.get_width() / 2, h),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color=NAVY,
        )

    ax2.plot(
        df["value_decile"],
        df["cumulative_pct_clv"],
        color=RISK,
        marker="o",
        linewidth=2,
        label="Cumulative % of CLV",
    )
    ax2.set_ylabel("Cumulative % of CLV", color=RISK)
    ax2.set_ylim(0, 110)
    ax2.spines["top"].set_visible(False)
    ax2.axhline(80, color=GOLD, linestyle="--", linewidth=0.8, alpha=0.7)
    ax2.annotate(
        "Pareto 80% line",
        xy=(8.5, 80),
        xytext=(5.2, 95),
        fontsize=8,
        color=GOLD,
        arrowprops={"arrowstyle": "->", "color": GOLD, "lw": 0.6},
    )
    # Label the cumulative line at the second-decile point (the "60%" headline)
    ax2.annotate(
        "60%\n(top 2 deciles)",
        xy=(2, 59.5),
        xytext=(2.8, 70),
        fontsize=8,
        color=RISK,
        ha="left",
        arrowprops={"arrowstyle": "->", "color": RISK, "lw": 0.6},
    )

    # Convention: decile 1 = HIGHEST value (top 10%), decile 10 = lowest
    ax1.set_xlabel("Customer value decile  (1 = top 10%, 10 = bottom 10%)", color=NAVY)
    ax1.set_title("Value concentration — top 20% of customers hold ~60% of CLV", loc="left")
    return _save(fig, "01_pareto.png")


def chart_persona_scatter() -> Path:
    df = pd.read_csv(SQL_EXPORTS / "promo_retention_by_persona.csv")
    fig, ax = plt.subplots(figsize=(EMBED_WIDTH_IN, 4.0))

    sizes = (df["customers"] / df["customers"].max() * 800).clip(lower=80)
    sc = ax.scatter(
        df["avg_promo_dependency"],
        df["avg_loyalty"],
        s=sizes,
        c=df["avg_clv"],
        cmap="viridis",
        alpha=0.78,
        edgecolors=NAVY,
        linewidth=0.8,
    )
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label("Avg CLV ($)", color=NAVY)
    cbar.outline.set_visible(False)

    # Hand-tune annotation offsets to avoid overlapping quadrant labels and the colorbar
    label_offsets = {
        "Loyal Full-Price": (8, -14),
        "Premium Loyalist": (-110, -4),
        "At-Risk Premium": (8, -4),
        "Promo-Dependent High-Value": (-180, 6),
        "Standard": (8, -4),
        "Promo Hunter": (-90, 10),
    }
    for _, row in df.iterrows():
        offset = label_offsets.get(row["customer_persona"], (8, 4))
        ax.annotate(
            row["customer_persona"],
            xy=(row["avg_promo_dependency"], row["avg_loyalty"]),
            xytext=offset,
            textcoords="offset points",
            fontsize=8,
            color=NAVY,
            weight="bold",
        )

    ax.axvline(0.5, color=GREY, linestyle="--", linewidth=0.7, alpha=0.6)
    mean_loy = df["avg_loyalty"].mean()
    ax.axhline(mean_loy, color=GREY, linestyle="--", linewidth=0.7, alpha=0.6)

    # Quadrant tags pinned in the FAR corners (away from bubble label zone)
    ax.text(
        0.02,
        0.98,
        "HEALTHY CORE",
        transform=ax.transAxes,
        color=GOOD,
        fontsize=9,
        weight="bold",
        va="top",
        ha="left",
        bbox={"facecolor": "white", "edgecolor": GOOD, "alpha": 0.85, "pad": 3},
    )
    ax.text(
        0.98,
        0.98,
        "MARGIN AT RISK",
        transform=ax.transAxes,
        color=RISK,
        fontsize=9,
        weight="bold",
        va="top",
        ha="right",
        bbox={"facecolor": "white", "edgecolor": RISK, "alpha": 0.85, "pad": 3},
    )
    ax.text(
        0.02,
        0.02,
        "DORMANT",
        transform=ax.transAxes,
        color=GREY,
        fontsize=9,
        weight="bold",
        va="bottom",
        ha="left",
        bbox={"facecolor": "white", "edgecolor": GREY, "alpha": 0.85, "pad": 3},
    )
    ax.text(
        0.98,
        0.02,
        "PROMO HUNTERS",
        transform=ax.transAxes,
        color=GOLD,
        fontsize=9,
        weight="bold",
        va="bottom",
        ha="right",
        bbox={"facecolor": "white", "edgecolor": GOLD, "alpha": 0.85, "pad": 3},
    )

    ax.set_xlabel("Average promo dependency  (→ more discount-reliant)")
    ax.set_ylabel("Average loyalty score  (→ more retention)")
    ax.set_title("Promo dependency × retention — by persona", loc="left")
    return _save(fig, "02_scatter.png")


def chart_persona_clv() -> Path:
    df = pd.read_csv(SQL_EXPORTS / "persona_scorecard.csv").sort_values("total_clv")
    fig, ax = plt.subplots(figsize=(EMBED_WIDTH_IN, 3.4))
    palette = [
        (
            GOOD
            if "Loyal" in p or "Premium Loyalist" in p
            else RISK if "At-Risk" in p or "Margin" in p else GOLD if "Promo" in p else ACCENT
        )
        for p in df["customer_persona"]
    ]
    ax.barh(df["customer_persona"], df["total_clv"] / 1e6, color=palette, edgecolor="white")
    for i, (_, row) in enumerate(df.iterrows()):
        # pct_of_clv from the CSV is already in 0-100 form (e.g. 21.4); do NOT multiply by 100
        ax.annotate(
            f"${row['total_clv']/1e6:.2f}M  ({row['pct_of_clv']:.1f}%)",
            xy=(row["total_clv"] / 1e6, i),
            xytext=(4, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
            color=NAVY,
        )
    ax.set_xlabel("Total projected CLV ($ millions)")
    ax.set_title("CLV by persona — concentration profile", loc="left")
    ax.margins(x=0.18)
    return _save(fig, "03_persona_clv.png")


def chart_sunset_timeline() -> Path:
    # Short bar labels (rendered inside the bar) + full segment names on the y-axis
    waves = [
        ("Wave 1\nFull-Price Loyalists", "W1", 0, 2, GOOD),
        ("Wave 2\nOccasional Discount", "W2", 2, 2, ACCENT),
        ("Wave 3\nPromo Hunters", "W3", 4, 4, GOLD),
        ("Wave 4\nHigh-Value Discount-Dep.", "W4", 8, 4, RISK),
    ]
    fig, ax = plt.subplots(figsize=(EMBED_WIDTH_IN, 3.0))
    for i, (_full_name, short, start, dur, color) in enumerate(waves):
        ax.barh(i, dur, left=start, color=color, edgecolor="white", alpha=0.92, height=0.7)
        ax.text(
            start + dur / 2,
            i,
            short,
            ha="center",
            va="center",
            color="white",
            fontsize=12,
            weight="bold",
        )
    ax.set_yticks(range(len(waves)))
    ax.set_yticklabels([w[0] for w in waves], fontsize=8.5)
    ax.set_xticks(range(0, 13, 2))
    ax.set_xticklabels([f"M{m}" for m in range(0, 13, 2)])
    ax.set_xlabel("Months from program start")
    ax.set_xlim(-0.2, 12.2)
    ax.invert_yaxis()  # Wave 1 at the top
    ax.set_title("Promotional sunset — 12-month sequenced rollout", loc="left")
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    return _save(fig, "04_timeline.png")


def chart_margin_waterfall() -> Path:
    # Switch from a fragile baseline-vs-deltas waterfall (deltas too tiny to see)
    # to a horizontal bar chart of the per-wave recovery, with a cumulative line
    # showing total margin freed by month 12.
    waves = [
        ("Wave 1 — Full-Price Loyalists", 54_000, GOOD, "Negligible churn risk; pure leakage"),
        ("Wave 2 — Occasional Discount", 180_000, ACCENT, "A/B test; low–moderate risk"),
        ("Wave 3 — Promo Hunters", 95_000, GOLD, "Controlled lapse; no margin defending"),
        (
            "Wave 4 — High-Value Discount-Dep.",
            320_000,
            RISK,
            "Behind loyalty programme soft landing",
        ),
    ]
    names = [w[0] for w in waves]
    vals = [w[1] for w in waves]
    colors_w = [w[2] for w in waves]
    cumulative = []
    running = 0
    for v in vals:
        running += v
        cumulative.append(running)

    fig, ax = plt.subplots(figsize=(EMBED_WIDTH_IN, 3.6))
    bars = ax.barh(
        range(len(waves)), [v / 1e3 for v in vals], color=colors_w, edgecolor="white", height=0.55
    )
    for i, (_bar, val, _color, note) in enumerate(zip(bars, vals, colors_w, [w[3] for w in waves])):
        ax.text(
            val / 1e3 + 6, i, f"${val/1e3:.0f}k   ·   {note}", va="center", fontsize=8.5, color=NAVY
        )
    ax.set_yticks(range(len(waves)))
    ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Annual margin recovery ($ thousands, 15% margin assumption)")
    ax.set_title("Margin recovery by wave — cumulative ~$649k/year", loc="left")
    ax.margins(x=0.45)
    ax.set_xlim(0, max(vals) / 1e3 * 1.8)
    # Big cumulative tag (escape $ signs so matplotlib does NOT enter mathtext mode)
    ax.text(
        0.99,
        -0.18,
        rf"Cumulative 12-month recovery: \${sum(vals)/1e3:.0f}k  (~\${sum(vals)/1e6:.2f}M)",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=10,
        weight="bold",
        color=NAVY,
        bbox={"facecolor": BG, "edgecolor": NAVY, "boxstyle": "round,pad=0.4"},
    )
    return _save(fig, "05_waterfall.png")


def chart_icp_demographics() -> Path:
    df = pd.read_csv(SQL_EXPORTS / "demographic_opportunity.csv")
    pivot = df.pivot_table(index="age_band", columns="gender", values="avg_clv", aggfunc="mean")
    order = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+", "Under 25", "Senior"]
    pivot = pivot.reindex(
        [b for b in order if b in pivot.index] + [b for b in pivot.index if b not in order]
    )

    fig, ax = plt.subplots(figsize=(EMBED_WIDTH_IN, 3.6))
    im = ax.imshow(pivot.values, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.values[i, j]
            if pd.notna(v):
                color = "white" if v > pivot.values.mean() else NAVY
                ax.text(
                    j,
                    i,
                    f"${v:,.0f}",
                    ha="center",
                    va="center",
                    color=color,
                    fontsize=8.5,
                    weight="bold",
                )
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Avg CLV ($)")
    cbar.outline.set_visible(False)
    ax.set_title("ICP demographics — average CLV by age band × gender", loc="left")
    return _save(fig, "06_demographics.png")


def chart_icp_categories() -> Path:
    df = pd.read_csv(SQL_EXPORTS / "category_scorecard.csv").sort_values(
        "total_clv", ascending=True
    )
    fig, ax = plt.subplots(figsize=(EMBED_WIDTH_IN, 2.8))
    ax.barh(df["category"], df["total_clv"] / 1e6, color=ACCENT, edgecolor="white")
    for i, (_, row) in enumerate(df.iterrows()):
        ax.annotate(
            f"${row['total_clv']/1e6:.2f}M",
            xy=(row["total_clv"] / 1e6, i),
            xytext=(4, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
            color=NAVY,
        )
    ax.set_xlabel("Total CLV ($ millions)")
    ax.set_title("ICP category preferences — where high-value customers spend", loc="left")
    ax.margins(x=0.15)
    return _save(fig, "07_categories.png")


def chart_geo_top10() -> Path:
    df = pd.read_csv(SQL_EXPORTS / "high_margin_regions.csv")
    df = (
        df.sort_values("margin_adjusted_clv", ascending=False)
        .head(10)
        .sort_values("margin_adjusted_clv")
    )
    fig, ax = plt.subplots(figsize=(EMBED_WIDTH_IN, 3.4))
    # Values here are per-state averages in raw dollars (~$2,000-$2,600 range).
    # Show them as full dollars with commas — dividing by 1e3 rounds them all to "$2k".
    ax.barh(df["location"], df["margin_adjusted_clv"], color=GOOD, edgecolor="white")
    for i, (_, row) in enumerate(df.iterrows()):
        ax.annotate(
            f"${row['margin_adjusted_clv']:,.0f}",
            xy=(row["margin_adjusted_clv"], i),
            xytext=(4, 0),
            textcoords="offset points",
            va="center",
            fontsize=8.5,
            color=NAVY,
        )
    ax.set_xlabel("Margin-adjusted CLV per customer ($)")
    ax.set_title("Top 10 acquisition-priority states (CLV × low promo dependency)", loc="left")
    ax.xaxis.set_major_formatter(plt.matplotlib.ticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.margins(x=0.25)
    return _save(fig, "08_geo.png")


def generate_all_charts() -> dict[str, Path]:
    setup_mpl()
    return {
        "pareto": chart_pareto(),
        "scatter": chart_persona_scatter(),
        "persona_clv": chart_persona_clv(),
        "timeline": chart_sunset_timeline(),
        "waterfall": chart_margin_waterfall(),
        "demographics": chart_icp_demographics(),
        "categories": chart_icp_categories(),
        "geo": chart_geo_top10(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Style + helpers shared by all 3 PDFs
# ─────────────────────────────────────────────────────────────────────────────


def make_styles():
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=NAVY_RL,
            spaceBefore=16,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=NAVY_RL,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "h3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=ACCENT_RL,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14.5,
            textColor=NAVY_RL,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        ),
        "callout": ParagraphStyle(
            "callout",
            parent=base["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=10.5,
            leading=15,
            textColor=NAVY_RL,
            alignment=TA_LEFT,
            leftIndent=14,
            rightIndent=14,
            borderPadding=10,
            spaceAfter=12,
            backColor=BG_RL,
            borderColor=ACCENT_RL,
            borderWidth=0,
        ),
        "small": ParagraphStyle(
            "small",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=GREY_RL,
            alignment=TA_LEFT,
        ),
        "kicker": ParagraphStyle(
            "kicker",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=ACCENT_RL,
            alignment=TA_LEFT,
            spaceBefore=2,
            spaceAfter=2,
        ),
        "cover_title": ParagraphStyle(
            "ctitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=32,
            leading=40,
            textColor=NAVY_RL,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "cover_subtitle": ParagraphStyle(
            "csubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=14,
            leading=20,
            textColor=ACCENT_RL,
            alignment=TA_CENTER,
            spaceAfter=30,
        ),
        "cover_body": ParagraphStyle(
            "cbody",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=12,
            leading=18,
            textColor=NAVY_RL,
            alignment=TA_CENTER,
        ),
        "cover_kicker": ParagraphStyle(
            "ckicker",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=GOLD_RL,
            alignment=TA_CENTER,
            spaceAfter=24,
        ),
        "tablecell": ParagraphStyle(
            "tc",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=NAVY_RL,
            alignment=TA_LEFT,
        ),
        "tablecell_b": ParagraphStyle(
            "tcb",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=NAVY_RL,
            alignment=TA_LEFT,
        ),
        "memo_title": ParagraphStyle(
            "memo",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=28,
            textColor=NAVY_RL,
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "memo_subtitle": ParagraphStyle(
            "memos",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=GREY_RL,
            alignment=TA_LEFT,
            spaceAfter=18,
        ),
    }


def make_header_footer(title: str):
    def _hf(canvas, doc):
        canvas.saveState()
        w, h = LETTER
        if doc.page > 1:
            canvas.setStrokeColor(NAVY_RL)
            canvas.setLineWidth(0.6)
            canvas.line(0.75 * inch, h - 0.5 * inch, w - 0.75 * inch, h - 0.5 * inch)
            canvas.setFillColor(GREY_RL)
            canvas.setFont("Helvetica", 8)
            canvas.drawString(0.75 * inch, h - 0.65 * inch, title)
            canvas.drawRightString(
                w - 0.75 * inch, h - 0.65 * inch, "CA Club, IIT Guwahati submission"
            )
            canvas.line(0.75 * inch, 0.55 * inch, w - 0.75 * inch, 0.55 * inch)
            canvas.setFillColor(GREY_RL)
            canvas.drawString(
                0.75 * inch, 0.4 * inch, "Anant Shukla · Khushi Rawat  ·  IIT Roorkee"
            )
            canvas.drawRightString(w - 0.75 * inch, 0.4 * inch, f"Page {doc.page}")
        canvas.restoreState()

    return _hf


def image(path: Path) -> Image:
    img = PILImage.open(path)
    aspect = img.height / img.width
    return Image(
        str(path),
        width=EMBED_WIDTH_IN * inch,
        height=EMBED_WIDTH_IN * aspect * inch,
        hAlign="CENTER",
    )


def two_col_table(rows, styles, col_widths=(2.4, 4.5)) -> Table:
    data = [
        [Paragraph(k, styles["tablecell_b"]), Paragraph(v, styles["tablecell"])] for k, v in rows
    ]
    t = Table(data, colWidths=[col_widths[0] * inch, col_widths[1] * inch])
    t.setStyle(
        TableStyle(
            [
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [BG_RL, colors.white]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, GREY_RL),
                ("BOX", (0, 0), (-1, -1), 0.6, NAVY_RL),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def cover(styles, title_lines: list[str], kicker: str | None = None) -> list:
    s = [Spacer(1, 2.0 * inch)]
    for i, line in enumerate(title_lines):
        s.append(Paragraph(line, styles["cover_title" if i == 0 else "cover_subtitle"]))
    s.append(
        HRFlowable(
            width="40%", thickness=1, color=GOLD_RL, spaceBefore=4, spaceAfter=24, hAlign="CENTER"
        )
    )
    if kicker:
        s.append(Paragraph(kicker, styles["cover_kicker"]))
    s.append(Spacer(1, 1.4 * inch))
    s.append(Paragraph("<b>Submitted by</b>", styles["cover_body"]))
    s.append(Spacer(1, 0.1 * inch))
    s.append(Paragraph("Anant Shukla &nbsp;·&nbsp; Khushi Rawat", styles["cover_body"]))
    s.append(Paragraph("B.Tech. Civil Engineering &nbsp;·&nbsp; IIT Roorkee", styles["cover_body"]))
    s.append(
        Paragraph(
            "anant_s@ce.iitr.ac.in &nbsp;·&nbsp; khushi_r@ce.iitr.ac.in", styles["cover_body"]
        )
    )
    s.append(Spacer(1, 0.5 * inch))
    s.append(Paragraph("Submitted to", styles["cover_body"]))
    s.append(
        Paragraph("<b>Consulting &amp; Analytics Club — IIT Guwahati</b>", styles["cover_body"])
    )
    s.append(PageBreak())
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Document 1 — Executive Summary (memo style, ~2 pages)
# ─────────────────────────────────────────────────────────────────────────────


def story_executive_summary(styles, charts) -> list:
    s: list = []
    # Memo-style header (no cover page; the brief says max 1 page substantive)
    s.append(Paragraph("Executive Summary", styles["memo_title"]))
    s.append(
        Paragraph(
            "Decoding Customer Value — A SQL-Driven Retention Strategy &nbsp;·&nbsp; "
            "Submitted to CA Club, IIT Guwahati &nbsp;·&nbsp; "
            "Anant Shukla &amp; Khushi Rawat, IIT Roorkee",
            styles["memo_subtitle"],
        )
    )
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=0, spaceAfter=14))

    s.append(
        Paragraph(
            "<b>Verdict.</b> The brand is <i>partially</i> reliant on promotional activity: "
            "<b>43.0% of customers are discounted and 39.0% of projected CLV is discount-attached</b>. "
            "But the data is unambiguous about <i>why</i>: most of that discounting is habit, not "
            "stimulus. The top 20% of customers — who carry <b>59.5% of projected value</b> — show "
            "low promo dependency. <b>Loyalty is being built, but the brand is also subsidising "
            "demand it does not need to.</b>",
            styles["callout"],
        )
    )

    s.append(Paragraph("Headline metrics", styles["h2"]))
    s.append(
        two_col_table(
            [
                ("Customers analysed", "3,900"),
                ("Total projected CLV", "$12,598,337"),
                ("Average CLV per customer", "$3,230"),
                ("Revenue from top 20% of customers", "59.5%"),
                ("Customers receiving a discount", "43.0%"),
                ("Projected CLV that is discount-attached", "39.0%"),
                ("Discount-dependent customers", "1,326"),
                ("Premium customers (top-tier flag)", "20.0%"),
                ("Satisfied customers (rating ≥ 3.8)", "50.1%"),
                ("Canonical loyalty definition", "Definition B — Margin-aware (loyalty_score_v2)"),
            ],
            styles,
            col_widths=(2.7, 4.2),
        )
    )

    s.append(Paragraph("Value concentration by persona", styles["h2"]))
    s.append(
        two_col_table(
            [
                ("Promo-Dependent High-Value", "$2,699,102  (21.4%)"),
                ("Loyal Full-Price", "$2,563,813  (20.4%)"),
                ("Standard", "$2,279,173  (18.1%)"),
                ("At-Risk Premium", "$2,199,949  (17.5%)"),
                ("Premium Loyalist", "$2,001,515  (15.9%)"),
                ("Promo Hunter", "$854,785  (6.8%)"),
            ],
            styles,
            col_widths=(2.7, 4.2),
        )
    )
    s.append(image(charts["pareto"]))

    s.append(PageBreak())

    s.append(Paragraph("So what — three moves this quarter", styles["h2"]))
    s.append(
        Paragraph(
            "<b>1. Protect the top 20%.</b> They carry 59.5% of projected value — a retention failure "
            "here dwarfs any acquisition win. Ring-fence them from discount-led messaging.",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "<b>2. Sunset discounts where they are habit, not stimulus.</b> 1,326 customers are "
            "discount-dependent; the promotional sunset plan sequences who loses discounts first by "
            "margin-at-risk versus retention-risk. Wave 1 alone recovers ~$54k/yr at negligible risk.",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "<b>3. Reallocate to organic-demand regions.</b> Region quality and organic demand scores "
            "identify markets that grow without subsidy — the highest-ROI destination for freed-up "
            "promotional budget.",
            styles["body"],
        )
    )

    s.append(Paragraph("Persona value concentration", styles["h2"]))
    s.append(image(charts["persona_clv"]))

    s.append(Paragraph("Data-integrity caveats", styles["h2"]))
    s.append(
        Paragraph(
            "<b>Subscription–discount confound.</b> Every subscriber in the source data carries a "
            'discount. "Subscribers are discount-dependent" is a data artefact, not a behavioural '
            "finding — promo metrics are reported net of subscription where it matters.",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "<b>Gender–discount confound.</b> No female customer in the source data received a "
            "discount. Geographic / segment discount rates partly reflect gender mix, not pure "
            "regional behaviour; treat promo-by-geography as directional and validate before acting.",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "<b>No timestamps / churn labels.</b> Loyalty, tenure, and CLV are engineered proxies "
            "built from previous_purchases (volume) and frequency_of_purchases (cadence). They rank "
            "customers reliably but are not audited financial figures.",
            styles["body"],
        )
    )
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Document 2 — Promotional Sunset Plan
# ─────────────────────────────────────────────────────────────────────────────


def wave_table(styles) -> Table:
    header = ["Wave", "SEGMENT", "TRIGGER", "TIMELINE", "METRIC"]
    rows = [
        [
            Paragraph("<b>Wave&nbsp;1</b>", styles["tablecell_b"]),
            Paragraph(
                "Full-Price Loyalists currently receiving incidental discounts (~351 customers)",
                styles["tablecell"],
            ),
            Paragraph(
                "Auto-discount detected on a customer whose 12-month full-price share ≥ 70%",
                styles["tablecell"],
            ),
            Paragraph("Month 0–2", styles["tablecell"]),
            Paragraph(
                "Repeat-purchase rate within ±2pp of baseline; ~$54k/yr margin recovery",
                styles["tablecell"],
            ),
        ],
        [
            Paragraph("<b>Wave&nbsp;2</b>", styles["tablecell_b"]),
            Paragraph("Occasional-Discount tier (~1,162 customers)", styles["tablecell"]),
            Paragraph(
                "Discount frequency reduced from blanket to event-based", styles["tablecell"]
            ),
            Paragraph("Month 2–4", styles["tablecell"]),
            Paragraph(
                "A/B test: price-hold vs −5%; success = ≤3pp drop in repeat rate",
                styles["tablecell"],
            ),
        ],
        [
            Paragraph("<b>Wave&nbsp;3</b>", styles["tablecell_b"]),
            Paragraph(
                "Promo Hunters — low-value, discount-dependent (~1,047)", styles["tablecell"]
            ),
            Paragraph(
                "CLV decile in bottom 30% AND promo dependency &gt; 0.65", styles["tablecell"]
            ),
            Paragraph("Month 4–8", styles["tablecell"]),
            Paragraph(
                "Allow natural lapse; track cost-per-acquired vs cost-of-retained margin",
                styles["tablecell"],
            ),
        ],
        [
            Paragraph("<b>Wave&nbsp;4</b>", styles["tablecell_b"]),
            Paragraph(
                "Margin-at-Risk Premium — high-value, discount-dependent (~230, ~$2.1M CLV)",
                styles["tablecell"],
            ),
            Paragraph(
                "Loyalty programme live AND opt-in &gt; 60% before withdrawal", styles["tablecell"]
            ),
            Paragraph("Month 8–12", styles["tablecell"]),
            Paragraph(
                "Top-20% CLV retention ≥ 100%; loyalty-programme adoption rate", styles["tablecell"]
            ),
        ],
    ]
    data = [[Paragraph(h, styles["tablecell_b"]) for h in header]] + rows
    t = Table(data, colWidths=[0.5 * inch, 1.9 * inch, 1.7 * inch, 0.85 * inch, 1.75 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY_RL),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BG_RL, colors.white]),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, GREY_RL),
                ("BOX", (0, 0), (-1, -1), 0.6, NAVY_RL),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def kpi_grid(styles) -> Table:
    header = ["KPI", "Target direction", "Source", "Owner"]
    rows = [
        [
            "% CLV discount-attached",
            "↓ (39% → 28% in 12 months)",
            "v_revenue_discount_split",
            "Growth",
        ],
        [
            "Discount penetration",
            "↓ controlled (43% → 30%)",
            "v_executive_kpis.pct_discounted",
            "Marketing",
        ],
        ["Full-price repeat rate", "↑ or hold", "feature table", "CRM"],
        [
            "Churn proxy in affected waves",
            "Within plan (±50% of baseline)",
            "cohort tracking",
            "Analytics",
        ],
        ["Gross margin %", "↑ (+200 bps by Q4)", "finance", "CFO"],
        ["Top-20% CLV retention", "Hold ≥ 100%", "v_revenue_concentration", "Retention"],
    ]
    data = [
        [
            Paragraph(c, styles["tablecell_b"] if i == 0 else styles["tablecell"])
            for i, c in enumerate(r)
        ]
        for r in [header] + rows
    ]
    t = Table(data, colWidths=[2.0 * inch, 2.1 * inch, 1.75 * inch, 0.85 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY_RL),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BG_RL, colors.white]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, GREY_RL),
                ("BOX", (0, 0), (-1, -1), 0.6, NAVY_RL),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def story_sunset_plan(styles, charts) -> list:
    s: list = cover(
        styles,
        ["Promotional Sunset Plan", "Weaning the base off discounts without sacrificing revenue"],
        kicker="PART OF THE RETENTION PLAYBOOK",
    )

    s.append(Paragraph("1.&nbsp;&nbsp;The problem in one sentence", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(
        Paragraph(
            "<b>The brand is paying to retain customers who would largely stay anyway, while a "
            "genuinely price-sensitive minority masks the difference.</b> 43% of customers receive a "
            "discount and ~39% of projected CLV is discount-attached — but the data shows most of "
            "that is habit, not stimulus. The objective is <i>not</i> to cut promotions across the "
            "board. It is to <b>stop discounting the customers who do not need it</b>, redirecting "
            "that margin toward acquisition and the retention of customers who genuinely respond to "
            "price.",
            styles["body"],
        )
    )

    s.append(Paragraph("2.&nbsp;&nbsp;How value is distributed (the foundation)", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(
        Paragraph(
            "Every sunset decision begins with the value distribution. The top decile holds ~38% of "
            "all projected CLV; the top 20% holds 59.5%. The chart below quantifies the concentration:",
            styles["body"],
        )
    )
    s.append(image(charts["pareto"]))
    s.append(
        Paragraph(
            "Two observations drive the architecture. <b>First</b>, the top deciles are "
            "low-promo-dependency by construction — discounting them is pure leakage. <b>Second</b>, "
            "the bottom deciles contribute so little CLV in absolute terms that aggressive discounting "
            "there cannot pay for itself; it must be allowed to lapse.",
            styles["body"],
        )
    )

    s.append(PageBreak())
    s.append(Paragraph("3.&nbsp;&nbsp;Four-wave sunset architecture", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(
        Paragraph(
            "Each wave names a SEGMENT, a TRIGGER behaviour, a TIMELINE, and a METRIC the brand "
            'tracks to know whether it is working. "Reduce discounts" is not acceptable — the table '
            "below is specific enough that any account manager can act on it tomorrow.",
            styles["body"],
        )
    )
    s.append(wave_table(styles))
    s.append(Spacer(1, 10))
    s.append(
        Paragraph(
            "The promo×retention map below names which persona sits in each wave. The healthy core "
            "(top-left) is the protect-at-all-costs cohort; the margin-at-risk quadrant (top-right) "
            "is Wave 4 — touched only after a loyalty programme is live.",
            styles["body"],
        )
    )
    s.append(image(charts["scatter"]))

    s.append(PageBreak())
    s.append(Paragraph("4.&nbsp;&nbsp;Rollout timeline and margin recovery", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(image(charts["timeline"]))
    s.append(
        Paragraph(
            "<b>Why this order matters.</b> Waves 1–2 are nearly pure margin recovery — the customers "
            "in scope already buy at full price most of the time. Wave 3 is a controlled lapse: the "
            "brand spends no margin defending customers whose CLV does not justify it. Wave 4 is "
            "where naïve discount-cutting would destroy value, so it sits behind a loyalty-programme "
            "soft landing — never a blunt price increase.",
            styles["body"],
        )
    )
    s.append(image(charts["waterfall"]))
    s.append(
        Paragraph(
            "Wave-by-wave annual estimates: Wave 1 ≈ <b>$54k</b> at negligible risk · "
            "Wave 2 ≈ <b>$180k</b> at low–moderate risk · Wave 3 ≈ <b>$95k</b> in lapse-savings · "
            "Wave 4 ≈ <b>$320k</b> via loyalty-programme migration. Cumulative 12-month annualised "
            "recovery ≈ <b>$649k</b>. The 15% margin-recovery assumption can be sensitivity-tested in "
            "the project's Promo Impact Simulator.",
            styles["body"],
        )
    )

    s.append(PageBreak())
    s.append(Paragraph("5.&nbsp;&nbsp;KPI dashboard and stop-loss rules", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(
        Paragraph(
            "The KPIs below sit on the founder's Power BI dashboard. Each KPI has a target "
            "direction, a source, and an owner. The stop-loss rule is non-negotiable.",
            styles["body"],
        )
    )
    s.append(kpi_grid(styles))
    s.append(Spacer(1, 10))
    s.append(
        Paragraph(
            "<b>Stop-loss rule.</b> If any wave's churn proxy exceeds plan by more than 50% of the "
            "baseline, pause that wave and shift the affected customers to the loyalty-programme "
            "track. Reversibility is designed into the sequencing: every wave is recoverable in the "
            "first 90 days because the customers in scope have not yet been told they are losing a "
            "discount — only that they are being moved to a perk-based programme.",
            styles["callout"],
        )
    )
    s.append(Paragraph("Persona CLV breakdown (basis for stop-loss thresholds)", styles["h3"]))
    s.append(image(charts["persona_clv"]))

    s.append(PageBreak())
    s.append(
        Paragraph("6.&nbsp;&nbsp;Risks, mitigations, and what success looks like", styles["h1"])
    )
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(Paragraph("Named risks", styles["h2"]))
    s.append(
        Paragraph(
            "<b>Risk 1 — Cutting a discount that was actually load-bearing.</b> Mitigation: every "
            "wave is reversible within 90 days; Wave 4 is gated behind a loyalty programme so the "
            "high-value cohort never experiences the discount withdrawal as a price increase.",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            '<b>Risk 2 — Brand-perception spillover.</b> Mitigation: frame the change as "better '
            'rewards" — early access, free returns, faster shipping — never as "we removed your '
            'discount". Lead all communication with the perk, not the loss.',
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "<b>Risk 3 — Confounded data.</b> Subscription status and gender are entangled with "
            "discount-applied in the source. Mitigation: treat segment-level discount rates as "
            "<i>directional</i>; validate Wave 4 targeting against live behaviour before acting; "
            "never target on gender.",
            styles["body"],
        )
    )
    s.append(Paragraph("What success looks like in 12 months", styles["h2"]))
    s.append(
        Paragraph(
            "% CLV discount-attached <b>↓ from 39% to ≤ 28%</b>. Top-20% CLV retention <b>≥ 100%</b> "
            "(no shrinkage at the top of the pyramid). Gross margin <b>+200&nbsp;bps</b>. Loyalty-"
            "programme adoption among the Wave-4 cohort <b>≥ 60%</b>. Acquisition spend re-weighted "
            "toward organic-demand regions with measurable ROI uplift.",
            styles["body"],
        )
    )
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Document 3 — Ideal Customer Profile
# ─────────────────────────────────────────────────────────────────────────────


def icp_profile_table(styles) -> Table:
    rows = [
        ("Age", "Median 45 (IQR 31–57) — established, higher-disposable-income adult"),
        ("Purchase cadence", "Weekly / Bi-Weekly — high velocity is the strongest loyalty signal"),
        ("Category", "Clothing (42%) · Accessories (30%) · Footwear (18%)"),
        (
            "Hero items",
            "Boots · Coats · Skirts · Jewelry — wardrobe staples + considered accessories",
        ),
        ("Satisfaction", "Avg rating 4.39 — materially above the 3.75 base average"),
        (
            "Discount behaviour",
            "Low promo dependency — buys because they want to, not because it's cheap",
        ),
        (
            "Geography",
            "New York · Georgia · Tennessee · Alabama · Maryland — South-East + North-East spine",
        ),
        ("Shipping", "Skews to 2-Day / Express / Next-Day — willing to pay for speed"),
        ("Payment", "Credit Card · PayPal · Cash mix — no single lock-in, convenience-led"),
    ]
    return two_col_table(rows, styles, col_widths=(1.5, 5.4))


def story_icp(styles, charts) -> list:
    s: list = cover(
        styles,
        ["Ideal Customer Profile", "Who to acquire more of, and who to protect"],
        kicker="PART OF THE RETENTION PLAYBOOK",
    )

    s.append(Paragraph("1.&nbsp;&nbsp;The ICP at a glance", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(
        Paragraph(
            "<b>The brand's most valuable customer is a ~45-year-old repeat apparel buyer who shops "
            "weekly, pays full price, rates the brand ~4.4/5, and buys core wardrobe items — boots, "
            "coats, skirts, jewelry — across the South-East and North-East. Average projected CLV ≈ "
            "$7,145, roughly 2.2× the overall average of $3,230.</b>",
            styles["callout"],
        )
    )
    s.append(
        Paragraph(
            "<b>Derivation, not declaration.</b> The ICP is the empirical mean of the two highest-"
            "quality personas — <i>Premium Loyalists</i> and <i>Loyal Full-Price</i> customers "
            "(n ≈ 639). These are the customers who combine high projected value, high loyalty, "
            "low discount reliance, and high satisfaction. Every figure below comes directly from "
            "the feature table; nothing is assumed.",
            styles["body"],
        )
    )
    s.append(Paragraph("Why leadership should care", styles["h2"]))
    s.append(
        Paragraph(
            "<b>Acquisition efficiency.</b> Every dollar spent acquiring an ICP look-alike returns "
            "~2.2× the average customer's projected value — and does so without a discount subsidy, "
            "so the margin is real.",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "<b>Retention priority.</b> This cohort is the core that the Promotional Sunset Plan is "
            "designed to <i>protect</i>. They must never be the target of price-led messaging.",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "<b>Creative direction.</b> Lead acquisition creative with the hero items (boots, coats) "
            "and the speed-of-delivery value proposition, not price.",
            styles["body"],
        )
    )

    s.append(PageBreak())
    s.append(Paragraph("2.&nbsp;&nbsp;Profile detail", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(icp_profile_table(styles))
    s.append(Paragraph("Demographic composition", styles["h2"]))
    s.append(image(charts["demographics"]))
    s.append(
        Paragraph(
            "The heatmap above shows average CLV by age band × gender. CLV concentrates in the "
            "established adult bands; the brand does <i>not</i> target on gender (see methodology — "
            "gender is confounded with discount-applied in the source).",
            styles["body"],
        )
    )

    s.append(PageBreak())
    s.append(Paragraph("3.&nbsp;&nbsp;Category preferences", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(image(charts["categories"]))
    s.append(
        Paragraph(
            "Clothing and Accessories carry the largest absolute CLV. Lead acquisition creative with "
            "wardrobe staples — <b>boots, coats, skirts, jewelry</b> — not deep-cut SKUs.",
            styles["body"],
        )
    )
    s.append(Paragraph("4.&nbsp;&nbsp;Geographic prioritisation", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(image(charts["geo"]))
    s.append(
        Paragraph(
            "Top 10 acquisition-priority states are ranked by <b>margin-adjusted CLV</b> = CLV × "
            '(1 − promo&nbsp;dependency). This single metric encodes both "high spend" and '
            '"low promo dependency" — the states that buy in volume without needing to be '
            "discounted into doing so.",
            styles["body"],
        )
    )

    s.append(PageBreak())
    s.append(Paragraph("5.&nbsp;&nbsp;How to operationalise the ICP", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(
        Paragraph(
            "<b>1. Look-alike acquisition.</b> Export the ICP cohort "
            "(<font face='Courier'>customer_persona IN ('Premium Loyalist','Loyal Full-Price')</font>) "
            "and seed look-alike audiences on paid social and programmatic.",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "<b>2. Geo-weighting.</b> Over-index spend on the ICP's strong states (chart §4); test "
            "adjacent markets with similar demographics.",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "<b>3. Creative.</b> Wardrobe-staple hero products + speed/service value proposition; "
            "<b>no discount in the hook</b>.",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "<b>4. Onboarding.</b> Route new ICP-matched customers into the loyalty programme "
            "immediately to lock in full-price habit before any discount exposure.",
            styles["body"],
        )
    )

    s.append(Paragraph("6.&nbsp;&nbsp;Anti-profile — who NOT to chase", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(
        Paragraph(
            "<b>The Promo Hunter persona</b> (n ≈ 1,047; avg CLV ≈ $814) is the mirror image of the "
            "ICP: discount-dependent, low value, low loyalty. Acquisition campaigns that lead with "
            "discounts disproportionately attract this cohort — <b>growth that dilutes margin</b>. "
            "Suppress discount-led creative in prospecting channels to avoid manufacturing more of them.",
            styles["body"],
        )
    )
    s.append(Paragraph("Prospect-qualification decision rule", styles["h2"]))
    s.append(
        Paragraph(
            "Qualify a prospect as ICP-fit if and only if <b>three of the following four</b> "
            "conditions hold: (a) age 30–60, (b) historical full-price share in any retail category "
            "≥ 60%, (c) shipping preference for expedited tiers, (d) geographic match to the "
            "South-East / North-East spine. Below three matches, drop into a standard nurture flow "
            "— do not over-spend on acquisition.",
            styles["callout"],
        )
    )
    s.append(
        Paragraph(
            "<b>Caveat (repeating for emphasis).</b> Gender is confounded with discounting in the "
            "source data, so the ICP intentionally does <i>not</i> target on gender. Validate any "
            "demographic targeting against live campaign response before scaling spend.",
            styles["body"],
        )
    )
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Build harness
# ─────────────────────────────────────────────────────────────────────────────


def build_pdf(pdf_path: Path, story: list, title: str, top_margin: float = 0.95) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(pdf_path),
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=top_margin * inch,
        bottomMargin=0.8 * inch,
        title=title,
        author="Anant Shukla, Khushi Rawat",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates(
        [PageTemplate(id="default", frames=[frame], onPage=make_header_footer(title))]
    )
    doc.build(story)


def main() -> None:
    print("Generating charts...")
    charts = generate_all_charts()
    for k, p in charts.items():
        print(f"  + {k:14s}  {p.name}  ({p.stat().st_size / 1024:.1f} KB)")

    styles = make_styles()

    print("\nBuilding 3 PDFs...")
    build_pdf(
        EXEC_PDF,
        story_executive_summary(styles, charts),
        "Decoding Customer Value — Executive Summary",
        top_margin=0.75,
    )
    print(f"  + {EXEC_PDF.relative_to(ROOT)}  ({EXEC_PDF.stat().st_size / 1024:.1f} KB)")

    build_pdf(
        SUNSET_PDF,
        story_sunset_plan(styles, charts),
        "Decoding Customer Value — Promotional Sunset Plan",
    )
    print(f"  + {SUNSET_PDF.relative_to(ROOT)}  ({SUNSET_PDF.stat().st_size / 1024:.1f} KB)")

    build_pdf(
        ICP_PDF, story_icp(styles, charts), "Decoding Customer Value — Ideal Customer Profile"
    )
    print(f"  + {ICP_PDF.relative_to(ROOT)}  ({ICP_PDF.stat().st_size / 1024:.1f} KB)")

    print("\nDone.")


if __name__ == "__main__":
    main()
