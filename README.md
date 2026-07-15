# MiTehuacán (combi-tracker)

Open-source crowd-mapping of Mexico's informal transit (combis/colectivos): find and
plan combi trips, while consenting riders' phones passively keep the map alive.
First city: **Tehuacán, Puebla**. Production site: **https://mitehuacan.mx** (directory
per city: `/tehuacan`; QR stickers resolve via `/qr/<sticker-id>` and never break).

**Code:** AGPL-3.0 (`LICENSE`) · **Data:** ODbL 1.0 (`data-LICENSE.md`) · **Security & privacy:** [`SECURITY.md`](SECURITY.md)

## What's here

| Path | What |
|---|---|
| `tehuacan/` | Complete Tehuacán route dataset (82 routes, 80 with geometry), scrape/normalize pipeline, provenance docs |
| `tehuacan/map/` | The web map: route explorer + A→B combi trip planner (MapLibre + OpenFreeMap, no keys, no Google) |
| `site/` | Generated mitehuacan.mx static site (landing, city hub, 82 per-route SEO pages, map, `_redirects` for QR) — rebuild with `tehuacan/scripts/09_build_site.py` |
| `docs/system-design.md` | Interview-style system design: DAU math, Tier 0 ($0/mo) and Tier 1 (~$30/mo) architectures, diagrams |
| `PRD.md` | Coordinator web app (Traccar-based ride collection pipeline) |
| `PRD-mobile.md` | Mobile app spec: planner + passive telemetry + crowding tags |
| `traccar-rider-guide.md` | Field guide (ES/EN) for riders recording routes with Traccar Client |
| `SECURITY.md` | Rules for humans and AI agents; location data is radioactive |

## Status / decisions (2026-07)

- Launch architecture: **Tier 0** (Cloudflare Pages + Worker + D1, nightly processing) — see system design §6
- Mobile v0: **planner + manual ride recording**; passive auto-collection in v1
- Distribution: QR stickers on combis/stops → landing page → web map + store links
- Next build targets: Tier 0 ingest worker + D1 schema · landing page · Expo v0 scaffold

## Quick start (web map)

```bash
cd tehuacan/map && python3 -m http.server 8123
# open http://localhost:8123 — needs internet for basemap tiles + geocoding
```

Dataset rebuild: `tehuacan/scripts/01…08` in order (see `tehuacan/README.md`).
