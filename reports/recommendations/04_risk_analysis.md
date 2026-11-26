# Risk Analysis, Assumptions & Limitations
### What could go wrong, and what we are taking on faith

A recommendation is only as good as the honesty of its caveats. This section
states the assumptions the analysis rests on, the things that could invalidate
it, and the trade-offs leadership is implicitly accepting.

---

## 1. Data limitations (the big ones)

| Limitation | Impact | Mitigation |
|---|---|---|
| **No timestamps** | Tenure, recency, and true purchase velocity are unobservable. Loyalty/CLV are *proxies* from `previous_purchases` (volume) + `frequency_of_purchases` (cadence). | Proxies are used for **ranking**, not as audited financials. Validate against real transaction logs before booking value. |
| **No churn labels** | "Retention" is inferred (loyalty as a proxy), not measured. | Treat churn-risk figures in the simulator as scenario inputs, not predictions. |
| **`Discount Applied` ≡ `Promo Code Used`** | One signal, not two. | Redundant column dropped; documented in validation. |
| **Subscription–discount confound** | Every subscriber is discounted → "subscribers are discount-dependent" is an artefact. | Promo metrics reported net of subscription where it matters; flagged on every surface. |
| **Gender–discount confound** | No female customer is discounted in source. | ICP and targeting deliberately **do not** use gender; geo promo rates flagged directional. |
| **Single transaction per customer** | Category breadth, seasonal consistency cannot be directly observed. | Computed as clearly-labelled **estimates**; never presented as observed behaviour. |

## 2. Key modelling assumptions (and their sensitivity)

| Assumption | Default | If wrong… | How to test |
|---|---|---|---|
| Cadence → annual frequency mapping | Weekly=52 … Annually=1 | Mis-scales CLV velocity term | Calibrate against real order counts |
| Expected tenure = 1 + 4×loyalty_v2 | 1–5 years | Scales all CLV proportionally | Back out from observed retention curves |
| Margin haircut on discounted sales | 15% | Over/understates margin recovery | Use actual category gross margins |
| Premium = top-20% CLV | P80 | Changes cohort size, not the thesis | Adjust `DCV_THRESH_premium_value_percentile` |
| Loyalty weights (Definition B) | fixed | Could reorder champions | **Loyalty Simulator** shows robustness (high top-tier overlap under ±20%) |

> The loyalty definition was **stress-tested**: top-quintile membership is stable
> under ±20% weight perturbation (see `reports/loyalty_framework.md`), so the core
> conclusions are not an artefact of a single weight choice.

## 3. Execution risks of the recommendations

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| Sunsetting a load-bearing discount → churn | Med | High | Reversible waves; high-value cohort gated behind loyalty programme (Wave 4) |
| Brand backlash to "lost discount" | Med | Med | Reframe as added rewards; lead with perks, never price |
| Over-investing in noisy customers | Low | Med | `loyalty_confidence_index` down-weights thin-history customers |
| KMeans cluster instability | Low | Low | Clusters used only to *validate* rule-based personas, not to drive action |
| Targeting on confounded variables | Med | High | Gender excluded from targeting; segment promo rates treated as directional |

## 4. Trade-offs leadership is accepting
- **Margin now vs volume later:** the sunset plan trades some short-term
  discount-driven volume for structural margin and healthier demand.
- **Simplicity vs nuance:** Definition B (margin-aware loyalty) adds two
  assumptions over the volume-led version in exchange for separating *profitable*
  loyalty from *habitual* discount use — a trade we judged worthwhile and
  documented.
- **Proxy speed vs measured certainty:** engineered proxies let us act now;
  certainty requires the transactional data the source lacks.

## 5. What would change the conclusions
1. Real transaction history showing discount-dependent customers **do** lapse at
   full price → slow the sunset, widen the loyalty-programme net.
2. Actual gross margins materially below 15% → smaller recovery, re-prioritise to
   the cleanest waves only.
3. Evidence that the gender/subscription confound reflects genuine behaviour (not
   data generation) → revisit promo-by-segment targeting.

**Bottom line:** the *direction* (protect the top, wean off habitual discounting,
acquire ICP look-alikes) is robust to these uncertainties. The *magnitudes*
should be re-estimated against transactional data before large budget commitment.
