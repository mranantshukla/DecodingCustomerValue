"""Generate docs/FEATURE_GLOSSARY.md from the feature registry.

Run: python scripts/generate_glossary.py
Keeping the glossary generated (not hand-written) means it can never drift from
the code — the registry is the single source of truth.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.feature_engineering.registry import FEATURE_REGISTRY  # noqa: E402


def main() -> None:
    groups: dict[str, list] = {}
    for spec in FEATURE_REGISTRY:
        groups.setdefault(spec.group, []).append(spec)

    lines = [
        "# Feature Glossary",
        "",
        "> **Auto-generated** from `src/feature_engineering/registry.py` "
        "(`python scripts/generate_glossary.py`). Do not edit by hand.",
        "",
        f"The pipeline engineers **{len(FEATURE_REGISTRY)} features** across "
        f"{len(groups)} families. Every feature lists its formula, what it measures, "
        "why leadership should care, and an honest **proxy-quality** tag.",
        "",
        "## Proxy-quality legend",
        "",
        "| Tag | Meaning |",
        "|---|---|",
        "| `derived` | Deterministic transform of observed columns. Fully reliable. |",
        "| `composite` | Transparent weighted blend of observed/derived signals (weights auditable). |",
        "| `empirical` | Computed from group-level statistics observed in the data. |",
        "| `proxy` | Stand-in for an unobservable construct, built from related signals. Directional. |",
        "| `estimate` | Clearly-labelled best guess for something the data cannot directly measure. |",
        "",
    ]
    for group in ["Loyalty", "Promotion", "Value", "Behavioural", "Geography"]:
        specs = groups.get(group, [])
        if not specs:
            continue
        lines += [f"## {group}", ""]
        for s in specs:
            lines += [
                f"### `{s.name}`  _({s.dtype})_  · quality: `{s.proxy_quality}`",
                "",
                f"- **Formula:** `{s.formula}`",
                f"- **Why it matters:** {s.rationale}",
                "",
            ]
    out = ROOT / "docs" / "FEATURE_GLOSSARY.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out} ({len(FEATURE_REGISTRY)} features)")


if __name__ == "__main__":
    main()
