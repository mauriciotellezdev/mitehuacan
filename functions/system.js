/**
 * GET /system — private analytics dashboard. Not linked anywhere, absent from
 * sitemap.xml, X-Robots-Tag noindex. The page itself holds no secrets: it asks
 * for the token and calls /api/stats with it (token kept in localStorage).
 */
const HTML = `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>QueCombi · sistema</title>
<style>
:root{--bg:#fff;--panel:#f7f7f8;--ink:#1a1a1e;--ink2:#55555e;--line:#e2e2e6;--accent:#0f62fe}
@media(prefers-color-scheme:dark){:root{--bg:#17171b;--panel:#1f1f24;--ink:#ececf0;--ink2:#a5a5b0;--line:#33333a;--accent:#6ea6ff}}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 system-ui,sans-serif;color:var(--ink);background:var(--bg);padding:18px}
h1{font-size:19px;margin:0 0 14px}h2{font-size:15px;margin:22px 0 8px}
input{padding:9px 12px;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--ink);width:280px}
button{padding:9px 16px;border:none;border-radius:8px;background:var(--accent);color:#fff;font-weight:600;cursor:pointer;margin-left:8px}
.wrap{max-width:1100px;margin:0 auto}
.tblwrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th,td{padding:6px 10px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap;max-width:340px;overflow:hidden;text-overflow:ellipsis}
th{background:var(--panel);position:sticky;top:0}
.muted{color:var(--ink2)}#err{color:#d4351c}
.cards{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 16px}
.card b{font-size:20px;display:block}
</style>
</head>
<body>
<div class="wrap">
<h1>QueCombi · sistema</h1>
<div id="auth"><input id="tok" type="password" placeholder="token"><button onclick="go()">Entrar</button> <span id="err"></span></div>
<div id="dash" hidden>
  <div class="cards" id="cards"></div>
  <h2>Uso de funciones (30d)</h2><div class="tblwrap"><table id="t-features"></table></div>
  <h2>Problemas reportados (errores JS, 30d)</h2><div class="tblwrap"><table id="t-problems"></table></div>
  <h2>Por día (visitantes = cookie/ip dedup)</h2><div class="tblwrap"><table id="t-day"></table></div>
  <h2>Stickers QR</h2><div class="tblwrap"><table id="t-qr"></table></div>
  <h2>Páginas</h2><div class="tblwrap"><table id="t-pages"></table></div>
  <h2>Últimos hits</h2><div class="tblwrap"><table id="t-recent"></table></div>
  <h2>Reportes de rutas</h2><div class="tblwrap"><table id="t-reports"></table></div>
</div>
</div>
<script>
function table(el, rows) {
  const t = document.getElementById(el);
  if (!rows || !rows.length) { t.innerHTML = '<tr><td class="muted">sin datos</td></tr>'; return; }
  const cols = Object.keys(rows[0]);
  t.innerHTML = '<tr>' + cols.map(c => '<th>' + c + '</th>').join('') + '</tr>' +
    rows.map(r => '<tr>' + cols.map(c => '<td>' + (r[c] === null ? '<span class="muted">—</span>' : String(r[c]).replace(/</g,'&lt;')) + '</td>').join('') + '</tr>').join('');
}
async function load(token) {
  const r = await fetch('/api/stats', {headers: {Authorization: 'Bearer ' + token}});
  if (!r.ok) throw new Error(r.status);
  const d = await r.json();
  document.getElementById('auth').hidden = true;
  document.getElementById('dash').hidden = false;
  const today = d.by_day[0] || {hits:0, visitors:0, new_visitors:0};
  const total = d.by_day.reduce((s,x) => s + x.hits, 0);
  const k = d.kpis || {};
  const card = (v, label) => '<div class="card"><b>' + (v ?? '—') + '</b>' + label + '</div>';
  document.getElementById('cards').innerHTML =
    card(k.dau_avg_7d, 'DAU prom. 7d') +
    card(k.dau_avg_30d, 'DAU prom. 30d') +
    card(k.wau, 'WAU') +
    card(k.mau, 'MAU') +
    card(k.stickiness_dau_mau, 'DAU/MAU') +
    card(k.new_visitors_30d, 'nuevos 30d') +
    card(k.qr_scans_30d, 'scans QR 30d') +
    card(today.visitors || 0, 'visitantes hoy') +
    card(total, 'hits 30d');
  table('t-features', d.features); table('t-problems', d.problems);
  table('t-day', d.by_day); table('t-qr', d.qr_stickers); table('t-pages', d.top_pages);
  table('t-recent', d.recent_hits); table('t-reports', d.route_reports);
}
async function go() {
  const tok = document.getElementById('tok').value.trim();
  try { await load(tok); localStorage.setItem('qc_stats_token', tok); }
  catch (e) { document.getElementById('err').textContent = 'token inválido'; }
}
const saved = localStorage.getItem('qc_stats_token');
if (saved) load(saved).catch(() => localStorage.removeItem('qc_stats_token'));
</script>
</body>
</html>`;

export function onRequestGet() {
  return new Response(HTML, {
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "X-Robots-Tag": "noindex, nofollow",
      "Cache-Control": "no-store",
    },
  });
}
