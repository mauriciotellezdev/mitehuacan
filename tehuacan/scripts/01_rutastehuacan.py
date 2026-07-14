#!/usr/bin/env python3
"""Source 1: rutastehuacan.th1.mx — resolve goo.gl links to My Maps, download KML, parse to GeoJSON."""
import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent / "data"
RAW = BASE / "raw" / "rutastehuacan"
GEO = BASE / "geojson" / "rutastehuacan"
GEO.mkdir(parents=True, exist_ok=True)
(RAW / "kml").mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
DELAY = 1.0
KML_NS = "{http://www.opengis.net/kml/2.2}"

KNOWN_ROUTES = [
    "Ruta 1", "Ruta 2", "Ruta 3", "Ruta 4", "Ruta 5", "Ruta 6", "Ruta 7",
    "Ruta 8", "Ruta 9", "Ruta 10", "Ruta 11", "Ruta 12", "Ruta 13",
    "Ruta 15", "Ruta 15 Frailes", "Ruta 16", "Ruta 18", "Ruta 19",
    "Ruta 20", "Ruta 21", "Ruta 22 Cardenas", "Ruta 22 Bella Vista",
    "Ruta 22 San Marcos", "Ruta 23", "Ruta 23 San Isidro",
    "Ruta 23 Maravillas", "Ruta 24", "Ruta 24 Bosques de Reforma",
    "Ruta 25 3 de Mayo", "Ruta 26", "Ruta 27 El Riego",
    "Ruta 28 San Lorenzo", "Ruta 29 San Lorenzo", "Ruta 30 San Lorenzo",
    "Ruta 36 San Lorenzo", "Ruta 31 Fovissste-Resurreccion",
    "Ruta 32 CBTis", "Ruta 32 San Francisco", "Ruta 32 Colosio",
    "Ruta 33 Palmas", "Ruta 34 Viveros", "Ruta 35 San Vicente Ferrer",
    "Ruta 37 San Isidro", "Ruta 38 Santa Cruz Unidad Militar",
    "Ruta 40", "Ruta 41", "Ruta 42", "Ruta 43",
    "RC", "RC Del Valle", "Transporte Cuayucatepec",
]


def slugify(name):
    s = name.lower()
    for a, b in zip("áéíóúñü", "aeiounu"):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def norm(name):
    """Normalized key for matching page names against the known list."""
    s = slugify(name)
    s = re.sub(r"\b(la|el|de|del)\b", "", s)
    return re.sub(r"-+", "-", s).strip("-")


def extract_links(html):
    """Return ordered [(name, url)] from anchor tags pointing at goo.gl/maps."""
    pairs = []
    for m in re.finditer(r'<a\s+href="(https://goo\.gl/maps/[^"]+)"[^>]*>(.*?)</a>', html, re.S):
        url, label = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
        label = re.sub(r"\s+", " ", label).replace("📍", "").strip()
        pairs.append((label, url))
    return pairs


def resolve_mid(session, url):
    r = session.get(url, headers=UA, allow_redirects=True, timeout=30)
    r.raise_for_status()
    qs = parse_qs(urlparse(r.url).query)
    mid = qs.get("mid", [None])[0]
    if not mid:
        m = re.search(r"mid=([\w-]+)", r.url)
        mid = m.group(1) if m else None
    return mid, r.url


def kml_coords(text):
    pts = []
    for triple in text.split():
        parts = triple.split(",")
        if len(parts) >= 2:
            pts.append([float(parts[0]), float(parts[1])])
    return pts


def kml_to_features(kml_bytes):
    root = ET.fromstring(kml_bytes)
    feats = []
    for pm in root.iter(f"{KML_NS}Placemark"):
        name_el = pm.find(f"{KML_NS}name")
        pname = (name_el.text or "").strip() if name_el is not None else ""
        for ls in pm.iter(f"{KML_NS}LineString"):
            c = ls.find(f"{KML_NS}coordinates")
            if c is not None and c.text:
                feats.append({"type": "Feature",
                              "properties": {"name": pname, "kind": "route_line"},
                              "geometry": {"type": "LineString", "coordinates": kml_coords(c.text)}})
        for pt in pm.iter(f"{KML_NS}Point"):
            c = pt.find(f"{KML_NS}coordinates")
            if c is not None and c.text:
                coords = kml_coords(c.text)
                if coords:
                    feats.append({"type": "Feature",
                                  "properties": {"name": pname, "kind": "stop"},
                                  "geometry": {"type": "Point", "coordinates": coords[0]}})
    return feats


def fetch_with_retries(session, url, tries=3):
    last = None
    for i in range(tries):
        try:
            r = session.get(url, headers=UA, timeout=60)
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(DELAY * (i + 1))
    raise last


def main():
    html = (RAW / "index.html").read_text(encoding="utf-8", errors="replace")
    pairs = extract_links(html)
    print(f"found {len(pairs)} route links on index page")

    session = requests.Session()
    results, failures = [], []
    for i, (name, url) in enumerate(pairs, 1):
        slug = slugify(name)
        rec = {"name": name, "slug": slug, "shorturl": url, "mid": None,
               "kml_file": None, "geojson_file": None, "n_lines": 0, "n_stops": 0,
               "error": None}
        try:
            mid, full_url = resolve_mid(session, url)
            rec["mid"], rec["resolved_url"] = mid, full_url
            if not mid:
                raise ValueError("no mid in resolved URL")
            time.sleep(DELAY)
            kml_url = f"https://www.google.com/maps/d/kml?mid={mid}&forcekml=1"
            r = fetch_with_retries(session, kml_url)
            kml_path = RAW / "kml" / f"{slug}.kml"
            kml_path.write_bytes(r.content)
            rec["kml_file"] = str(kml_path.relative_to(BASE))
            feats = kml_to_features(r.content)
            rec["n_lines"] = sum(1 for f in feats if f["properties"]["kind"] == "route_line")
            rec["n_stops"] = sum(1 for f in feats if f["properties"]["kind"] == "stop")
            gj = {"type": "FeatureCollection",
                  "properties": {"route": name, "source": "rutastehuacan.th1.mx", "mid": mid},
                  "features": feats}
            gj_path = GEO / f"{slug}.geojson"
            gj_path.write_text(json.dumps(gj, ensure_ascii=False), encoding="utf-8")
            rec["geojson_file"] = str(gj_path.relative_to(BASE))
            print(f"[{i}/{len(pairs)}] {name}: {rec['n_lines']} lines, {rec['n_stops']} stops")
        except Exception as e:  # noqa: BLE001
            rec["error"] = str(e)
            failures.append(name)
            print(f"[{i}/{len(pairs)}] {name}: FAILED — {e}")
        results.append(rec)
        time.sleep(DELAY)

    # validation against known route set
    page_keys = {norm(r["name"]): r["name"] for r in results}
    known_keys = {norm(k): k for k in KNOWN_ROUTES}
    missing = [v for k, v in known_keys.items() if k not in page_keys]
    extra = [v for k, v in page_keys.items() if k not in known_keys]

    manifest = {"source": "rutastehuacan.th1.mx", "fetched": "2026-07-14",
                "routes": results, "failures": failures,
                "validation": {"known_not_on_page": missing, "on_page_not_known": extra}}
    (RAW / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nok={len(results)-len(failures)} failed={len(failures)}")
    print(f"known-but-missing: {missing}")
    print(f"on-page-but-unknown: {extra}")


if __name__ == "__main__":
    main()
