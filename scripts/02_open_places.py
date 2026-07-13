#!/usr/bin/env python3
"""
FREE source: church locations from Overture Maps places (Meta + Microsoft
POI data, bulk parquet, no API key, no cost).

Downloads all places in the region's bbox via the official overturemaps CLI,
then filters to churches by category and name keywords (English + Telugu).

Usage (CI): pip install overturemaps pyarrow pandas
            REGION=ap python3 02_open_places.py
Output: data/<region>/open_places_churches.json  (same shape as the Places
        sweep output, so merge/dating stages work unchanged)
"""
import json, os, re, subprocess, sys

REGION = os.environ.get("REGION", "ap")
BASE = os.path.join(os.path.dirname(__file__), "..", "data", REGION)

# bbox from boundary
g = json.load(open(os.path.join(BASE, "boundary.geojson")))["features"][0]["geometry"]
pts = [p for poly in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]])
       for ring in poly for p in ring]
xs, ys = [p[0] for p in pts], [p[1] for p in pts]
bbox = f"{min(xs):.4f},{min(ys):.4f},{max(xs):.4f},{max(ys):.4f}"
print("bbox:", bbox)

pq = "/tmp/overture_places.geoparquet"
subprocess.run([sys.executable, "-m", "overturemaps", "download",
                f"--bbox={bbox}", "-f", "geoparquet", "--type=place", "-o", pq],
               check=True)

import pyarrow.parquet as pa
t = pa.read_table(pq).to_pandas()
print("places in bbox:", len(t))

CHURCH_CATS = re.compile(r"church|cathedral|chapel", re.I)
GENERIC_CATS = re.compile(r"place_of_worship|religious", re.I)
NAME_PAT = re.compile(
    r"church|chapel|cathedral|ministr|gospel|pentecost|prayer\s*(house|hall)|"
    r"assembl(y|ies)\s*of\s*god|\bAG\b|zion|bethel|hosanna|calvary|maranatha|hebron|"
    r"shalom|jehovah|baptist|lutheran|catholic|\bCSI\b|salvation army|"
    r"చర్చి|క్రీస్తు|ప్రార్థనా?\s*మందిరం|దేవాలయము?\s*క్రీస్తు", re.I)
EXCLUDE = re.compile(r"temple|masjid|mosque|dargah|gurudwara|mandir", re.I)

def get_cat(row):
    c = row.get("categories")
    if isinstance(c, dict):
        return str(c.get("primary") or "")
    return str(c or "")

def get_name(row):
    n = row.get("names")
    if isinstance(n, dict):
        return str(n.get("primary") or "")
    return str(n or "")

out = []
for _, row in t.iterrows():
    cat, name = get_cat(row), get_name(row)
    is_church = bool(CHURCH_CATS.search(cat)) or \
                (bool(GENERIC_CATS.search(cat)) and NAME_PAT.search(name or "")) or \
                bool(NAME_PAT.search(name or ""))
    if not is_church or EXCLUDE.search(name or ""):
        continue
    geom = row["geometry"]
    try:
        from shapely import wkb
        p = wkb.loads(bytes(geom))
        lon, lat = p.x, p.y
    except Exception:
        continue
    out.append({"id": f"ovt/{row.get('id','')}", "name": name, "lat": lat, "lon": lon,
                "category": cat, "source": "overture"})

path = os.path.join(BASE, "open_places_churches.json")
json.dump(out, open(path, "w"), ensure_ascii=False, indent=1)
print(f"{len(out)} churches (Overture) -> {path}")
