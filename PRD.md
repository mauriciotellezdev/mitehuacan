# PRD — Combi Route Mapper (web app)

**Status:** Draft v1
**Owner:** Michael
**Date:** 2026-07-14

---

## 1. Problem

Combis (shared vans) run informal, undocumented routes across Mexican cities. There is no map of where they go. We are sending riders on combis with the Traccar Client app on their phones, which streams GPS positions to our Traccar server. That raw data is currently only visible as dots and breadcrumb trails in Traccar's generic fleet dashboard — which knows nothing about rides, routes, lines, or streets.

We need a web app that turns raw GPS traces into a **catalog of named combi routes** — each one snapped to the street grid with street and cross-street detail — and presents them on one large map.

## 2. Goals

1. **Ingest** rider traces from the Traccar server automatically — no manual GPX exports.
2. **Label** each ride: which combi line, which direction, boarding/exit points, data quality.
3. **Match** each trace to the street network so a ride becomes an ordered list of named streets and intersections, not raw GPS points.
4. **Aggregate** multiple rides of the same line into one canonical route geometry, with branch/variant detection.
5. **Explore** everything on a single interactive map: all routes, filterable, with per-route detail (streets, cross streets, ride history).
6. **Export** routes as GeoJSON and GTFS so the data outlives this tool.

### Non-goals (v1)

- Real-time passenger-facing arrival predictions ("where is my combi now").
- Trip planning / routing for end users.
- Fare, schedule, or headway data collection (fields can exist, but no dedicated tooling).
- Mobile app work — phone side is Traccar Client, unchanged.
- Public anonymous access (v1 is internal; a public read-only map is a later phase).

## 3. Users

| Persona | Description | Primary needs |
|---|---|---|
| **Coordinator** (Michael) | Runs the mapping operation | Device/rider management, ride labeling, data quality control, route approval, exports |
| **Reviewer** | Helper who labels and cleans data | Simple queue: see a trace, label it, flag junk |
| **Viewer** (later) | Anyone consuming the finished map | Browse routes, search by street/line, no editing |

Roles: `admin` (coordinator), `editor` (reviewer), `viewer`. v1 can ship with a single shared admin login, but the role model should exist from the start.

## 4. Core concepts / data model

- **Device** — a phone running Traccar Client (`combi-07`). Belongs to a rider. Synced from Traccar.
- **Trace** — the raw GPS point stream for one recording session (service on → service off). Detected automatically from Traccar position gaps.
- **Ride** — a labeled trace: line, direction, boarding/exit points, quality rating, notes. One trace → at most one ride (traces can be discarded as junk).
- **Line** — a combi line as riders know it ("Ruta 12 — Centro–San Pedro"). Has a name, destination sign text, color, notes.
- **Route** — the canonical geometry for one line + direction, built by aggregating its rides' map-matched results. Has an ordered street/intersection list. Versioned; one version is "published."
- **Segment** — a map-matched street edge (OSM way reference + name) inside a ride or route.

```
Device 1—* Trace 1—0..1 Ride *—1 Line 1—* Route(direction, version) 1—* Segment
```

## 5. Functional requirements

### 5.1 Ingestion (Traccar sync)

- **F1.** Poll or subscribe to the Traccar REST/WebSocket API; import new positions continuously.
- **F2.** Auto-segment position streams into Traces using configurable gap rules (default: new trace after >15 min with no positions, or device service stop event).
- **F3.** Show a live view of currently-transmitting devices on a map (who is mid-ride right now), so the coordinator can verify a ride is recording before the combi leaves. Devices that have gone quiet mid-ride are flagged as "possibly offline-buffering" rather than assumed dead — riders in dead zones or out of credit keep recording locally and upload later.
- **F4.** Never mutate or delete data in Traccar; it stays the raw source of truth. Re-import must be idempotent.
- **F4a. Late arrivals are the norm, not the exception.** Phones with no signal or no data credit buffer the entire ride locally and upload it later (possibly hours later, over Wi-Fi). Ingestion must accept positions arriving long after their GPS timestamps, and trace segmentation must key on GPS time, not arrival time, so a late-uploaded ride assembles into a complete, correctly-ordered trace.
- **F4b. Trace completeness check.** Per trace, compute and display a completeness signal (expected vs. actual point count for the recording span, largest internal gap). The coordinator uses this to confirm receipt back to the rider — until confirmed, the rider's phone holds the only copy, so the "pending upload" state must be visible per device (last position received vs. last known service start).

### 5.2 Ride labeling queue

- **F5.** Inbox of unlabeled traces, newest first, each showing: device, rider, date/time, duration, distance, and a mini-map preview of the raw trail.
- **F6.** Label form: line (pick existing or create new), direction (outbound/inbound/loop), boarding point, exit point, full-ride vs partial, quality (good / usable / junk), free-text notes.
- **F7.** Trim tool: drag start/end handles on the trace timeline to cut walking-to-the-stop and after-alighting segments before matching.
- **F7a. Auto-trim (untrusted boundaries).** Riders are instructed to start/stop the service at boarding/alighting, but the pipeline must not rely on it — treat trace boundaries as untrusted. Detect the vehicle-motion window from the speed profile (sustained vehicle speeds vs. walking/stationary) and pre-place the trim handles on it; the reviewer confirms or adjusts. Stationary blips (e.g. the few minutes recorded during a later Wi-Fi upload session) and walking tails (e.g. a forgotten toggle and a walk home) are auto-flagged for discard. This is also a privacy control: points outside the confirmed ride window are excluded from matching, aggregation, and exports.
- **F8.** Junk traces are archived, not deleted, and excluded from all aggregation.

