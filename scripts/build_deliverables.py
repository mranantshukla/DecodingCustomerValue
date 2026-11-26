"""build_deliverables.py — Assemble a self-contained `Deliverables/` folder
that maps 1:1 to the PDF's Deliverables table:

    Python   -> 01_Python   (cleaned dataset + engineered features)
    SQL      -> 02_SQL      (segmentation queries answering 5 key questions)
    Power BI -> 03_PowerBI  (four-panel founder dashboard PBIP)
    Playbook -> 04_Playbook (promo sunset plan + ICP)
    Summary  -> 05_Summary  (executive summary)

Output: e:/Cagiitg/Deliverables/
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path("e:/Cagiitg")
OUT = ROOT / "Deliverables"


def clean() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(src, dst)
        print(f"  + {dst.relative_to(OUT)}")
    else:
        print(f"  ! MISSING: {src}")


def copy_tree(src: Path, dst: Path, *, ignore_patterns: tuple[str, ...] = ()) -> None:
    if not src.exists():
        print(f"  ! MISSING TREE: {src}")
        return
    ignore = shutil.ignore_patterns(*ignore_patterns) if ignore_patterns else None
    shutil.copytree(src, dst, ignore=ignore, dirs_exist_ok=True)
    n = sum(1 for _ in dst.rglob("*") if _.is_file())
    print(f"  + {dst.relative_to(OUT)}/  ({n} files)")


# ─────────────────────────────────────────────────────────────────────────────
# Section 1 — Python (cleaned data + engineered features)
# ─────────────────────────────────────────────────────────────────────────────


def build_python_section() -> None:
    sec = OUT / "01_Python"
    print("\n[1/5] Python — cleaned dataset + engineered features")
    copy_file(ROOT / "data" / "processed" / "customer_features.csv", sec / "customer_features.csv")
    copy_file(ROOT / "data" / "raw" / "Dataset.csv", sec / "raw_dataset.csv")
    copy_file(ROOT / "docs" / "FEATURE_GLOSSARY.md", sec / "FEATURE_GLOSSARY.md")
    copy_file(ROOT / "docs" / "DATA_DICTIONARY.md", sec / "DATA_DICTIONARY.md")
    # Source code (only the directly relevant modules)
    copy_tree(
        ROOT / "src" / "data_processing",
        sec / "source" / "data_processing",
        ignore_patterns=("__pycache__",),
    )
    copy_tree(
        ROOT / "src" / "feature_engineering",
        sec / "source" / "feature_engineering",
        ignore_patterns=("__pycache__",),
    )
    copy_tree(
        ROOT / "src" / "business_logic",
        sec / "source" / "business_logic",
        ignore_patterns=("__pycache__",),
    )
    copy_file(ROOT / "src" / "pipeline.py", sec / "source" / "pipeline.py")


# ─────────────────────────────────────────────────────────────────────────────
# Section 2 — SQL (5 key questions)
# ─────────────────────────────────────────────────────────────────────────────


def build_sql_section() -> None:
    sec = OUT / "02_SQL"
    print("\n[2/5] SQL — segmentation queries answering all 5 key questions")
    copy_tree(ROOT / "src" / "sql" / "views", sec / "views")
    copy_tree(ROOT / "src" / "sql" / "queries", sec / "queries")
    copy_tree(ROOT / "reports" / "sql_exports", sec / "exports")
    copy_file(ROOT / "docs" / "SQL_DOCUMENTATION.md", sec / "SQL_DOCUMENTATION.md")
    copy_file(ROOT / "docs" / "SQL_METRICS.md", sec / "SQL_METRICS.md")


# ─────────────────────────────────────────────────────────────────────────────
# Section 3 — Power BI (four-panel founder dashboard)
# ─────────────────────────────────────────────────────────────────────────────


def build_powerbi_section() -> None:
    sec = OUT / "03_PowerBI"
    print("\n[3/5] Power BI — four-panel founder dashboard")
    # The working PBIP (legacy variant — opens cleanly without preview features)
    copy_tree(ROOT / "powerbi" / "dashboard_v2_legacy", sec / "PBIP_Project")
    # Theme
    copy_file(ROOT / "powerbi" / "theme.json", sec / "theme.json")
    # Layout spec
    copy_file(ROOT / "powerbi" / "DASHBOARD_GUIDE.md", sec / "DASHBOARD_GUIDE.md")
    # DAX measures reference
    copy_file(ROOT / "powerbi" / "measures.dax", sec / "measures.dax")
    # Screenshots
    for name in (
        "founder_dashboard_mockup.png",
        "powerbi_v2_legacy_full_dashboard.png",
        "powerbi_v2_legacy_visuals.png",
        "powerbi_v2_legacy_loaded.png",
    ):
        src = ROOT / "assets" / name
        if src.exists():
            copy_file(src, sec / "screenshots" / name)


# ─────────────────────────────────────────────────────────────────────────────
# Section 4 — Playbook (promo sunset plan + ICP)
# ─────────────────────────────────────────────────────────────────────────────


def build_playbook_section() -> None:
    sec = OUT / "04_Playbook"
    print("\n[4/5] Playbook — promo sunset plan + ideal customer profile")
    # Required by PDF:
    copy_file(
        ROOT / "reports" / "recommendations" / "01_promotional_sunset_plan.md",
        sec / "01_promotional_sunset_plan.md",
    )
    copy_file(
        ROOT / "reports" / "recommendations" / "02_ideal_customer_profile.md",
        sec / "02_ideal_customer_profile.md",
    )
    # Bonus (beyond PDF requirements):
    copy_file(
        ROOT / "reports" / "recommendations" / "03_growth_strategy.md",
        sec / "extras" / "03_growth_strategy.md",
    )
    copy_file(
        ROOT / "reports" / "recommendations" / "04_risk_analysis.md",
        sec / "extras" / "04_risk_analysis.md",
    )
    copy_file(
        ROOT / "docs" / "LIMITATIONS_AND_ETHICS.md",
        sec / "extras" / "LIMITATIONS_AND_ETHICS.md",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Section 5 — Summary (executive summary, ≤1 page)
# ─────────────────────────────────────────────────────────────────────────────


def build_summary_section() -> None:
    sec = OUT / "05_Summary"
    print("\n[5/5] Summary - executive summary (<= 1 page) + intelligence report")
    copy_file(ROOT / "reports" / "executive_summary.md", sec / "executive_summary.md")
    # Bonus consolidated report (beyond PDF):
    copy_file(
        ROOT / "reports" / "CUSTOMER_INTELLIGENCE_REPORT.md",
        sec / "extras" / "CUSTOMER_INTELLIGENCE_REPORT.md",
    )
    copy_file(
        ROOT / "reports" / "loyalty_framework.md",
        sec / "extras" / "loyalty_framework.md",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Top-level README mapping PDF deliverables to files
# ─────────────────────────────────────────────────────────────────────────────


README = """# Deliverables — Decoding Customer Value: A SQL-Driven Retention Strategy

