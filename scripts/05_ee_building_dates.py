#!/usr/bin/env python3
"""
Date the appearance of the building at each church location using
Google Open Buildings 2.5D Temporal (2016-2023, Sentinel-2 derived,
~4m effective resolution).

Method:
  For each church point, take mean building_presence within a 15m buffer
  for each year 2016..2023 (annual mosaics). The appearance year is the
  first year presence >= THRESH. If 2016 already >= THRESH -> "pre-2016"
  (building predates the observable window). If never >= THRESH ->
  "undetected" (open-air, tiny structure, or geocode offset).

Prereqs:
  pip install earthengine-api
  earthengine authenticate     (free for non-commercial use)
  python3 05_ee_building_dates.py --project YOUR_EE_PROJECT

Runs in chunks of 1000 points via getInfo; ~5k points takes minutes.
"""
import argparse, json, os
import ee

BASE = os.path.join(os.path.dirname(__file__), "..", "data")
THRESH = 0.5
YEARS = list(range(2016, 2024))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--infile", default=os.path.join(BASE, "churches_merged.json"))
    args = ap.parse_args()

    ee.Initialize(project=args.project)
    col = ee.ImageCollection("GOOGLE/Research/open-buildings-temporal/v1")

    churches = json.load(open(args.infile))
    print(f"{len(churches)} points to date")

    # One multi-band image: presence_2016 .. presence_2023
    bands = []
    for y in YEARS:
        img = col.filter(ee.Filter.calendarRange(y, y, "year")).mosaic() \
                 .select("building_presence").rename(f"p{y}")
        bands.append(img)
    stack = ee.Image.cat(bands)

    results = []
    CHUNK = 1000
    for i in range(0, len(churches), CHUNK):
        chunk = churches[i:i + CHUNK]
        fc = ee.FeatureCollection([
            ee.Feature(ee.Geometry.Point([c["lon"], c["lat"]]).buffer(15), {"idx": i + j})
            for j, c in enumerate(chunk)
        ])
        sampled = stack.reduceRegions(collection=fc, reducer=ee.Reducer.mean(), scale=4).getInfo()
        for f in sampled["features"]:
            props = f["properties"]
            c = churches[props["idx"]]
            series = {y: props.get(f"p{y}") for y in YEARS}
            c["presence"] = {str(y): (round(v, 3) if v is not None else None) for y, v in series.items()}
            appear = None
            for y in YEARS:
                v = series[y]
                if v is not None and v >= THRESH:
                    appear = y
                    break
            if appear is None:
                c["built"] = "undetected"
            elif appear == 2016:
                c["built"] = "pre-2016"
            else:
                c["built"] = str(appear)
            results.append(c)
        print(f"  {min(i + CHUNK, len(churches))}/{len(churches)}")

    out = os.path.join(BASE, "churches_dated.json")
    json.dump(results, open(out, "w"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(Counter(c["built"] for c in results))
    print(f"-> {out}")

if __name__ == "__main__":
    main()
