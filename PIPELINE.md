# Guntur Church-Growth Pilot

Goal: produce a defensible "church buildings by year of appearance" dataset for
undivided Guntur district (Guntur + Palnadu + Bapatla), 2016-2023, using
satellite building detection at scraped church locations — calibrated against
the Catholic parish registry.

## Run order

| Step | Script | Needs | Output |
|---|---|---|---|
| 1 | (done) `01_boundary_grid.py` | — | `guntur_boundary.geojson`, `search_grid.geojson` (shipped) |
| 2 | `03_places_sweep.py` | `GOOGLE_MAPS_API_KEY` | `places_churches.json` |
| 3 | `04_osm_churches.py` | internet | `osm_churches.json` |
| 4 | `06_analyze.py merge` | — | `churches_merged.json` |
| 5 | `05_ee_building_dates.py --project <EE_PROJECT>` | Earth Engine auth (free, non-commercial) | `churches_dated.json` |
| 6 | `06_analyze.py report` | — | `pilot_report.txt`, `churches.geojson` |
| 7 | `07_catholic_calibration.py` | internet | `guntur_catholic_stats.json` |

## Costs
- Places Nearby Search (Pro SKU): 1,652 seed cells + adaptive subdivision,
  expect ~2-4k calls. Likely inside the free monthly Pro allowance; worst
  case a few tens of USD. Use `--dry-run` first. Script checkpoints/resumes.
- Earth Engine: free tier is sufficient.

## Method notes / honest caveats (put these on the map too)
- **Dates the building, not the congregation.** A church in a pre-existing
  or rented building shows as "pre-2016". House churches don't appear at all.
  This measures a *floor* on construction, not a ceiling on congregations.
- **Geocode offset**: Google pins are sometimes 10-50m off; the 15m buffer +
  0.5 threshold in `05_` are tunable (sensitivity-test both).
- **Rebuild ambiguity**: a building appearing in 2019 may replace an older
  structure demolished on the same plot.
- **Listing bias**: Google Maps coverage of churches itself grew over the
  decade; that's why dating comes from satellite, not listing age. First-review
  dates (phase 2, needs a third-party scraper — official API returns only 5
  reviews) give an independent "existed-by" bound.
- **Validation**: Diocese of Guntur = undivided Guntur district. If satellite-
  detected new Catholic buildings ≈ Annuario parish growth 2017-2023, the
  method holds for the unregistered denominations.

## Scaling
Everything is parameterized by boundary + grid. `01_boundary_grid.py` takes any
state geojson + district list. AP statewide ≈ 12x Guntur's call volume.
