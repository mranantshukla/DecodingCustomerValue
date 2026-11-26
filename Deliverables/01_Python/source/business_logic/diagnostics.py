"""Lightweight diagnostics: bootstrap CIs, sensitivity, and feature correlations.

The goal of this module is *decision-relevant* uncertainty, not statistical
theatre. Three concrete artefacts are produced:

  1. **Bootstrap CIs** for the few headline metrics leadership actually quotes
     (top-20% value share, % CLV discount-attached, avg CLV by persona). Tells
     the reader "this is real" vs "this could move materially on resampling".

  2. **Sensitivity table** for the two main modelling assumptions (margin
     haircut, tenure multiplier) — by how much does CLV move when the assumption
     shifts ±20%? Quantifies the risk in the assumption set.

  3. **Feature correlation matrix** over the engineered features, so any
     hidden multicollinearity (e.g. between loyalty_v2 and CLV — by design)
     is visible rather than implicit.

Outputs land in ``reports/diagnostics/`` as CSV + Markdown summary.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from config.settings import Settings, get_settings
from src.feature_engineering.value import MARGIN_HAIRCUT, MAX_TENURE_BONUS
from src.utils.logging_config import get_logger

log = get_logger(__name__)

DEFAULT_N_BOOTSTRAP = 500


@dataclass
class CI:
    metric: str
    point: float
    lo: float
    hi: float

    def to_dict(self) -> dict:
        return {"metric": self.metric, "point": self.point, "lo": self.lo, "hi": self.hi}


def _bootstrap(values: np.ndarray, fn, n: int, seed: int) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    n_rows = len(values)
    samples = np.empty(n, dtype=float)
    for i in range(n):
        idx = rng.integers(0, n_rows, n_rows)
        samples[i] = fn(values[idx])
    return float(fn(values)), float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))


def headline_confidence_intervals(
    feat: pd.DataFrame, n_bootstrap: int = DEFAULT_N_BOOTSTRAP, seed: int = 42
) -> list[CI]:
    """Bootstrap 95% CIs on a small set of decision-relevant metrics."""
    clv = feat["estimated_clv_proxy"].to_numpy(dtype=float)
    disc_flag = feat["discount_applied_flag"].to_numpy(dtype=float)

    def top20_share(arr: np.ndarray) -> float:
        cut = np.quantile(arr, 0.80)
        return float(arr[arr >= cut].sum() / arr.sum())

    def disc_attached(arr: np.ndarray) -> float:
        # arr is a 2-col stack [clv, disc_flag]
        clv_, flag_ = arr[:, 0], arr[:, 1]
        return float((clv_ * flag_).sum() / clv_.sum())

    out: list[CI] = []
    out.append(CI("top20_clv_share", *_bootstrap(clv, top20_share, n_bootstrap, seed)))

    # Stack the two arrays so bootstrap pairs them.
    stacked = np.column_stack([clv, disc_flag])

    def boot_disc(idx_array: np.ndarray) -> float:
        return disc_attached(idx_array)

    # Manually run bootstrap on the stacked pair (the generic helper takes 1-D).
    rng = np.random.default_rng(seed + 1)
    samples = np.empty(n_bootstrap)
    n_rows = len(stacked)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n_rows, n_rows)
        samples[i] = boot_disc(stacked[idx])
    out.append(
        CI(
            "pct_clv_discount_attached",
            float(disc_attached(stacked)),
            float(np.quantile(samples, 0.025)),
            float(np.quantile(samples, 0.975)),
        )
    )

    # Avg CLV inside each persona (top 3 personas by size only — actionable focus).
    top_personas = feat["customer_persona"].value_counts().head(3).index.tolist()
    for persona in top_personas:
        vals = feat.loc[feat["customer_persona"] == persona, "estimated_clv_proxy"].to_numpy(float)
        if len(vals) >= 30:
            point, lo, hi = _bootstrap(vals, np.mean, n_bootstrap, seed + len(out))
            out.append(CI(f"avg_clv__{persona.replace(' ', '_')}", point, lo, hi))
    return out


def sensitivity_table(feat: pd.DataFrame) -> pd.DataFrame:
    """How much does total CLV move when the two main assumptions shift ±20%?"""
    annual = feat["annual_value"].to_numpy(float)
    disc = feat["discount_applied_flag"].to_numpy(float)
    loyalty_v2 = feat["loyalty_score_v2"].to_numpy(float)

    rows = []
    for haircut_scale in (0.8, 1.0, 1.2):
        for tenure_scale in (0.8, 1.0, 1.2):
            margin = 1.0 - (MARGIN_HAIRCUT * haircut_scale) * disc
            tenure = 1.0 + (MAX_TENURE_BONUS * tenure_scale) * loyalty_v2
            total_clv = (annual * margin * tenure).sum()
            rows.append(
                {
                    "margin_haircut_scale": haircut_scale,
                    "tenure_multiplier_scale": tenure_scale,
                    "total_clv": round(float(total_clv), 0),
                }
            )
    df = pd.DataFrame(rows)
    base = df.loc[
        (df.margin_haircut_scale == 1.0) & (df.tenure_multiplier_scale == 1.0), "total_clv"
    ].iloc[0]
    df["pct_vs_base"] = (100 * (df["total_clv"] - base) / base).round(1)
    return df


def feature_correlations(feat: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlation across the engineered numeric features."""
    cols = [
        "loyalty_score_v1",
        "loyalty_score_v2",
        "loyalty_confidence_index",
        "repeat_purchase_intensity",
        "brand_affinity_score",
        "promo_dependency_score",
        "non_discount_purchase_ratio",
        "annual_value",
        "economic_value_proxy",
        "estimated_clv_proxy",
        "expected_tenure_years",
        "high_value_probability",
        "shipping_urgency_index",
        "payment_repeat_index",
        "organic_demand_score",
        "region_quality_index",
    ]
    present = [c for c in cols if c in feat.columns]
    return feat[present].corr(method="pearson").round(3)


