#!/usr/bin/env python3
"""Extract embedded Leaflet GeoJSON (`var ruta = {...}`) from saved queruta.mx pages."""
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "data"
PAGES = BASE / "raw" / "queruta" / "pages"
GEO = BASE / "geojson" / "queruta"
GEO.mkdir(parents=True, exist_ok=True)


def extract_json_object(text, start):
    """Balanced-brace scan from the first '{' at/after start."""
    i = text.index("{", start)
    depth, in_str, esc = 0, False, False
    for j in range(i, len(text)):
        ch = text[j]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[i:j + 1]
    raise ValueError("unbalanced braces")


def main():
    results = []
    for page in sorted(PAGES.glob("*.html")):
        slug = page.stem
        html = page.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"(?:var|const|let)\s+ruta\s*=\s*", html)
        rec = {"slug": slug, "geometry": False, "n_lines": 0, "n_points": 0}
        if m:
            try:
                raw = extract_json_object(html, m.end())
                # some pages have commented-out features (/** ... */) inside the literal
                raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
                raw = re.sub(r",\s*([}\]])", r"\1", raw)  # trailing commas left behind
                gj = json.loads(raw)
                feats = gj.get("features", [])
                rec["n_lines"] = sum(1 for f in feats if f.get("geometry", {}).get("type") in ("LineString", "MultiLineString"))
                rec["n_points"] = sum(1 for f in feats if f.get("geometry", {}).get("type") == "Point")
                gj["properties"] = {"route_slug": slug, "source": "queruta.mx", "fetched": "2026-07-14"}
                (GEO / f"{slug}.geojson").write_text(json.dumps(gj, ensure_ascii=False), encoding="utf-8")
                rec["geometry"] = True
            except Exception as e:  # noqa: BLE001
                rec["error"] = str(e)
        results.append(rec)
        print(f"{slug}: geometry={rec['geometry']} lines={rec['n_lines']} points={rec['n_points']}" + (f" ERR={rec.get('error')}" if rec.get("error") else ""))

    with_geom = sum(1 for r in results if r["geometry"])
    (BASE / "raw" / "queruta" / "geometry_manifest.json").write_text(
        json.dumps({"extracted": with_geom, "total": len(results), "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\ngeometry extracted for {with_geom}/{len(results)} pages")


if __name__ == "__main__":
    main()
