# PRD — Phase 2: Sponsorship revenue

**Status:** Written down 2026-07-14 (build after launch traction) · **Owner:** project owner

## 1. Model

QueCombi stays free for riders forever. Revenue comes from **local business sponsorships**:

- **Monthly subscription** (recurring sponsor) or **one-time support donation**.
- A sponsor gets their **logo shown on route views** — only when a specific route is
  displayed (selected route / route deep-link / planner result legs), **never on the
  full network map**. The unit of inventory is a *route*, not the map.
- Sponsors can give us their **locations** (branches/stores); we show their pins on
  the routes that pass near those locations ("your logo on every route that passes
  your door"). Route↔location matching reuses the existing places/proximity pipeline.

**Validation that this works:** the original rutastehuacan maps carried paid business
pins (the "Tacos Genaro" pins on all 52 maps) — local businesses already pay for
combi-map visibility in this exact city.

## 2. Pricing strategy

- **Start intentionally cheap** ("get it lived in"): low flat monthly price per route
  sponsorship so early businesses say yes and the map looks alive with local brands.
- **Price rises with sell-through**: as inventory fills (X% of routes sponsored),
  new sponsorships cost more; renewals keep their old price for loyalty. Publish no
  rate card at first — quote per lead while calibrating.
- One-time donations: any amount, logo shown for a fixed period proportional to amount.

## 3. Seeding (day one)

Seed the sponsor slots with 1–2 **aspirational house placeholders we don't expect to
close** (e.g., OXXO, a national bank) so the surface never launches empty and small
businesses see the format next to big brands. These seeds show **whenever any route is
shown** (they have locations everywhere), clearly rendered in the same "Patrocinador"
format. Rule: replace a seed with a paying sponsor the moment one signs; seeds are
marked internally as `seed` status and are never invoiced.
*Note: showing a brand's logo unpaid is a courtesy/aspiration play — if any brand
objects, remove immediately; never imply endorsement in copy.*

## 4. Product surfaces

1. **Route view sponsor slot** (map detail panel + planner option legs): small
   "Patrocinador:" row with logo + name; tap → sponsor's locations highlighted as pins
   along that route. Never obscures route info; max 1–2 sponsors per route view.
2. **Sponsor pins**: the sponsor's given locations rendered on the selected route only.
3. **/system/ads** (token-gated, same auth as /system): lead + inventory management —
   - leads table: business, contact, notes, **status pipeline:**
     `lead → contacted → negotiating → active_sub | donor → churned` (+ `seed`).
   - `active_sub`/`donor` status is the switch: logo starts showing on their routes.
   - fields: plan (monthly/one-time), amount, start/end, routes[] or locations[],
     logo asset path.
4. **Logo "CDN"**: simple by design — logo files live in the repo under
   `site/patrocinadores/<sponsor-id>.png` (Cloudflare Pages *is* the CDN); adding a
   sponsor = drop file + set status. Sponsor config served from D1 via `/api/sponsors`
   (cached, public, contains only active sponsors' display data).

## 5. Data model (D1, when built)

```
sponsors(id, name, status, plan, amount_mxn, start_date, end_date,
         logo_path, contact, notes, created_at)
sponsor_locations(sponsor_id, name, lon, lat)        -- their branches
sponsor_routes(sponsor_id, route_key)                 -- computed from locations (or manual)
```

`/api/sponsors` → `{route_key: [{name, logo, locations[]}]}` for active only.
Analytics tie-in: `track('sponsor_view'|'sponsor_tap', sponsor_id)` gives sponsors a
simple monthly report (views/taps) — our retention tool.

## 6. Guardrails

- Sponsors never influence route data, ordering, or planner results. Ads are labeled
  "Patrocinador". No sponsor tracking scripts — impressions/taps come from our own
  first-party events only. Riders' data is never shared with sponsors (SECURITY.md).
- Revenue funds: store fees ($99+$25), server tier upgrades, stickers, field days.

## 7. Build order (when Phase 2 starts)

1. `migrations/0004_sponsors.sql` + `/api/sponsors` + seed rows (OXXO/bank placeholders).
2. Map UI: sponsor row in route detail + planner legs; pins layer; `sponsor_*` events.
3. `/system/ads`: CRUD over sponsors + status pipeline (reuse /system auth + shell).
4. Logo workflow doc: resize → `site/patrocinadores/` → commit → set status.
