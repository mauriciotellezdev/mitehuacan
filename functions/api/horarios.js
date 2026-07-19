/**
 * GET /api/horarios — public read of per-line schedules (combi_lines), keyed by
 * slug (= routes.js properties.id for published lines). The map fetches this to
 * show first/last run + headway and to estimate the next combi. Writes happen
 * through the token-gated /api/lineas (see /system/combis).
 */
const json = (obj, status = 200, cache = "public, max-age=300") =>
  new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json", "Cache-Control": cache } });

export async function onRequestGet({ env }) {
  const { results } = await env.DB.prepare(
    "SELECT slug, first_run, last_run, headway_min, fare_mxn, fare_max_mxn, notes FROM combi_lines " +
    "WHERE first_run IS NOT NULL OR last_run IS NOT NULL OR headway_min IS NOT NULL OR fare_mxn IS NOT NULL").all();
  const schedules = {};
  for (const r of results) {
    schedules[r.slug] = { first_run: r.first_run, last_run: r.last_run, headway_min: r.headway_min,
                          fare_mxn: r.fare_mxn, fare_max_mxn: r.fare_max_mxn, notes: r.notes };
  }
  return json({ schedules });
}
