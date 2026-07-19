# PRD — Backoffice / Operations System ("el sistema")

Status: spec v1 · 2026-07-19
Owner: Mike · Builds on: `/system` (dashboard), `/system/map` (route editor), `/system/combis` (line manager), D1 `quecombi`, `/qr/*` redirect + scan tracking, `sponsors.js` build pipeline.

The public map is only as good as the operation behind it. This spec defines the
tooling for the three crews that keep MiTehuacán alive:

| Crew | Job to be done | Today's pain |
|---|---|---|
| **Mapeadores** | Record rides, turn GPS into routes, create/prune/fix routes and their info | Editor exists but publishing is a laptop-and-scripts ritual; no lifecycle, no route retirement, citizen reports rot in a table |
| **Instaladores** | Put our QR stickers on the inside top of combis, keep them alive | No sticker inventory, no install log, no way to know which stickers are dead |
| **Gestión de patrocinios** | Place sponsor placards (with our QR) at sponsor locations; sponsors "pay" by displaying our placard — later with $$ | Sponsors are a hand-edited seed file; no locations workflow, no verification, no attribution of scans, no path to billing |

Principles (unchanged from the system design): **Tier 0 architecture** — Cloudflare
Pages Functions + D1, no servers; **phones first** — every field flow must work
one-handed on a phone with patchy data; **location data is radioactive** —
SECURITY.md rules apply to every new table; **provenance everywhere** — every row
knows who touched it and when; **the public site consumes only published state.**

---

## 0. Architecture at a glance

```
                       field phones                        laptop/admin
                 ┌───────────┬───────────┐                ┌───────────┐
                 │ Traccar   │ /system/* │                │ /system/* │
                 │ Client    │ (PWA-ish) │                │           │
                 └─────┬─────┴─────┬─────┘                └─────┬─────┘
                       │           │      Bearer token (per-role)│
                       ▼           ▼                            ▼
   Cloudflare Pages Functions:  /api/gps  /api/lineas  /api/stickers  /api/sponsors …
                       │
                       ▼
                     D1 (quecombi): positions · route_drafts · combi_lines · reports
                                    devices · stickers · sponsors · sponsor_locations · audit
                       │
        publish step   ▼
   routes.js / pois.js (build-time, git)   ·   /api/horarios /api/sponsor-pins (live, cached)
                       │
                       ▼
                public map (mitehuacan.mx/combis)
```

### 0.1 Deployment split (constraint from Mike, 2026-07-19)

The backoffice **UI runs on a different network** than the public app — it is
NOT served from the same code/server as the frontend. Consequences baked into
this spec:

