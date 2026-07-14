/**
 * /api/gps — publicly hosted GPS ingest speaking Traccar Client's (osmand) protocol.
 * Phone config: Server URL = https://<site>/api/gps · identifier must be in the
 * GPS_DEVICES env allowlist (comma-separated) — unknown devices are rejected so
 * strangers can't poison the data (SECURITY.md §5).
 *
 * Traccar Client sends GET or POST with query/form params:
 *   id, timestamp (unix s or ISO), lat, lon, speed, bearing, altitude, accuracy, batt
 */
export async function onRequest({ request, env }) {
  if (request.method !== "GET" && request.method !== "POST") {
    return new Response(null, { status: 405 });
  }
  const url = new URL(request.url);
  let p = url.searchParams;
  if (request.method === "POST" && ![...p.keys()].length) {
    try { p = new URLSearchParams(await request.text()); } catch { /* keep query */ }
  }

  const device = (p.get("id") || "").slice(0, 40);
  const allowed = (env.GPS_DEVICES || "").split(",").map(s => s.trim()).filter(Boolean);
  if (!device || !allowed.includes(device)) return new Response(null, { status: 403 });

  const lat = parseFloat(p.get("lat")), lon = parseFloat(p.get("lon"));
  // sanity: inside Mexico, plausible values only
  if (!isFinite(lat) || !isFinite(lon) || lat < 14 || lat > 33 || lon < -118 || lon > -86) {
    return new Response(null, { status: 400 });
  }
  const speed = parseFloat(p.get("speed"));
  if (isFinite(speed) && speed > 120) return new Response(null, { status: 400 });

  let ts = p.get("timestamp") || "";
  if (/^\d+$/.test(ts)) ts = new Date(parseInt(ts, 10) * 1000).toISOString();
  else if (ts) ts = new Date(ts).toISOString();
  else ts = new Date().toISOString();

  const num = k => { const v = parseFloat(p.get(k)); return isFinite(v) ? v : null; };
  await env.DB.prepare(
    `INSERT INTO positions (device, fix_ts, lat, lon, speed, bearing, altitude, accuracy, batt)
     VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)`
  ).bind(device, ts, lat, lon,
         isFinite(speed) ? speed : null, num("bearing"), num("altitude"),
         num("accuracy"), num("batt")).run();

  return new Response("OK", { status: 200 });
}
