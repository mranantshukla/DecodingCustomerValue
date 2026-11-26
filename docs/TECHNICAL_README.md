# Technical README (Developer Guide)

Engineering-facing companion to the root `README.md`. Covers local setup, the
module map, conventions, and how to extend each layer.

## 1. Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"          # core + postgres + dashboard + validation + dev
pre-commit install               # black + ruff on commit
pytest -q                        # run the suite
python -m src.pipeline           # full run
```

Minimal install (core pipeline only, no extras):
```bash
pip install pandas numpy pydantic pydantic-settings python-dotenv scikit-learn matplotlib
python -m src.pipeline --no-db   # or with the stdlib sqlite3 default DB
```

## 2. Module map

```
config/settings.py            Pydantic settings + BusinessThresholds + DB URL resolution
src/
  utils/
    logging_config.py         get_logger() — one stdout handler, namespaced loggers
    schema.py                 RAW_TO_CLEAN contract, domains, frequency maps  ← edit columns here
    io.py                     read_csv / write_csv / write_json (logged)
  data_processing/
    clean.py                  composable cleaning steps + clean_dataset()
    validate.py               severity-tagged check engine + ValidationReport
    profile.py                JSON/Markdown profiling
    schemas.py                OPTIONAL pandera schema (import-guarded)
  feature_engineering/
    base.py                   minmax/zscore/sigmoid/percentile/tier helpers
    registry.py               FEATURE_REGISTRY — single source of truth (21 features)
    loyalty.py promotion.py value.py behavioral.py geography.py
    build_features.py         orchestrates families in dependency order
  business_logic/
    loyalty_framework.py      A/B scoring + selection + canonical attach
    segmentation.py           personas (rules) + behaviour_cluster (KMeans)
    insights.py               headline metrics, caveats, executive_summary.md
  sql/
    database.py               DatabaseManager (SQLAlchemy ↔ sqlite3) + statement splitter
    runner.py                 load table, apply schema/views, export view CSVs
    schema/ views/ queries/   the SQL itself
  dashboard/                  Streamlit app (app.py + pages/) + theme + cached data_access
  pipeline.py                 run_pipeline() + CLI entrypoint (dcv-pipeline)
scripts/generate_glossary.py  regenerates docs/FEATURE_GLOSSARY.md from the registry
tests/                        cleaning, features, loyalty/segmentation, SQL
```

## 3. Conventions
- **Type hints + docstrings** on public functions; docstrings state the *why*.
- **No hard-coded thresholds** in logic — put them in `config/settings.py`.
- **Columns** are referenced via `src/utils/schema.py`, never as string literals
  scattered across modules.
- **Logging, not print** — every stage logs inputs/outputs.
- **Determinism** — seeded (`DCV_RANDOM_SEED`); a feature determinism test guards it.
- **Style** — black (line length 100) + ruff; enforced by pre-commit and CI.

## 4. Extending

| To add… | Do this | Guardrail |
|---|---|---|
| A feature | function in the right `feature_engineering` module + `FeatureSpec` in `registry.py` | `test_all_registered_features_present` fails if unregistered |
| A SQL view | `.sql` file in `src/sql/views/`; add to `VIEW_EXPORTS` to export it | runner applies it automatically |
| A validation rule | add a `CheckResult` in `validate.py` | severity controls whether it blocks |
| A dashboard page | file in `src/dashboard/pages/` | Streamlit auto-discovers it |
| A threshold | field on `BusinessThresholds` | overridable via `DCV_THRESH_*` |

## 5. Testing
```bash
pytest -q                       # all
pytest tests/test_sql_layer.py  # one module
pytest --cov=src                # coverage (needs pytest-cov)
```
The SQL tests build a real SQLite DB in a temp dir from a fresh `Settings`
instance, so they never touch your working database.

## 6. Performance notes
- Full pipeline ≈ 8–10s on 3,900 rows (KMeans + 16 view exports dominate).
- For larger data: switch to Postgres, convert hot views to materialized views,
  and consider chunked feature computation (the transforms are vectorised today).