- **The APIs stay where the data is.** All `/api/*` admin endpoints remain
  Pages Functions on the main project (that's where the D1 binding lives).
  The backoffice UI is a **separate static deployment** (its own Pages project,
  a laptop, an office intranet box — anywhere) that calls
  `https://mitehuacan.mx/api/...` cross-origin.
- **CORS, explicitly:** admin endpoints answer `OPTIONS` and set
  `Access-Control-Allow-Origin` from an `ADMIN_ORIGINS` env allowlist (comma
  separated; e.g. the backoffice host + `http://localhost:*` for dev), plus
  `Access-Control-Allow-Headers: Authorization, Content-Type`. Public read
  endpoints (`/api/horarios`, `/api/sponsor-pins`) stay same-origin-only — the
  map is served from the main site.
- **Auth is header-only across origins.** The legacy `?token=` query-param
  fallback is removed from admin endpoints (tokens in URLs leak into logs and
  referers; unacceptable cross-network). `Authorization: Bearer` only.
- **The current `/system/*` pages become the seed of the separate app.** They
  are already static HTML calling APIs with a bearer token, so the migration is
  mechanical: move them to `backoffice/` (own mini-project, own deploy), point
  them at the production API base URL (configurable `API_BASE`), delete them
  from the public project once the crews have switched. Interim: they keep
  working on the main site during the transition.
- **Rate limiting / abuse:** admin endpoints get a simple per-IP request cap
  (D1-free, in-memory per isolate is fine as a tripwire) since they're now
  reachable cross-origin; real protection remains the tokens.

Two publication lanes, deliberately:
- **Geometry lane (build-time, git-reviewed):** route shapes change rarely and
  deserve review — drafts → import script → `routes.js` → deploy. Git is the audit log.
- **Metadata lane (live, edge-cached):** schedules, fares, sponsor pins, sticker
  status change often and are low-risk — D1 → public API with `max-age=300`.

---

## 1. Auth & roles

**Phase 1 (build now):** per-role bearer tokens, all set as Pages secrets:

| Secret | Role | Can |
|---|---|---|
| `STATS_TOKEN` | admin | everything (existing behavior, unchanged) |
| `TOKEN_MAPEO` | mapeador | route drafts, lines, devices, reports triage |
| `TOKEN_CAMPO` | instalador | stickers module only |
| `TOKEN_PATROCINIO` | patrocinios | sponsors module only |

One shared `auth(request, env, ...roles)` helper replaces the copy-pasted
`auth()` in every function; it returns the matched role, and every write handler
records that role in the audit table. Tokens are entered once per phone and kept
in `localStorage` (same UX as today's `/system`).

**Phase 2:** magic-link accounts (email → signed cookie) with per-user names in
the audit log, so "who installed this sticker" is a person, not a token. Not
needed to launch the crews.

**Audit table (phase 1, cheap and universal):**
```sql
CREATE TABLE audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL DEFAULT (datetime('now')),
  role TEXT NOT NULL,            -- which token did it
  action TEXT NOT NULL,          -- e.g. sticker.install, line.update, draft.attach
  entity TEXT,                   -- e.g. stickers:TEH-0042
  detail TEXT                    -- small JSON blob of the change
);
```
Every write endpoint inserts one row. `/system` gets a "Bitácora" table (last 200).

---

## 2. Rutas — the mapeador module

### 2.1 What exists (keep)
- `/api/gps` OsmAnd ingest with `GPS_DEVICES` allowlist → `positions`.
- `/system/map` editor: load a device+time window, trim, Douglas-Peucker
  simplify, OSRM street-align, name it, save to `route_drafts`.
- `/system/combis`: lines with schedule/fare, drafts attach/detach.
- `tehuacan/scripts/14_import_drafts.py`: drafts → dataset.
- `reports` table fed by the public "reporta una ruta" form.

### 2.2 Gaps to close

**a) Route lifecycle.** Published routes currently have no states. Add
`route_status` (D1) keyed by route id — the geometry stays in git, the *status*
is metadata:
```sql
CREATE TABLE route_status (
  route_id TEXT PRIMARY KEY,     -- routes.js properties.id
  status TEXT NOT NULL DEFAULT 'published',  -- published | review | retired
  reason TEXT,                   -- why retired/review ("dejó de operar 2026-05")
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```
- `retired` routes: hidden from the public map (the map fetches `/api/horarios`
  which will carry status; retired ids get filtered client-side) without waiting
  for a rebuild. Next dataset rebuild removes them from `routes.js` for real.
- `review` routes: shown with the existing "variantes sin conciliar" warning.
- UI: status selector + reason on each line in `/system/combis` (one more field
  in the line panel — the line IS the route's admin home).

**b) Pruning & merging drafts.** The drafts inbox gets three more actions
(all in `/system/combis`, `/api/route-drafts` grows PATCH verbs):
- **descartar** (status `discarded`, kept 30 days then purged) — bad recordings.
- **reemplazar geometría**: mark a draft as the *replacement* for a published
  route (`replaces = route_id`). The import script consumes these first: same id,
  new geometry, one diff to review.
- **variante de**: attach as a named variant (`variant_of = route_id`) so the
  dataset build can emit `-a`/`-b` variants instead of a new top-level route.

**c) Reports triage — close the citizen loop.** New `/system/reportes`:
list of `reports` rows with status buttons (`new → reviewing → mapped | rejected`),
assignment note, and a "crear línea desde reporte" shortcut that pre-fills a new
line (name = reported name, notes = description). KPI on `/system`: reports
older than 14 days in `new`.

