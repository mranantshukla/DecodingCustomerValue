import json
import os
import sys

root = r'e:/Cagiitg/powerbi/dashboard_v2'
exts = ('.json', '.pbip', '.pbism', '.pbir', '.platform', '.bookmark.json')

measures = {
    "Total Customers","Total Projected CLV","Avg CLV per Customer","Avg Loyalty Score",
    "Avg Promo Dependency","Pct Premium Customers","Pct Satisfied","Pct Discounted",
    "Pct Subscribed","CLV Top 20 Pct","Pct CLV from Top 20 Pct","Discounted CLV",
    "Full Price CLV","Pct CLV Discount Attached","Estimated Margin Recovery",
    "Margin At Risk CLV","Avg Region Quality","Avg Organic Demand","Margin Adjusted CLV"
}

files = []
for dirpath, dirnames, filenames in os.walk(root):
    for fn in filenames:
        full = os.path.join(dirpath, fn)
        low = fn.lower()
        if low.endswith(exts):
            files.append(full)

ok = 0
errs = []
binding_issues = []

def walk(node, path, visual_path):
    """Walk JSON, look for queryRef in projections and Measure/Column entity references."""
    pass

def collect_query_refs(node, refs):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == 'queryRef' and isinstance(v, str):
                refs.append(v)
            else:
                collect_query_refs(v, refs)
    elif isinstance(node, list):
        for item in node:
            collect_query_refs(item, refs)

def find_measure_column_wrappers(node, results):
    """Find entries like {"Measure": {"Property": "...", ...}} or {"Column": {...}} and capture the property name + wrapper kind."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ('Measure', 'Column') and isinstance(v, dict):
                prop = v.get('Property')
                if prop:
                    results.append((k, prop))
            find_measure_column_wrappers(v, results)
    elif isinstance(node, list):
        for item in node:
            find_measure_column_wrappers(item, results)

def has_query_block(node):
    if isinstance(node, dict):
        if 'query' in node:
            return True
        for v in node.values():
            if has_query_block(v):
                return True
    elif isinstance(node, list):
        for item in node:
            if has_query_block(item):
                return True
    return False

def get_visual_type(data):
    """Try to find the visual type from a visual.json."""
    if not isinstance(data, dict):
        return None
    # Common paths: data["visual"]["visualType"] or data["visualType"]
    v = data.get('visual')
    if isinstance(v, dict):
        vt = v.get('visualType')
        if vt:
            return vt
    return data.get('visualType')

for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            text = fh.read()
        data = json.loads(text)
        ok += 1
    except Exception as e:
        errs.append({"file": f.replace('\\', '/'), "error": f"{type(e).__name__}: {e}"})
        continue

    # Only check visual.json files for binding rules
    base = os.path.basename(f).lower()
    if base == 'visual.json':
        # 1) queryRef uniqueness
        refs = []
        collect_query_refs(data, refs)
        seen = {}
        dups = []
        for r in refs:
            seen[r] = seen.get(r, 0) + 1
        for r, c in seen.items():
            if c > 1:
                dups.append(f"{r} (x{c})")
        if dups:
            binding_issues.append(f"DUPLICATE queryRef in {f}: {', '.join(dups)}")

        # 2) measures should use Measure wrapper, not Column
        wrappers = []
        find_measure_column_wrappers(data, wrappers)
        for kind, prop in wrappers:
            if prop in measures and kind == 'Column':
                binding_issues.append(f"Measure '{prop}' wrapped as Column in {f}")

        # 3) textbox must not have a query block
        vtype = get_visual_type(data)
        if vtype and vtype.lower() == 'textbox':
            if has_query_block(data):
                binding_issues.append(f"textbox visual has a query block in {f}")

print("TOTAL_FILES:", len(files))
print("PARSED_OK:", ok)
print("PARSE_ERRORS:", len(errs))
for e in errs:
    print("  ERR:", e["file"], "->", e["error"])
print("BINDING_ISSUES:", len(binding_issues))
for b in binding_issues:
    print("  BIND:", b)
