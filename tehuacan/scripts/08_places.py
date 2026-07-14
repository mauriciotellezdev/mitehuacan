#!/usr/bin/env python3
"""Derive towns/localities served by each route from OSM place nodes + route geometry."""
import json
import math
import unicodedata
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent / "data"
UA = {"User-Agent": "combi-tracker research (contact: augmentedmike@gmail.com)"}

# proximity thresholds by place type (meters): big places have big footprints
RADIUS = {"city": 2000, "town": 1500, "village": 1000, "suburb": 800,
          "neighbourhood": 500, "hamlet": 600, "locality": 500, "quarter": 600}


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def main():
    routes = json.loads((BASE.parent / "map" / "routes.js").read_text().split("const ROUTES = ", 1)[1].rstrip().rstrip(";"))
    feats = routes["features"]

    # bbox of all geometry + ~4 km pad
    lons, lats = [], []
    for f in feats:
        for part in f["geometry"]["coordinates"]:
            for c in part:
                lons.append(c[0]); lats.append(c[1])
    pad = 0.04
    s, w, n, e = min(lats) - pad, min(lons) - pad, max(lats) + pad, max(lons) + pad
    print(f"geometry bbox + pad: {s:.3f},{w:.3f},{n:.3f},{e:.3f}")

    q = f"""[out:json][timeout:90];
node["place"~"^(city|town|village|suburb|neighbourhood|hamlet|locality|quarter)$"]({s},{w},{n},{e});
out body;"""
    els = None
    for ep in ("https://overpass-api.de/api/interpreter",
               "https://overpass.kumi.systems/api/interpreter",
               "https://overpass-api.de/api/interpreter"):
        try:
            r = requests.post(ep, data={"data": q}, headers=UA, timeout=150)
            r.raise_for_status()
            els = r.json()["elements"]
            break
        except Exception as exc:  # noqa: BLE001
            print(f"{ep}: {exc}; retrying on next endpoint")
    if els is None:
        raise SystemExit("all Overpass endpoints failed")
    places = [{"name": el["tags"].get("name"), "type": el["tags"]["place"],
               "lon": el["lon"], "lat": el["lat"]}
              for el in els if el.get("tags", {}).get("name")]
    (BASE / "raw" / "osm" / "places.json").write_text(json.dumps(places, ensure_ascii=False, indent=1))
    print(f"{len(places)} named places in region")

    lat0 = (s + n) / 2
    MLON = 111320 * math.cos(math.radians(lat0)); MLAT = 110570

    # grid-index route vertices for speed
    CELL = 500  # m
    for f in feats:
        pts = [(c[0] * MLON, c[1] * MLAT) for part in f["geometry"]["coordinates"] for c in part]
        grid = {}
        for i, p in enumerate(pts):
            grid.setdefault((int(p[0] // CELL), int(p[1] // CELL)), []).append(i)
        f["_pts"], f["_grid"] = pts, grid

    def route_near(f, px, py, rad):
        cx, cy = int(px // CELL), int(py // CELL)
        span = int(rad // CELL) + 1
        best = None
        for gx in range(cx - span, cx + span + 1):
            for gy in range(cy - span, cy + span + 1):
                for i in f["_grid"].get((gx, gy), ()):
                    x, y = f["_pts"][i]
                    d = math.hypot(x - px, y - py)
                    if d <= rad and (best is None or d < best[0]):
                        best = (d, i)
        return best

    result = {}
    for f in feats:
        served = []
        for pl in places:
            rad = RADIUS[pl["type"]]
            hit = route_near(f, pl["lon"] * MLON, pl["lat"] * MLAT, rad)
            if hit:
                served.append((hit[1], pl["name"], pl["type"], round(hit[0])))
        served.sort()  # order along the route by vertex index
        # dedupe repeated names keeping first occurrence
        seen, ordered = set(), []
        for _, name, typ, dist in served:
            if name not in seen:
                seen.add(name)
                ordered.append({"name": name, "type": typ, "dist_m": dist})
        result[f["properties"]["id"]] = ordered
        del f["_pts"], f["_grid"]

    (BASE / "route_places.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
    n_with = sum(1 for v in result.values() if v)
    print(f"places computed for {n_with}/{len(result)} routes")
    for rid in ("ajalpan", "chilac", "altepexi", "miahuatlan"):
        if rid in result:
            print(f"  {rid}: " + ", ".join(p["name"] for p in result[rid][:10]))


if __name__ == "__main__":
    main()
