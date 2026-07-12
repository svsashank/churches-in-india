#!/usr/bin/env python3
"""
Build district boundary + seed search grid. Already run for Guntur
(outputs shipped in data/). For scaling, point it at any state geojson
from github.com/udit-001/india-maps-data and list the (post-2022)
districts that compose the undivided unit.

Usage: python3 01_boundary_grid.py data/andhra-pradesh.geojson "Guntur,Palnadu,Bapatla" guntur
"""
import json, math, sys
from shapely.geometry import shape, mapping, box
from shapely.ops import unary_union

src, districts, tag = sys.argv[1], sys.argv[2].split(","), sys.argv[3]
d = json.load(open(src))
parts = [shape(f["geometry"]) for f in d["features"] if f["properties"]["district"] in districts]
geom = unary_union(parts).buffer(0)
json.dump({"type":"FeatureCollection","features":[{"type":"Feature","properties":{"name":tag},"geometry":mapping(geom)}]},
          open(f"data/{tag}_boundary.geojson","w"))
minx,miny,maxx,maxy = geom.bounds
cell_km=3.0; dlat=cell_km/111.0; dlon=cell_km/(111.0*math.cos(math.radians((miny+maxy)/2)))
cells=[]; lat=miny
while lat<maxy:
    lon=minx
    while lon<maxx:
        c=box(lon,lat,lon+dlon,lat+dlat)
        if c.intersects(geom):
            cells.append({"type":"Feature","properties":{"id":len(cells),"center":[round(lon+dlon/2,5),round(lat+dlat/2,5)]},"geometry":mapping(c)})
        lon+=dlon
    lat+=dlat
json.dump({"type":"FeatureCollection","features":cells}, open("data/search_grid.geojson","w"))
print(f"{tag}: bounds {geom.bounds}, {len(cells)} seed cells")
