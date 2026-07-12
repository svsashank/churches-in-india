#!/usr/bin/env python3
"""
Calibration backbone: Diocese of Guntur statistics (Annuario Pontificio data
as republished by catholic-hierarchy.org). The diocese territory matches
undivided Guntur district.

Pulls the year-by-year stats table (Catholics, parishes, priests) from
https://www.catholic-hierarchy.org/diocese/dgunt.html

Validation logic once the pipeline runs:
  - Filter churches_dated.json to denom == "catholic"
  - Compare satellite-detected new Catholic buildings 2017-2023 against
    the parish-count delta in this table over the same window.
  - If they're in the same ballpark, the method is defensible for the
    denominations that have NO registry.

Usage: pip install requests beautifulsoup4 && python3 07_catholic_calibration.py
"""
import json, os, re
import requests
from bs4 import BeautifulSoup

BASE = os.path.join(os.path.dirname(__file__), "..", "data")
URL = "https://www.catholic-hierarchy.org/diocese/dgunt.html"

html = requests.get(URL, headers={"User-Agent": "Mozilla/5.0 (research pilot)"}, timeout=30).text
soup = BeautifulSoup(html, "html.parser")

rows = []
for table in soup.find_all("table"):
    header = [th.get_text(strip=True).lower() for th in table.find_all("th")]
    if any("parish" in h for h in header):
        keys = header
        for tr in table.find_all("tr"):
            tds = [td.get_text(strip=True) for td in tr.find_all("td")]
            if tds and re.match(r"^\d{4}$", tds[0]):
                rows.append(dict(zip(keys, tds)))
if not rows:
    raise SystemExit("Stats table not found - page layout may have changed; inspect the URL manually.")

out = os.path.join(BASE, "guntur_catholic_stats.json")
json.dump(rows, open(out, "w"), indent=1)
print(f"{len(rows)} annual rows -> {out}")
for r in rows[-8:]:
    print(r)
