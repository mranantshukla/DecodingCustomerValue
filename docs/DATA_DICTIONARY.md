# Data Dictionary

Two layers are documented: the **raw source fields** (as shipped in
`data/raw/Dataset.csv`) and the **cleaned/derived columns** produced by the
pipeline. Engineered analytical features are documented separately in
[FEATURE_GLOSSARY.md](FEATURE_GLOSSARY.md).

## 1. Raw source fields (`data/raw/Dataset.csv`)

| Raw column | Clean name | Type | Domain / range | Notes |
|---|---|---|---|---|
| Customer ID | `customer_id` | int | unique | Primary key, one row per customer |
| Age | `age` | int | 18–70 | |
| Gender | `gender` | str | Male, Female | **Confounded with discount** (no female is discounted) |
| Item Purchased | `item_purchased` | str | 25 items | |
| Category | `category` | str | Clothing, Accessories, Footwear, Outerwear | |
| Purchase Amount (USD) | `purchase_amount` | float | 20–100 | Representative transaction amount |
| Location | `location` | str | 50 US states | |
| Size | `size` | str | S, M, L, XL | |
| Color | `color` | str | 25 colors | |
| Season | `season` | str | Spring, Summer, Fall, Winter | |
| Review Rating | `review_rating` | float | 2.5–5.0 | **37 nulls** → imputed by category median |
| Subscription Status | `subscription_status` | str | Yes, No | **Every subscriber is discounted** (confound) |
| Shipping Type | `shipping_type` | str | 6 types | Maps to `shipping_urgency_index` |
| Discount Applied | `discount_applied` | str | Yes, No | Canonical promo signal |
| Promo Code Used | _(dropped)_ | str | Yes, No | **Perfectly collinear with Discount Applied** → dropped |
| Previous Purchases | `previous_purchases` | int | 1–50 | Key loyalty/volume signal |
| Payment Method | `payment_method` | str | 6 methods | Maps to `payment_stability_score` |
| Frequency of Purchases | `frequency_of_purchases` | str | 7 cadences | Mapped to annual frequency + ordinal rank |

## 2. Derived columns added during cleaning

| Column | Type | Description |
|---|---|---|
| `review_rating_imputed` | bool | True where `review_rating` was missing and imputed |
| `subscription_status_flag` | bool | `subscription_status == 'Yes'` |
| `discount_applied_flag` | bool | `discount_applied == 'Yes'` |

## 3. Base derivations added during feature engineering

| Column | Type | Description |
|---|---|---|
| `annual_purchase_freq` | float | Cadence → annualised purchase count (Weekly=52 … Annually=1) |
| `freq_rank` | int | Ordinal cadence rank 1 (Annually) … 7 (Weekly) |
| `freq_rank_norm` | float | `freq_rank / 7` |
| `satisfaction_norm` | float | `(review_rating − 1) / 4`, clipped to [0,1] |
| `age_norm` | float | min-max scaled age |
| `annual_value` | float | `purchase_amount × annual_purchase_freq` |

## 4. Segmentation columns

| Column | Type | Values |
|---|---|---|
| `loyalty_score` | float | Canonical loyalty (winning definition) |
| `loyalty_tier` | str | L1-Dormant … L5-Champion (quintiles) |
| `customer_persona` | str | Premium Loyalist, Loyal Full-Price, Promo-Dependent High-Value, At-Risk Premium, High-Value Low-Frequency, Promo Hunter, Standard |
| `behaviour_cluster` | str | C0 … C{n−1}, ordered low→high mean CLV (KMeans) |

## 5. Key assumptions (see also [`reports/recommendations/04_risk_analysis.md`](../reports/recommendations/04_risk_analysis.md))

- **No timestamps** → tenure/CLV are engineered proxies from volume + cadence.
- **Cadence → annual frequency** mapping is an explicit, tunable assumption.
- **Margin haircut** on discounted sales assumed 15% (config-tunable).
- **Premium** = top 20% of projected CLV (config-tunable percentile).
