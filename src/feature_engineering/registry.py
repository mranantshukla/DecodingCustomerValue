"""Feature registry: the single source of truth for every engineered feature.

Each feature is documented here with its formula, the business question it
answers, *why leadership would care*, and an honest **proxy_quality** tag so
consumers know whether a value is observed, derived, proxied, or estimated.

This registry powers two things:
  1. ``docs/FEATURE_GLOSSARY.md`` is generated from it (docs never drift from code).
  2. Tests assert that every registered feature actually appears in the output.

If you add a feature without registering it, the glossary test fails — by design.

Proxy-quality scale (most reliable -> least):
  * **derived**   — a deterministic transform of observed columns (e.g. flags,
                    annual_value, percentile tiers). Fully reliable.
  * **composite** — a transparent weighted blend of observed/derived signals
                    (the loyalty scores, brand affinity). Reliable but assumption-
                    bearing; the weights are auditable here.
  * **empirical** — derived from group-level statistics observed in the data
                    (e.g. payment_repeat_index, region elasticity). Honest about
                    the data; may be weak if the group signal is weak.
  * **proxy**     — a stand-in for an unobservable construct, derived from
                    related signals (e.g. promo_dependency_score blending an
                    individual flag with a segment baseline). Directional.
  * **estimate**  — a clearly-labelled best guess for something the source data
                    cannot directly measure (e.g. category_breadth_est on
                    single-transaction data). Use for ranking, not as a fact.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    group: str
    dtype: str
    formula: str
    rationale: str  # what it measures + why leadership cares
    proxy_quality: str = "derived"  # one of: derived | composite | empirical | proxy | estimate


FEATURE_REGISTRY: list[FeatureSpec] = [
    # --- Loyalty -------------------------------------------------------------
    FeatureSpec(
        "loyalty_score_v1",
        "Loyalty",
        "float[0-1]",
        "0.50*norm(previous_purchases) + 0.30*(freq_rank/7) + 0.20*subscription_flag",
        "Volume-led loyalty (Definition A). Transparent and easy to defend, but "
        "treats a discount-driven frequent buyer the same as a full-price one.",
        proxy_quality="composite",
    ),
    FeatureSpec(
        "loyalty_score_v2",
        "Loyalty",
        "float[0-1]",
        "0.35*norm(prev) + 0.25*(freq_rank/7) + 0.15*subscription + 0.15*satisfaction_norm "
        "+ 0.10*non_discount_ratio",
        "Margin-aware loyalty (Definition B). Rewards customers who buy often, AT "
        "FULL PRICE, and are satisfied. Distinguishes profitable loyalty from habit.",
        proxy_quality="composite",
    ),
    FeatureSpec(
        "loyalty_confidence_index",
        "Loyalty",
        "float[0-1]",
        "0.60*norm(previous_purchases) + 0.40*(1 - review_rating_imputed)",
        "How much to trust a customer's loyalty score. Thin history or imputed "
        "satisfaction lowers confidence — stops leadership over-investing on noise.",
        proxy_quality="composite",
    ),
    FeatureSpec(
        "repeat_purchase_intensity",
        "Loyalty",
        "float[0-1]",
        "norm(previous_purchases * annual_purchase_freq)",
        "Momentum: volume weighted by cadence. A high-RPI customer is actively "
        "repeating now, not just historically — the prime retention-marketing target.",
        proxy_quality="derived",
    ),
    FeatureSpec(
        "brand_affinity_score",
        "Loyalty",
        "float[0-1]",
        "0.30*subscription + 0.30*satisfaction_norm + 0.20*(freq_rank/7) + 0.20*non_discount_ratio",
        "Attitudinal closeness to the brand (vs transactional volume). Identifies "
        "advocates and referral/community candidates, not just big spenders.",
        proxy_quality="composite",
    ),
    # --- Promotion -----------------------------------------------------------
    FeatureSpec(
        "promo_dependency_score",
        "Promotion",
        "float[0-1]",
        "0.70*discount_applied_flag + 0.30*segment_discount_rate(location, category)",
        "How reliant a customer is on discounts, blending their own behaviour with "
        "their micro-segment's discount intensity. Directly sizes margin-at-risk.",
        proxy_quality="proxy",
    ),
    FeatureSpec(
        "non_discount_purchase_ratio",
        "Promotion",
        "float[0-1]",
        "1 - discount_applied_flag",
        "Share of engagement that is full-price. The cleanest single signal of "
        "self-sustaining, healthy demand; feeds the margin-aware loyalty score.",
        proxy_quality="derived",
    ),
    FeatureSpec(
        "discount_elasticity_proxy",
        "Promotion",
        "float (signed)",
        "(mean_amount[discounted] - mean_amount[full]) / mean_amount[full], within category",
        "Proxy for whether discounting grows or shrinks basket size in a category. "
        "Negative => discounts attract bargain-hunters; positive => they lift spend. "
        "Directional only — actual elasticity needs price variation we do not observe.",
        proxy_quality="empirical",
    ),
    FeatureSpec(
        "promo_reliance_tier",
        "Promotion",
        "category",
        "Bucket promo_dependency_score: <0.34 Full-Price, 0.34-0.66 Occasional, >0.66 Dependent",
        "Plain-English segmentation for the promotional sunset plan — tells ops "
        "exactly which customers can lose discounts safely first.",
        proxy_quality="derived",
    ),
    # --- Value ---------------------------------------------------------------
    FeatureSpec(
        "estimated_clv_proxy",
        "Value",
        "float (USD)",
        "economic_value_proxy * expected_tenure_years; "
        "tenure = 1 + 4*loyalty_v2 (loyalty enters HERE, not earlier)",
        "Forward 1–5yr value with explicit, auditable assumptions. The backbone "
        "metric for retention budgeting. Decomposed deliberately: the loyalty-free "
        "`economic_value_proxy` is the orthogonal target used to validate loyalty.",
        proxy_quality="composite",
    ),
    FeatureSpec(
        "revenue_contribution_tier",
        "Value",
        "category",
        "Quartile of estimated_clv_proxy -> Platinum / Gold / Silver / Bronze",
        "Turns CLV into an actionable hierarchy. Enables the customer pyramid and "
        "the 'protect the top 20%' executive narrative.",
        proxy_quality="derived",
    ),
    FeatureSpec(
        "high_value_probability",
        "Value",
        "float[0-1]",
        "sigmoid(z) over standardised non-spend signals (annual_purchase_freq, prev, "
        "freq, subscription) — explicitly excludes loyalty and CLV to avoid leakage",
        "Propensity-to-be-high-value scored from BEHAVIOUR, so it can rank new/low-"
        "history customers for proactive nurture before they prove out.",
        proxy_quality="composite",
    ),
    FeatureSpec(
        "premium_customer_flag",
        "Value",
        "bool",
        "estimated_clv_proxy >= P80 of CLV distribution",
        "The high-value cohort the whole engagement protects. Percentile-based so "
        "it stays meaningful as the customer base scales.",
        proxy_quality="derived",
    ),
    # --- Behavioural ---------------------------------------------------------
    FeatureSpec(
        "satisfaction_flag",
        "Behavioural",
        "bool",
        "review_rating >= 3.8 (config: satisfaction_rating_floor)",
        "Binary CX health marker. Pairs with loyalty to separate 'loyal & happy' "
        "(protect) from 'loyal but unhappy' (at-risk despite the numbers).",
        proxy_quality="derived",
    ),
    FeatureSpec(
        "category_breadth_est",
        "Behavioural",
        "float[1-4]",
        "1 + 3 * percentile_rank(previous_purchases)  (rank-based, robust to outliers)",
        "Estimated cross-category repertoire. A rescaled depth-of-history signal "
        "since single-transaction data cannot directly observe breadth. Use for "
        "ranking only — not as an absolute count.",
        proxy_quality="estimate",
    ),
    FeatureSpec(
        "shipping_urgency_index",
        "Behavioural",
        "float[0-1]",
        "ordinal_rank(shipping_type) / (n_options - 1)   "
        "[Pickup=0 ... Next Day=1, uniform 0.2 steps]",
        "Willingness to pay for speed — a premium-intent signal independent of "
        "spend. Uniform ordinal steps (no hand-picked gaps).",
        proxy_quality="derived",
    ),
    FeatureSpec(
        "payment_repeat_index",
        "Behavioural",
        "float[0-1]",
        "min-max(mean previous_purchases by payment_method)  "
        "— empirically derived, not opinion-coded",
        "How repeat-prone customers on each payment method are, OBSERVED in the "
        "data. Replaces the previous hand-coded stability score; honest about a "
        "weak signal if the data shows one.",
        proxy_quality="empirical",
    ),
    FeatureSpec(
        "seasonal_consistency_score",
        "Behavioural",
        "float[0-1]",
        "P(observed_season | category) from the data",
        "How typical a customer's buying season is for their category. Drives "
        "inventory timing and seasonal campaign targeting.",
        proxy_quality="empirical",
    ),
    # --- Geography -----------------------------------------------------------
    FeatureSpec(
        "organic_demand_score",
        "Geography",
        "float[0-1]",
        "1 - location_discount_rate",
        "Share of a region's demand that occurs WITHOUT discounts. High = healthy, "
        "self-sustaining market worth doubling down on; low = propped up by promos.",
        proxy_quality="empirical",
    ),
    FeatureSpec(
        "region_quality_index",
        "Geography",
        "float[0-1]",
        "mean(norm(loc_avg_loyalty_v2), norm(loc_avg_satisfaction), organic_demand, norm(loc_avg_clv))",
        "Composite health score per region. Ranks geographies for expansion vs "
        "rationalisation — a board-level capital-allocation lens.",
        proxy_quality="composite",
    ),
    FeatureSpec(
        "promo_sensitivity_geo",
        "Geography",
        "float (signed)",
        "Within-region (mean_amount[disc] - mean_amount[full]) / mean_amount[full]",
        "Regional discount elasticity. Tells you where pulling promotions is safe "
        "(low sensitivity) vs where it will hurt volume (high sensitivity). "
        "Directional only — confounded with gender mix per data caveats.",
        proxy_quality="empirical",
    ),
]


def feature_names() -> list[str]:
    return [f.name for f in FEATURE_REGISTRY]
