#!/usr/bin/env python3
"""
Pull Christian places of worship in the Guntur bbox from OpenStreetMap
(free supplement + cross-check to the Places sweep).

Usage: python3 04_osm_churches.py
"""
import json, os, urllib.request, urllib.parse

BASE = os.path.join(os.path.dirname(__file__), "..", "data")
BBOX = "15.613,79.208,16.822,80.910"  # S,W,N,E (undivided Guntur bounds)

query = f"""
[out:json][timeout:120];
(
  node["amenity"="place_of_worship"]["religion"="christian"]({BBOX});
  way["amenity"="place_of_worship"]["religion"="christian"]({BBOX});
  node["building"="church"]({BBOX});
  way["building"="church"]({BBOX});
);
out center tags;
"""
req = urllib.request.Request(
    "https://overpass-api.de/api/interpreter",
    data=urllib.parse.urlencode({"data": query}).encode(),
    headers={"User-Agent": "guntur-church-pilot/0.1"},
)
with urllib.request.urlopen(req, timeout=180) as r:
    data = json.load(r)

out = []
for el in data.get("elements", []):
    lat = el.get("lat") or el.get("center", {}).get("lat")
    lon = el.get("lon") or el.get("center", {}).get("lon")
    if lat is None:
        continue
    t = el.get("tags", {})
    out.append({
        "osm_id": f"{el['type']}/{el['id']}",
        "name": t.get("name", ""),
        "denomination": t.get("denomination", ""),
        "lat": lat, "lon": lon,
        "start_date": t.get("start_date", ""),  # rare but gold when present
    })
path = os.path.join(BASE, "osm_churches.json")
json.dump(out, open(path, "w"), ensure_ascii=False, indent=1)
print(f"{len(out)} OSM churches -> {path}")
