"""Loyalty definition framework: rigorously compare two definitions and pick one.

The brief explicitly requires two competing loyalty definitions and a defensible
selection. We treat this the way a senior consultant would: define the contenders,
score each against criteria that matter commercially, and let the evidence — not
taste — choose.

Definition A  (loyalty_score_v1) — Volume-led
    Loyalty = how much and how often a customer has bought.
    Pro: simple, intuitive, hard to argue with.
    Con: a customer who only ever buys on discount scores as "loyal".

Definition B  (loyalty_score_v2) — Margin-aware
    Loyalty = frequent, satisfied, FULL-PRICE engagement.
    Pro: aligns loyalty with profit; separates habit from genuine preference.
    Con: more assumptions (weights on satisfaction and discount avoidance).

Evaluation criteria (each scored 0–1, higher is better):
    1. Revenue alignment   — |corr| with estimated CLV proxy. A loyalty metric
                             that does not track value is not useful for targeting.
    2. Margin alignment    — corr with non-discount ratio. Does "loyal" mean
                             "profitable", or just "active"?
    3. Segment separation  — gap in mean CLV between top and bottom loyalty
                             quintiles, normalised. Good metrics discriminate.
    4. Robustness          — stability of the top-quintile membership under a
                             ±20% weight perturbation (Jaccard overlap). A metric
                             whose conclusions flip when a weight nudges is fragile.
    5. Explainability      — a fixed expert score: both are linear and readable;
                             A is marginally simpler, B is only slightly heavier.

The winner is the higher weighted total, with the rationale written to a report.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.feature_engineering.loyalty import V2_WEIGHTS, add_loyalty_features
from src.utils.logging_config import get_logger

log = get_logger(__name__)

CRITERIA_WEIGHTS = {
    "revenue_alignment": 0.30,
    "margin_alignment": 0.25,
    "segment_separation": 0.20,
    "robustness": 0.15,
    "explainability": 0.10,
}

# Expert explainability scores (both are transparent linear blends).
EXPLAINABILITY = {"loyalty_score_v1": 1.00, "loyalty_score_v2": 0.85}


@dataclass
class DefinitionScore:
    name: str
    label: str
    criteria: dict[str, float] = field(default_factory=dict)

    @property
    def total(self) -> float:
        return float(sum(CRITERIA_WEIGHTS[k] * v for k, v in self.criteria.items()))


@dataclass
class FrameworkResult:
    scores: list[DefinitionScore]
    winner: str

    def to_dict(self) -> dict:
        return {
            "winner": self.winner,
            "criteria_weights": CRITERIA_WEIGHTS,
            "definitions": [
                {
                    "name": s.name,
                    "label": s.label,
                    "criteria": s.criteria,
                    "total": round(s.total, 4),
                }
                for s in self.scores
            ],
        }


def _quintile_value_gap(df: pd.DataFrame, score_col: str, value_col: str) -> float:
    q = pd.qcut(df[score_col].rank(method="first"), 5, labels=False)
    top = df.loc[q == 4, value_col].mean()
    bot = df.loc[q == 0, value_col].mean()
    denom = df[value_col].mean()
    if not denom:
        return 0.0
    return float(np.clip((top - bot) / denom, 0, 1))


def _robustness_jaccard(df: pd.DataFrame, base_col: str) -> float:
    """Recompute a perturbed v2 and measure top-quintile membership stability.

    We only perturb v2 (it has the most weights to be sensitive to). For v1 we
    perturb its weights analogously. Returns Jaccard overlap of the top quintile.
    """
    base_top = set(df.nlargest(max(1, len(df) // 5), base_col).index)

    rng = np.random.default_rng(42)
    if base_col == "loyalty_score_v2":
        # Perturb v2 weights ±20% and renormalise; recompute.
        perturbed = df.copy()
        w = {k: v * (1 + rng.uniform(-0.2, 0.2)) for k, v in V2_WEIGHTS.items()}
        tot = sum(w.values())
        w = {k: v / tot for k, v in w.items()}
        prev_norm = (df["previous_purchases"] - df["previous_purchases"].min()) / (
            df["previous_purchases"].max() - df["previous_purchases"].min()
        )
        score = (
            w["prev"] * prev_norm
            + w["freq"] * df["freq_rank_norm"]
            + w["sub"] * df["subscription_status_flag"].astype(float)
            + w["sat"] * df["satisfaction_norm"]
            + w["ndr"] * df["non_discount_purchase_ratio"]
        )
        perturbed["_p"] = score
        pert_top = set(perturbed.nlargest(max(1, len(df) // 5), "_p").index)
    else:
        # v1: perturb its three weights.
        prev_norm = (df["previous_purchases"] - df["previous_purchases"].min()) / (
            df["previous_purchases"].max() - df["previous_purchases"].min()
        )
        w = {"prev": 0.5, "freq": 0.3, "sub": 0.2}
        w = {k: v * (1 + rng.uniform(-0.2, 0.2)) for k, v in w.items()}
        tot = sum(w.values())
        w = {k: v / tot for k, v in w.items()}
        score = (
            w["prev"] * prev_norm
            + w["freq"] * df["freq_rank_norm"]
            + w["sub"] * df["subscription_status_flag"].astype(float)
        )
        pert_top = set(score.nlargest(max(1, len(df) // 5)).index)

    inter = len(base_top & pert_top)
    union = len(base_top | pert_top)
    return inter / union if union else 0.0


def evaluate_loyalty_definitions(feat: pd.DataFrame) -> FrameworkResult:
    """Score both definitions across all criteria and select the winner.

    Important: the **target** of the revenue-alignment and segment-separation
    criteria is ``economic_value_proxy`` (current-period margin-adjusted value),
    NOT ``estimated_clv_proxy``. CLV mechanically incorporates loyalty (via the
    tenure term), so evaluating loyalty against CLV is partly self-correlation.
    The orthogonal target removes that loop and produces a clean validation.
    """
    log.info("Evaluating competing loyalty definitions A (v1) and B (v2)")
    df = feat
    # Orthogonal value target (no loyalty in its formula) — see value.py.
    value_col, margin_col = "economic_value_proxy", "non_discount_purchase_ratio"

    scores: list[DefinitionScore] = []
    for col, label in [
        ("loyalty_score_v1", "Definition A — Volume-led"),
        ("loyalty_score_v2", "Definition B — Margin-aware"),
    ]:
        crit = {
            "revenue_alignment": float(abs(df[col].corr(df[value_col]))),
            # Normalise margin corr from [-1,1] to [0,1] (positive alignment is good).
            "margin_alignment": float((df[col].corr(df[margin_col]) + 1) / 2),
            "segment_separation": _quintile_value_gap(df, col, value_col),
            "robustness": _robustness_jaccard(df, col),
            "explainability": EXPLAINABILITY[col],
        }
        scores.append(DefinitionScore(col, label, crit))

    winner = max(scores, key=lambda s: s.total).name
    log.info(
        "Loyalty framework winner: %s (totals: %s)",
        winner,
        {s.name: round(s.total, 3) for s in scores},
    )
    return FrameworkResult(scores=scores, winner=winner)


def framework_to_markdown(result: FrameworkResult) -> str:
    lines = [
        "# Loyalty Definition Framework — A vs B",
        "",
        "Two loyalty definitions were engineered and evaluated against five "
        "commercial criteria. The winner is selected by weighted total score.",
        "",
        "> **Validation target:** revenue-alignment and segment-separation are "
        "computed against `economic_value_proxy` (current-period margin-adjusted "
        "value, **loyalty-free**), not against `estimated_clv_proxy`. CLV contains "
        "a loyalty-derived tenure term, so using it as the target would be partly "
        "self-correlation. The orthogonal target gives a clean validation.",
        "",
        "## Criteria weights",
        "",
        "| Criterion | Weight | Why it matters |",
        "|---|---:|---|",
        "| Revenue alignment | 30% | Loyalty must track customer value to be useful for targeting. |",
        "| Margin alignment | 25% | Distinguishes profitable loyalty from discount-driven habit. |",
        "| Segment separation | 20% | A good metric discriminates high- from low-value customers. |",
        "| Robustness | 15% | Conclusions must not flip when weights are nudged ±20%. |",
        "| Explainability | 10% | Leadership must be able to understand and defend it. |",
        "",
        "## Scores",
        "",
        "| Definition | Revenue | Margin | Separation | Robustness | Explainability | **Total** |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for s in result.scores:
        c = s.criteria
        lines.append(
            f"| {s.label} | {c['revenue_alignment']:.3f} | {c['margin_alignment']:.3f} | "
            f"{c['segment_separation']:.3f} | {c['robustness']:.3f} | "
            f"{c['explainability']:.3f} | **{s.total:.3f}** |"
        )
    winner_label = next(s.label for s in result.scores if s.name == result.winner)
    lines += [
        "",
        f"## Selected definition: **{winner_label}** (`{result.winner}`)",
        "",
        _selection_rationale(result),
        "",
    ]
    return "\n".join(lines) + "\n"


def _selection_rationale(result: FrameworkResult) -> str:
    by_name = {s.name: s for s in result.scores}
    v1, v2 = by_name["loyalty_score_v1"], by_name["loyalty_score_v2"]
    if result.winner == "loyalty_score_v2":
        return (
            "**Definition B (margin-aware) is adopted as the canonical loyalty "
            "metric.** It aligns more strongly with customer value "
            f"({v2.criteria['revenue_alignment']:.3f} vs {v1.criteria['revenue_alignment']:.3f}) "
            "and, critically, with margin "
            f"({v2.criteria['margin_alignment']:.3f} vs {v1.criteria['margin_alignment']:.3f}), "
            "because it explicitly rewards full-price, satisfied, repeat behaviour. "
            "Definition A's blind spot is fatal for this engagement: it labels "
            "discount-dependent buyers as loyal, which would send retention budget "
            "to exactly the customers eroding margin. The modest loss in "
            "explainability (B has two more weights) is an acceptable price for a "
            "metric that distinguishes *profitable* loyalty from *habitual* "
            "discount usage — the central question the brand asked."
        )
    return (
        "**Definition A (volume-led) is adopted.** On this data it matched or beat "
        "the margin-aware variant on the weighted criteria while remaining simpler "
        "to explain. The margin-aware refinements did not add enough discriminating "
        "power to justify their extra assumptions."
    )


def attach_canonical_loyalty(feat: pd.DataFrame, winner: str) -> pd.DataFrame:
    """Expose the chosen definition as ``loyalty_score`` + a 1–5 ``loyalty_tier``."""
    df = feat.copy()
    if winner not in df.columns:
        df = add_loyalty_features(df)
    df["loyalty_score"] = df[winner]
    df["loyalty_tier"] = pd.qcut(
        df["loyalty_score"].rank(method="first"),
        5,
        labels=["L1-Dormant", "L2-Casual", "L3-Engaged", "L4-Committed", "L5-Champion"],
    ).astype("string")
    return df
