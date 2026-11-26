# Limitations & Ethics

The credibility of this project rests on being *visibly* honest about what the
data can and cannot say. This page consolidates those caveats in one place,
beyond the per-doc footnotes.

## 1. What the data can support

- **Ranking** customers, regions, and categories on the engineered metrics.
- **Concentration** statements (e.g. "top 20% hold 60% of projected CLV") —
  these are stable under bootstrap resampling (see
  [diagnostics](../reports/diagnostics/diagnostics_summary.md)).
- **Directional** comparisons (which markets / personas are healthier).
- **Decision framing** — the dataset is rich enough to scope the *shape* of a
  retention strategy, even if the *magnitudes* require validation.

## 2. What the data cannot support

| Claim | Why it would be unsafe |
|---|---|
| Audited financial figures (LTV, GMV) | No timestamps. CLV is a forward proxy with explicit assumptions. |
| Churn probabilities | No churn labels exist; "loyalty" is a *behavioural composite*, not a survival model. |
| Causal claims about discounting | Discount, subscription, and gender are structurally entangled (see §4). |
| Cross-category breadth per customer | Single transaction per customer; `category_breadth_est` is a clearly-labelled estimate. |
| Discount price-elasticity | Requires price variation per customer, which the data does not show. We expose an *aggregate proxy* only. |

## 3. Honest tagging of every engineered feature

Each feature in [FEATURE_GLOSSARY.md](FEATURE_GLOSSARY.md) carries a
`proxy_quality` tag — `derived`, `composite`, `empirical`, `proxy`, or
`estimate`. The first three are fully reliable signals; the last two carry the
caveats above and should never be quoted without context. The tag flows from
the registry to the docs automatically, so it cannot drift from the code.

## 4. The structural confounds

These are not edge cases; they are central to the source data and the analysis
deliberately accounts for them everywhere:

1. **`Discount Applied` ≡ `Promo Code Used`** are perfectly collinear. Treated
   as one signal; the redundant column is dropped.
2. **Every subscriber is discounted** in the source data. "Subscribers are
   discount-dependent" is therefore a *data artefact*, not behaviour.
3. **No female customer is discounted** in the source data. Regional discount
   rates partly reflect gender mix, not pure regional behaviour. Targeting in
   the ICP and the sunset plan deliberately does **not** condition on gender.

The validation engine asserts (1); the executive summary and recommendations
flag (2) and (3) explicitly. The Streamlit cockpit shows the caveat banner on
every page.

## 5. Ethics

- **Targeting:** the project recommends targeting and suppression by *behaviour*
  (Promo Hunter, ICP look-alike) — never by demographic protected classes. The
  ICP document explicitly excludes gender from acquisition targeting.
- **Discount sunset:** the plan sequences customers by *risk*, with reversible
  waves and a high-care path for the high-value discount-dependent cohort.
  Discount withdrawal is reframed as added rewards, not punitive price changes.
- **Reproducibility & auditability:** every figure quoted in the executive
  summary and recommendations can be traced to a named SQL view or pipeline
  artefact. There is no "black-box" model whose decisions cannot be inspected.
- **Privacy:** the dataset has no PII beyond a synthetic `customer_id` and
  city-level location. No effort is made (or possible) to re-identify customers.

## 6. What would change the conclusions

If we had real transactional data with timestamps:

| Today's proxy | Could be replaced by |
|---|---|
| `expected_tenure_years` from loyalty | Observed survival / Kaplan-Meier curves |
| `estimated_clv_proxy` | Discounted-cashflow CLV with empirical retention |
| `frequency_of_purchases` mapping | Actual annualised purchase rate per customer |
| `category_breadth_est` | Observed distinct-category count |
| Discount elasticity *proxies* | Actual price-test elasticities |

The **direction** of the recommendations (protect the top, sequence the sunset,
acquire ICP look-alikes) is robust to those upgrades; the **magnitudes** should
be re-estimated against real data before large budget commitment.

## 7. How we keep ourselves honest

- **Diagnostics** (bootstrap CIs, sensitivity, correlations) ship in every run
  and quantify uncertainty for the headline metrics.
- **The loyalty A/B framework** is validated against an *orthogonal* value
  metric (`economic_value_proxy`) that contains no loyalty term, so the
  validation is not self-correlation.
- **Invariant tests** check monotonicity, decomposition identity, and stability
  under small input noise.
- **No ML black boxes.** Every score is a transparent, auditable formula in
  `src/feature_engineering/` with weights reviewable in code review.