**d) Devices.** Replace the `GPS_DEVICES` env allowlist with a table so field
phones can be added without a deploy:
```sql
CREATE TABLE devices (
  device TEXT PRIMARY KEY,       -- osmand id
  label TEXT,                    -- "tel. de Rafa"
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  last_seen TEXT                 -- updated by /api/gps on every accepted fix
);
```
`/api/gps` checks the table (env stays as emergency fallback). `/system` shows
device health (last_seen, fixes today) — a mapper knows their phone is
recording before they ride for an hour.

**e) Positions hygiene.** Nightly-equivalent (on-demand button, phase 1):
purge `positions` older than 90 days that belong to imported drafts. Raw GPS is
the most sensitive data we hold; it should not accumulate.

### 2.3 Mapeador day-in-the-life (target)
1. Phone: Traccar on, ride the route. `/system` shows the device going green.
2. Same phone or laptop: `/system/map` → load today's window → trim/simplify/
   align → save draft (auto-suggests `replaces` if geometry overlaps an existing
   route ≥70%).
3. `/system/combis`: attach draft to its line (or create the line), set
   schedule/fare while it's fresh — the driver just told you.
4. Admin reviews drafts weekly: runs `14_import_drafts.py`, eyeballs the git
   diff, rebuild + deploy. Drafts flip to `imported`, statuses reconcile.

---

## 3. Stickers — the instalador module

The sticker on the combi ceiling is the product's #1 acquisition channel, and
scan data already flows: `/qr/<id>` → 302 → `hits.qr`. What's missing is the
inventory and lifecycle around the physical object.

### 3.1 Data model
```sql
CREATE TABLE stickers (
  id TEXT PRIMARY KEY,           -- printed code, e.g. TEH-0042 (short, human-radioable)
  batch TEXT NOT NULL,           -- print batch, e.g. 2026-07-A
  status TEXT NOT NULL DEFAULT 'printed',
                                 -- printed | installed | verified | dead | retired
  route_id TEXT,                 -- line it was installed on (nullable until installed)
  unit_desc TEXT,                -- free text: "combi blanca, placa SXY-123-A" (NO photos of people)
  installed_by TEXT,             -- role/name from audit
  installed_at TEXT,
  last_scan TEXT,                -- denormalized from hits for cheap dashboards
  scans_30d INTEGER DEFAULT 0,   -- refreshed by the stats endpoint
  notes TEXT,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```
Sticker IDs are pre-printed; the table is seeded when a batch is generated.

### 3.2 Flows
- **Generate batch** (admin, `/system/stickers`): "crear lote de 100" → inserts
  TEH-0101…TEH-0200 with `batch`, and produces a **print sheet**: an HTML page
  (print-to-PDF) of QR codes pointing at `https://mitehuacan.mx/qr/TEH-0142`,
  each with the id printed under it, sized for the sticker die-cut. QR SVGs are
  generated client-side (tiny QR lib vendored, no external service).
- **Install** (instalador, phone): `/system/stickers` mobile view →
  "instalar" → type/scan the sticker id → pick the route (searchable list from
  routes.js) → optional unit description → save. Two taps and a text field.
  Status → `installed`, audit row written.
- **Verify** (automatic): first scan recorded via `hits.qr` flips `installed →
  verified` (the endpoint that computes stats does the flip). A sticker that a
  real rider scanned is proof of install — no photo bureaucracy needed.
- **Dead sticker detection** (automatic): `verified` stickers with zero scans in
  30 days → `dead` list on the dashboard. Combis get repainted, stickers get
  sun-bleached, units change routes — this is the re-visit worklist.
- **Retire**: sticker removed/replaced → `retired` with note; id is never reused.

