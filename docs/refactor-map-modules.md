# Plan: split tehuacan/map/index.html into shell + ES modules + i18n files

Status: plan v1 · 2026-07-19 · produced by a planning agent from the real file
(2,439 lines), the build script, data-file headers, and deploy docs.
Key deployment fact: the Cloudflare Pages build command is python-only
(06_build_map.py && 12_build_sponsors.py && 09_build_site.py) — the plan keeps
it that way.

## Decision summary
- **No-build native ES modules** (no bundler). ~15 small modules over HTTP/2 are
  noise next to the 584 KB routes.js that already ships unbundled; prod files =
  source files; the Pages pipeline stays python-only with zero new failure modes.
- **Cache busting in pure Python** inside 09_build_site.py: content-hash rename
  of the js/ directory (js-<hash>/ — relative imports need no rewriting; kills
  mid-deploy version skew) + ?v= hashes on styles.css / routes.js / sponsors.js
  / pois.js. Optional _headers: /combis/js-*/* immutable.
- **i18n as modules, not JSON**: js/i18n/es.js and en.js export objects with the
  arrow-function entries intact (count, schedRange, poiLine…); i18n/index.js owns
  LANG detection + t() + static-label application. Both locales stay statically
  imported (~6 KB total, t() stays synchronous).
- **TypeScript: not now.** Plain ESM + JSDoc + ambient types.d.ts checked with
  `bunx typescript tsc -p tehuacan/map --noEmit` (dev/CI only, never in deploy).
  Typing the I18N dictionary shape keeps es/en key- and signature-compatible.
  Real .ts later is mechanical once the split exists (bun build wiring documented).

## Target layout
```
tehuacan/map/
  index.html            # shell: head, <link styles.css>, DOM, 4-line inline theme
                        # bootstrap, classic data <script>s, one <script type=module>
  styles.css
  routes.js sponsors.js pois.js   # UNCHANGED generated script-globals
  js/
    main.js             # entry: import order, boot/deep-link/restore, wiring
    i18n/{es.js,en.js,index.js}
    lib/{time.js,geom.js,geocode.js,track.js}
    data.js             # bridge over bare globals ROUTES/SPONSORS/POIS
    state.js            # state, M, MV, ui{sheet,sheetMode,trip}, BOOT, saveStatus,
                        # favorites, isMobile; documents the mt* localStorage contract
    map.js              # init, layers, paintHover/paintCurrent, hit-test, fitToSelection
    pins.js             # sponsor/poi pins + highlight + counts
    schedules.js        # /api/horarios fetch, SCHEDULES, nextCombiAt, fareParts
    trips.js            # findTrips engine + walk constants (pure)
    sidebar.js planner.js          # desktop panes
    mobile.js trip-mobile.js sheets.js icons.js
    types.d.ts
```

## Migration order (each step ships alone)
1. Extract CSS to styles.css (link AFTER maplibre css) + land the Python
   cache-busting pass — this alone fixes stale routes.js after rebuilds.
2. Move the THEME bootstrap to a 4-line inline <script> in <head> (kills the
   only must-run-early code + the theme flash).
3. Cut all JS verbatim to js/app.js as a CLASSIC script (pure move).
4. Flip app.js to type=module — riskiest step, ship alone (strict mode; globals
   stop leaking; bare ROUTES/… still resolve because classic scripts parse first).
5. Still one file: rewrite SHEET/SHEET_MODE/TRIP to a shared `ui` object and
   DELETE every `typeof X !== 'undefined'` guard (they THROW on imported
   bindings under ESM — the #1 gotcha).
6. Extract leaves: lib/time.js (fmt12 first — i18n depends on it), lib/track.js,
   then i18n/ (es.js, en.js, index.js).
7. Extract pure engines: data.js, lib/geom.js, trips.js, lib/geocode.js.
   (Rename the local `const feats` shadow inside setSponsorPins during the move.)
8. Extract state.js + schedules.js (export let SCHEDULES, loadSchedules(cb)
   inversion) + pins.js.
9. Extract map.js; boot/deep-link tail moves to main.js via onMapReady(cb).
10. Extract desktop: sidebar.js + planner.js.
11. Extract mobile: icons.js, mobile.js, trip-mobile.js, sheets.js; main.js
    shrinks to boot + wiring. Rule for the cyclic trio: no top-level statement
    may CALL into another app module (attaching listeners is fine).
12. Optional dev-only type checking (jsconfig checkJs + types.d.ts).

Verification recipe per step: rebuild via 09_build_site.py, serve, console
clean, full desktop + mobile smoke (search/suggest incl. geocoder rows, select,
detail, planner, trip from-my-location, sheets drag, favorites, ES/EN, theme,
?ruta= and ?embed=1 deep links, mtStatus restore).

## Gotchas ledger (from reading the real code)
1. ROUTES/SPONSORS/POIS are global *lexical* consts — NOT window properties;
   reference bare from data.js. Keep the `typeof POIS` absent-tolerance (safe on
   globals, fatal on imports).
2. typeof-guards on imported bindings throw (TDZ) — remove in step 5, before splitting.
3. Hoisting deps resolved by extraction ORDER: I18N.*.schedRange → fmt12;
   paintCurrent → TRIP; select → saveStatus/setSponsorPins; schedules fetch →
   renderDetail/openSheet (callback inversion).
4. Cross-module mutation: SHEET/SHEET_MODE/TRIP become ui.* properties;
   SCHEDULES is single-writer → live `export let` is fine.
5. Strict-mode flip ships alone; the js_error beacon (/api/evento) is the canary.
6. localStorage contract: mtTheme/mtLang shared with portal+acerca (LANG_JS in
   09_build_site.py); mtLoc/mtFav/mtStatus app-only; mtStatus shape must stay
   byte-compatible.
7. Never conditionally import mobile.js/sidebar.js — isMobile() is per-event;
   a desktop window resized under 700 px must keep working.
8. Don't "clean up" while moving: analytics side effects (sponsor_view on
   render, route_select in two places) are behavior.
9. Shell load order: data files stay classic parse-blocking scripts; module
   entry may sit in <head> (deferred) but never `async`.
10. styles.css link stays render-blocking in head (sheet measuring depends on
    computed CSS at boot).
