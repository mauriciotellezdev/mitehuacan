/**
 * First-party analytics: server-side page-hit logging to D1 (no client beacon,
 * no third parties). Logs page views + /qr/ scans; static assets are skipped.
 * Visitor identity = first-party cookie (qcv) + IP fallback, so revisits vs new
 * visits are distinguishable. Retention: 90-day opportunistic purge.
 */
const COOKIE = "qcv";

export async function onRequest(context) {
  const { request, env, next } = context;
  const url = new URL(request.url);

  const isPage =
    request.method === "GET" &&
    (url.pathname === "/" || url.pathname.endsWith("/") || url.pathname.startsWith("/qr/"));

  let response = await next();

  if (isPage) {
    const cookies = Object.fromEntries(
      (request.headers.get("Cookie") || "").split(";").map(c => c.trim().split("=").map(decodeURIComponent)).filter(p => p[0])
    );
    let visitor = cookies[COOKIE];
    const isNew = !visitor;
    if (isNew) {
      visitor = crypto.randomUUID();
      response = new Response(response.body, response);
      response.headers.append(
        "Set-Cookie",
        `${COOKIE}=${visitor}; Path=/; Max-Age=31536000; SameSite=Lax; HttpOnly; Secure`
      );
    }
    if (env.DB) context.waitUntil(logHit(request, env, url, visitor, isNew).catch(() => {}));
  }
  return response;
}

async function logHit(request, env, url, visitor, isNew) {
  const cf = request.cf || {};
  const qr = url.pathname.startsWith("/qr/")
    ? url.pathname.slice(4)
    : url.searchParams.get("qr");

  await env.DB.prepare(
    `INSERT INTO hits (path, query, qr, visitor, is_new, ip, country, region, city, asn, ua, referer, lang)
     VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)`
  ).bind(
    url.pathname.slice(0, 200),
    url.search.slice(0, 200) || null,
    qr ? qr.slice(0, 64) : null,
    visitor,
    isNew ? 1 : 0,
    request.headers.get("CF-Connecting-IP") || "unknown",
    cf.country || null,
    cf.region || null,
    cf.city || null,
    cf.asn ? String(cf.asn) : null,
    (request.headers.get("User-Agent") || "").slice(0, 300),
    (request.headers.get("Referer") || "").slice(0, 300) || null,
    (request.headers.get("Accept-Language") || "").slice(0, 60) || null
  ).run();

  // opportunistic retention purge (~1 in 100 hits): keep 90 days
  if (Math.random() < 0.01) {
    await env.DB.prepare("DELETE FROM hits WHERE ts < datetime('now','-90 days')").run();
  }
}