### 3.3 Endpoints
```
GET  /api/stickers            admin/instalador: list + filters (status, batch, route)
POST /api/stickers/batch      admin: {prefix, count, batch} → seeded rows
POST /api/stickers/install    instalador: {id, route_id, unit_desc?, notes?}
POST /api/stickers/status     admin/instalador: {id, status, notes?}   (retire/dead override)
GET  /api/stickers/stats      admin: joins hits.qr — per-sticker scans 7/30d, last_scan;
                              refreshes last_scan/scans_30d; flips installed→verified
```
Public side: nothing new — `/qr/*` already tracks. (Per-sticker deep links to a
route later: sticker knows its route, so `/qr/TEH-0142` can eventually 302 to
`/combis/?ruta=<route>&qr=TEH-0142` — one-line change in `_redirects`
replaced by a tiny function reading the stickers table.)

### 3.4 Instalador day-in-the-life
Board combi at the terminal → ask driver (script provided in the field guide) →
peel, stick inside top → open `/system/stickers` on phone → instalar → id,
route, "combi gris placa XYZ" → save → next combi. Dashboard shows their count
for the day. If a sticker dies later, it shows up on the revisit list with the
unit description they wrote.

---

## 4. Patrocinadores — the sponsor module

Model: a sponsor's *locations* appear as pins on the routes that pass them.
Payment phase 1 is **barter**: the sponsor displays our placard (with a QR that
markets the map) in their store. Phase 2 is money. The system must make the
barter measurable — placard scans — so the $$ conversation has numbers.

### 4.1 Data model (replaces the hand-edited `sponsors.js` seed)
```sql
CREATE TABLE sponsors (
  slug TEXT PRIMARY KEY,          -- oxxo
  name TEXT NOT NULL,
  logo_path TEXT,                 -- served from site assets (checked into git for now)
  tier TEXT NOT NULL DEFAULT 'barter',   -- barter | paid | suspended
  contact TEXT,                   -- name/phone/email, free text
  notes TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE sponsor_locations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sponsor_slug TEXT NOT NULL REFERENCES sponsors(slug),
  label TEXT,                     -- "1 Oriente", "sucursal centro"
  lat REAL NOT NULL, lon REAL NOT NULL,
  placard TEXT,                   -- our placard QR id, e.g. P-0007 (nullable = no placard yet)
  placard_status TEXT NOT NULL DEFAULT 'pending',
                                  -- pending | placed | verified | removed
  placed_at TEXT, placed_by TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```
Placards are stickers with a different prefix (`P-…`) living in the same
`stickers` table machinery? **No** — placards attach to *locations*, stickers to
*combis*; different lifecycles, keep tables separate but reuse the same QR print
sheet generator and the same `hits.qr` attribution (placard ids resolve via
`/qr/P-0007` like any sticker — scans at the store measure the barter value).

### 4.2 Route matching = code that already exists
`12_build_sponsors.py` matches locations to routes. Move that logic into the
publish endpoint: `GET /api/sponsor-pins` (public, `max-age=300`) returns
`{sponsors, by_route}` in exactly the shape the map already consumes from
`sponsors.js` — the map swaps a `<script src>` for a fetch (graceful fallback to
the checked-in file). Matching runs server-side on save (cheap: N locations × 78
routes, precomputed into a `by_route` JSON column or recomputed on read — start
with recompute-on-read + edge cache; optimize never).

