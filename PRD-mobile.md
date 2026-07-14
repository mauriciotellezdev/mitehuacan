# PRD — Combi mobile app (rider app with passive data collection)

**Status:** Draft v1 · **Owner:** Michael · **Date:** 2026-07-14
**Decision:** Native mobile app (not PWA). Rationale: passive/background telemetry from every user's phone is the core value — each rider becomes a sensor. Web apps cannot do background location on iOS or Android; this capability alone justifies the native build and the store accounts (Apple $99/yr + Google Play $25 once).

## 1. What the app is

One app, two faces:

1. **For the rider (the reason they install it):** find combis and plan trips — the existing web map's Rutas + ¿Cómo llego? features, plus live "where is my combi" once enough riders feed data.
2. **For the project (the reason it exists):** every consenting user passively contributes GPS traces while riding, and one-tap context tags (crowding, comfort, detours). The map stops being 2023 citizen data and becomes continuously self-updating.

## 2. The data flywheel

```
more riders → more traces/tags → fresher routes + real times → better app → more riders
```

Auto-collected (passive, consent required):
- **Ride traces** — GPS while the user is riding a combi (auto-detected, see §4)
- **Times** — boarding/alighting timestamps → real trip durations, wait patterns by hour
- **Detours** — traces diverging from the canonical route geometry → auto-flag route changes (this would have caught the San Isidro gap automatically)

Tap-collected (one prompt per ride, skippable):
- **Crowding:** lleno / cómodo / vacío (full / comfortable / empty)
- Optional free tag: detour reason, fare paid, incident

## 3. Stack

- **React Native + Expo** (dev builds, not Expo Go — background location needs native modules): one codebase, both stores.
- Background location: `expo-location` background updates + Android foreground service; iOS "Always" authorization.
- Activity recognition (walking vs vehicle) for ride detection: iOS CMMotionActivity / Android Activity Recognition API.
- Map: MapLibre React Native (same style + routes.js pipeline as the web map).
- Backend: same server as the PRD.md web app — add `/api/traces`, `/api/tags` ingest endpoints; traces enter the existing Traccar-style pipeline (trim → map-match → aggregate).
- Offline-first: queue traces/tags in SQLite on device, sync on connectivity (dead zones and no-credit riders are the norm — same lesson as Traccar).

## 4. Auto-collection design (the hard part)

Battery and permissions kill naive implementations. Design:

- **Armed, not always-on:** low-power geofences around route corridors + activity recognition. GPS at full rate ONLY when (in vehicle motion) AND (near a known route). City-scale geofencing keeps idle drain near zero.
- **Ride detection:** vehicle motion sustained >90s near a route corridor → start trace; stationary/walking >3 min → end trace, prompt once for crowding tag.
- **Auto-trim on device** (same logic as PRD.md F7a): only the vehicle-motion window is uploaded. Walking to/from the stop never leaves the phone.
- **Data minimization:** no accounts required; anonymous device ID rotated monthly; traces uploaded without any user identifier linkage beyond the rotating ID; home/work endpoints fuzzed (drop first/last 100 m of every trace server-side).

## 5. App Store reality check (plan for review friction)

- iOS "Always" location triggers manual App Review scrutiny: need an in-app purpose screen BEFORE the OS permission prompt, a visible indicator while collecting, an easy pause/opt-out, and a privacy policy URL. Contribution must be genuinely optional — the route planner must work with "While Using" or no location at all.
- Android: `ACCESS_BACKGROUND_LOCATION` requires a Play Console declaration + demo video of the consent flow.
- Both stores require a privacy policy and data-deletion path. Budget 1–2 rejection cycles; this category (passive location) is the most-reviewed thing there is.

## 6. Phasing

1. **v0 (TestFlight/internal, ~100 testers on Apple individual account):** map + planner (port of web map) + manual ride recording button (press when boarding — replaces Traccar Client for our own riders) + crowding tag prompt.
2. **v1 (public stores):** auto ride detection + passive traces + consent/privacy flow done properly.
3. **v2:** live layer — recent-trace freshness on the map, "combi passed here N min ago", detour alerts from trace divergence; push notifications.

## 7. Costs

| Item | Cost |
|---|---|
| Apple Developer Program | $99/yr (waivable only via university/nonprofit/gov enrollment — see partnership note) |
| Google Play Console | $25 once |
| Server (same VPS as web/Traccar) | ~$5–10/mo, no change |
| Geocoding/tiles | $0 (Photon/Nominatim + OpenFreeMap, same as web) |

## 8. Open questions

1. Anonymous vs optional accounts (accounts enable contributor stats/gamification — "you mapped 45 km this month" — which drives retention, but raise the privacy bar).
2. Incentives for tagging: gamification only, or partner perks (e.g., local business coupons — the rutastehuacan advertiser-pin model suggests local businesses already pay for combi-adjacent visibility)?
3. Publish under personal account ($99) now, or pursue university/civic partnership (fee waiver + credibility + student riders) first? These aren't exclusive — start personal, transfer the app later.
4. Does v0 fully replace Traccar Client for recruited riders, or run both until auto-detection is proven?
