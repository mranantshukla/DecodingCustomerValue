# Diagnostics

Lightweight, decision-relevant uncertainty quantification. CIs are 95% bootstrap (resampling with replacement); sensitivity scales the two main modelling assumptions ±20%; correlations expose multicollinearity by design.

## 1. Bootstrap 95% confidence intervals

| Metric | Point | 2.5% | 97.5% | Half-width |
|---|---:|---:|---:|---:|
| top20_clv_share | 0.5950 | 0.5841 | 0.6062 | 0.0111 |
| pct_clv_discount_attached | 0.3903 | 0.3659 | 0.4159 | 0.0250 |
| avg_clv__Standard | 1521.4772 | 1444.5578 | 1606.1643 | 80.8032 |
| avg_clv__Promo_Hunter | 815.6346 | 771.7997 | 857.0774 | 42.6388 |
| avg_clv__Promo-Dependent_High-Value | 5599.7968 | 5324.9857 | 5871.3158 | 273.1651 |

**Read-out.** Narrow intervals (half-width < a few percentage points) mean the metric is *real* and would survive a re-sample of the customer base. Wider intervals — typical of small persona slices — should be quoted with their range, not as point estimates.

## 2. Assumption sensitivity (total projected CLV)

| Margin haircut × | Tenure mult × | Total CLV | % vs base |
|---:|---:|---:|---:|
| 0.8 | 0.8 | $10,986,128 | -12.8% |
| 0.8 | 1.0 | $12,771,902 | +1.4% |
| 0.8 | 1.2 | $14,557,676 | +15.6% |
| 1.0 | 0.8 | $10,836,863 | -14.0% |
| 1.0 | 1.0 | $12,598,340 | +0.0% |
| 1.0 | 1.2 | $14,359,816 | +14.0% |
| 1.2 | 0.8 | $10,687,599 | -15.2% |
| 1.2 | 1.0 | $12,424,778 | -1.4% |
| 1.2 | 1.2 | $14,161,957 | +12.4% |

**Read-out.** Total CLV scales roughly linearly with the tenure multiplier and inversely (more mildly) with the margin haircut. The 1.0/1.0 row is the base case; the spread shows how much an assumption shift moves the headline. Use this to size confidence in absolute CLV figures.

## 3. Feature correlation matrix

Saved separately as `feature_correlations.csv` (16×16). High correlations to highlight (and that are expected by design):

- `loyalty_score_v2` ↔ `expected_tenure_years`: **+1.00**
- `promo_dependency_score` ↔ `non_discount_purchase_ratio`: **-1.00**
- `annual_value` ↔ `economic_value_proxy`: **+0.99**
- `economic_value_proxy` ↔ `estimated_clv_proxy`: **+0.98**
- `annual_value` ↔ `estimated_clv_proxy`: **+0.98**
- `loyalty_score_v1` ↔ `loyalty_score_v2`: **+0.92**
- `loyalty_score_v1` ↔ `expected_tenure_years`: **+0.92**
- `repeat_purchase_intensity` ↔ `high_value_probability`: **+0.87**
- `loyalty_score_v2` ↔ `high_value_probability`: **+0.86**
- `expected_tenure_years` ↔ `high_value_probability`: **+0.86**

Loyalty ↔ CLV correlation is high *by design* (loyalty feeds the tenure term). This is why the loyalty framework validates against `economic_value_proxy` (loyalty-free), not against CLV.

