#!/usr/bin/env python3
"""Source 2: queruta.mx — crawl route listing + per-route pages, extract metadata/itineraries/embeds."""
import json
import re
import time
from html import unescape
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent / "data"
RAW = BASE / "raw" / "queruta"
(RAW / "pages").mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
DELAY = 1.0
LISTING = "https://queruta.mx/transporte-publico-de-tehuacan/"


def get(session, url, tries=3):
    last = None
    for i in range(tries):
        try:
            r = session.get(url, headers=UA, timeout=45)
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(DELAY * (i + 1))
    raise last


def strip_tags(html):
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<br\s*/?>|</p>|</li>|</h[1-6]>", "\n", html, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def extract_route_page(html, url):
    rec = {"url": url, "slug": url.rstrip("/").rsplit("/", 1)[-1]}
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    rec["title"] = strip_tags(m.group(1)) if m else None

    # main article body
    m = re.search(r"<article[^>]*>(.*?)</article>", html, re.S) or \
        re.search(r'<div[^>]*class="[^"]*entry-content[^"]*"[^>]*>(.*)', html, re.S)
    body_html = m.group(1) if m else html
    rec["text"] = strip_tags(body_html)

    # embedded maps: iframes, KML/KMZ refs, google maps links, inline JSON coords
    rec["iframes"] = re.findall(r'<iframe[^>]+src="([^"]+)"', body_html)
    rec["map_links"] = sorted(set(re.findall(r'https://(?:www\.google\.com/maps[^\s"\'<>]+|goo\.gl/maps/[^\s"\'<>]+|maps\.app\.goo\.gl/[^\s"\'<>]+)', html)))
    rec["kml_refs"] = sorted(set(re.findall(r'https?://[^\s"\'<>]+\.km[lz]\b[^\s"\'<>]*', html)))
    has_coord_json = bool(re.search(r'"lat"\s*:\s*-?\d+\.\d+', html) or re.search(r"\[\s*-9[67]\.\d+\s*,\s*18\.\d+", html))
    rec["has_inline_coord_json"] = has_coord_json

    # fares: $ amounts near fare-ish words
    fares = re.findall(r"(?:tarifa|costo|pasaje|cobra|precio)[^.\n]{0,80}?\$ ?\d+(?:\.\d+)?[^.\n]{0,40}", rec["text"], re.I)
    rec["fare_mentions"] = [f.strip() for f in fares][:5]

    # schedule/hours mentions
    sched = re.findall(r"(?:horario|opera|circula|servicio)[^.\n]{0,120}?\d{1,2}(?::\d{2})? ?(?:am|pm|hrs|horas|:\d{2})[^.\n]{0,60}", rec["text"], re.I)
    rec["schedule_mentions"] = [s.strip() for s in sched][:5]

    # itinerary: list items under a heading mentioning recorrido/itinerario/calles, else all <li> runs
    lis = re.findall(r"<li[^>]*>(.*?)</li>", body_html, re.S)
    items = [strip_tags(li) for li in lis]
    rec["list_items"] = [i for i in items if i][:200]
    return rec


def main():
    session = requests.Session()
    listing_urls = [LISTING] + [f"{LISTING}page/{n}/" for n in (2, 3, 4)]
    route_urls = []
    for i, lu in enumerate(listing_urls, 1):
        try:
            r = get(session, lu)
        except Exception as e:  # noqa: BLE001
            print(f"listing {lu}: FAILED — {e}")
            continue
        (RAW / f"listing-{i}.html").write_bytes(r.content)
        found = re.findall(r'href="(https://queruta\.mx/rutas-de-tehuacan/[^"#]+)"', r.text)
        new = [u for u in found if u not in route_urls]
        route_urls.extend(new)
        print(f"listing {i}: +{len(new)} routes (total {len(route_urls)})")
        time.sleep(DELAY)

    records, failures = [], []
    for i, url in enumerate(route_urls, 1):
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        try:
            r = get(session, url)
            (RAW / "pages" / f"{slug}.html").write_bytes(r.content)
            rec = extract_route_page(r.text, url)
            records.append(rec)
            print(f"[{i}/{len(route_urls)}] {slug}: iframes={len(rec['iframes'])} maplinks={len(rec['map_links'])} kml={len(rec['kml_refs'])} inline_json={rec['has_inline_coord_json']} lis={len(rec['list_items'])}")
        except Exception as e:  # noqa: BLE001
            failures.append({"url": url, "error": str(e)})
            print(f"[{i}/{len(route_urls)}] {slug}: FAILED — {e}")
        time.sleep(DELAY)

    out = {"source": "queruta.mx", "fetched": "2026-07-14",
           "n_routes": len(records), "routes": records, "failures": failures}
    (RAW / "routes.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nok={len(records)} failed={len(failures)}")


if __name__ == "__main__":
    main()