> **Consulting & Analytics Club — IIT Guwahati**
> Submission for the official Problem Statement PDF.

## Submitted by

| Team member | Programme | Institute | Email |
|---|---|---|---|
| **Anant Shukla** | B.Tech. Civil Engineering | IIT Roorkee | anant_s@ce.iitr.ac.in |
| **Khushi Rawat** | B.Tech. Civil Engineering | IIT Roorkee | khushi_r@ce.iitr.ac.in |

---

This folder is self-contained and maps 1:1 to the **Deliverables table on page 3
of the PDF**:

| PDF Deliverable | Folder | What's inside |
|---|---|---|
| **Python** — Cleaned dataset + engineered features (dependency score, value tier, satisfaction flag) | [`01_Python/`](01_Python/) | `customer_features.csv` (3,900 rows × 46 typed features), the raw dataset, the feature glossary, and the source code that produced them |
| **SQL** — Segmentation queries answering all 5 key questions | [`02_SQL/`](02_SQL/) | 19 SQL views (`views/`) + 6 ad-hoc analytical queries (`queries/`), CSV exports (`exports/`), and full documentation |
| **Power BI** — Four-panel founder dashboard as described in scope | [`03_PowerBI/`](03_PowerBI/) | PBIP project (opens in Power BI Desktop, save as `.pbix`), theme, DAX measures, layout spec, and screenshots of the rendered dashboard |
| **Playbook** — Promo sunset plan + ideal customer profile | [`04_Playbook/`](04_Playbook/) | The two required documents at the root; two bonus recommendations (`growth`, `risk`) in `extras/` |
| **Summary** — Concise executive summary (max 1 page) of findings and recommendations | [`05_Summary/`](05_Summary/) | `executive_summary.md` (≤1 page); bonus 3-page consolidated `CUSTOMER_INTELLIGENCE_REPORT.md` and `loyalty_framework.md` in `extras/` |

---

## How to consume this folder

