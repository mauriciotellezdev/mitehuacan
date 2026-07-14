#!/usr/bin/env python3
"""Fetch live OXXO convenience-store locations in the Tehuacan region from OSM.

Queries the Overpass API for nodes/ways/relations tagged as OXXO within the
network boundary bbox (+ pan margin), dedupes, and writes:
  - tehuacan/data/raw/osm/oxxo_raw.json          (raw Overpass response)
  - tehuacan/data/sponsors/oxxo_locations.json    (processed list)
  - tehuacan/data/sponsors/oxxo_locations.geojson (FeatureCollection of Points)

Source: OpenStreetMap (ODbL). Rerunnable.
"""

import json
import math
import sys
import time
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]  # tehuacan/
RAW_PATH = ROOT / "data" / "raw" / "osm" / "oxxo_raw.json"
OUT_JSON = ROOT / "data" / "sponsors" / "oxxo_locations.json"
OUT_GEOJSON = ROOT / "data" / "sponsors" / "oxxo_locations.geojson"

# bbox (S, W, N, E): network boundary + pan margin
BBOX = (18.216, -97.651, 18.705, -97.139)

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
USER_AGENT = "quecombi sponsor data (opensource project)"
TIMEOUT = 120

# Boundary circle for the inside/outside summary
BOUNDARY_CENTER = (-97.395, 18.4605)  # lon, lat
BOUNDARY_RADIUS_KM = 19.3

QUERY = f"""
[out:json][timeout:{TIMEOUT}];
(
  nwr["shop"="convenience"]["brand"~"OXXO",i]{BBOX};
  nwr["name"~"^OXXO",i]{BBOX};
);
out center tags;
"""


def fetch_overpass():
    """POST the query, trying each endpoint with one retry."""
    last_err = None
    for endpoint in ENDPOINTS:
        for attempt in (1, 2):
            try:
                resp = requests.post(
                    endpoint,
                    data={"data": QUERY},
                    headers={"User-Agent": USER_AGENT},
                    timeout=TIMEOUT,
                )
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, ValueError) as e:
                last_err = e
                print(f"warn: {endpoint} attempt {attempt} failed: {e}", file=sys.stderr)
                time.sleep(5)
    raise SystemExit(f"error: all Overpass endpoints failed: {last_err}")


def haversine_km(lon1, lat1, lon2, lat2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def main():
    raw = fetch_overpass()

    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    # Dedupe by (type, id); union of both query clauses is already merged by
    # Overpass, but guard anyway.
    seen = set()
    locations = []
    for el in raw.get("elements", []):
        key = (el.get("type"), el.get("id"))
        if key in seen:
            continue
        seen.add(key)

        if el.get("type") == "node":
            lon, lat = el.get("lon"), el.get("lat")
        else:  # way/relation -> use Overpass-provided center
            center = el.get("center") or {}
            lon, lat = center.get("lon"), center.get("lat")
        if lon is None or lat is None:
            continue

        tags = el.get("tags", {})
        street = tags.get("addr:street", "").strip()
        housenumber = tags.get("addr:housenumber", "").strip()
        addr = " ".join(x for x in (street, housenumber) if x)

        locations.append(
            {
                "osm_id": f"{el['type']}/{el['id']}",
                "name": tags.get("name", "OXXO"),
                "lon": round(lon, 7),
                "lat": round(lat, 7),
                "addr": addr,
            }
        )

    locations.sort(key=lambda x: x["osm_id"])

    out = {
        "sponsor": "oxxo",
        "fetched": date.today().isoformat(),
        "source": "OpenStreetMap (ODbL)",
        "count": len(locations),
        "locations": locations,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [loc["lon"], loc["lat"]]},
                "properties": {"name": loc["name"], "addr": loc["addr"]},
            }
            for loc in locations
        ],
    }
    OUT_GEOJSON.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")

    clon, clat = BOUNDARY_CENTER
    inside = sum(
        1
        for loc in locations
        if haversine_km(loc["lon"], loc["lat"], clon, clat) <= BOUNDARY_RADIUS_KM
    )
    outside = len(locations) - inside

    print(f"total OXXO locations: {len(locations)}")
    print(
        f"inside {BOUNDARY_RADIUS_KM} km of ({clon}, {clat}): {inside}; outside: {outside}"
    )
    print(f"wrote {RAW_PATH}")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_GEOJSON}")


if __name__ == "__main__":
    main()
