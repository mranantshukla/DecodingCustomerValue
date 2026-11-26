"""build_dashboard_v2_model_only.py — Build a *model-only* PBIP (no PBIR report
tier) so Power BI Desktop loads the semantic model 100% reliably regardless of
whether the user has the PBIR preview features enabled. The user then drops the
visuals manually using the 5-minute click-build path in DASHBOARD_GUIDE.md.

Re-uses the table specifications, measures, and TMDL emitter from build_dashboard_v2.

Output: e:/Cagiitg/powerbi/dashboard_v2_model_only/
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

ROOT = Path("e:/Cagiitg")

# Load the v2 builder module so we reuse its table specs & TMDL emitters
spec = importlib.util.spec_from_file_location("bv2", ROOT / "scripts" / "build_dashboard_v2.py")
assert spec and spec.loader
bv2 = importlib.util.module_from_spec(spec)
sys.modules["bv2"] = bv2

# Redirect output to a sibling folder BEFORE running the module
ALT_OUT = ROOT / "powerbi" / "dashboard_v2_model_only"
ALT_PROJECT = "DecodingCustomerValue_V2_ModelOnly"

# Monkey-patch module-level constants before loading
bv2.OUT = ALT_OUT
bv2.PROJECT = ALT_PROJECT
bv2.REPORT_DIR = ALT_OUT / f"{ALT_PROJECT}.Report"
bv2.MODEL_DIR = ALT_OUT / f"{ALT_PROJECT}.SemanticModel"
bv2.DEFS = bv2.REPORT_DIR / "definition"
bv2.PAGES_DIR = bv2.DEFS / "pages"
bv2.BOOKMARKS_DIR = bv2.DEFS / "bookmarks"
bv2.THEME_DIR = bv2.REPORT_DIR / "StaticResources" / "RegisteredResources"

spec.loader.exec_module(bv2)


def main() -> None:
    # Re-apply the constants because the module body reset them on exec_module
    bv2.OUT = ALT_OUT
    bv2.PROJECT = ALT_PROJECT
    bv2.REPORT_DIR = ALT_OUT / f"{ALT_PROJECT}.Report"
    bv2.MODEL_DIR = ALT_OUT / f"{ALT_PROJECT}.SemanticModel"
    bv2.DEFS = bv2.REPORT_DIR / "definition"
    bv2.PAGES_DIR = bv2.DEFS / "pages"

    print(f"Building model-only PBIP at {ALT_OUT}")
    if ALT_OUT.exists():
        shutil.rmtree(ALT_OUT)
    ALT_OUT.mkdir(parents=True)

    # Semantic model (uses the patched paths)
    bv2.write_semantic_model()

    # Minimal Report tier — single empty page so PBI Desktop has somewhere to
    # land the user. The user click-builds visuals from the Data pane.
    bv2.writej(
        bv2.REPORT_DIR / ".platform",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "Report", "displayName": ALT_PROJECT},
            "config": {"version": "2.0", "logicalId": bv2.guid()},
        },
    )
    bv2.writej(
        bv2.REPORT_DIR / "definition.pbir",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
            "version": "4.0",
            "datasetReference": {
                "byPath": {"path": f"../{ALT_PROJECT}.SemanticModel"},
                "byConnection": None,
            },
        },
    )
    bv2.writej(
        bv2.DEFS / "version.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
            "version": "4.0",
        },
    )
    bv2.writej(
        bv2.DEFS / "report.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.0.0/schema.json",
            "themeCollection": {"baseTheme": {"name": "CY24SU10"}},
            "resourcePackages": [],
            "settings": {
                "useStylableVisualContainerHeader": True,
                "useNewFilterPaneExperience": True,
            },
        },
    )
    bv2.writej(
        bv2.PAGES_DIR / "pages.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
            "pageOrder": ["Blank"],
            "activePageName": "Blank",
        },
    )
    bv2.writej(
        bv2.PAGES_DIR / "Blank" / "page.json",
        {
            "$schema": bv2.PAGE_SCHEMA,
            "name": "Blank",
            "displayName": "Founder Dashboard (click-build here)",
            "displayOption": "FitToPage",
            "width": 1280,
            "height": 720,
        },
    )

    # PBIP root
    bv2.writej(
        ALT_OUT / f"{ALT_PROJECT}.pbip",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{ALT_PROJECT}.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )
    bv2.write(ALT_OUT / ".gitignore", "**/.pbi/localSettings.json\r\n**/.pbi/cache.abf\r\n")

    print("\nDone. 19 tables, 19 measures, 1 blank page (you click-build the visuals).")
    print(f"\nOpen in Power BI Desktop:\n  {ALT_OUT / (ALT_PROJECT + '.pbip')}")


if __name__ == "__main__":
    main()
