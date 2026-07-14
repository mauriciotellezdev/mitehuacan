/**
 * /api/route-drafts — save/list/delete named route drafts from the /system/map
 * editor. Token-gated (STATS_TOKEN) like everything under /system.
 */
function auth(request, env) {
  const url = new URL(request.url);
  const token = url.searchParams.get("token") || (request.headers.get("Authorization") || "").replace("Bearer ", "");
  return env.STATS_TOKEN && token === env.STATS_TOKEN;
}
const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store", "X-Robots-Tag": "noindex" } });

export async function onRequestGet({ request, env }) {
  if (!auth(request, env)) return json({ error: "unauthorized" }, 401);
  const url = new URL(request.url);
  const slug = url.searchParams.get("slug");
  if (slug) {
    const row = await env.DB.prepare("SELECT * FROM route_drafts WHERE slug = ?1").bind(slug).first();
    return row ? json(row) : json({ error: "not found" }, 404);
  }
  const { results } = await env.DB.prepare(
    "SELECT id, created_at, slug, name, device, t0, t1, n_source, length(geometry) AS geom_bytes, status FROM route_drafts ORDER BY id DESC LIMIT 100").all();
  return json({ drafts: results });
}

export async function onRequestPost({ request, env }) {
  if (!auth(request, env)) return json({ error: "unauthorized" }, 401);
  let b;
  try { b = await request.json(); } catch { return json({ error: "invalid json" }, 400); }
  const slug = (b.slug || "").toString().trim().toLowerCase().replace(/[^a-z0-9-]/g, "-").slice(0, 60);
  const name = (b.name || "").toString().trim().slice(0, 80);
  const coords = b.coordinates;
  if (!slug || !name || !Array.isArray(coords) || coords.length < 2 || coords.length > 20000) {
    return json({ error: "slug, name y >=2 coordenadas requeridos" }, 422);
  }
  for (const c of coords) {
    if (!Array.isArray(c) || !isFinite(c[0]) || !isFinite(c[1])) return json({ error: "coordenadas inválidas" }, 422);
  }
  await env.DB.prepare(
    `INSERT INTO route_drafts (slug, name, device, t0, t1, n_source, geometry)
     VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)
     ON CONFLICT(slug) DO UPDATE SET name=?2, device=?3, t0=?4, t1=?5, n_source=?6, geometry=?7, status='draft'`
  ).bind(slug, name, (b.device || "").slice(0, 40), (b.t0 || "").slice(0, 30), (b.t1 || "").slice(0, 30),
         b.n_source || coords.length, JSON.stringify(coords)).run();
  return json({ ok: true, slug }, 201);
}

export async function onRequestDelete({ request, env }) {
  if (!auth(request, env)) return json({ error: "unauthorized" }, 401);
  const slug = new URL(request.url).searchParams.get("slug");
  if (!slug) return json({ error: "slug requerido" }, 400);
  await env.DB.prepare("DELETE FROM route_drafts WHERE slug = ?1").bind(slug).run();
  return json({ ok: true });
}
