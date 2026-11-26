# Promotional Sunset Plan
### Weaning the base off discounts without sacrificing revenue

**Prepared for:** D2C Fashion Brand — Executive Leadership
**Prepared by:** Customer Value Analytics
**Status:** Recommendation for decision

---

## 1. The problem in one line

**43% of customers receive a discount, and ~39% of projected customer value is
"discount-attached" — but most of that discounting is habit, not stimulus.** The
brand is paying to retain customers who would largely stay anyway, while a
genuinely price-sensitive minority masks the difference.

The objective is **not** to cut promotions across the board. It is to **stop
discounting the customers who do not need it**, redirecting that margin toward
acquisition and the retention of customers who genuinely respond to price.

## 2. Segmentation for the sunset (who loses discounts, and when)

We sequence by a simple, defensible rule: **withdraw discounts first where churn
risk is lowest and margin recovery is cleanest.** The `promo_reliance_tier`
feature gives us exactly this ordering.

| Wave | Segment (promo reliance) | Logic | Churn risk | Action |
|---|---|---|---|---|
| **Wave 1 (Month 0–2)** | Full-Price Loyalists currently receiving incidental discounts (~351 customers) | They already buy at full price; the discount is leakage. | **Negligible** | Stop auto-applying discounts; replace with non-price perks (early access, free returns). |
| **Wave 2 (Month 2–4)** | Occasional-Discount tier | Discount is a nudge, not a crutch. | **Low–moderate** | Reduce discount frequency/depth; A/B test price-hold vs −5%. |
| **Wave 3 (Month 4–8)** | Discount-Dependent, **low value** (Promo Hunters, ~1,047) | Low CLV; not worth subsidising. | Moderate (acceptable) | Let lapse gracefully; no margin spent defending. |
| **Wave 4 (Month 8–12)** | Discount-Dependent, **high value** (~230 customers, ~$2.1M CLV) | Real margin at stake; must be handled with care. | **High** | Migrate to a loyalty/membership construct that rewards *behaviour*, not price. Soft landing only. |

> **Why this order matters:** Waves 1–2 are nearly pure margin recovery. Wave 4
> is where naïve discount-cutting destroys value — so it goes last, behind a
> loyalty programme, never as a blunt price increase.

## 3. Rollout timeline

```
Month:      0────2────4────6────8────10────12
Wave 1  ████████
Wave 2       ████████
Wave 3            ██████████
Wave 4                      ████████████  (with loyalty programme live first)
Monitoring ───────────────────────────────►  (KPIs reviewed monthly)
```

## 4. Financial impact (illustrative, from the model)

- **Wave 1 alone** recovers an estimated **~$54k/yr** in margin from full-price-
  leaning customers who are currently discounted (at a 15% margin-recovery
  assumption), at negligible churn risk.
- The **Promo Impact Simulator** (`src/dashboard/pages/5_Promo_Impact_Simulator.py`)
  lets leadership re-run the full waterfall under their own margin and churn
  assumptions before committing budget.
- The **high-value discount-dependent cohort (~$2.1M CLV)** is explicitly *not*
  touched until Wave 4, capping downside.

## 5. KPI monitoring (review monthly)

| KPI | Target direction | Source |
|---|---|---|
| % CLV discount-attached | ↓ | `v_revenue_discount_split` |
| Discount penetration (% customers) | ↓ controlled | `v_executive_kpis.pct_discounted` |
| Full-price repeat rate (non_discount_purchase_ratio) | ↑ or hold | feature table |
| Churn proxy in affected waves (lapse vs baseline) | within plan | cohort tracking |
| Gross margin % | ↑ | finance |
| Top-20% CLV retention | hold ≥ 100% | `v_revenue_concentration` |

**Stop-loss rule:** if any wave's churn proxy exceeds plan by >50%, pause that
wave and shift the affected customers to the loyalty-programme track.

## 6. Risks & mitigations
- **Risk: cutting a discount that was actually load-bearing.** → Waves are
  reversible; Wave 4 is gated behind the loyalty programme.
- **Risk: brand-perception spillover.** → Frame as "better rewards", never as
  "we removed your discount". Lead with perks.
- **Risk: confounded data.** Subscription/gender are entangled with discounting
  in the source (see caveats), so treat *segment-level* discount rates as
  directional and validate Wave 4 targeting against live behaviour before acting.