### 5.3 Map matching

- **F9.** On label (or on demand), send the trimmed trace to the Valhalla map-matching service; store the matched geometry and the ordered segment list (OSM way IDs + street names).
- **F10.** Derive the **cross-street sequence**: every transition between differently-named ways is recorded as an intersection ("continues on Av. Juárez, crosses Calle 5 de Mayo, turns onto Reforma…").
- **F11.** Side-by-side review: raw points vs matched line on the map, with a match-confidence score. Low-confidence sections highlighted; reviewer can mark a ride "match failed" to exclude it.
- **F12.** Matching is re-runnable (e.g., after an OSM data update) without re-labeling.

### 5.4 Route builder (aggregation)

- **F13.** For a line + direction, overlay all its good/usable matched rides and compute a canonical route: segments used by the majority of rides form the trunk.
- **F14.** Detect variants: segment sequences used by a minority of rides are surfaced as branches the coordinator can accept (named variant), merge, or reject (driver detour).
- **F15.** Coordinator publishes a route version; the published version is what the explorer map and exports use. Prior versions retained.
- **F16.** Route detail view: geometry on map + ordered street list with cross streets + endpoints + length + number of supporting rides.

### 5.5 Map explorer ("the large map")

- **F17.** One map showing all published routes, color-coded by line, with sensible decluttering at low zoom.
- **F18.** Filters: by line, by area (draw a box), by street name ("which combis run on Av. Insurgentes?").
- **F19.** Click a route → detail panel (F16). Click a street segment → all lines that use it.
- **F20.** Coverage view: raw-trace heat layer toggle, to show where we have ridden vs. blank areas — this drives where to send riders next.

### 5.6 Exports

- **F21.** Per-route and bulk **GeoJSON** export (published versions).
- **F22.** **GTFS** export: agencies/routes/shapes from published routes; stops v1 = endpoints + labeled boarding/exit points only (full stop inference is out of scope).
- **F23.** **CSV** of the street/cross-street sequence per route (for the print-map / cartography workflow).

### 5.7 Admin

- **F24.** Device & rider registry (synced from Traccar, enriched with rider name/contact).
- **F25.** Ride log export (device, rider, line, direction, timestamps) — replaces the manual spreadsheet from the rider guide.
- **F26.** Basic auth with the three roles in §3.

## 6. Technical shape (assumptions, not mandates)

- **Stack:** single web app (SPA + API) — proposed: TypeScript, Bun runtime, React + MapLibre GL frontend, PostgreSQL + PostGIS.
- **Map data:** OpenStreetMap Mexico extract; self-hosted **Valhalla** for map matching (Meili); self-hosted or free-tier vector tiles for the basemap.
- **Deployment:** Docker Compose alongside the existing Traccar server on one VPS. Single-node is fine — data volume is tiny (tens of devices, thousands of rides at most).
- **Geometry storage:** PostGIS linestrings; segment lists as rows referencing OSM way IDs so street names can be refreshed from OSM.

## 7. Phasing

**Phase 1 — See the data (MVP):** F1–F8. Traccar sync, live view, trace inbox, labeling, trimming. Value: replaces the Traccar dashboard + spreadsheet immediately.

**Phase 2 — Streets:** F9–F12, F21, F23. Map matching, cross-street derivation, GeoJSON/CSV export. Value: a labeled ride becomes a street-by-street route description.

**Phase 3 — The map:** F13–F20, F22, F24–F26. Aggregation, publishing, the explorer map, GTFS, admin. Value: the actual product — the large map.

## 8. Success metrics

- Time from "rider stops service" to "ride labeled and matched" < 10 minutes of coordinator effort.
- ≥ 90% of good-quality traces map-match with high confidence without manual fixup.
- Coordinator can answer "which lines run on street X?" in < 30 seconds.
- Full network export (GeoJSON + GTFS) in one click.

## 9. Risks & mitigations

| Risk | Mitigation |
|---|---|
| GPS noise in dense urban canyons breaks matching | Confidence scoring (F11), exclude-and-re-ride workflow, multiple rides per line (F13) |
| OSM coverage gaps on peripheral/unpaved streets | Surface unmatched sections explicitly; contributing fixes back to OSM is the escape hatch |
| Same physical line labeled under different names by different reviewers | Line picker with fuzzy search + destination-sign text; admin merge tool (backlog) |
| Battery savers kill Traccar Client mid-ride → partial traces | Live view (F3) catches dead devices early; partial rides still aggregate (F13) |
| Rider loses/wipes phone before an offline-buffered ride uploads → ride lost | Pending-upload visibility (F4b) + rider guide rule: don't remove the app until coordinator confirms receipt |
| Rider forgets to stop the service → walk home / home location captured | Auto-trim to vehicle-motion window (F7a); out-of-window points excluded from matching and exports |
| One-person ops bus factor | Everything exportable (F21–F23, F25); Postgres dumps in backups |

## 10. Open questions

1. ~~Do we need offline-recorded GPX file upload as a secondary ingestion path (riders without data plans)?~~ **Resolved:** dead zones and zero-credit riders are expected and handled by Traccar Client's offline buffering + Wi-Fi upload (F4a/F4b) — no separate GPX path needed in v1. Revisit only if a rider cohort can't reach Wi-Fi at all.
2. City scope for v1 — one metro area, or multi-city from the start (affects line naming/namespacing)?
3. Should reviewers see rider identities, or only device IDs (privacy)?
4. Is the eventual "large map" digital-only, or is print cartography a first-class output (affects styling/export work in Phase 3)?
