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
    if not places and not osm:
        raise SystemExit("no input lists found")
    for p in places: p["source"] = "gmaps"
    for o in osm: o["source"] = "osm"

    inside = [c for c in places + osm if boundary.contains(Point(c["lon"], c["lat"]))]
    merged = []
    for c in inside:  # greedy dedupe
        if any(dist_m(c, m) <= 40 for m in merged):
            continue
        merged.append(c)
    out = os.path.join(BASE, "churches_merged.json")
    json.dump(merged, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"{len(places)} gmaps + {len(osm)} osm -> {len(inside)} in-boundary -> {len(merged)} after dedupe -> {out}")

def report():
    churches = json.load(open(os.path.join(BASE, "churches_dated.json")))
    for c in churches:
        c["denom"] = classify(c.get("name"))

    hist = Counter(c["built"] for c in churches)
    lines = ["GUNTUR PILOT - CHURCH BUILDING APPEARANCE YEARS",
             "(Open Buildings 2.5D Temporal, max presence in 40m buffer, threshold 0.4)", ""]
    for k in ["pre-2016"] + [str(y) for y in range(2017, 2024)] + ["undetected"]:
        lines.append(f"  {k:>10}: {hist.get(k, 0):5d}  {'#' * (hist.get(k, 0) // 5)}")
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
        "properties": {"name": c.get("name"), "built": c["built"], "denom": c["denom"],
                       "source": c.get("source"), "n_ratings": c.get("n_ratings")},
        "geometry": {"type": "Point", "coordinates": [c["lon"], c["lat"]]},
    } for c in churches]}
    json.dump(gj, open(os.path.join(BASE, "churches.geojson"), "w"), ensure_ascii=False)
    print(f"\n-> churches.geojson ({len(churches)} points, ready for MapLibre)")

if __name__ == "__main__":
    {"merge": merge, "report": report}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit("usage: merge|report"))()
