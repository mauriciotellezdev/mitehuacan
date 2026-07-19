/**
 * /api/horarios — per-route service window + headway (route_schedules table).
 * GET is public (the map shows it in the route detail); writes are token-gated
 * (STATS_TOKEN) like everything under /system. GET with ?token= also serves as
 * the /system/horarios login probe: an invalid token 401s instead of degrading.
 */
function auth(request, env) {
  const url = new URL(request.url);
  const token = url.searchParams.get("token") || (request.headers.get("Authorization") || "").replace("Bearer ", "");
  return env.STATS_TOKEN && token === env.STATS_TOKEN;
}
const json = (obj, status = 200, cache = "no-store") =>
  new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json", "Cache-Control": cache } });

const TIME_RE = /^([01]?\d|2[0-3]):[0-5]\d$/;

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const hasToken = url.searchParams.get("token") || request.headers.get("Authorization");
  if (hasToken && !auth(request, env)) return json({ error: "unauthorized" }, 401);
  const { results } = await env.DB.prepare(
    "SELECT route_id, first_run, last_run, headway_min, notes, updated_at FROM route_schedules").all();
  const schedules = {};
  for (const r of results) {
    schedules[r.route_id] = { first_run: r.first_run, last_run: r.last_run, headway_min: r.headway_min,
                              notes: r.notes, updated_at: r.updated_at };
  }
  // public reads cache 5 min at the edge; admin (token) reads stay fresh
  return json({ schedules }, 200, hasToken ? "no-store" : "public, max-age=300");
}

export async function onRequestPost({ request, env }) {
  if (!auth(request, env)) return json({ error: "unauthorized" }, 401);
  let b;
  try { b = await request.json(); } catch { return json({ error: "invalid json" }, 400); }
  const routeId = (b.route_id || "").toString().trim().slice(0, 80);
  if (!routeId) return json({ error: "route_id requerido" }, 422);
  const first = (b.first_run || "").toString().trim();
  const last = (b.last_run || "").toString().trim();
  const notes = (b.notes || "").toString().trim().slice(0, 160);
  const headway = b.headway_min === null || b.headway_min === undefined || b.headway_min === ""
    ? null : Number(b.headway_min);
  if (first && !TIME_RE.test(first)) return json({ error: "first_run debe ser HH:MM" }, 422);
  if (last && !TIME_RE.test(last)) return json({ error: "last_run debe ser HH:MM" }, 422);
  if (headway !== null && (!Number.isInteger(headway) || headway < 1 || headway > 240))
    return json({ error: "headway_min debe ser entero 1–240" }, 422);
  if (!first && !last && headway === null && !notes) {
    await env.DB.prepare("DELETE FROM route_schedules WHERE route_id = ?1").bind(routeId).run();
    return json({ ok: true, route_id: routeId, cleared: true });
  }
  await env.DB.prepare(
    `INSERT INTO route_schedules (route_id, first_run, last_run, headway_min, notes, updated_at)
     VALUES (?1, ?2, ?3, ?4, ?5, datetime('now'))
     ON CONFLICT(route_id) DO UPDATE SET first_run=?2, last_run=?3, headway_min=?4, notes=?5, updated_at=datetime('now')`
  ).bind(routeId, first || null, last || null, headway, notes || null).run();
  return json({ ok: true, route_id: routeId });
}