1. **Read first:** [`05_Summary/executive_summary.md`](05_Summary/executive_summary.md) — one page, gives the verdict and the headlines.
2. **For the Power BI dashboard:** [`03_PowerBI/PBIP_Project/DecodingCustomerValue_V2_Legacy.pbip`](03_PowerBI/PBIP_Project/) — open in Power BI Desktop, refresh, save as `.pbix`. The 4 panels and 4 KPI cards render automatically from the embedded `report.json`.
3. **For the SQL layer:** every CSV in [`02_SQL/exports/`](02_SQL/exports/) is the output of the SQL view of the same name in [`02_SQL/views/`](02_SQL/views/). The 5 PDF questions map 1:1 to views — see [`02_SQL/SQL_DOCUMENTATION.md`](02_SQL/SQL_DOCUMENTATION.md).
4. **For the recommendations:** [`04_Playbook/01_promotional_sunset_plan.md`](04_Playbook/01_promotional_sunset_plan.md) names the SEGMENT, TRIGGER, TIMELINE, METRIC per wave (as the PDF mandates — "Reduce discounts is not an acceptable answer"). [`04_Playbook/02_ideal_customer_profile.md`](04_Playbook/02_ideal_customer_profile.md) gives the ICP precise enough for a marketing team to act on today.

---

## How the dashboard satisfies the four PDF panel mandates

The PDF section 3 mandates these four panels for the Founder Dashboard. Each is present:

| PDF mandate | How it's built |
|---|---|
| **Customer pyramid** — value distribution across the customer base | `revenue_tier_contribution` bar chart (Bronze · Silver · Gold · Platinum) — Power BI Panel 1 |
| **Promo dependency vs. retention rate, plotted by segment** | Scatter bubble chart: X = avg promo dependency, Y = avg loyalty, bubbles = customer personas — Power BI Panel 2 |
| **Geographic opportunity map — high spend AND low promo dependency** | Filled map keyed off `margin_adjusted_clv` = `estimated_clv × (1 − promo_dependency)` — encodes both signals in one metric. Power BI Panel 3 |
| **Category funnel — low purchase history vs high purchase history** | Funnel of entry-point categories by `new_ish_customers` count (customers with < median previous_purchases) — Power BI Panel 4 |

---

## How the methodology satisfies the Central Analytical Challenge

The PDF's "Central Analytical Challenge" requires:

- **Loyalty must be defined, not declared. At least two competing definitions, tested, with one defended.**
  → Two definitions (A: behaviour-only, B: behaviour + margin-aware) are scored on 5 criteria
  in [`05_Summary/extras/loyalty_framework.md`](05_Summary/extras/loyalty_framework.md). **Definition B wins** with 0.666 vs 0.627 on the orthogonal `economic_value_proxy` validation target. The score is not self-correlated because the validation target excludes loyalty from its construction.

- **Every segment claim must be traceable.**
  → Each of the 6 personas (`Premium Loyalist`, `Loyal Full-Price`, `Margin-at-Risk Premium`, `Promo Hunter`, `At-Risk Premium`, `Casual Buyer`) is a stated combination of `loyalty_tier × promo_reliance_tier × revenue_contribution_tier`. See [`02_SQL/views/10_segmentation.sql`](02_SQL/views/10_segmentation.sql).

- **Expected Outcome question:** "Is the business successfully building a loyal customer base, or is it reliant on continuous promotional activity?"
  → Answered explicitly on the first line of [`05_Summary/executive_summary.md`](05_Summary/executive_summary.md): **partially reliant — 43% discounted, 39% of CLV discount-attached, but most is habit not stimulus. Loyalty is being built, but the brand is also subsidising demand it doesn't need to.**

"""


def write_readme() -> None:
    (OUT / "README.md").write_text(README, encoding="utf-8")
    print(f"\n+ README.md ({len(README)} bytes)")


def main() -> None:
    print(f"Building deliverables bundle at {OUT}")
    clean()
    build_python_section()
    build_sql_section()
    build_powerbi_section()
    build_playbook_section()
    build_summary_section()
    write_readme()

    # Final inventory
    n_files = sum(1 for _ in OUT.rglob("*") if _.is_file())
    total_bytes = sum(_.stat().st_size for _ in OUT.rglob("*") if _.is_file())
    print(f"\nDone. {n_files} files, {total_bytes / 1024 / 1024:.1f} MB total")
    print(f"\nBundle root: {OUT}")


if __name__ == "__main__":
    main()
