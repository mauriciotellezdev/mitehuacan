/**
 * GET /api/rides?device=mauricio-1&from=2026-07-15T09:00&to=2026-07-15T10:20
 * Token-gated (STATS_TOKEN) export of recorded positions — feeds
 * tehuacan/scripts/13_traccar_export.py --remote. Times are ISO, treated as sent.
 */
export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const token = url.searchParams.get("token") || (request.headers.get("Authorization") || "").replace("Bearer ", "");
  if (!env.STATS_TOKEN || token !== env.STATS_TOKEN) {
    return new Response(JSON.stringify({ error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
  }
  const device = url.searchParams.get("device") || "";
  const from = url.searchParams.get("from") || "1970-01-01";
  const to = url.searchParams.get("to") || "2100-01-01";

  const { results } = await env.DB.prepare(
    `SELECT fix_ts, lat, lon, speed, accuracy, batt FROM positions
     WHERE device = ?1 AND fix_ts >= ?2 AND fix_ts <= ?3 ORDER BY fix_ts LIMIT 50000`
  ).bind(device, from, to).all();

  return new Response(JSON.stringify({ device, from, to, count: results.length, positions: results }), {
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}
