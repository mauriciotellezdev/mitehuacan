# MAPPING.md — mapping routes yourself (manager + client)

You ride the combi with **Traccar Client** on your phone; a **Traccar server** on your
Mac collects the traces; an export script drops each ride into the dataset. Cost: $0.

## 1. The manager (Traccar server on your Mac)

Prereqs you already have: colima + docker.

```bash
colima start                                  # once per boot
cd infra/traccar && docker compose up -d      # starts Traccar 6.5
open http://localhost:8082                    # web UI
```

**Already set up (2026-07-14):** admin user **admin@quecombi.local / cambiame-ya**
(→ log in and change the password now: top-right → Account; then
`export TRACCAR_PASSWORD=...` for the export script) and device **`mauricio-1`**
already exist. Ingest was smoke-tested end to end.

Your Mac's LAN address (the phone talks to this): `ipconfig getifaddr en0`
(e.g. `192.168.1.68`). The phone URL is `http://<that-ip>:5055`.

**Keep the Mac awake while flushing rides:** `caffeinate -dims` in a terminal
(or just have the laptop open when you get home).

## 2. The client (your phone)

Install **Traccar Client** (App Store / Play Store). Settings:

| Setting | Value |
|---|---|
| Device identifier | `mauricio-1` |
| Server URL | `http://<mac-ip>:5055` |
| Location accuracy | High |
| Frequency | 10 (seconds) |
| Distance / Angle | 0 / 0 |
| Offline buffering | ON (default) |

Permissions: Location **Always** + Precise (iOS) / **Allow all the time** + battery
**Unrestricted** (Android). Full details + ride protocol: `traccar-rider-guide.md`.

**How it works away from home:** the server is only reachable on your Wi-Fi. That's
fine — the client buffers every point locally during the ride (GPS needs no signal)
and flushes automatically when your phone rejoins home Wi-Fi with the service ON.
Leave the service on for ~5 min at home, watch the device go green in the web UI.

## 3. Ride protocol (click A / click B)

1. Note the route's painted name + where you board.
2. **Service ON at boarding. OFF the moment you step off.** (It records your walk
   home otherwise — and note the exact times, you need them for export.)
3. One ride = one recording. Return trip = second recording.
4. Back home: flush (above), then verify the trace in the web UI
   (Reports → Route, pick device + time window).

## 4. Into the dataset

```bash
python3 tehuacan/scripts/13_traccar_export.py \
  --device mauricio-1 --from "2026-07-15T09:00" --to "2026-07-15T10:20" \
  --slug tecoxteo-coxcatlan-ida
```

It writes `tehuacan/data/geojson/field/<slug>.geojson` and prints the two follow-up
steps (CSV row + rebuild). Use the ride start/end you noted — that's the manual trim.
The script assumes admin/admin; after you change the password, edit `AUTH` in it.

## 5. Priority targets (from field_reports.json)

1. **«Tecoxteo» combis, Coxcatlán corridor** — Tehuacán → Tequexco → San Sebastián
   Zinacatepec → Coxcatlán, both variants (ida + the Ajalpan connector).
2. **San José route** — confirm which San José; note the painted name.
3. **Ruta C family** — one ride settles whether C/C-TEC-21 and the two Valle
   variants are duplicates.
4. **San Isidro extension** — your own combi, Camino a San Isidro ↔ CC El Paseo.

## 6. Live tracking away from home (SET UP AND RUNNING)

The server is exposed to the internet through a free Cloudflare quick tunnel, so the
phone reports **live during the ride** — no home Wi-Fi needed. Before leaving:

```bash
infra/traccar/start-mapping.sh
```

It brings up colima + Traccar, keeps the Mac awake (`caffeinate`), starts the tunnel,
and prints the HTTPS URL for Traccar Client (e.g.
`https://reveals-knife-cabinets-plymouth.trycloudflare.com` — the URL as of
2026-07-14; it is ALREADY configured end-to-end and verified).

**The one gotcha:** quick-tunnel URLs change every time the tunnel restarts — if the
script prints a new URL, update the phone's Server URL before riding. (Offline
buffering still backstops you: worst case the ride uploads when the phone can reach
whatever URL it has.) The permanent fix is a named tunnel `gps.quecombi.mx` once the
domain is on Cloudflare — docs/setup/cloudflare.md §6 — which never changes.
