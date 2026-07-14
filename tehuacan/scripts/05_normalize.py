#!/usr/bin/env python3
"""Normalize all sources into master_route_index.csv + pseudo-GTFS (agency/routes/shapes)."""
import csv
import json
import re
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "data"
GTFS = BASE / "gtfs"
GTFS.mkdir(parents=True, exist_ok=True)
FETCH_DATE = "2026-07-14"

FORANEA_SLUGS = {"ajalpan", "miahuatlan", "ruta-chapulco", "ruta-chilac", "ruta-altepexi",
                 "ruta-zapotitlan", "ruta-cuayuca", "coapan-nacional", "coapan-carranza",
                 "ruta-zinacatepec", "san-marcos", "santa-maria-coapan", "san-diego-chalma",
                 "magdalena-cuayucatepec", "teotitlan", "tilapa", "vista-hermosa"}


def norm_key(name):
    """Canonical matching key for a route name across sources."""
    s = unicodedata.normalize("NFKD", name.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("transporte ", "").replace("ruta ", "").replace("linea ", "")
    s = re.sub(r"\(verificando\)", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    # collapse "22 cardenas" style: keep number + qualifier
    return re.sub(r"\s+", "-", s)


def main():
    # --- load source manifests
    s1 = json.loads((BASE / "raw/rutastehuacan/manifest.json").read_text())
    s2meta = json.loads((BASE / "raw/queruta/routes.json").read_text())
    s2geo = {r["slug"]: r for r in json.loads((BASE / "raw/queruta/geometry_manifest.json").read_text())["results"]}
    s3 = json.loads((BASE / "raw/moovit/moovit_lines.json").read_text())

    index = {}  # key -> row

    def row_for(key, display):
        if key not in index:
            index[key] = {"route_key": key, "display_name": display, "variant": "",
                          "kind": "local", "sources": set(),
                          "geometry": "no", "geometry_files": [],
                          "itinerary_text": "no", "stops_data": "no",
                          "fare_info": "no", "schedule_info": "no", "notes": []}
        return index[key]

    # source 1: rutastehuacan (geometry authority)
    for r in s1["routes"]:
        key = norm_key(r["name"])
        row = row_for(key, r["name"])
        row["sources"].add("rutastehuacan.th1.mx")
        if r.get("geojson_file"):
            row["geometry"] = "yes"
            row["geometry_files"].append(f"geojson/rutastehuacan/{r['slug']}.geojson")
        if r.get("error"):
            row["notes"].append(f"rutastehuacan fetch error: {r['error']}")

    # source 2: queruta (metadata + geometry)
    for r in s2meta["routes"]:
        slug = r["slug"]
        title = (r.get("title") or slug).replace(" - Que ruta", "").strip()
        key = norm_key(title)
        row = row_for(key, title)
        row["sources"].add("queruta.mx")
        if slug in FORANEA_SLUGS or any(f in slug for f in FORANEA_SLUGS):
            row["kind"] = "foránea"
        g = s2geo.get(slug, {})
        if g.get("geometry"):
            row["geometry"] = "yes"
            row["geometry_files"].append(f"geojson/queruta/{slug}.geojson")
        if len(r.get("text") or "") > 400 or r.get("list_items"):
            row["itinerary_text"] = "yes"
        if r.get("fare_mentions"):
            row["fare_info"] = "yes"
        if r.get("schedule_mentions"):
            row["schedule_info"] = "yes"

    # source 3: moovit (stops/duration/hours)
    for ln in s3["lines"]:
        xref = ln.get("cross_ref", "")
        m = re.search(r"matches (.+?) on", xref)
        key = norm_key(m.group(1)) if m else norm_key(ln["name"].split("—")[0])
        row = row_for(key, ln["name"] if key not in index else index[key]["display_name"])
        row["sources"].add("moovitapp.com")
        row["stops_data"] = "yes"
        row["schedule_info"] = "yes"
        row["notes"].append(f"moovit: {ln['n_stops']} stops, ~{ln['trip_duration_min']} min, {ln['service_hours']}")
        if ln.get("note") == "foránea":
            row["kind"] = "foránea"

    # --- number-based merge for systematic naming mismatches
    # (rutastehuacan: "Ruta 26 - El Riego" vs queruta: "Ruta 26")
    def route_num(key):
        m = re.match(r"^(\d+)(?:-|$)", key)
        return m.group(1) if m else None

    def merge(dst, src):
        dst["sources"] |= src["sources"]
        dst["geometry_files"] += src["geometry_files"]
        if src["geometry"] == "yes":
            dst["geometry"] = "yes"
        for f in ("itinerary_text", "stops_data", "fare_info", "schedule_info"):
            if src[f] == "yes":
                dst[f] = "yes"
        dst["notes"] += src["notes"]
        dst["notes"].append(f"merged by route number: also known as '{src['display_name']}'")

    r1_only = {k: v for k, v in index.items() if v["sources"] == {"rutastehuacan.th1.mx"}}
    r2_only = {k: v for k, v in index.items() if v["sources"] == {"queruta.mx"}}
    by_num_1, by_num_2 = {}, {}
    for k, v in r1_only.items():
        n = route_num(k)
        if n:
            by_num_1.setdefault(n, []).append(k)
    for k, v in r2_only.items():
        n = route_num(k)
        if n:
            by_num_2.setdefault(n, []).append(k)
    merged = 0
    for n in sorted(set(by_num_1) & set(by_num_2)):
        k1s, k2s = by_num_1[n], by_num_2[n]
        if len(k1s) == 1 and len(k2s) == 1:
            merge(index[k1s[0]], index[k2s[0]])
            del index[k2s[0]]
            merged += 1
        else:
            for k in k1s + k2s:
                index[k]["notes"].append(
                    f"unmerged number-{n} candidates: {', '.join(k1s + k2s)} — needs human review")
    print(f"number-merge: {merged} pairs merged")

    # --- write master index
    out = BASE / "master_route_index.csv"
    rows = sorted(index.values(), key=lambda r: (r["kind"], r["route_key"]))
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["route_key", "display_name", "kind", "sources", "geometry",
                    "geometry_files", "itinerary_text", "stops_data", "fare_info",
                    "schedule_info", "notes"])
        for r in rows:
            w.writerow([r["route_key"], r["display_name"], r["kind"],
                        "; ".join(sorted(r["sources"])), r["geometry"],
                        "; ".join(r["geometry_files"]), r["itinerary_text"],
                        r["stops_data"], r["fare_info"], r["schedule_info"],
                        " | ".join(r["notes"])])
    print(f"master index: {len(rows)} routes -> {out}")

    # --- pseudo-GTFS
    (GTFS / "agency.txt").write_text(
        "agency_id,agency_name,agency_url,agency_timezone,agency_lang\n"
        "TEHUACAN_COMBIS,Combis y Colectivos de Tehuacan (informal consolidated),http://rutastehuacan.th1.mx/,America/Mexico_City,es\n",
        encoding="utf-8")

    routes_rows, shapes_rows = [], []
    for r in rows:
        rid = r["route_key"]
        routes_rows.append([rid, "TEHUACAN_COMBIS", r["display_name"][:50], r["display_name"], "3"])
        # prefer rutastehuacan geometry, fall back to queruta; first LineString-ish feature per file
        gj_path = next((BASE / p for p in r["geometry_files"]), None)
        if not gj_path or not gj_path.exists():
            continue
        gj = json.loads(gj_path.read_text())
        seq = 0
        shape_id = f"shp_{rid}"
        for feat in gj["features"]:
            geom = feat.get("geometry") or {}
            lines = []
            if geom.get("type") == "LineString":
                lines = [geom["coordinates"]]
            elif geom.get("type") == "MultiLineString":
                lines = geom["coordinates"]
            for line in lines:
                for lon, lat, *_ in line:
                    shapes_rows.append([shape_id, f"{lat:.6f}", f"{lon:.6f}", seq])
                    seq += 1
        if seq:
            routes_rows[-1].append(shape_id)

    with (GTFS / "routes.txt").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"])
        for rr in routes_rows:
            w.writerow(rr[:5])
    with (GTFS / "shapes.txt").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"])
        w.writerows(shapes_rows)
    n_shapes = len({s[0] for s in shapes_rows})
    print(f"gtfs: {len(routes_rows)} routes, {n_shapes} shapes, {len(shapes_rows)} shape points")


if __name__ == "__main__":
    main()
