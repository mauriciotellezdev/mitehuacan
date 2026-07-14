/**
 * POST /api/reportes — citizen reports of missing/changed combi routes.
 * Cloudflare Pages Function; storage: D1 binding `DB` (see migrations/0001_reports.sql).
 * Validation per SECURITY.md §5: length caps, honeypot, per-IP rate limit, no PII required.
 */
export async function onRequestPost({ request, env }) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "invalid json" }, 400);
  }

  // honeypot: bots fill every field; humans never see `website`
  if (body.website) return json({ ok: true }, 201);

  const nombre = (body.nombre || "").toString().trim().slice(0, 80);
  const descripcion = (body.descripcion || "").toString().trim().slice(0, 1500);
  const ciudad = (body.ciudad || "tehuacan").toString().trim().slice(0, 40);
  if (nombre.length < 2 || descripcion.length < 10) {
    return json({ error: "nombre y descripción son obligatorios" }, 422);
  }

  // crude per-IP rate limit: max 10 reports/day (D1 count; fine at our scale)
  const ipHash = await sha256(request.headers.get("CF-Connecting-IP") || "unknown");
  const { count } = await env.DB
    .prepare("SELECT COUNT(*) AS count FROM reports WHERE ip_hash = ?1 AND created_at > datetime('now','-1 day')")
    .bind(ipHash).first();
  if (count >= 10) return json({ error: "demasiados reportes hoy" }, 429);

  await env.DB
    .prepare("INSERT INTO reports (ciudad, nombre, descripcion, ip_hash) VALUES (?1, ?2, ?3, ?4)")
    .bind(ciudad, nombre, descripcion, ipHash)
    .run();

  return json({ ok: true }, 201);
}

function json(obj, status) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function sha256(s) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}