def run_diagnostics(feat: pd.DataFrame, settings: Settings | None = None) -> dict[str, Path]:
    """Write all diagnostics artefacts. Returns the paths it created."""
    settings = settings or get_settings()
    out_dir = settings.reports_path / "diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)

    cis = headline_confidence_intervals(feat)
    sens = sensitivity_table(feat)
    corr = feature_correlations(feat)

    paths: dict[str, Path] = {}
    paths["confidence_intervals"] = out_dir / "confidence_intervals.csv"
    pd.DataFrame([c.to_dict() for c in cis]).to_csv(paths["confidence_intervals"], index=False)
    paths["sensitivity"] = out_dir / "sensitivity.csv"
    sens.to_csv(paths["sensitivity"], index=False)
    paths["correlations"] = out_dir / "feature_correlations.csv"
    corr.to_csv(paths["correlations"])

    paths["summary"] = out_dir / "diagnostics_summary.md"
    paths["summary"].write_text(_to_markdown(cis, sens, corr), encoding="utf-8")
    log.info("Wrote diagnostics (%d files) -> %s", len(paths), out_dir)
    return paths


def _to_markdown(cis: list[CI], sens: pd.DataFrame, corr: pd.DataFrame) -> str:
    lines = [
        "# Diagnostics",
        "",
        "Lightweight, decision-relevant uncertainty quantification. CIs are 95% "
        "bootstrap (resampling with replacement); sensitivity scales the two main "
        "modelling assumptions ±20%; correlations expose multicollinearity by design.",
        "",
        "## 1. Bootstrap 95% confidence intervals",
        "",
        "| Metric | Point | 2.5% | 97.5% | Half-width |",
        "|---|---:|---:|---:|---:|",
    ]
    for c in cis:
        hw = (c.hi - c.lo) / 2
        lines.append(f"| {c.metric} | {c.point:.4f} | {c.lo:.4f} | {c.hi:.4f} | {hw:.4f} |")

    lines += [
        "",
        "**Read-out.** Narrow intervals (half-width < a few percentage points) mean "
        "the metric is *real* and would survive a re-sample of the customer base. "
        "Wider intervals — typical of small persona slices — should be quoted with "
        "their range, not as point estimates.",
        "",
        "## 2. Assumption sensitivity (total projected CLV)",
        "",
        "| Margin haircut × | Tenure mult × | Total CLV | % vs base |",
        "|---:|---:|---:|---:|",
        *[
            f"| {row.margin_haircut_scale:.1f} | {row.tenure_multiplier_scale:.1f} | "
            f"${row.total_clv:,.0f} | {row.pct_vs_base:+.1f}% |"
            for row in sens.itertuples(index=False)
        ],
        "",
        "**Read-out.** Total CLV scales roughly linearly with the tenure multiplier "
        "and inversely (more mildly) with the margin haircut. The 1.0/1.0 row is "
        "the base case; the spread shows how much an assumption shift moves the "
        "headline. Use this to size confidence in absolute CLV figures.",
        "",
        "## 3. Feature correlation matrix",
        "",
        "Saved separately as `feature_correlations.csv` (16×16). High correlations "
        "to highlight (and that are expected by design):",
        "",
    ]
    # Pick out a few high-cor pairs to flag explicitly.
    pairs = []
    for i, a in enumerate(corr.columns):
        for j, b in enumerate(corr.columns):
            if j <= i:
                continue
            v = corr.iloc[i, j]
            if abs(v) >= 0.7:
                pairs.append((a, b, v))
    pairs.sort(key=lambda x: -abs(x[2]))
    for a, b, v in pairs[:10]:
        lines.append(f"- `{a}` ↔ `{b}`: **{v:+.2f}**")
    if not pairs:
        lines.append("_No pair exceeded |0.70|._")
    lines += [
        "",
        "Loyalty ↔ CLV correlation is high *by design* (loyalty feeds the tenure "
        "term). This is why the loyalty framework validates against "
        "`economic_value_proxy` (loyalty-free), not against CLV.",
        "",
    ]
    return "\n".join(lines) + "\n"
