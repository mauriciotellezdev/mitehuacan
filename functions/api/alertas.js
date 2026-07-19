/**
 * /api/alertas — service alerts. Public GET returns active alerts (the map's
 * Alertas tab); with a valid token it returns all (admin view). Writes are
 * token-gated (STATS_TOKEN), managed from /system/combis.
 */
function auth(request, env) {
  const url = new URL(request.url);
  const token = url.searchParams.get("token") || (request.headers.get("Authorization") || "").replace("Bearer ", "");
  return env.STATS_TOKEN && token === env.STATS_TOKEN;
}
const json = (obj, status = 200, cache = "no-store") =>
  new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json", "Cache-Control": cache } });

export async function onRequestGet({ request, env }) {
  const hasToken = new URL(request.url).searchParams.get("token") || request.headers.get("Authorization");
  if (hasToken && !auth(request, env)) return json({ error: "unauthorized" }, 401);
  const { results } = await env.DB.prepare(
    hasToken
      ? "SELECT id, created_at, line_slug, message, active FROM alerts ORDER BY id DESC LIMIT 100"
      : "SELECT id, created_at, line_slug, message FROM alerts WHERE active = 1 ORDER BY id DESC LIMIT 50").all();
  return json({ alerts: results }, 200, hasToken ? "no-store" : "public, max-age=120");
}

export async function onRequestPost({ request, env }) {
  if (!auth(request, env)) return json({ error: "unauthorized" }, 401);
  let b;
  try { b = await request.json(); } catch { return json({ error: "invalid json" }, 400); }
  const message = (b.message || "").toString().trim().slice(0, 200);
  if (message.length < 3) return json({ error: "mensaje requerido (3–200)" }, 422);
  const line = (b.line_slug || "").toString().trim() || null;
  if (line) {
    const exists = await env.DB.prepare("SELECT slug FROM combi_lines WHERE slug = ?1").bind(line).first();
    if (!exists) return json({ error: "línea no existe" }, 422);
  }
  const r = await env.DB.prepare("INSERT INTO alerts (line_slug, message) VALUES (?1, ?2)").bind(line, message).run();
  return json({ ok: true, id: r.meta.last_row_id }, 201);
}

export async function onRequestPatch({ request, env }) {
  if (!auth(request, env)) return json({ error: "unauthorized" }, 401);
  let b;
  try { b = await request.json(); } catch { return json({ error: "invalid json" }, 400); }
  if (!Number.isInteger(b.id)) return json({ error: "id requerido" }, 422);
  const r = await env.DB.prepare("UPDATE alerts SET active = ?2 WHERE id = ?1")
    .bind(b.id, b.active ? 1 : 0).run();
  return r.meta.changes ? json({ ok: true }) : json({ error: "no existe" }, 404);
}

export async function onRequestDelete({ request, env }) {
  if (!auth(request, env)) return json({ error: "unauthorized" }, 401);
  const id = Number(new URL(request.url).searchParams.get("id"));
  if (!Number.isInteger(id)) return json({ error: "id requerido" }, 400);
  await env.DB.prepare("DELETE FROM alerts WHERE id = ?1").bind(id).run();
  return json({ ok: true });
}
