#!/usr/bin/env python3
"""
Extend dating back to 1985 using World Settlement Footprint Evolution
(DLR, Landsat, 30m): per-pixel year of first settlement, 1985-2015.

For every church, take the EARLIEST settled year within a 40m buffer.
Interpretation: a floor — the church cannot predate the settlement of its
ground. Buildings inside long-settled cores read as the core's age.

Adds "wsf_year" to churches_dated.json (None where WSF has no data).
Run after 05. Usage: REGION=guntur python3 08_wsf_settlement.py --project X [--sa-key k.json]
"""
import argparse, json, os
import ee

REGION = os.environ.get("REGION", "guntur")
BASE = os.path.join(os.path.dirname(__file__), "..", "data", REGION)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--sa-key", default=None)
    args = ap.parse_args()
    if args.sa_key:
        sa = json.load(open(args.sa_key))
        ee.Initialize(ee.ServiceAccountCredentials(sa["client_email"], args.sa_key), project=args.project)
    else:
        ee.Initialize(project=args.project)

    # WSF Evolution (community catalog): pixel value = first settled year, 0 = never
    wsf = ee.ImageCollection("projects/sat-io/open-datasets/WSF/WSF_EVO").mosaic().selfMask()

    churches = json.load(open(os.path.join(BASE, "churches_dated.json")))
    print(f"{len(churches)} churches")
    CHUNK = 1000
    for i in range(0, len(churches), CHUNK):
        chunk = churches[i:i + CHUNK]
        fc = ee.FeatureCollection([
            ee.Feature(ee.Geometry.Point([c["lon"], c["lat"]]).buffer(40), {"idx": i + j})
            for j, c in enumerate(chunk)
        ])
        sampled = wsf.reduceRegions(collection=fc, reducer=ee.Reducer.min(), scale=30).getInfo()
        for f in sampled["features"]:
            p = f["properties"]
            v = p.get("min")
            churches[p["idx"]]["wsf_year"] = int(v) if v else None
        print(f"  {min(i + CHUNK, len(churches))}/{len(churches)}")

    json.dump(churches, open(os.path.join(BASE, "churches_dated.json"), "w"), ensure_ascii=False, indent=1)
    from collections import Counter
    got = [c["wsf_year"] for c in churches if c.get("wsf_year")]
    print(f"WSF year found for {len(got)}/{len(churches)}; range {min(got)}-{max(got)}" if got else "no WSF data")

if __name__ == "__main__":
    main()
