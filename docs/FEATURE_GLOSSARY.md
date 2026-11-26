# Feature Glossary

> **Auto-generated** from `src/feature_engineering/registry.py` (`python scripts/generate_glossary.py`). Do not edit by hand.

The pipeline engineers **21 features** across 5 families. Every feature lists its formula, what it measures, why leadership should care, and an honest **proxy-quality** tag.

## Proxy-quality legend

| Tag | Meaning |
|---|---|
| `derived` | Deterministic transform of observed columns. Fully reliable. |
| `composite` | Transparent weighted blend of observed/derived signals (weights auditable). |
| `empirical` | Computed from group-level statistics observed in the data. |
| `proxy` | Stand-in for an unobservable construct, built from related signals. Directional. |
| `estimate` | Clearly-labelled best guess for something the data cannot directly measure. |

## Loyalty

### `loyalty_score_v1`  _(float[0-1])_  · quality: `composite`

- **Formula:** `0.50*norm(previous_purchases) + 0.30*(freq_rank/7) + 0.20*subscription_flag`
- **Why it matters:** Volume-led loyalty (Definition A). Transparent and easy to defend, but treats a discount-driven frequent buyer the same as a full-price one.

### `loyalty_score_v2`  _(float[0-1])_  · quality: `composite`

- **Formula:** `0.35*norm(prev) + 0.25*(freq_rank/7) + 0.15*subscription + 0.15*satisfaction_norm + 0.10*non_discount_ratio`
- **Why it matters:** Margin-aware loyalty (Definition B). Rewards customers who buy often, AT FULL PRICE, and are satisfied. Distinguishes profitable loyalty from habit.

### `loyalty_confidence_index`  _(float[0-1])_  · quality: `composite`

- **Formula:** `0.60*norm(previous_purchases) + 0.40*(1 - review_rating_imputed)`
- **Why it matters:** How much to trust a customer's loyalty score. Thin history or imputed satisfaction lowers confidence — stops leadership over-investing on noise.

### `repeat_purchase_intensity`  _(float[0-1])_  · quality: `derived`

- **Formula:** `norm(previous_purchases * annual_purchase_freq)`
- **Why it matters:** Momentum: volume weighted by cadence. A high-RPI customer is actively repeating now, not just historically — the prime retention-marketing target.

### `brand_affinity_score`  _(float[0-1])_  · quality: `composite`

- **Formula:** `0.30*subscription + 0.30*satisfaction_norm + 0.20*(freq_rank/7) + 0.20*non_discount_ratio`
- **Why it matters:** Attitudinal closeness to the brand (vs transactional volume). Identifies advocates and referral/community candidates, not just big spenders.

## Promotion

### `promo_dependency_score`  _(float[0-1])_  · quality: `proxy`

- **Formula:** `0.70*discount_applied_flag + 0.30*segment_discount_rate(location, category)`
- **Why it matters:** How reliant a customer is on discounts, blending their own behaviour with their micro-segment's discount intensity. Directly sizes margin-at-risk.

### `non_discount_purchase_ratio`  _(float[0-1])_  · quality: `derived`

- **Formula:** `1 - discount_applied_flag`
- **Why it matters:** Share of engagement that is full-price. The cleanest single signal of self-sustaining, healthy demand; feeds the margin-aware loyalty score.

### `discount_elasticity_proxy`  _(float (signed))_  · quality: `empirical`

- **Formula:** `(mean_amount[discounted] - mean_amount[full]) / mean_amount[full], within category`
- **Why it matters:** Proxy for whether discounting grows or shrinks basket size in a category. Negative => discounts attract bargain-hunters; positive => they lift spend. Directional only — actual elasticity needs price variation we do not observe.

### `promo_reliance_tier`  _(category)_  · quality: `derived`

- **Formula:** `Bucket promo_dependency_score: <0.34 Full-Price, 0.34-0.66 Occasional, >0.66 Dependent`
- **Why it matters:** Plain-English segmentation for the promotional sunset plan — tells ops exactly which customers can lose discounts safely first.

## Value

### `estimated_clv_proxy`  _(float (USD))_  · quality: `composite`

