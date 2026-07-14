#!/usr/bin/env python3
"""Merge duplicate routes (same line mapped independently by two sources) using
geometry proof: mean bidirectional nearest-neighbor distance < 60 m AND no
conflicting brand qualifiers. Distinct variants (10-amarilla vs 10-verde) survive.
Also annotates same-number pairs whose geometry proves them distinct.
"""
import csv
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "master_route_index.csv"
MLON = 111320 * math.cos(math.radians(18.462)); MLAT = 110570
MERGE_MAX = 60.0
DISTINCT_MIN = 100.0


def load_geo():
    js = (ROOT / "map" / "routes.js").read_text().split("const ROUTES = ", 1)[1].rstrip().rstrip(";")
    return {f["properties"]["id"]: f for f in json.loads(js)["features"]}


def pts(f):
    return [(c[0] * MLON, c[1] * MLAT) for part in f["geometry"]["coordinates"] for c in part]


def mean_nn(a, b):
    sa = a[::max(1, len(a) // 120)]
    return sum(min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in b) for p in sa) / len(sa)


def sim(f1, f2):
    a, b = pts(f1), pts(f2)
    return max(mean_nn(a, b), mean_nn(b, a)) if a and b else None


def qualifier(key):
    m = re.match(r"^(?:\d+|rc|c)(?:-(.*))?$", key)
    return (m.group(1) or "") if m else key


def num(key):
    m = re.match(r"^(\d+|rc|c)(?:-|$)", key)
    return m.group(1) if m else None


def conflicting(q1, q2):
    """Two nonempty, different qualifiers that don't share a token = distinct brands."""
    if not q1 or not q2:
        return False
    t1, t2 = set(q1.split("-")), set(q2.split("-"))
    return not (t1 & t2)


def main():
    geo = load_geo()
    rows = list(csv.DictReader(CSV.open()))
    by_key = {r["route_key"]: r for r in rows}

    groups = {}
    for k in by_key:
        n = num(k)
        if n:
            groups.setdefault(n, []).append(k)

    merged, verified = [], []
    for n, ks in sorted(groups.items()):
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                k1, k2 = ks[i], ks[j]
                if k1 not in by_key or k2 not in by_key:
                    continue  # already merged away
                f1, f2 = geo.get(k1), geo.get(k2)
                if not f1 or not f2:
                    continue
                s = sim(f1, f2)
                if s is None:
                    continue
                if s < MERGE_MAX and not conflicting(qualifier(k1), qualifier(k2)):
                    keep, drop = (k1, k2) if len(k1) >= len(k2) else (k2, k1)
                    kr, dr = by_key[keep], by_key[drop]
                    kr["sources"] = "; ".join(sorted(set(kr["sources"].split("; ")) | set(dr["sources"].split("; "))))
                    kf = [x.strip() for x in kr["geometry_files"].split(";") if x.strip()]
                    df = [x.strip() for x in dr["geometry_files"].split(";") if x.strip()]
                    kr["geometry_files"] = "; ".join(dict.fromkeys(kf + df))
                    if not kr.get("colonias") and dr.get("colonias"):
                        kr["colonias"] = dr["colonias"]
                    for fld in ("itinerary_text", "stops_data", "fare_info", "schedule_info"):
                        if dr.get(fld) == "yes":
                            kr[fld] = "yes"
                    note = f"merged duplicate '{dr['display_name']}' (geometry match, meanNN {s:.0f} m, 2026-07-14)"
                    kr["notes"] = re.sub(r"unmerged number-\d+ candidates:[^|]*— needs human review", "", kr["notes"]).strip(" |")
                    kr["notes"] = (kr["notes"] + " | " if kr["notes"] else "") + note
                    del by_key[drop]
                    merged.append((keep, drop, round(s)))
                elif s > DISTINCT_MIN:
                    for k in (k1, k2):
                        r = by_key[k]
                        if "needs human review" in r["notes"]:
                            r["notes"] = re.sub(r"unmerged number-\d+ candidates:[^|]*— needs human review",
                                                f"geometry-verified distinct from same-number variants (meanNN {s:.0f} m)",
                                                r["notes"])
                            verified.append(k)

    # geometry-less rows: keep in dataset, flag as excluded from the map
    for k, r in by_key.items():
        if not r["geometry_files"].strip():
            if "excluded from map" not in r["notes"]:
                r["notes"] = (r["notes"] + " | " if r["notes"] else "") + \
                    "excluded from map: no geometry; moovit-only intercity line, existence unverified on the ground"

    out = list(by_key.values())
    with CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(out)

    print(f"{len(rows)} -> {len(out)} routes")
    for keep, drop, s in merged:
        print(f"  merged: {drop} -> {keep} ({s} m)")
    print(f"  review flags resolved as distinct: {len(set(verified))}")


if __name__ == "__main__":
    main()
