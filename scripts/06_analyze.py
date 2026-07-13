#!/usr/bin/env python3
"""
Two modes:

  merge    Combine Places + OSM lists, dedupe (<=40m apart = same church),
           clip to the Guntur boundary -> churches_merged.json
           (run BEFORE 05_ee_building_dates.py)

  report   After dating: construction-year histogram, denominational split
           (name heuristics), and map-ready churches.geojson
           -> data/churches.geojson, data/pilot_report.txt

Usage: python3 06_analyze.py merge | report
"""
import json, math, os, sys, re
from collections import Counter

REGION = os.environ.get("REGION", "guntur")
BASE = os.path.join(os.path.dirname(__file__), "..", "data", REGION)

def dist_m(a, b):
    dlat = (a["lat"] - b["lat"]) * 111000
    dlon = (a["lon"] - b["lon"]) * 111000 * math.cos(math.radians(a["lat"]))
    return math.hypot(dlat, dlon)

DENOM_PATTERNS = [
    ("catholic", r"catholic|rc church|st\.? ?(mary|joseph|anthony|paul|peter|francis)"),
    ("cbcnc/baptist", r"baptist|cbcnc"),
    ("lutheran", r"lutheran|aelc"),
    ("csi/anglican", r"\bcsi\b|church of south india|anglican"),
    ("pentecostal/independent", r"pentecost|assembl|zion|bethel|hosanna|calvary|gospel|prayer house|ministr|philadelphia|maranatha|hebron|shalom|emmanuel|jehovah|charism"),
]

def classify(name):
    n = (name or "").lower()
    for label, pat in DENOM_PATTERNS:
        if re.search(pat, n):
            return label
    return "other/unclassified"

def merge():
    from shapely.geometry import shape, Point
    boundary = shape(json.load(open(os.path.join(BASE, "boundary.geojson")))["features"][0]["geometry"])
    def load(name):
        try:
            return json.load(open(os.path.join(BASE, name)))
        except FileNotFoundError:
            return []
    places = load("places_churches.json")
    osm = load("osm_churches.json")
    openp = load("open_places_churches.json")
    if not places and not osm and not openp:
        raise SystemExit("no input lists found")
    for p in places: p["source"] = "gmaps"
    for o in osm: o["source"] = "osm"

    inside = [c for c in places + openp + osm if boundary.contains(Point(c["lon"], c["lat"]))]
    merged = []
    for c in inside:  # greedy dedupe
        if any(dist_m(c, m) <= 40 for m in merged):
            continue
        merged.append(c)
    out = os.path.join(BASE, "churches_merged.json")
    json.dump(merged, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"{len(places)} gmaps + {len(openp)} overture + {len(osm)} osm -> {len(inside)} in-boundary -> {len(merged)} after dedupe -> {out}")

ERAS = ["pre-1985", "1985-1995", "1996-2005", "2006-2015"]

def era_of(c):
    b = c.get("built")
    if b not in ("pre-2016", None):
        return b  # 2017..2023 or undetected
    w = c.get("wsf_year")
    if not w:
        return "pre-2016"
    if w <= 1985: return "pre-1985"
    if w <= 1995: return "1985-1995"
    if w <= 2005: return "1996-2005"
    return "2006-2015"

def report():
    churches = json.load(open(os.path.join(BASE, "churches_dated.json")))
    for c in churches:
        c["denom"] = classify(c.get("name"))
        c["when"] = era_of(c)

    hist = Counter(c["when"] for c in churches)
    lines = [f"{REGION.upper()} - CHURCH SITE APPEARANCE ERAS",
             "(1985-2015: WSF Evolution settlement onset, 30m floor;",
             " 2017-2023: Open Buildings Temporal, building-level)", ""]
    for k in ERAS + ["pre-2016"] + [str(y) for y in range(2017, 2024)] + ["undetected"]:
        lines.append(f"  {k:>10}: {hist.get(k, 0):5d}  {'#' * max(1, hist.get(k, 0) // 40) if hist.get(k,0) else ''}")
    lines += ["", "By denomination (name heuristic) x new-build 2017-2023:"]
    for denom in set(c["denom"] for c in churches):
        sub = [c for c in churches if c["denom"] == denom]
        new = sum(1 for c in sub if c["built"] not in ("pre-2016", "undetected"))
        lines.append(f"  {denom:28s} total={len(sub):5d} built2017-23={new:4d} ({new/len(sub)*100:.0f}%)")
    txt = "\n".join(lines)
    open(os.path.join(BASE, "pilot_report.txt"), "w").write(txt)
    print(txt)

    gj = {"type": "FeatureCollection", "features": [{
        "type": "Feature",
        "properties": {"name": c.get("name"), "built": c["when"], "denom": c["denom"],
                       "source": c.get("source"), "n_ratings": c.get("n_ratings")},
        "geometry": {"type": "Point", "coordinates": [c["lon"], c["lat"]]},
    } for c in churches]}
    json.dump(gj, open(os.path.join(BASE, "churches.geojson"), "w"), ensure_ascii=False)
    print(f"\n-> churches.geojson ({len(churches)} points, ready for MapLibre)")

if __name__ == "__main__":
    {"merge": merge, "report": report}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit("usage: merge|report"))()
