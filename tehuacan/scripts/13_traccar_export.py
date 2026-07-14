#!/usr/bin/env python3
"""Export a recorded ride from the local Traccar server into the dataset.

Usage:
  python3 tehuacan/scripts/13_traccar_export.py --device mauricio-1 \
      --from "2026-07-15T09:00" --to "2026-07-15T10:30" --slug tecoxteo-coxcatlan

Writes tehuacan/data/geojson/field/<slug>.geojson and prints the follow-up steps
(add/point a master_route_index.csv row at it, rebuild 06 -> 12 -> 09).
Times are LOCAL (America/Mexico_City, UTC-6); pass the ride window you noted.
"""
import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
TRACCAR = "http://localhost:8082"
AUTH = (os.environ.get("TRACCAR_EMAIL", "admin@quecombi.local"),
        os.environ.get("TRACCAR_PASSWORD", "cambiame-ya"))  # change in Traccar UI + export TRACCAR_PASSWORD
UTC_OFFSET = -6


def to_utc(s):
    return (datetime.fromisoformat(s) - timedelta(hours=UTC_OFFSET)).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_remote(args):
    """Pull from the deployed Cloudflare ingest (default; laptop-free collection)."""
    base = os.environ.get("QUECOMBI_BASE", "https://quecombi.pages.dev")
    token = os.environ.get("QUECOMBI_STATS_TOKEN")
    if not token:
        raise SystemExit("set QUECOMBI_STATS_TOKEN (same value as the Pages STATS_TOKEN secret)")
    r = requests.get(f"{base}/api/rides",
                     params={"device": args.device, "from": to_utc(args.t0), "to": to_utc(args.t1)},
                     headers={"Authorization": f"Bearer {token}"}, timeout=60)
    r.raise_for_status()
    pos = r.json()["positions"]
    return [[round(p["lon"], 6), round(p["lat"], 6)] for p in pos]


def fetch_local_traccar(args):
    """Pull from a local Traccar server (legacy/home setup)."""
    s = requests.Session()
    s.auth = AUTH
    devs = s.get(f"{TRACCAR}/api/devices", timeout=15).json()
    dev = next((d for d in devs if d["uniqueId"] == args.device or d["name"] == args.device), None)
    if not dev:
        raise SystemExit(f"device '{args.device}' not found; have: {[d['uniqueId'] for d in devs]}")
    pos = s.get(f"{TRACCAR}/api/positions",
                params={"deviceId": dev["id"], "from": to_utc(args.t0), "to": to_utc(args.t1)},
                headers={"Accept": "application/json"}, timeout=60).json()
    pos.sort(key=lambda p: p["fixTime"])
    return [[round(p["longitude"], 6), round(p["latitude"], 6)] for p in pos]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", required=True, help="device identifier (e.g. mauricio-1)")
    ap.add_argument("--from", dest="t0", required=True, help="ride start, local time ISO (2026-07-15T09:00)")
    ap.add_argument("--to", dest="t1", required=True, help="ride end, local time ISO")
    ap.add_argument("--slug", required=True, help="output name, e.g. tecoxteo-coxcatlan-ida")
    ap.add_argument("--local", action="store_true", help="pull from local Traccar instead of the deployed ingest")
    args = ap.parse_args()

    coords = fetch_local_traccar(args) if args.local else fetch_remote(args)
    if not coords:
        raise SystemExit("no positions in that window — check times (local) and the device id")

    out = ROOT / "data" / "geojson" / "field"
    out.mkdir(parents=True, exist_ok=True)
    gj = {"type": "FeatureCollection",
          "properties": {"source": "field ride (Traccar)", "device": args.device,
                         "from": args.t0, "to": args.t1, "n_points": len(coords)},
          "features": [{"type": "Feature",
                        "properties": {"name": args.slug, "kind": "route_line"},
                        "geometry": {"type": "LineString", "coordinates": coords}}]}
    path = out / f"{args.slug}.geojson"
    path.write_text(json.dumps(gj, ensure_ascii=False), encoding="utf-8")

    dur = (datetime.fromisoformat(args.t1) - datetime.fromisoformat(args.t0)).seconds // 60
    print(f"wrote {path.relative_to(ROOT)}  ({len(coords)} points, ~{dur} min)")
    print("\nnext steps:")
    print(f"  1. add/update a row in tehuacan/data/master_route_index.csv:")
    print(f"     geometry_files = geojson/field/{args.slug}.geojson  · sources += field-ride")
    print(f"  2. rebuild: python3 tehuacan/scripts/06_build_map.py && 12_build_sponsors.py && 09_build_site.py")
    print(f"  3. check it on quecombi.localhost, then commit")


if __name__ == "__main__":
    main()
