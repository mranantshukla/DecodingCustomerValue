# Interviewer / Recruiter Walkthrough

A focused 15-minute tour of the project for a technical interviewer or
analytics-engineering recruiter. Pick the section that matches the conversation
you want to have.

## 30-second pitch
> A D2C fashion brand needs to find the most-valuable customers and reduce
> promotional dependency. The dataset has **no timestamps, no churn, no loyalty
> label** — so loyalty, value, and retention are *engineered* from first
> principles, two competing loyalty definitions are scored against an
> **orthogonal** value target, and the winning model drives a full SQL
> analytics layer plus Streamlit and Power BI deliverables. One command rebuilds
> everything, 42 tests guard the invariants, lightweight diagnostics quantify
> the uncertainty in the headline numbers.

## The three things to look at first

1. **`reports/loyalty_framework.md`** — two loyalty definitions scored on five
   commercial criteria (revenue alignment, margin alignment, separation,
   robustness, explainability) against the **loyalty-free** `economic_value_proxy`.
   This is where the analytical maturity is most visible.
2. **`docs/FEATURE_GLOSSARY.md`** — every engineered feature with formula,
   rationale, and a `proxy_quality` tag (derived / composite / empirical / proxy
   / estimate). Auto-generated from the registry so docs cannot drift from code.
3. **`reports/diagnostics/diagnostics_summary.md`** — bootstrap CIs on the
   headline KPIs and a ±20% sensitivity table on the two main modelling
   assumptions. Tells you *which numbers to trust to two decimals*.

## "Show me the architecture"
- Layered pipeline (clean → validate → profile → features → loyalty A/B →
  segment → SQL → diagnostics → exec summary) with one entrypoint.
- Pydantic-driven config; business thresholds are configuration, not constants.
- Database manager abstracts SQLite (default, zero-setup) and PostgreSQL.
- See [ARCHITECTURE.md](ARCHITECTURE.md) for the diagram.

## "Show me the analytical rigour"
- **Two competing loyalty definitions**, not one. Volume-led (Definition A) vs
  margin-aware (Definition B), explicitly evaluated and selected.
- **Orthogonal validation target**: loyalty is evaluated against
  `economic_value_proxy` (which contains no loyalty term), not against CLV
  (which mechanically includes loyalty). This breaks a subtle self-correlation
  the v1 of this project had.
- **Bootstrap CIs** on headline metrics (`top20_clv_share` is `59.5% ±~1pp`,
  rock-solid; persona-level averages have wider CIs that are honestly reported).
- **Sensitivity table**: total CLV shifts ±14% under ±20% tenure changes; only
  ±1.4% under margin shifts — the dominant uncertainty is in the tenure
  assumption, which is therefore the first thing to validate against real data.

## "Show me the SQL"
- 19 documented analytical views: segmentation, geography, product, revenue,
  executive — all running on SQLite **and** PostgreSQL.
- **`v_metrics_base`** is the semantic layer: every other view consumes it for
  grand totals so a number cannot disagree between the dashboard, the exec
  summary, and an ad-hoc query.
- CTEs + window functions for deciles, ranks, and cumulative Pareto curves.
- See [SQL_DOCUMENTATION.md](SQL_DOCUMENTATION.md) and
  [SQL_METRICS.md](SQL_METRICS.md).

## "Show me the engineering"
- 42 tests including **property/invariant tests** (monotonicity, orthogonality
  decomposition, noise stability, fuzz on subsets, negative cases).
- `ruff` + `black` clean; CI runs across Python 3.10/3.11/3.12.
- Per-stage timing logged in every pipeline run (`reports/pipeline_timings.json`).
- Streamlit app: reusable UI helpers, persistent global filter via
  `st.session_state`, a small CSS pass for executive feel (no animation).

## "Show me the business framing"
- Read `reports/executive_summary.md` (auto-generated), then the four
  consulting docs under `reports/recommendations/` (sunset plan, ICP, growth,
  risk analysis). Every figure is traced to a SQL view or pipeline artefact.
- Three structural confounds in the source data are flagged on every surface
  (see [LIMITATIONS_AND_ETHICS.md](LIMITATIONS_AND_ETHICS.md)).

## Likely interview questions, and where to answer them

| Question | Where to look |
|---|---|
| "How did you define loyalty?" | `src/feature_engineering/loyalty.py` + `reports/loyalty_framework.md` |
| "How do you know your loyalty score is good?" | The orthogonal-target validation in the framework, plus `noise_robustness` invariant test |
| "How confident are you in the top-20% claim?" | `reports/diagnostics/confidence_intervals.csv` — `top20_clv_share = 0.595 [0.584, 0.606]` |
| "Aren't subscribers just discount-dependent?" | The confound is flagged everywhere; `data_integrity_caveats()` in `insights.py` explains why that claim is a data artefact |
| "Would your dashboard scale?" | `v_metrics_base` semantic layer + indexes in `01_schema.sql` + the Postgres switch via one env var |
| "Why two loyalty definitions?" | A single loyalty score is an opinion; two scored on five criteria is a decision |
| "What's the riskiest assumption?" | The tenure multiplier (sensitivity table shows ±14% CLV move under ±20% shift) |

## What I deliberately *didn't* do
- No deep-learning, no random forest "churn prediction" without labels.
- No dbt or warehouse semantic-layer DSL — over-engineering at 3,900 rows.
- No fake precision (the old `payment_stability = 0.85 for Bank Transfer` is now
  empirically derived; the old `shipping_urgency = 0.3 for Free Shipping`
  step is now a uniform ordinal rank).
- No targeting on protected classes (the ICP excludes gender by design).
