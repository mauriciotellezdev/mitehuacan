#!/usr/bin/env python3
"""Enrich master index with branded combi names (known_as) + served colonias; update CSV."""
import csv
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "data"

# brandings confirmed from external sources beyond the route's own display name
# (moovit line descriptors, primeralinea.com.mx article, 2026-07-14)
OVERRIDES = {
    "21": ("Santa Cruz", "moovitapp.com: 'Ramal Santa Cruz - Centro'"),
    "40": ("Fracc. Santa María - La Purísima", "moovitapp.com: 'Ramal Fracc. Santa. María - La Purísima'"),
    "37": ("San Isidro - La Purísima", "moovitapp.com: 'San Isidro - La Purísima (Circuito)'"),
}


def alias_from_name(display, key):
    """'Ruta 33 - Palmas' -> 'Palmas'; plain 'Ruta 12' -> ''."""
    m = re.match(r"^(?:Transporte|Ruta)\s+[\w-]+\s*[-–—]\s*(.+)$", display)
    if m:
        return m.group(1).strip()
    if not re.match(r"^Ruta\s+[\dA-Z-]+\s*$", display):
        return display  # foráneas like 'Ajalpan' are their own brand
    return ""


def main():
    q = json.loads((BASE / "raw/queruta/routes.json").read_text())
    colonias_by_slug = {}
    for r in q["routes"]:
        text = r.get("list_items") and r["list_items"][0] or r.get("text", "")
        m = re.search(r"Colonias\s*\n\s*(.+?)\s*\n", text)
        if m:
            cols = [c.strip() for c in m.group(1).split(",") if c.strip()]
            colonias_by_slug[r["slug"]] = cols

    rows = list(csv.DictReader((BASE / "master_route_index.csv").open()))
    n_alias = n_col = 0
    for r in rows:
        num = r["route_key"].split("-")[0]
        alias = alias_from_name(r["display_name"], r["route_key"])
        src = "route name (rutastehuacan/queruta)"
        if not alias and num in OVERRIDES:
            alias, src = OVERRIDES[num]
        r["known_as"] = alias
        r["known_as_source"] = src if alias else ""
        # colonias: match queruta slug from geometry file path
        cols = []
        for f in r["geometry_files"].split(";"):
            f = f.strip()
            if f.startswith("geojson/queruta/"):
                cols = colonias_by_slug.get(f.split("/")[-1].replace(".geojson", ""), [])
        r["colonias"] = ", ".join(cols)
        if alias:
            n_alias += 1
        if cols:
            n_col += 1

    fields = list(rows[0].keys())
    with (BASE / "master_route_index.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} routes: {n_alias} with known_as, {n_col} with colonias list")


if __name__ == "__main__":
    main()
