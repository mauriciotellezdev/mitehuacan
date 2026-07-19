/**
 * /api/lineas — combi line CRUD for /system/combis. A line = name + schedule
 * (first/last run, headway) + attached recorded drafts. Token-gated
 * (STATS_TOKEN); the public read of schedules is /api/horarios.
 *
 *   GET              lines + all drafts (attached and unattached)
 *   POST             upsert line {slug?, name, first_run, last_run, headway_min, notes}
 *   PATCH            attach/detach a draft {draft_slug, line_slug|null}
 *   DELETE ?slug=    delete line (its drafts return to the unattached inbox)
 */
function auth(request, env) {
  const url = new URL(request.url);
  const token = url.searchParams.get("token") || (request.headers.get("Authorization") || "").replace("Bearer ", "");
  return env.STATS_TOKEN && token === env.STATS_TOKEN;
}
const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store", "X-Robots-Tag": "noindex" } });

const TIME_RE = /^([01]?\d|2[0-3]):[0-5]\d$/;
const slugify = (s) => s.toString().trim().toLowerCase()
  .normalize("NFD").replace(/[̀-ͯ]/g, "")
  .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);

export async function onRequestGet({ request, env }) {
  if (!auth(request, env)) return json({ error: "unauthorized" }, 401);
  const lines = (await env.DB.prepare(
    "SELECT slug, name, first_run, last_run, headway_min, fare_mxn, fare_max_mxn, notes, updated_at FROM combi_lines ORDER BY name").all()).results;
  const drafts = (await env.DB.prepare(
    "SELECT slug, name, device, t0, t1, n_source, status, line_slug, created_at FROM route_drafts ORDER BY id DESC").all()).results;
  return json({ lines, drafts });
}

export async function onRequestPost({ request, env }) {
  if (!auth(request, env)) return json({ error: "unauthorized" }, 401);
  let b;
  try { b = await request.json(); } catch { return json({ error: "invalid json" }, 400); }
  const name = (b.name || "").toString().trim().slice(0, 80);
  if (!name) return json({ error: "name requerido" }, 422);
  const slug = slugify(b.slug || name);
  if (!slug) return json({ error: "slug inválido" }, 422);
  const first = (b.first_run || "").toString().trim();
  const last = (b.last_run || "").toString().trim();
  const notes = (b.notes || "").toString().trim().slice(0, 160);
  const headway = b.headway_min === null || b.headway_min === undefined || b.headway_min === ""
    ? null : Number(b.headway_min);
  if (first && !TIME_RE.test(first)) return json({ error: "primera salida debe ser HH:MM" }, 422);
  if (last && !TIME_RE.test(last)) return json({ error: "última salida debe ser HH:MM" }, 422);
  if (headway !== null && (!Number.isInteger(headway) || headway < 1 || headway > 240))
    return json({ error: "intervalo debe ser entero 1–240 min" }, 422);
  const fare = b.fare_mxn === null || b.fare_mxn === undefined || b.fare_mxn === ""
    ? null : Number(b.fare_mxn);
  if (fare !== null && (!isFinite(fare) || fare <= 0 || fare > 1000))
    return json({ error: "tarifa debe ser un monto entre 0 y 1000 MXN" }, 422);
  const fareMax = b.fare_max_mxn === null || b.fare_max_mxn === undefined || b.fare_max_mxn === ""
    ? null : Number(b.fare_max_mxn);
  if (fareMax !== null && (!isFinite(fareMax) || fareMax <= 0 || fareMax > 1000))
    return json({ error: "tarifa máxima debe ser un monto entre 0 y 1000 MXN" }, 422);
  if (fare !== null && fareMax !== null && fareMax < fare)
    return json({ error: "tarifa máxima debe ser mayor o igual a la tarifa base" }, 422);
  await env.DB.prepare(
    `INSERT INTO combi_lines (slug, name, first_run, last_run, headway_min, fare_mxn, fare_max_mxn, notes, updated_at)
     VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, datetime('now'))
     ON CONFLICT(slug) DO UPDATE SET name=?2, first_run=?3, last_run=?4, headway_min=?5, fare_mxn=?6, fare_max_mxn=?7, notes=?8, updated_at=datetime('now')`
  ).bind(slug, name, first || null, last || null, headway, fare, fareMax, notes || null).run();
  return json({ ok: true, slug });
}

export async function onRequestPatch({ request, env }) {
  if (!auth(request, env)) return json({ error: "unauthorized" }, 401);
  let b;
  try { b = await request.json(); } catch { return json({ error: "invalid json" }, 400); }
  const draft = (b.draft_slug || "").toString().trim();
  if (!draft) return json({ error: "draft_slug requerido" }, 422);
  const line = b.line_slug ? slugify(b.line_slug) : null;
  if (line) {
    const exists = await env.DB.prepare("SELECT slug FROM combi_lines WHERE slug = ?1").bind(line).first();
    if (!exists) return json({ error: "línea no existe" }, 422);
  }
  const r = await env.DB.prepare("UPDATE route_drafts SET line_slug = ?2 WHERE slug = ?1").bind(draft, line).run();
  if (!r.meta.changes) return json({ error: "grabación no existe" }, 404);
  return json({ ok: true, draft_slug: draft, line_slug: line });
}

export async function onRequestDelete({ request, env }) {
  if (!auth(request, env)) return json({ error: "unauthorized" }, 401);
  const slug = new URL(request.url).searchParams.get("slug");
  if (!slug) return json({ error: "slug requerido" }, 400);
  await env.DB.prepare("UPDATE route_drafts SET line_slug = NULL WHERE line_slug = ?1").bind(slug).run();
  await env.DB.prepare("DELETE FROM combi_lines WHERE slug = ?1").bind(slug).run();
  return json({ ok: true });
}
