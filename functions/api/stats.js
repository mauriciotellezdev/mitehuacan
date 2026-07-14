/**
 * GET /api/stats?token=... — private analytics data for /system (hits contain IPs:
 * STATS_TOKEN required, never expose publicly, never index. See SECURITY.md).
 * Visitor identity: cookie id, falling back to ip for cookie-less clients.
 */
export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const token = url.searchParams.get("token") || (request.headers.get("Authorization") || "").replace("Bearer ", "");
  if (!env.STATS_TOKEN || token !== env.STATS_TOKEN) {
    return new Response(JSON.stringify({ error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
  }

  const V = "COALESCE(visitor, 'ip:' || ip)";
  const kpiRow = await env.DB.prepare(
    `SELECT
       (SELECT ROUND(AVG(v), 1) FROM (SELECT COUNT(DISTINCT ${V}) v FROM hits
         WHERE ts > datetime('now','-7 days') GROUP BY date(ts))) AS dau_avg_7d,
       (SELECT ROUND(AVG(v), 1) FROM (SELECT COUNT(DISTINCT ${V}) v FROM hits
         WHERE ts > datetime('now','-30 days') GROUP BY date(ts))) AS dau_avg_30d,
       (SELECT COUNT(DISTINCT ${V}) FROM hits WHERE ts > datetime('now','-7 days')) AS wau,
       (SELECT COUNT(DISTINCT ${V}) FROM hits WHERE ts > datetime('now','-30 days')) AS mau,
       (SELECT SUM(is_new) FROM hits WHERE ts > datetime('now','-30 days')) AS new_visitors_30d,
       (SELECT COUNT(*) FROM hits WHERE qr IS NOT NULL AND ts > datetime('now','-30 days')) AS qr_scans_30d`
  ).first();
  const kpis = {
    ...kpiRow,
    stickiness_dau_mau: kpiRow.mau ? Math.round(100 * (kpiRow.dau_avg_30d || 0) / kpiRow.mau) + "%" : null,
  };

  const [features, problems, byDay, byPath, byQr, recent, reports] = await Promise.all([
    env.DB.prepare(
      `SELECT event, COUNT(*) AS veces, COUNT(DISTINCT COALESCE(visitor, 'ip:' || ip)) AS visitantes
       FROM events WHERE event != 'js_error' AND ts > datetime('now','-30 days')
       GROUP BY event ORDER BY veces DESC`).all().catch(() => ({ results: [] })),
    env.DB.prepare(
      `SELECT label AS problema, COUNT(*) AS veces, MAX(ts) AS ultimo
       FROM events WHERE event = 'js_error' AND ts > datetime('now','-30 days')
       GROUP BY label ORDER BY veces DESC LIMIT 50`).all().catch(() => ({ results: [] })),
    env.DB.prepare(
      `SELECT date(ts) AS day, COUNT(*) AS hits,
              COUNT(DISTINCT ${V}) AS visitors,
              SUM(is_new) AS new_visitors,
              COUNT(DISTINCT ${V}) - SUM(is_new) AS recurrentes
       FROM hits GROUP BY day ORDER BY day DESC LIMIT 30`).all(),
    env.DB.prepare("SELECT path, COUNT(*) AS hits FROM hits GROUP BY path ORDER BY hits DESC LIMIT 20").all(),
    env.DB.prepare(
      `SELECT qr, COUNT(*) AS scans, COUNT(DISTINCT ${V}) AS visitors
       FROM hits WHERE qr IS NOT NULL GROUP BY qr ORDER BY scans DESC LIMIT 100`).all(),
    env.DB.prepare("SELECT ts, path, qr, visitor, is_new, ip, country, city, ua, referer FROM hits ORDER BY id DESC LIMIT 100").all(),
    env.DB.prepare("SELECT id, created_at, ciudad, nombre, descripcion, status FROM reports ORDER BY id DESC LIMIT 50").all().catch(() => ({ results: [] })),
  ]);

  return new Response(JSON.stringify({
    kpis,
    features: features.results,
    problems: problems.results,
    by_day: byDay.results,
    top_pages: byPath.results,
    qr_stickers: byQr.results,
    recent_hits: recent.results,
    route_reports: reports.results,
  }, null, 2), {
    headers: { "Content-Type": "application/json", "X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store" },
  });
}
