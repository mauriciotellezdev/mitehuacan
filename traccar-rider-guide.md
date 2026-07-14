# Combi Route Tracker — Rider Guide (Traccar Client)

This guide explains how to install and use the **Traccar Client** app to record the route of a combi ride. The app runs in the background and sends your position to our server — you start it before boarding, put the phone away, and stop it when you get off. That's it.

> **Before you ride, you need two things from the coordinator:**
> 1. The **server URL** (looks like `http://tracker.example.com:5055`)
> 2. Your assigned **device identifier** (e.g. `combi-07`)

---

## iPhone (iOS)

### 1. Install

- Open the **App Store**.
- Search for **"Traccar Client"** (publisher: Traccar).
- Install it — it's free, no account or sign-up needed.

### 2. Configure (one time only)

Open the app and set:

| Setting | Value |
|---|---|
| **Device identifier** | The ID you were given (e.g. `combi-07`) |
| **Server URL** | The URL you were given |
| **Location accuracy** | **High** |
| **Frequency** | **10** (seconds) |
| **Distance** | 0 |
| **Angle** | 0 |

### 3. Grant permissions

When the app asks for location access:

- Choose **"Allow While Using App"** first if that's the only option, then go to **Settings → Privacy & Security → Location Services → Traccar Client** and change it to **"Always"**.
- Make sure **Precise Location** is **ON**.

Without "Always" + "Precise", the trace will have gaps and the ride is wasted — please double-check this.

### 4. Before boarding

- **Turn OFF Low Power Mode** (Settings → Battery). Low Power Mode throttles GPS.
- Make sure the phone is charged (a 1–2 hour ride uses roughly 10–20% battery).
- In the app, flip the **Service status** switch to **ON**. The status line should start showing "location update" messages.

### 5. During the ride

- Lock the screen and put the phone away. Tracking continues in the background.
- Don't force-quit the app (don't swipe it away in the app switcher).
- If you have no signal for part of the ride, that's fine — the app queues positions and sends them when coverage returns.

### 6. After the ride

- Flip **Service status** back to **OFF** the moment you step off the combi — this marks the end of the ride, and the app records everything (including your walk home) until you do. If you had no signal during the ride, your recording is saved on the phone — see "No signal or no credit?" below for how to upload it.
- Message the coordinator: your device ID, the combi line/destination sign, where you boarded, and where you got off.

---

## Android

### 1. Install

- Open the **Play Store**.
- Search for **"Traccar Client"** (publisher: Traccar).
- Install it — free, no account needed.

### 2. Configure (one time only)

Open the app and set:

| Setting | Value |
|---|---|
| **Device identifier** | The ID you were given (e.g. `combi-07`) |
| **Server URL** | The URL you were given |
| **Location accuracy** | **High** |
| **Frequency** | **10** (seconds) |
| **Distance** | 0 |
| **Angle** | 0 |

### 3. Grant permissions

- When asked for location access, choose **"While using the app"**, then when prompted (or via **Settings → Apps → Traccar Client → Permissions → Location**) upgrade it to **"Allow all the time"**.
- **Disable battery optimization** for the app: Settings → Apps → Traccar Client → Battery → **Unrestricted** (wording varies by phone brand). On Xiaomi/Huawei/Oppo phones this step is *critical* — their aggressive battery savers will silently kill the app mid-ride otherwise.

### 4. Before boarding

- Turn off **Battery Saver** mode.
- Make sure the phone is charged.
- In the app, switch **Service status** to **ON**. You should see a persistent notification saying the tracking service is running — leave that notification alone.

### 5. During the ride

- Lock the screen and put the phone away.
- Don't swipe the app away from recents, and don't dismiss the tracking notification.
- No signal for a stretch is fine — positions are queued and sent later.

### 6. After the ride

- Switch **Service status** to **OFF** the moment you step off the combi — this marks the end of the ride, and the app records everything (including your walk home) until you do. If you had no signal during the ride, your recording is saved on the phone — see "No signal or no credit?" below for how to upload it.
- Message the coordinator: your device ID, the combi line/destination sign, boarding point, and exit point.

---

## No signal or no credit? Read this (both platforms)

GPS works without any cell signal — the app keeps recording your full route through dead zones and even with **zero data credit**. Positions are saved on the phone and uploaded automatically when a connection comes back. Your job doesn't change: **service ON when you board, OFF when you get off** — the recording is safe on the phone even with the service off.

To upload a stored ride later:

- Get on any Wi-Fi (home, café, OXXO), open the app, and flip the **service ON for about 5 minutes** — the stored ride uploads automatically. Then flip it OFF again. (It will record a few points wherever you are during those minutes; that's expected and gets discarded on our side.)
- **Do not** uninstall the app, clear its data, or reset the phone until the coordinator confirms the ride arrived — until it uploads, **your phone holds the only copy**.
- If you know in advance you'll have no data, that's fine — ride as normal and do the Wi-Fi upload at the end of the day.

---

## Tips for a clean trace (both platforms)

- **Start the app *before* boarding**, ideally a minute early while standing at the stop — the first GPS fix is the slowest.
- **One ride = one recording.** Stop the service when you get off; if you ride back on the return route, that's a second recording (tell the coordinator it's the return direction).
- Sit **away from the floor/engine** if you can; a window seat gives better GPS.
- Ride the line **end to end** when possible — partial rides are still useful, but say so.
- If the app shows errors or the status log stops updating, note the time and tell the coordinator — the trace may still be partially usable.

---

## Coordinator pre-flight checklist

Before sending anyone out:

- [ ] Server is up and reachable at the URL you're handing out (test from a phone on mobile data, not just Wi-Fi).
- [ ] Each rider has a **unique device identifier** — duplicates merge two people's traces into garbage.
- [ ] Do a walk test with each phone: start the service, walk a block, confirm the device appears and moves on the Traccar web dashboard.
- [ ] Confirm **offline buffering** is enabled in each phone's Traccar Client settings (it's the default — just don't let anyone turn it off).
- [ ] Log each ride: device ID, rider, combi line name/sign, direction, date, boarding and exit points. You'll need this to label the traces when building the map.
- [ ] **A ride isn't done until its data is on the server.** Riders in dead zones or without credit will upload late (possibly hours later, over Wi-Fi) — check the trace arrived and spans the whole ride before confirming receipt to the rider. Until then, their phone holds the only copy.

---

## Guía rápida (español)

1. Instala **"Traccar Client"** desde la App Store (iPhone) o Play Store (Android). Es gratis.
2. En la app, escribe el **identificador** y la **URL del servidor** que te dieron. Pon precisión **alta** y frecuencia **10** segundos.
3. Permisos de ubicación: **"Siempre"** (iPhone: también activa **Ubicación precisa**; Android: también pon la batería en **"Sin restricciones"** para la app).
4. Desactiva el modo de **ahorro de batería** antes del viaje.
5. **Antes de subir** a la combi, activa el interruptor de **estado del servicio**. Guarda el teléfono; puedes bloquear la pantalla, pero **no cierres la app**.
6. **Al bajar de la combi, apaga el interruptor de inmediato** — si lo dejas encendido, la app también graba tu caminata a casa. Avisa al coordinador: tu identificador, la ruta de la combi, dónde subiste y dónde bajaste.
7. **¿Sin señal o sin saldo?** No pasa nada: el GPS funciona sin señal y el recorrido queda guardado en el teléfono. Después, conéctate a cualquier Wi-Fi, abre la app y **enciende el servicio unos 5 minutos** para que suba los datos; luego apágalo. **No borres la app** hasta que el coordinador confirme que llegó tu recorrido.
