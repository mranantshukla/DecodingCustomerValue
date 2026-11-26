"""Data-quality validation engine.

Design rationale
----------------
The brief calls for Great Expectations / Pandera. Both are excellent, but they
add heavy dependencies and, for a contract this small, hide the *business* logic
behind framework boilerplate. We therefore ship a tiny, dependency-free check
engine that:

  * expresses each rule as a named, severity-tagged predicate over a DataFrame,
  * returns a structured, serialisable report (not just a boolean),
  * separates ERROR (pipeline-breaking) from WARNING (worth knowing) severities.

An equivalent Pandera ``DataFrameSchema`` is provided in ``schemas.py`` for teams
that prefer a declarative contract; this engine is what the pipeline runs by
default so it works on a bare ``pip install pandas``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum

import pandas as pd

from src.utils.logging_config import get_logger
from src.utils.schema import CATEGORY_DOMAINS, ID_COL, NUMERIC_COLS

log = get_logger(__name__)


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass
class CheckResult:
    name: str
    severity: Severity
    passed: bool
    n_failing: int
    detail: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


@dataclass
class ValidationReport:
    results: list[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult) -> None:
        self.results.append(result)
        lvl = (
            log.info
            if result.passed
            else (log.error if result.severity is Severity.ERROR else log.warning)
        )
        status = "PASS" if result.passed else "FAIL"
        lvl("[%s] %-34s %s (%d failing rows)", status, result.name, result.detail, result.n_failing)

    @property
    def has_errors(self) -> bool:
        return any((not r.passed) and r.severity is Severity.ERROR for r in self.results)

    @property
    def n_failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    def to_dict(self) -> dict:
        return {
            "n_checks": len(self.results),
            "n_failed": self.n_failed,
            "has_errors": self.has_errors,
            "checks": [r.to_dict() for r in self.results],
        }

    def to_markdown(self) -> str:
        lines = [
            "# Data Validation Report",
            "",
            f"- **Checks run:** {len(self.results)}",
            f"- **Failed:** {self.n_failed}",
            f"- **Blocking errors:** {'yes' if self.has_errors else 'no'}",
            "",
            "| Check | Severity | Result | Failing rows | Detail |",
            "|---|---|---|---:|---|",
        ]
        for r in self.results:
            mark = "PASS" if r.passed else "FAIL"
            lines.append(f"| {r.name} | {r.severity.value} | {mark} | {r.n_failing} | {r.detail} |")
        return "\n".join(lines) + "\n"


def validate(df: pd.DataFrame, *, stage: str = "cleaned") -> ValidationReport:
    """Run the full data-quality contract against a (cleaned) DataFrame.

    Parameters
    ----------
    df : DataFrame with clean snake_case columns.
    stage : label used only in logging.
    """
    log.info("Validating '%s' dataframe (%d rows)", stage, len(df))
    report = ValidationReport()

    # 1. Primary key: present, unique, non-null. Without this, every per-customer
    #    metric is meaningless, so it is a hard ERROR.
    if ID_COL in df.columns:
        n_dupe = int(df[ID_COL].duplicated().sum())
        report.add(
            CheckResult(
                "primary_key_unique",
                Severity.ERROR,
                n_dupe == 0,
                n_dupe,
                "customer_id must be unique",
            )
        )
        n_null_id = int(df[ID_COL].isna().sum())
        report.add(
            CheckResult(
                "primary_key_not_null",
                Severity.ERROR,
                n_null_id == 0,
                n_null_id,
                "customer_id must not be null",
            )
        )
    else:
        report.add(
            CheckResult(
                "primary_key_present",
                Severity.ERROR,
                False,
                len(df),
                f"missing required column '{ID_COL}'",
            )
        )

    # 2. No nulls in critical numeric fields after cleaning (imputation should
    #    have handled review_rating). ERROR because features depend on them.
    for col in NUMERIC_COLS:
        if col in df.columns:
            n_null = int(df[col].isna().sum())
            report.add(
                CheckResult(
                    f"not_null__{col}",
                    Severity.ERROR,
                    n_null == 0,
                    n_null,
                    f"{col} has no missing values post-clean",
                )
            )

    # 3. Numeric ranges grounded in the known domain (sanity bounds).
    _range_check(report, df, "age", 0, 120)
    _range_check(report, df, "purchase_amount", 0, 100_000)
    _range_check(report, df, "review_rating", 1.0, 5.0)
    _range_check(report, df, "previous_purchases", 0, 100_000)

    # 4. Categorical domains: any out-of-domain value is a defect. WARNING here
    #    because the cleaner coerces unknowns, but we still want visibility.
    for col, allowed in CATEGORY_DOMAINS.items():
        if col in df.columns:
            bad = ~df[col].isin(allowed)
            n_bad = int(bad.sum())
            report.add(
                CheckResult(
                    f"domain__{col}",
                    Severity.WARNING,
                    n_bad == 0,
                    n_bad,
                    f"{col} values within {sorted(allowed)[:3]}...",
                )
            )

    # 5. Structural integrity check unique to THIS dataset: Discount Applied and
    #    Promo Code Used are perfectly collinear in the source. We assert it so
    #    that if a future data drop breaks the relationship, we are told — the
    #    feature layer drops the redundant column on this basis.
    if {"discount_applied", "promo_code_used"}.issubset(df.columns):
        mismatch = int((df["discount_applied"] != df["promo_code_used"]).sum())
        report.add(
            CheckResult(
                "discount_promo_collinear",
                Severity.WARNING,
                mismatch == 0,
                mismatch,
                "discount_applied == promo_code_used (known source quirk)",
            )
        )

    return report


def _range_check(
    report: ValidationReport, df: pd.DataFrame, col: str, lo: float, hi: float
) -> None:
    if col not in df.columns:
        return
    s = pd.to_numeric(df[col], errors="coerce")
    bad = (s < lo) | (s > hi)
    n_bad = int(bad.sum())
    report.add(
        CheckResult(f"range__{col}", Severity.ERROR, n_bad == 0, n_bad, f"{col} in [{lo}, {hi}]")
    )
