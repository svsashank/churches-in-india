#!/usr/bin/env python3
"""
Sweep Google Places API (New) for churches across the Guntur search grid.

- Nearby Search caps at 20 results per call with no pagination, so any cell
  that returns 20 is subdivided into 4 and re-queried (quadtree) until
  results < 20 or cell < MIN_CELL_KM.
- Checkpoints progress to data/places_checkpoint.json so it can resume.
- Dedupes on place id.

Usage:
  export GOOGLE_MAPS_API_KEY=...
  python3 03_places_sweep.py [--dry-run]

Cost note: Nearby Search is a "Pro" SKU (~$35/1000 beyond the free monthly
allowance of ~5,000 Pro calls). Expected pilot volume: ~2,000-4,000 calls,
i.e. likely free, worst case a few tens of dollars. --dry-run counts seed
cells without calling the API.
"""
import json, math, os, sys, time
import urllib.request

BASE = os.path.join(os.path.dirname(__file__), "..", "data")
GRID = os.path.join(BASE, "search_grid.geojson")
CKPT = os.path.join(BASE, "places_checkpoint.json")
OUT = os.path.join(BASE, "places_churches.json")
MIN_CELL_KM = 0.4
API = "https://places.googleapis.com/v1/places:searchNearby"
FIELDS = "places.id,places.displayName,places.location,places.types,places.rating,places.userRatingCount,places.formattedAddress"

def call_api(lat, lon, radius_m, key):
    body = json.dumps({
        "includedTypes": ["church"],
        "maxResultCount": 20,
        "locationRestriction": {"circle": {"center": {"latitude": lat, "longitude": lon}, "radius": min(radius_m, 50000)}},
    }).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": FIELDS,
    })
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r).get("places", [])
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            raise
    raise RuntimeError("rate-limited after retries")

def main():
    dry = "--dry-run" in sys.argv
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key and not dry:
        sys.exit("Set GOOGLE_MAPS_API_KEY")

    grid = json.load(open(GRID))["features"]
    # work queue: (center_lon, center_lat, half_size_km)
    queue = [(f["properties"]["center"][0], f["properties"]["center"][1], 1.5) for f in grid]
    if dry:
        print(f"{len(queue)} seed cells; expect ~1.2-2.5x that in total calls after subdivision")
        return

    done, places = set(), {}
    if os.path.exists(CKPT):
        ck = json.load(open(CKPT))
        done, places = set(ck["done"]), ck["places"]
        print(f"resuming: {len(done)} cells done, {len(places)} churches so far")

    calls = 0
    while queue:
        lon, lat, half_km = queue.pop()
        cell_id = f"{lon:.5f},{lat:.5f},{half_km:.2f}"
        if cell_id in done:
            continue
        radius = half_km * 1000 * 1.42  # cover cell corners
        res = call_api(lat, lon, radius, key)
        calls += 1
        for p in res:
            places[p["id"]] = {
                "id": p["id"],
                "name": p.get("displayName", {}).get("text", ""),
                "lat": p["location"]["latitude"],
                "lon": p["location"]["longitude"],
                "types": p.get("types", []),
                "rating": p.get("rating"),
                "n_ratings": p.get("userRatingCount"),
                "address": p.get("formattedAddress", ""),
            }
        if len(res) >= 20 and half_km > MIN_CELL_KM:  # cap hit -> subdivide
            q = half_km / 2
            dlat = q / 111.0
            dlon = q / (111.0 * math.cos(math.radians(lat)))
            for sx in (-1, 1):
                for sy in (-1, 1):
                    queue.append((lon + sx * dlon, lat + sy * dlat, q))
        done.add(cell_id)
        if calls % 50 == 0:
            json.dump({"done": list(done), "places": places}, open(CKPT, "w"))
            print(f"calls={calls} queue={len(queue)} churches={len(places)}")
        time.sleep(0.05)

    json.dump({"done": list(done), "places": places}, open(CKPT, "w"))
    json.dump(list(places.values()), open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"DONE: {calls} calls, {len(places)} unique churches -> {OUT}")

if __name__ == "__main__":
    main()