### 4.3 Flows
- **Alta de patrocinador** (patrocinios): create sponsor, add locations by
  dropping a pin on a mini-map (reuse the editor's map) or pasting coords; label it.
- **Placard placement**: generate placard QR (print sheet), visit the store,
  place it, mark `placed`. First `hits.qr` scan of that placard id →
  `verified` (same auto-verification as stickers).
- **Publication rules** (enforced in `/api/sponsor-pins`): a location's pin
  appears on the public map ONLY while `sponsors.active AND sponsor.tier !=
  'suspended' AND location.active AND placard_status IN ('placed','verified')`.
  The barter is literal: no placard on their wall, no pin on our map.
- **Suspend/remove**: one toggle; pins disappear within the cache TTL (≤5 min).
- **Phase 2 ($$)**: `tier='paid'` bypasses the placard requirement; add
  `billing` table (sponsor_slug, period, amount_mxn, status) with manual
  invoicing first. Pricing input: the dashboard already counts `sponsor_view`
  events per route (map detail views) and placard scans — that's the rate card.

### 4.4 Dashboard additions (`/system`)
- Placards: pending / placed / verified counts; verified-but-zero-scans-30d list.
- Per sponsor: locations, routes covered, map views (`events.sponsor_view`),
  placard scans. This table IS the sales deck for converting barter → paid.

---

## 5. `/system` hub restructure

`/system` becomes a hub with role-aware sections (client-side: sections light up
for whichever token validates):

```
/system            hub: KPIs + bitácora + links
/system/map        route editor            (exists, mapeador)
/system/combis     lines: schedule/fare/drafts/status  (exists + status field)
/system/reportes   citizen reports triage  (new, mapeador)
/system/stickers   inventory + install + print sheets  (new, instalador)
/system/patrocinios sponsors + locations + placards    (new, patrocinios)
```
All pages: same nocturne-admin styling as today, `noindex`, token gate,
phone-first layouts for stickers/patrocinios (those crews are standing in a
combi/store, not at a desk).

KPI strip on the hub: routes published/review/retired · drafts pending ·
reports new>14d · stickers installed/verified/dead · placards pending/verified ·
scans 7d (stickers vs placards) · DAU (existing).

---

## 6. Public-side touchpoints (small, deliberate)

- Map fetches `/api/sponsor-pins` (replaces static sponsors.js) and filters
  retired routes via status carried on `/api/horarios`.
- `/qr/<id>`: function replaces the blanket redirect — sticker ids deep-link to
  their route (`?ruta=`), placard ids link to the map home; both keep `?qr=` so
  `hits.qr` attribution is unchanged.
- Nothing else. Riders never see the backoffice.

---

## 7. Build order (each step ships alone)

1. **Migration 0011**: `audit`, `route_status`, `devices`, `stickers`,
   `sponsors`, `sponsor_locations`. Shared `lib` auth helper + role tokens.
2. **Stickers module** (`/api/stickers*`, `/system/stickers`, print sheet,
   auto-verify + dead detection in stats). Highest leverage: the crew can start
   the same week, scans already tracked.
3. **Sponsors module** (`/api/sponsors*`, `/api/sponsor-pins`, `/system/patrocinios`,
   map switches to live pins). Seeds migrated from sponsors.js (OXXO).
4. **Route lifecycle + reports triage + devices table** (spread across
   `/system/combis`, new `/system/reportes`, `/api/gps` change).
5. **QR function** (per-id deep links) once stickers table has real rows.
6. Phase 2 backlog: magic-link users, R2 for photos, billing table, positions
   auto-purge cron, draft-overlap auto-suggest.

## 8. Non-goals (v1)
- Photos in field flows (R2 + upload UX later; text descriptions suffice).
- Automated payments/invoicing (manual, phase 2).
- Real-time vehicle tracking for riders (different product).
- Per-user accounts (role tokens first).

## 9. Open questions for Mike
1. Sticker id format: `TEH-0042` proposed — short enough to read out loud in a
   moving combi. OK?
2. Who prints? Batch print sheet assumes local print shop; die-cut size needed
   for the QR layout (default 7×7 cm proposed).
3. Placard design: same QR sheet generator, A5 placard with brand + "¿En qué
   combi me voy?" copy — separate design task, spec assumes it exists.
4. Barter enforcement: OK that pins drop automatically when a placard is
   removed/never verified? (Spec says yes — it's the whole deal.)
5. Retired-route grace: hide immediately (spec) or show grayed for 2 weeks with
   "esta ruta dejó de operar"?
