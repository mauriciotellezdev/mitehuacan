#!/usr/bin/env python3
"""Import named route drafts (made in /system/map) into the dataset.

Usage: QUECOMBI_STATS_TOKEN=... python3 tehuacan/scripts/14_import_drafts.py [--slug X]
Writes tehuacan/data/geojson/field/<slug>.geojson for each draft and prints the
master_route_index.csv + rebuild steps.
"""
import argparse
import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("QUECOMBI_BASE", "https://mitehuacan.pages.dev")
TOKEN = os.environ.get("QUECOMBI_STATS_TOKEN")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", help="import only this draft")
    args = ap.parse_args()
    if not TOKEN:
        raise SystemExit("set QUECOMBI_STATS_TOKEN")

    h = {"Authorization": f"Bearer {TOKEN}"}
    drafts = requests.get(f"{BASE}/api/route-drafts", headers=h, timeout=30).json()["drafts"]
    if args.slug:
        drafts = [d for d in drafts if d["slug"] == args.slug]
    if not drafts:
        raise SystemExit("no drafts to import")

    out = ROOT / "data" / "geojson" / "field"
    out.mkdir(parents=True, exist_ok=True)
    for d in drafts:
        row = requests.get(f"{BASE}/api/route-drafts", params={"slug": d["slug"]}, headers=h, timeout=30).json()
        coords = json.loads(row["geometry"])
        gj = {"type": "FeatureCollection",
              "properties": {"source": "field ride (editor draft)", "device": row.get("device"),
                             "window": [row.get("t0"), row.get("t1")], "n_source": row.get("n_source")},
              "features": [{"type": "Feature",
                            "properties": {"name": row["name"], "kind": "route_line"},
                            "geometry": {"type": "LineString", "coordinates": coords}}]}
        p = out / f"{row['slug']}.geojson"
        p.write_text(json.dumps(gj, ensure_ascii=False), encoding="utf-8")
        print(f"imported {p.relative_to(ROOT)}  ({len(coords)} pts, '{row['name']}')")

    print("\nnext steps per route:")
    print("  1. master_route_index.csv: new/updated row with geometry_files=geojson/field/<slug>.geojson, sources += field-ride")
    print("  2. python3 tehuacan/scripts/06_build_map.py && 12_build_sponsors.py && 09_build_site.py")
    print("  3. review on mitehuacan.localhost, commit, deploy")


if __name__ == "__main__":
    main()
