"""End-to-end pipeline orchestrator — the single entrypoint for the whole project.

    python -m src.pipeline            # full run with defaults
    python -m src.pipeline --no-db    # skip the SQL layer (features only)
    dcv-pipeline                      # console-script alias (after pip install -e .)

Stages, in order:
    1. Ingest raw CSV
    2. Clean  -> data/processed/customers_clean.csv
    3. Validate (blocks on ERROR-severity failures when DCV_STRICT_VALIDATION)
    4. Profile -> reports/profiling_summary.{json,md}
    5. Engineer features
    6. Select canonical loyalty definition (A vs B) -> reports/loyalty_framework.md
    7. Segment customers (personas + behavioural clusters)
       -> data/processed/customer_features.csv
    8. Load SQL analytics layer + export views -> reports/sql_exports/*.csv
    9. Write executive insight summary -> reports/executive_summary.md

Every stage logs its inputs/outputs; a failed run is diagnosable from the log.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass

import pandas as pd

from config.settings import Settings, get_settings
from src.business_logic.diagnostics import run_diagnostics
from src.business_logic.insights import write_executive_summary, write_intelligence_report
from src.business_logic.loyalty_framework import (
    attach_canonical_loyalty,
    evaluate_loyalty_definitions,
    framework_to_markdown,
)
from src.business_logic.segmentation import persona_summary, segment_customers
from src.data_processing.clean import clean_dataset
from src.data_processing.profile import profile_dataframe, profile_to_markdown
from src.data_processing.validate import validate
from src.feature_engineering.build_features import build_features
from src.sql.runner import build_database, export_views
from src.utils.io import read_csv, write_csv, write_json
from src.utils.logging_config import get_logger


@dataclass
class PipelineArtifacts:
    """Handles to the in-memory outputs, returned for tests and the dashboard."""

    clean: pd.DataFrame
    features: pd.DataFrame
    loyalty_winner: str
    personas: pd.DataFrame


@dataclass
class StageTiming:
    """Per-stage wall-clock measurements (in seconds), useful for perf tracking."""

    timings: dict[str, float]

    def total(self) -> float:
        return sum(self.timings.values())


class _Stage:
    """Context manager that times a pipeline stage and logs it."""

    def __init__(self, name: str, log, bucket: dict[str, float]) -> None:
        self.name, self.log, self.bucket = name, log, bucket

    def __enter__(self):
        self.log.info(">> stage start: %s", self.name)
        self._t = time.perf_counter()
        return self

    def __exit__(self, *exc):
        dt = time.perf_counter() - self._t
        self.bucket[self.name] = dt
        self.log.info("OK stage done : %s (%.2fs)", self.name, dt)


def run_pipeline(settings: Settings | None = None, *, build_sql: bool = True) -> PipelineArtifacts:
    settings = settings or get_settings()
    log = get_logger("dcv.pipeline", settings.log_level)
    settings.ensure_dirs()
    timings: dict[str, float] = {}
    t0 = time.perf_counter()

    log.info("=" * 78)
    log.info("DECODING CUSTOMER VALUE — pipeline start")
    log.info("=" * 78)

    with _Stage("ingest", log, timings):
        raw = read_csv(settings.raw_data_file)

    with _Stage("clean", log, timings):
        clean = clean_dataset(raw)
        write_csv(clean, settings.processed_path / "customers_clean.csv")

    with _Stage("validate", log, timings):
        report = validate(clean)
        write_json(report.to_dict(), settings.reports_path / "validation_report.json")
        (settings.reports_path / "validation_report.md").write_text(
            report.to_markdown(), encoding="utf-8"
        )
        if report.has_errors and settings.strict_validation:
            raise SystemExit("Validation failed with blocking ERROR(s); aborting (strict mode).")

    with _Stage("profile", log, timings):
        profile = profile_dataframe(clean)
        write_json(profile, settings.reports_path / "profiling_summary.json")
        (settings.reports_path / "profiling_summary.md").write_text(
            profile_to_markdown(profile), encoding="utf-8"
        )

    with _Stage("features", log, timings):
        feat = build_features(clean)

    with _Stage("loyalty_framework", log, timings):
        framework = evaluate_loyalty_definitions(feat)
        (settings.reports_path / "loyalty_framework.md").write_text(
            framework_to_markdown(framework), encoding="utf-8"
        )
        write_json(framework.to_dict(), settings.reports_path / "loyalty_framework.json")
        feat = attach_canonical_loyalty(feat, framework.winner)

    with _Stage("segment", log, timings):
        feat = segment_customers(feat)
        write_csv(feat, settings.processed_path / "customer_features.csv")
        personas = persona_summary(feat)
        write_csv(personas, settings.reports_path / "persona_summary.csv")

    if build_sql:
        with _Stage("sql_layer", log, timings):
            db = build_database(feat, settings)
            export_views(db, settings)

    with _Stage("diagnostics", log, timings):
        run_diagnostics(feat, settings)

    with _Stage("executive_summary", log, timings):
        write_executive_summary(feat, framework, settings)

    with _Stage("intelligence_report", log, timings):
        write_intelligence_report(feat, framework, settings)

    # Persist the per-stage timings — useful for spotting regressions over time.
    write_json(timings, settings.reports_path / "pipeline_timings.json")

    elapsed = time.perf_counter() - t0
    log.info("=" * 78)
    log.info(
        "Pipeline complete in %.2fs | %d customers | loyalty=%s",
        elapsed,
        len(feat),
        framework.winner,
    )
    log.info(
        "Stage breakdown: %s",
        {k: round(v, 2) for k, v in sorted(timings.items(), key=lambda kv: -kv[1])},
    )
    log.info("Outputs: %s (data) | %s (reports)", settings.processed_path, settings.reports_path)
    log.info("=" * 78)

    return PipelineArtifacts(
        clean=clean, features=feat, loyalty_winner=framework.winner, personas=personas
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Decoding Customer Value pipeline")
    parser.add_argument("--no-db", action="store_true", help="Skip the SQL analytics layer")
    args = parser.parse_args()
    run_pipeline(build_sql=not args.no_db)


if __name__ == "__main__":
    main()