- **Formula:** `economic_value_proxy * expected_tenure_years; tenure = 1 + 4*loyalty_v2 (loyalty enters HERE, not earlier)`
- **Why it matters:** Forward 1–5yr value with explicit, auditable assumptions. The backbone metric for retention budgeting. Decomposed deliberately: the loyalty-free `economic_value_proxy` is the orthogonal target used to validate loyalty.

### `revenue_contribution_tier`  _(category)_  · quality: `derived`

- **Formula:** `Quartile of estimated_clv_proxy -> Platinum / Gold / Silver / Bronze`
- **Why it matters:** Turns CLV into an actionable hierarchy. Enables the customer pyramid and the 'protect the top 20%' executive narrative.

### `high_value_probability`  _(float[0-1])_  · quality: `composite`

- **Formula:** `sigmoid(z) over standardised non-spend signals (annual_purchase_freq, prev, freq, subscription) — explicitly excludes loyalty and CLV to avoid leakage`
- **Why it matters:** Propensity-to-be-high-value scored from BEHAVIOUR, so it can rank new/low-history customers for proactive nurture before they prove out.

### `premium_customer_flag`  _(bool)_  · quality: `derived`

- **Formula:** `estimated_clv_proxy >= P80 of CLV distribution`
- **Why it matters:** The high-value cohort the whole engagement protects. Percentile-based so it stays meaningful as the customer base scales.

## Behavioural

### `satisfaction_flag`  _(bool)_  · quality: `derived`

- **Formula:** `review_rating >= 3.8 (config: satisfaction_rating_floor)`
- **Why it matters:** Binary CX health marker. Pairs with loyalty to separate 'loyal & happy' (protect) from 'loyal but unhappy' (at-risk despite the numbers).

### `category_breadth_est`  _(float[1-4])_  · quality: `estimate`

- **Formula:** `1 + 3 * percentile_rank(previous_purchases)  (rank-based, robust to outliers)`
- **Why it matters:** Estimated cross-category repertoire. A rescaled depth-of-history signal since single-transaction data cannot directly observe breadth. Use for ranking only — not as an absolute count.

### `shipping_urgency_index`  _(float[0-1])_  · quality: `derived`

- **Formula:** `ordinal_rank(shipping_type) / (n_options - 1)   [Pickup=0 ... Next Day=1, uniform 0.2 steps]`
- **Why it matters:** Willingness to pay for speed — a premium-intent signal independent of spend. Uniform ordinal steps (no hand-picked gaps).

### `payment_repeat_index`  _(float[0-1])_  · quality: `empirical`

- **Formula:** `min-max(mean previous_purchases by payment_method)  — empirically derived, not opinion-coded`
- **Why it matters:** How repeat-prone customers on each payment method are, OBSERVED in the data. Replaces the previous hand-coded stability score; honest about a weak signal if the data shows one.

### `seasonal_consistency_score`  _(float[0-1])_  · quality: `empirical`

- **Formula:** `P(observed_season | category) from the data`
- **Why it matters:** How typical a customer's buying season is for their category. Drives inventory timing and seasonal campaign targeting.

## Geography

### `organic_demand_score`  _(float[0-1])_  · quality: `empirical`

- **Formula:** `1 - location_discount_rate`
- **Why it matters:** Share of a region's demand that occurs WITHOUT discounts. High = healthy, self-sustaining market worth doubling down on; low = propped up by promos.

### `region_quality_index`  _(float[0-1])_  · quality: `composite`

- **Formula:** `mean(norm(loc_avg_loyalty_v2), norm(loc_avg_satisfaction), organic_demand, norm(loc_avg_clv))`
- **Why it matters:** Composite health score per region. Ranks geographies for expansion vs rationalisation — a board-level capital-allocation lens.

### `promo_sensitivity_geo`  _(float (signed))_  · quality: `empirical`

- **Formula:** `Within-region (mean_amount[disc] - mean_amount[full]) / mean_amount[full]`
- **Why it matters:** Regional discount elasticity. Tells you where pulling promotions is safe (low sensitivity) vs where it will hurt volume (high sensitivity). Directional only — confounded with gender mix per data caveats.
