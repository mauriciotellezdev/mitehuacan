/**
 * POST /api/evento — first-party feature-usage/problem beacon from the map UI.
 * Body: {event, label?}. Visitor comes from the qcv cookie (HttpOnly, sent
 * automatically same-origin); no client-supplied identity is trusted.
 */
export async function onRequestPost({ request, env, waitUntil }) {
  if (!env.DB) return new Response(null, { status: 204 });
  let body;
  try {
    body = await request.json();
  } catch {
    return new Response(null, { status: 204 });
  }

  const event = (body.event || "").toString().slice(0, 40).replace(/[^a-z0-9_]/gi, "");
  if (!event) return new Response(null, { status: 204 });
  const label = body.label == null ? null : body.label.toString().slice(0, 200);

  const cookies = (request.headers.get("Cookie") || "");
  const visitor = (cookies.match(/(?:^|;\s*)qcv=([^;]+)/) || [])[1] || null;

  const p = env.DB.prepare(
    "INSERT INTO events (event, label, path, visitor, ip, ua) VALUES (?1, ?2, ?3, ?4, ?5, ?6)"
  ).bind(
    event,
    label,
    (body.path || "").toString().slice(0, 200) || null,
    visitor,
    request.headers.get("CF-Connecting-IP") || "unknown",
    (request.headers.get("User-Agent") || "").slice(0, 300)
  ).run().catch(() => {});
  waitUntil ? waitUntil(p) : await p;

  return new Response(null, { status: 204 });
}
