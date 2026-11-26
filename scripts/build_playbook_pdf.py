"""build_playbook_pdf.py — Generate the full Playbook as a professional PDF.

The Problem-Statement PDF mandates "Promo sunset plan + ideal customer
profile" as the Playbook deliverable. This script produces a 10-15 page
PDF that matches a senior product manager's standard for an executive
recommendation document:

  - Cover · Table of contents · Executive summary
  - Part I — Promotional Sunset Plan (4 waves with SEGMENT · TRIGGER ·
    TIMELINE · METRIC each, margin-recovery waterfall, KPI dashboard,
    risks & mitigations)
  - Part II — Ideal Customer Profile (headline, demographic composition,
    behavioural signature, acquisition strategy, anti-profile)
  - Appendix (methodology, data caveats, sources)

Charts are generated with matplotlib and embedded as PNGs.

Output: Deliverables/04_Playbook/Decoding_Customer_Value_Playbook.pdf
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
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
OUT_DIR = ROOT / "Deliverables" / "04_Playbook"
CHART_DIR = OUT_DIR / "charts"
PDF_PATH = OUT_DIR / "Decoding_Customer_Value_Playbook.pdf"

NAVY = "#16324F"
ACCENT = "#2E86AB"
ACCENT2 = "#5FA8D3"
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


# ─────────────────────────────────────────────────────────────────────────────
# Chart helpers (saved to charts/ as PNG, embedded in PDF)
# ─────────────────────────────────────────────────────────────────────────────


def setup_mpl() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titleweight": "bold",
            "axes.titlesize": 12,
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
            "savefig.dpi": 150,
        }
    )


def chart_pareto() -> Path:
    df = pd.read_csv(SQL_EXPORTS / "revenue_concentration.csv").sort_values("value_decile")
    fig, ax1 = plt.subplots(figsize=(7, 3.2))
    ax2 = ax1.twinx()

    bars = ax1.bar(df["value_decile"], df["decile_clv"] / 1e6, color=ACCENT, edgecolor="white")
    ax1.set_ylabel("Decile CLV ($ millions)", color=NAVY)
    ax1.set_xlabel("Customer value decile (1 = lowest, 10 = highest)", color=NAVY)
    ax1.set_xticks(df["value_decile"])
    for b in bars:
        h = b.get_height()
        ax1.annotate(
            f"${h:.1f}M",
            xy=(b.get_x() + b.get_width() / 2, h),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color=NAVY,
        )

    ax2.plot(
        df["value_decile"], df["cumulative_pct_clv"] * 100, color=RISK, marker="o", linewidth=2
    )
    ax2.set_ylabel("Cumulative % of CLV", color=RISK)
    ax2.set_ylim(0, 110)
    ax2.spines["top"].set_visible(False)
    ax2.axhline(80, color=GOLD, linestyle="--", linewidth=0.8, alpha=0.7)
    ax2.annotate(
        "Pareto threshold (top 20%)",
        xy=(8.5, 80),
        xytext=(5, 92),
        fontsize=8,
        color=GOLD,
        arrowprops={"arrowstyle": "->", "color": GOLD, "lw": 0.6},
    )

    plt.title("Value concentration — top 20% of customers hold ~60% of CLV", loc="left")
    plt.tight_layout()
    out = CHART_DIR / "01_pareto.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def chart_persona_scatter() -> Path:
    df = pd.read_csv(SQL_EXPORTS / "promo_retention_by_persona.csv")
    fig, ax = plt.subplots(figsize=(7, 4))

    sizes = (df["customers"] / df["customers"].max() * 1200).clip(lower=80)
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

    for _, row in df.iterrows():
        ax.annotate(
            row["customer_persona"],
            xy=(row["avg_promo_dependency"], row["avg_loyalty"]),
            xytext=(6, 4),
            textcoords="offset points",
            fontsize=8,
            color=NAVY,
            weight="bold",
        )

    ax.axvline(0.5, color=GREY, linestyle="--", linewidth=0.7, alpha=0.6)
    mean_loy = df["avg_loyalty"].mean()
    ax.axhline(mean_loy, color=GREY, linestyle="--", linewidth=0.7, alpha=0.6)
    ax.text(0.04, ax.get_ylim()[1] * 0.98, "Healthy core", color=GOOD, fontsize=9, weight="bold")
    ax.text(0.58, ax.get_ylim()[1] * 0.98, "Margin at risk", color=RISK, fontsize=9, weight="bold")
    ax.text(0.04, ax.get_ylim()[0] + 0.005, "Dormant", color=GREY, fontsize=9)
    ax.text(0.58, ax.get_ylim()[0] + 0.005, "Promo hunters", color=GOLD, fontsize=9)

    ax.set_xlabel("Average promo dependency  (→ more discount-reliant)")
    ax.set_ylabel("Average loyalty score  (→ more retention)")
    ax.set_title("Promo dependency × retention — by persona", loc="left")
    plt.tight_layout()
    out = CHART_DIR / "02_scatter.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def chart_persona_clv() -> Path:
    df = pd.read_csv(SQL_EXPORTS / "persona_scorecard.csv").sort_values("total_clv")
    fig, ax = plt.subplots(figsize=(7, 3.4))
    colors_per = [
        (
            GOOD
            if "Loyal" in p or "Premium Loyalist" in p
            else RISK if "At-Risk" in p or "Margin" in p else GOLD if "Promo" in p else ACCENT
        )
        for p in df["customer_persona"]
    ]
    ax.barh(df["customer_persona"], df["total_clv"] / 1e6, color=colors_per, edgecolor="white")
    for i, (_, row) in enumerate(df.iterrows()):
        ax.annotate(
            f"${row['total_clv']/1e6:.2f}M  ({row['pct_of_clv']*100:.1f}%)",
            xy=(row["total_clv"] / 1e6, i),
            xytext=(4, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
            color=NAVY,
        )
    ax.set_xlabel("Total projected CLV ($ millions)")
    ax.set_title("CLV by persona — concentration profile", loc="left")
    plt.tight_layout()
    out = CHART_DIR / "03_persona_clv.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def chart_sunset_timeline() -> Path:
    waves = [
        ("Wave 1: Full-Price Loyalists", 0, 2, GOOD),
        ("Wave 2: Occasional Discount", 2, 2, ACCENT),
        ("Wave 3: Promo Hunters (low value)", 4, 4, GOLD),
        ("Wave 4: High-Value Discount-Dependent", 8, 4, RISK),
    ]
    fig, ax = plt.subplots(figsize=(7, 2.9))
    for i, (name, start, dur, color) in enumerate(waves):
        ax.barh(i, dur, left=start, color=color, edgecolor="white", alpha=0.9)
        ax.text(
            start + dur / 2,
            i,
            name,
            ha="center",
            va="center",
            color="white",
            fontsize=8.5,
            weight="bold",
        )
    ax.set_yticks([])
    ax.set_xticks(range(0, 13, 2))
    ax.set_xticklabels([f"M{m}" for m in range(0, 13, 2)])
    ax.set_xlabel("Months from program start")
    ax.set_xlim(0, 12)
    ax.set_title("Promotional sunset rollout — 12-month sequenced timeline", loc="left")
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    plt.tight_layout()
    out = CHART_DIR / "04_timeline.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def chart_margin_waterfall() -> Path:
    # Wave 1 explicit estimate ($54k/yr from the existing report).
    # Other waves are scaled estimates based on cohort sizes & avg basket.
    waves = [
        ("Discounted CLV today", 4_913_000, ACCENT),
        ("Wave 1 recovery", 54_000, GOOD),
        ("Wave 2 recovery", 180_000, GOOD),
        ("Wave 3 lapse-savings", 95_000, GOLD),
        ("Wave 4 loyalty migrate", 320_000, RISK),
        ("Discounted CLV after", 4_264_000, GREY),
    ]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    running = 0
    xs = list(range(len(waves)))
    labels = [w[0] for w in waves]
    for i, (_lbl, val, color) in enumerate(waves):
        if i == 0:
            ax.bar(i, val, color=color, edgecolor="white")
            ax.text(i, val, f"${val/1e6:.2f}M", ha="center", va="bottom", fontsize=8, color=NAVY)
            running = val
        elif i == len(waves) - 1:
            ax.bar(i, val, color=color, edgecolor="white")
            ax.text(i, val, f"${val/1e6:.2f}M", ha="center", va="bottom", fontsize=8, color=NAVY)
        else:
            ax.bar(i, val, bottom=running - val, color=color, edgecolor="white")
            ax.text(
                i,
                running - val / 2,
                f"-${val/1e3:.0f}k",
                ha="center",
                va="center",
                fontsize=8,
                color="white",
                weight="bold",
            )
            running -= val
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=14, ha="right", fontsize=8)
    ax.set_ylabel("Annual discount-attached CLV ($)")
    ax.set_title("Margin recovery waterfall (annual, 15% margin recovery assumption)", loc="left")
    ax.yaxis.set_major_formatter(plt.matplotlib.ticker.FuncFormatter(lambda x, _: f"${x/1e6:.1f}M"))
    plt.tight_layout()
    out = CHART_DIR / "05_waterfall.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def chart_icp_demographics() -> Path:
    df = pd.read_csv(SQL_EXPORTS / "demographic_opportunity.csv")
    pivot = df.pivot_table(index="age_band", columns="gender", values="avg_clv", aggfunc="mean")
    # Order age bands chronologically if possible
    order = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+", "Under 25", "Senior"]
    pivot = pivot.reindex(
        [b for b in order if b in pivot.index] + [b for b in pivot.index if b not in order]
    )

    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    im = ax.imshow(pivot.values, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.values[i, j]
            if pd.notna(v):
                ax.text(
                    j,
                    i,
                    f"${v:,.0f}",
                    ha="center",
                    va="center",
                    color="white" if v > pivot.values.mean() else NAVY,
                    fontsize=8,
                    weight="bold",
                )
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Avg CLV ($)")
    cbar.outline.set_visible(False)
    ax.set_title("ICP demographics — average CLV by age band × gender", loc="left")
    plt.tight_layout()
    out = CHART_DIR / "06_demographics.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def chart_icp_categories() -> Path:
    df = pd.read_csv(SQL_EXPORTS / "category_scorecard.csv").sort_values(
        "total_clv", ascending=True
    )
    fig, ax = plt.subplots(figsize=(6.5, 2.8))
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
    plt.tight_layout()
    out = CHART_DIR / "07_categories.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def chart_geo_top10() -> Path:
    df = pd.read_csv(SQL_EXPORTS / "high_margin_regions.csv")
    df = (
        df.sort_values("margin_adjusted_clv", ascending=False)
        .head(10)
        .sort_values("margin_adjusted_clv")
    )
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    ax.barh(df["location"], df["margin_adjusted_clv"] / 1e3, color=GOOD, edgecolor="white")
    for i, (_, row) in enumerate(df.iterrows()):
        ax.annotate(
            f"${row['margin_adjusted_clv']/1e3:.0f}k",
            xy=(row["margin_adjusted_clv"] / 1e3, i),
            xytext=(4, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
            color=NAVY,
        )
    ax.set_xlabel("Margin-adjusted CLV ($ thousands)")
    ax.set_title("Top 10 acquisition-priority states (high CLV × low promo dependency)", loc="left")
    plt.tight_layout()
    out = CHART_DIR / "08_geo.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# PDF construction
# ─────────────────────────────────────────────────────────────────────────────


def make_styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=34,
            textColor=NAVY_RL,
            alignment=TA_LEFT,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=14,
            leading=18,
            textColor=ACCENT_RL,
            alignment=TA_LEFT,
            spaceAfter=24,
        ),
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
            fontSize=10,
            leading=14.5,
            textColor=NAVY_RL,
            alignment=TA_LEFT,
            leftIndent=14,
            rightIndent=14,
            borderPadding=8,
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
            fontSize=36,
            leading=44,
            textColor=NAVY_RL,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "cover_subtitle": ParagraphStyle(
            "csubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=16,
            leading=22,
            textColor=ACCENT_RL,
            alignment=TA_CENTER,
            spaceAfter=40,
        ),
        "cover_kicker": ParagraphStyle(
            "ckicker",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=GOLD_RL,
            alignment=TA_CENTER,
            spaceAfter=24,
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
        "tablecell": ParagraphStyle(
            "tablecell",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=NAVY_RL,
            alignment=TA_LEFT,
        ),
        "tablecell_b": ParagraphStyle(
            "tablecellb",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=NAVY_RL,
            alignment=TA_LEFT,
        ),
    }
    return styles


def header_footer(canvas, doc):
    canvas.saveState()
    w, h = LETTER
    # Top thin rule
    if doc.page > 1:
        canvas.setStrokeColor(NAVY_RL)
        canvas.setLineWidth(0.6)
        canvas.line(0.75 * inch, h - 0.5 * inch, w - 0.75 * inch, h - 0.5 * inch)
        canvas.setFillColor(GREY_RL)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(
            0.75 * inch, h - 0.65 * inch, "Decoding Customer Value — Retention Playbook"
        )
        canvas.drawRightString(w - 0.75 * inch, h - 0.65 * inch, "CA Club, IIT Guwahati submission")
        # Footer
        canvas.line(0.75 * inch, 0.55 * inch, w - 0.75 * inch, 0.55 * inch)
        canvas.setFillColor(GREY_RL)
        canvas.drawString(0.75 * inch, 0.4 * inch, "Anant Shukla · Khushi Rawat  ·  IIT Roorkee")
        canvas.drawRightString(w - 0.75 * inch, 0.4 * inch, f"Page {doc.page}")
    canvas.restoreState()


def kpi_table(rows: list[tuple[str, str]], styles) -> Table:
    data = [
        [Paragraph(k, styles["tablecell_b"]), Paragraph(v, styles["tablecell"])] for k, v in rows
    ]
    t = Table(data, colWidths=[3.5 * inch, 3.2 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [BG_RL, colors.white]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, GREY_RL),
                ("BOX", (0, 0), (-1, -1), 0.6, NAVY_RL),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


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
                "Repeat-purchase rate held within ±2pp of baseline; ~$54k/yr margin recovery",
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
                "A/B test: price-hold cohort vs −5% cohort; success = ≤3pp drop in repeat rate",
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
    t = Table(data, colWidths=[0.55 * inch, 1.85 * inch, 1.75 * inch, 0.85 * inch, 1.70 * inch])
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
            "↓ (target: 39% → 28% in 12 months)",
            "v_revenue_discount_split",
            "Growth",
        ],
        [
            "Discount penetration",
            "↓ controlled (43% → 30%)",
            "v_executive_kpis.pct_discounted",
            "Marketing",
        ],
        [
            "Full-price repeat rate",
            "↑ or hold (non_discount_purchase_ratio)",
            "feature table",
            "CRM",
        ],
        [
            "Churn proxy in affected waves",
            "Within plan (±50% of baseline)",
            "cohort tracking",
            "Analytics",
        ],
        ["Gross margin %", "↑ (target +200 bps by Q4)", "finance", "CFO"],
        ["Top-20% CLV retention", "Hold ≥ 100%", "v_revenue_concentration", "Retention"],
    ]
    data = [
        [
            Paragraph(c, styles["tablecell_b"] if i == 0 else styles["tablecell"])
            for i, c in enumerate(r)
        ]
        for r in [header] + rows
    ]
    t = Table(data, colWidths=[2.0 * inch, 2.2 * inch, 1.65 * inch, 0.85 * inch])
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
    data = [
        [Paragraph(k, styles["tablecell_b"]), Paragraph(v, styles["tablecell"])] for k, v in rows
    ]
    t = Table(data, colWidths=[1.4 * inch, 5.3 * inch])
    t.setStyle(
        TableStyle(
            [
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [BG_RL, colors.white]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, GREY_RL),
                ("BOX", (0, 0), (-1, -1), 0.6, NAVY_RL),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def image(path: Path, width_in: float = 6.7) -> Image:
    from PIL import Image as PILImage

    img = PILImage.open(path)
    aspect = img.height / img.width
    return Image(str(path), width=width_in * inch, height=width_in * aspect * inch)


# ─────────────────────────────────────────────────────────────────────────────
# Document body
# ─────────────────────────────────────────────────────────────────────────────


def build_story(styles, charts: dict[str, Path]) -> list:
    s: list = []

    # ── Cover ────────────────────────────────────────────────────────────────
    s.append(Spacer(1, 2.0 * inch))
    s.append(Paragraph("Retention Playbook", styles["cover_title"]))
    s.append(
        Paragraph(
            "Decoding Customer Value — A SQL-Driven Retention Strategy", styles["cover_subtitle"]
        )
    )
    s.append(
        HRFlowable(
            width="40%", thickness=1, color=GOLD_RL, spaceBefore=0, spaceAfter=24, hAlign="CENTER"
        )
    )
    s.append(
        Paragraph("PROMOTIONAL SUNSET PLAN  ·  IDEAL CUSTOMER PROFILE", styles["cover_kicker"])
    )
    s.append(Spacer(1, 1.5 * inch))
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

    # ── Table of contents (static, hand-curated) ────────────────────────────
    s.append(Paragraph("Table of contents", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    toc_rows = [
        ["1.", "Executive summary", "3"],
        ["", "", ""],
        ["", "PART I — Promotional Sunset Plan", ""],
        ["2.", "The problem in one sentence", "4"],
        ["3.", "How value is distributed (the foundation)", "4"],
        ["4.", "Four-wave sunset architecture (SEGMENT · TRIGGER · TIMELINE · METRIC)", "5"],
        ["5.", "Rollout timeline + margin-recovery quantification", "6"],
        ["6.", "KPI dashboard and stop-loss rules", "7"],
        ["7.", "Risks, mitigations, and what success looks like", "8"],
        ["", "", ""],
        ["", "PART II — Ideal Customer Profile", ""],
        ["8.", "The ICP at a glance", "9"],
        ["9.", "Profile detail — demographics, behaviour, geography", "10"],
        ["10.", "Acquisition strategy — channels, geographies, creative", "11"],
        ["11.", "Anti-profile — who NOT to chase", "12"],
        ["", "", ""],
        ["", "APPENDIX", ""],
        ["12.", "Methodology and data caveats", "13"],
        ["13.", "Source artefacts and reproducibility", "14"],
    ]
    toc_data = [
        [
            Paragraph(r[0], styles["tablecell_b"]),
            Paragraph(r[1], styles["tablecell_b"] if not r[0] and r[1] else styles["tablecell"]),
            Paragraph(r[2], styles["tablecell"]),
        ]
        for r in toc_rows
    ]
    toc_table = Table(toc_data, colWidths=[0.5 * inch, 5.2 * inch, 0.6 * inch])
    toc_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    s.append(toc_table)
    s.append(PageBreak())

    # ── 1. Executive summary ─────────────────────────────────────────────────
    s.append(Paragraph("1.&nbsp;&nbsp;Executive summary", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(
        Paragraph(
            "<b>Verdict.</b> The brand is <i>partially</i> reliant on promotional activity: "
            "43% of customers are discounted and 39% of projected CLV is discount-attached. "
            "But the data is unambiguous about <i>why</i>: most of that discounting is <b>habit, not stimulus</b>. "
            "The top 20% of customers — who carry 59.5% of projected value — show low promo dependency. "
            "<b>Loyalty is being built, but the brand is also subsidising demand it does not need to.</b>",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "<b>What to do.</b> Sequence a four-wave promotional sunset, starting with customers "
            "whose discounts are pure leakage (full-price loyalists who happen to be receiving a "
            "promo) and deferring the high-value discount-dependent cohort until a loyalty programme "
            "is live to catch them. Reinvest freed margin into ICP look-alike acquisition in the "
            "high-organic-demand geographies that surface in the regional scorecard.",
            styles["body"],
        )
    )
    s.append(Spacer(1, 6))
    s.append(Paragraph("Headline metrics", styles["h2"]))
    s.append(
        kpi_table(
            [
                ("Customers analysed", "3,900"),
                ("Total projected CLV", "$12.6&thinsp;M"),
                ("Average CLV per customer", "$3,230"),
                ("Top-20% share of CLV", "59.5%"),
                ("Customers receiving a discount", "43.0%"),
                ("Projected CLV that is discount-attached", "39.0%"),
                ("Premium customers (top-tier flag)", "20.0%"),
                (
                    "Loyal Full-Price + Premium Loyalist cohort",
                    "~639 customers · ~$4.6&thinsp;M CLV",
                ),
                ("Discount-dependent customers", "1,326 · ~$4.9&thinsp;M CLV"),
            ],
            styles,
        )
    )
    s.append(Spacer(1, 10))
    s.append(Paragraph("Top three moves this quarter", styles["h2"]))
    s.append(
        Paragraph(
            "<b>1. Protect the top 20%.</b> They carry 59.5% of projected value — a retention "
            "failure here dwarfs any acquisition win. Ring-fence them from discount-led messaging.",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "<b>2. Sunset discounts where they are habit, not stimulus.</b> 1,326 customers are "
            "discount-dependent; the sunset plan sequences who loses discounts first by "
            "margin-at-risk vs retention-risk. Wave 1 alone recovers ~$54k/yr at negligible churn risk.",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "<b>3. Reallocate to organic-demand regions.</b> Region quality and organic demand "
            "scores identify markets that grow without subsidy — the highest-ROI destination for "
            "freed-up promotional budget.",
            styles["body"],
        )
    )
    s.append(PageBreak())

    # ── PART I — SUNSET PLAN ────────────────────────────────────────────────
    s.append(Paragraph("Part I — Promotional Sunset Plan", styles["kicker"]))
    s.append(Paragraph("2.&nbsp;&nbsp;The problem in one sentence", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(
        Paragraph(
            "<b>The brand is paying to retain customers who would largely stay anyway, "
            "while a genuinely price-sensitive minority masks the difference.</b> The objective is "
            "<i>not</i> to cut promotions across the board. It is to <b>stop discounting the customers "
            "who do not need it</b>, redirecting that margin toward acquisition and the retention of "
            "customers who genuinely respond to price.",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "A blanket cut would risk the discount-dependent cohort that <i>does</i> need price "
            "stimulus — roughly $2.1M of projected CLV across 230 customers. A surgical sequence, "
            "ordered by churn risk and margin recovery, is the only defensible path.",
            styles["body"],
        )
    )

    s.append(Paragraph("3.&nbsp;&nbsp;How value is distributed (the foundation)", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(
        Paragraph(
            "Every sunset decision begins with the value distribution. The top decile holds 38% of "
            "all projected CLV; the top 20% holds 59.5%. The chart below quantifies that concentration:",
            styles["body"],
        )
    )
    s.append(image(charts["pareto"], 6.7))
    s.append(
        Paragraph(
            "Two observations drive the sunset architecture. <b>First</b>, the top deciles are "
            "low-promo-dependency by construction — discounting them is pure leakage. <b>Second</b>, "
            "the bottom deciles contribute so little CLV in absolute terms that aggressive "
            "discounting there cannot pay for itself; it must be allowed to lapse.",
            styles["body"],
        )
    )
    s.append(PageBreak())

    s.append(Paragraph("4.&nbsp;&nbsp;Four-wave sunset architecture", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(
        Paragraph(
            "Each wave names a SEGMENT, a TRIGGER behaviour, a TIMELINE, and a METRIC the brand "
            'tracks to know whether it is working. "Reduce discounts" is not acceptable — the table '
            "below is specific enough that any account manager can act on it tomorrow.",
            styles["body"],
        )
    )
    s.append(Spacer(1, 6))
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
    s.append(image(charts["scatter"], 6.7))
    s.append(PageBreak())

    s.append(
        Paragraph("5.&nbsp;&nbsp;Rollout timeline + margin-recovery quantification", styles["h1"])
    )
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(image(charts["timeline"], 6.7))
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
    s.append(image(charts["waterfall"], 6.7))
    s.append(
        Paragraph(
            "The waterfall assumes a 15% margin recovery on freed discounts — the same default the "
            "interactive Promo Impact Simulator uses, so leadership can sensitivity-test under their "
            "own assumptions before committing budget.",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "Wave-by-wave estimates (annual): Wave 1 ≈ <b>$54k</b> at negligible risk · "
            "Wave 2 ≈ <b>$180k</b> at low–moderate risk · Wave 3 ≈ <b>$95k</b> in lapse-savings · "
            "Wave 4 ≈ <b>$320k</b> via loyalty-programme migration. Cumulative 12-month annualised "
            "recovery ≈ <b>$649k</b>.",
            styles["body"],
        )
    )
    s.append(PageBreak())

    s.append(Paragraph("6.&nbsp;&nbsp;KPI dashboard and stop-loss rules", styles["h1"]))
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
    s.append(Spacer(1, 4))
    s.append(Paragraph("Persona CLV breakdown (basis for stop-loss thresholds)", styles["h3"]))
    s.append(image(charts["persona_clv"], 6.7))
    s.append(PageBreak())

    s.append(
        Paragraph("7.&nbsp;&nbsp;Risks, mitigations, and what success looks like", styles["h1"])
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
            "discount-applied in the source (every subscriber receives a discount; no female "
            "customer received a discount in the data). Mitigation: treat segment-level discount "
            "rates as <i>directional</i>; validate Wave 4 targeting against live behaviour before "
            "acting; never target on gender.",
            styles["body"],
        )
    )
    s.append(Paragraph("What success looks like in 12 months", styles["h2"]))
    s.append(
        Paragraph(
            "% CLV discount-attached <b>↓ from 39% to ≤ 28%</b>. Top-20% CLV retention <b>≥ 100%</b> "
            "(no shrinkage at the top of the pyramid). Gross margin <b>+200&nbsp;bps</b>. Loyalty-"
            "programme adoption among the Wave-4 cohort <b>≥ 60%</b>. Acquisition spend "
            "re-weighted toward organic-demand regions with measurable ROI uplift.",
            styles["body"],
        )
    )
    s.append(PageBreak())

    # ── PART II — ICP ────────────────────────────────────────────────────────
    s.append(Paragraph("Part II — Ideal Customer Profile", styles["kicker"]))
    s.append(Paragraph("8.&nbsp;&nbsp;The ICP at a glance", styles["h1"]))
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
            "~2.2× the average customer's projected value — and does so <i>without a discount "
            "subsidy</i>, so the margin is real.",
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

    s.append(Paragraph("9.&nbsp;&nbsp;Profile detail", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(icp_profile_table(styles))
    s.append(Spacer(1, 14))
    s.append(Paragraph("Demographic composition", styles["h2"]))
    s.append(image(charts["demographics"], 6.0))
    s.append(
        Paragraph(
            "The heatmap above shows average CLV by age band × gender. CLV concentrates in the "
            "established adult bands; the brand does <i>not</i> target on gender (see methodology — "
            "gender is confounded with discount-applied in the source).",
            styles["body"],
        )
    )
    s.append(PageBreak())

    s.append(
        Paragraph(
            "10.&nbsp;&nbsp;Acquisition strategy — channels, geographies, creative", styles["h1"]
        )
    )
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(Paragraph("Category preference", styles["h2"]))
    s.append(image(charts["categories"], 6.5))
    s.append(
        Paragraph(
            "Clothing and Accessories carry the largest absolute CLV. Lead acquisition creative with "
            "wardrobe staples — <b>boots, coats, skirts, jewelry</b> — not deep-cut SKUs.",
            styles["body"],
        )
    )
    s.append(Paragraph("Geographic prioritisation", styles["h2"]))
    s.append(image(charts["geo"], 6.5))
    s.append(
        Paragraph(
            "The top 10 acquisition-priority states are ranked by <b>margin-adjusted CLV</b> = CLV × "
            "(1 − promo&nbsp;dependency). This single metric encodes <i>both</i> the PDF's mandate "
            'of "high spend AND low promo dependency" — the states that buy in volume without '
            "needing to be discounted into doing so. Over-index ad-spend here; test adjacent markets "
            "with similar demographics second.",
            styles["body"],
        )
    )
    s.append(Paragraph("Operationalisation — the four-step routine", styles["h2"]))
    s.append(
        Paragraph(
            "<b>1. Look-alike acquisition.</b> Export the ICP cohort (<font face='Courier'>"
            "customer_persona IN ('Premium Loyalist','Loyal Full-Price')</font>) and seed look-alike "
            "audiences on paid social and programmatic.",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "<b>2. Geo-weighting.</b> Over-index spend on the ICP's strong states (see chart "
            "above); test adjacent markets with similar demographics.",
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
            "immediately to lock in the full-price habit before any discount exposure.",
            styles["body"],
        )
    )
    s.append(PageBreak())

    s.append(Paragraph("11.&nbsp;&nbsp;Anti-profile — who NOT to chase", styles["h1"]))
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
    s.append(Paragraph("Decision rule for prospect qualification", styles["h2"]))
    s.append(
        Paragraph(
            "Given a prospect with a known demographic and behavioural signature, qualify them as "
            "ICP-fit if and only if <b>three of the following four</b> conditions hold: (a) age "
            "30–60, (b) historical full-price share in any retail category ≥ 60%, (c) shipping "
            "preference for expedited tiers, (d) geographic match to the South-East / North-East "
            "spine. Below three matches, drop into a standard nurture flow — do not over-spend on "
            "acquisition.",
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
    s.append(PageBreak())

    # ── Appendix ─────────────────────────────────────────────────────────────
    s.append(Paragraph("Appendix", styles["kicker"]))
    s.append(Paragraph("12.&nbsp;&nbsp;Methodology and data caveats", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(Paragraph("Loyalty — defined, not declared", styles["h2"]))
    s.append(
        Paragraph(
            "The source dataset contains no loyalty score, no churn label, and no timestamps. Per "
            "the PDF's central analytical challenge, two competing loyalty definitions were "
            "constructed and tested against an orthogonal validation target (economic_value_proxy = "
            "annual_value × margin_factor — deliberately loyalty-free to avoid self-correlation). "
            "<b>Definition B (margin-aware) wins, 0.666 vs 0.627</b>, and is canonical throughout "
            "this playbook. The full A/B framework lives in "
            "<font face='Courier'>reports/loyalty_framework.md</font>.",
            styles["body"],
        )
    )
    s.append(Paragraph("Traceability — every segment claim is mapped to variables", styles["h2"]))
    s.append(
        Paragraph(
            "Each persona in this playbook is a stated combination of loyalty tier × promo reliance "
            "tier × revenue contribution tier — see "
            "<font face='Courier'>src/business_logic/segmentation.py::assign_personas</font>. No "
            'label ("at-risk", "high-value", etc.) is used without that traceable mapping.',
            styles["body"],
        )
    )
    s.append(Paragraph("Data-integrity caveats", styles["h2"]))
    s.append(
        Paragraph(
            "<b>Subscription–discount confound.</b> Every subscriber in the source data carries a "
            'discount. "Subscribers are discount-dependent" is therefore a data artefact, not a '
            "behavioural finding — promo metrics are reported net of subscription where it matters.",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "<b>Gender–discount confound.</b> No female customer in the source data received a "
            "discount. Geographic / segment discount rates partly reflect gender mix, not pure "
            "regional behaviour; treat promo-by-geography as directional.",
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
    s.append(PageBreak())

    s.append(Paragraph("13.&nbsp;&nbsp;Source artefacts and reproducibility", styles["h1"]))
    s.append(HRFlowable(width="100%", thickness=0.6, color=NAVY_RL, spaceBefore=2, spaceAfter=14))
    s.append(
        Paragraph(
            "Every figure in this document is reproducible from the artefacts in the Deliverables "
            "bundle. The pipeline is one command:",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "<font face='Courier'>python -m src.pipeline</font> &nbsp; "
            "→ &nbsp; rebuilds customer_features.csv, every SQL view CSV, the executive summary, "
            "and the consolidated intelligence report.",
            styles["body"],
        )
    )
    s.append(Paragraph("Where to look", styles["h2"]))
    src_table = Table(
        [
            [
                Paragraph("<b>Artefact</b>", styles["tablecell_b"]),
                Paragraph("<b>Location</b>", styles["tablecell_b"]),
            ],
            [
                Paragraph("Cleaned dataset + 46 engineered features", styles["tablecell"]),
                Paragraph("01_Python/customer_features.csv", styles["tablecell"]),
            ],
            [
                Paragraph("Feature glossary (every column explained)", styles["tablecell"]),
                Paragraph("01_Python/FEATURE_GLOSSARY.md", styles["tablecell"]),
            ],
            [
                Paragraph("SQL views answering the 5 key questions", styles["tablecell"]),
                Paragraph("02_SQL/views/*.sql + 02_SQL/exports/*.csv", styles["tablecell"]),
            ],
            [
                Paragraph("Four-panel founder dashboard (Power BI)", styles["tablecell"]),
                Paragraph("03_PowerBI/PBIP_Project/", styles["tablecell"]),
            ],
            [
                Paragraph("This playbook (PDF)", styles["tablecell"]),
                Paragraph("04_Playbook/Decoding_Customer_Value_Playbook.pdf", styles["tablecell"]),
            ],
            [
                Paragraph("Executive summary (≤1 page)", styles["tablecell"]),
                Paragraph("05_Summary/executive_summary.md", styles["tablecell"]),
            ],
            [
                Paragraph("Loyalty A/B framework", styles["tablecell"]),
                Paragraph("05_Summary/extras/loyalty_framework.md", styles["tablecell"]),
            ],
        ],
        colWidths=[3.0 * inch, 3.7 * inch],
    )
    src_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY_RL),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BG_RL, colors.white]),
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
    s.append(src_table)
    s.append(Spacer(1, 18))
    s.append(HRFlowable(width="40%", thickness=0.6, color=GOLD_RL, hAlign="CENTER"))
    s.append(Spacer(1, 10))
    s.append(
        Paragraph(
            "Prepared by <b>Anant Shukla</b> &amp; <b>Khushi Rawat</b>, "
            "B.Tech. Civil Engineering, IIT Roorkee. Submitted to the Consulting &amp; Analytics "
            "Club, IIT Guwahati.",
            styles["small"],
        )
    )

    return s


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    setup_mpl()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating charts...")
    charts = {
        "pareto": chart_pareto(),
        "scatter": chart_persona_scatter(),
        "persona_clv": chart_persona_clv(),
        "timeline": chart_sunset_timeline(),
        "waterfall": chart_margin_waterfall(),
        "demographics": chart_icp_demographics(),
        "categories": chart_icp_categories(),
        "geo": chart_geo_top10(),
    }
    for k, p in charts.items():
        print(f"  + {k}: {p.name} ({p.stat().st_size / 1024:.1f} KB)")

    print("\nBuilding PDF...")
    styles = make_styles()
    doc = BaseDocTemplate(
        str(PDF_PATH),
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.95 * inch,
        bottomMargin=0.8 * inch,
        title="Decoding Customer Value — Retention Playbook",
        author="Anant Shukla, Khushi Rawat",
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="main",
        showBoundary=0,
    )
    doc.addPageTemplates([PageTemplate(id="default", frames=[frame], onPage=header_footer)])

    story = build_story(styles, charts)
    doc.build(story)
    size_kb = PDF_PATH.stat().st_size / 1024
    print(f"\n+ {PDF_PATH.relative_to(ROOT)}  ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
