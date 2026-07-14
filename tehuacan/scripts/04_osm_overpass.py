#!/usr/bin/env python3
"""Source 3b: OSM Overpass — bus/share_taxi route relations in the Tehuacán bbox → GeoJSON."""
import json
import time
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent / "data"
RAW = BASE / "raw" / "osm"
GEO = BASE / "geojson" / "osm"
GEO.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "combi-tracker research (contact: augmentedmike@gmail.com)"}
BBOX = "18.42,-97.44,18.50,-97.36"  # S,W,N,E
QUERY = f"""
[out:json][timeout:90];
(
  relation["type"="route"]["route"~"^(bus|share_taxi|minibus)$"]({BBOX});
);
out body;
>;
out skel qt;
"""


def main():
    r = requests.post("https://overpass-api.de/api/interpreter", data={"data": QUERY}, headers=UA, timeout=120)
    r.raise_for_status()
    data = r.json()
    (RAW / "overpass_raw.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    nodes = {e["id"]: (e["lon"], e["lat"]) for e in data["elements"] if e["type"] == "node"}
    ways = {e["id"]: [nodes[n] for n in e["nodes"] if n in nodes] for e in data["elements"] if e["type"] == "way"}
    rels = [e for e in data["elements"] if e["type"] == "relation"]
    print(f"relations={len(rels)} ways={len(ways)} nodes={len(nodes)}")

    feats = []
    for rel in rels:
        tags = rel.get("tags", {})
        lines = []
        stop_pts = []
        for mem in rel.get("members", []):
            if mem["type"] == "way" and mem["ref"] in ways and mem.get("role", "") in ("", "forward", "backward"):
                coords = ways[mem["ref"]]
                if len(coords) >= 2:
                    lines.append(coords)
            elif mem["type"] == "node" and "stop" in mem.get("role", "") and mem["ref"] in nodes:
                stop_pts.append(nodes[mem["ref"]])
        props = {"osm_relation": rel["id"], **{k: v for k, v in tags.items()}}
        if lines:
            feats.append({"type": "Feature", "properties": {**props, "kind": "route_line"},
                          "geometry": {"type": "MultiLineString", "coordinates": lines}})
        for p in stop_pts:
            feats.append({"type": "Feature", "properties": {"osm_relation": rel["id"], "kind": "stop", "route": tags.get("name")},
                          "geometry": {"type": "Point", "coordinates": list(p)}})
        print(f"  rel {rel['id']}: {tags.get('name', '?')} — {len(lines)} way segments, {len(stop_pts)} stops")

    gj = {"type": "FeatureCollection",
          "properties": {"source": "OpenStreetMap via Overpass", "bbox": BBOX, "fetched": "2026-07-14",
                         "license": "ODbL 1.0"},
          "features": feats}
    (GEO / "osm_routes.geojson").write_text(json.dumps(gj, ensure_ascii=False), encoding="utf-8")
    summary = [{"relation": r_["id"], "tags": r_.get("tags", {})} for r_ in rels]
    (RAW / "relations_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
    time.sleep(0)
