/**
 * GET /system/horarios — admin editor for per-route schedules (first run, last
 * run, minutes between combis). Token-gated client-side like /system: the page
 * validates the token against /api/horarios?token= and saves row by row.
 * Route list comes from the public dataset (/combis/routes.js).
 */
const HTML = `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>MiTehuacán · horarios</title>
<style>
:root{--bg:#fff;--panel:#f7f7f8;--ink:#1a1a1e;--ink2:#55555e;--line:#e2e2e6;--accent:#0f62fe;--ok:#1a7f37;--bad:#d4351c}
@media(prefers-color-scheme:dark){:root{--bg:#17171b;--panel:#1f1f24;--ink:#ececf0;--ink2:#a5a5b0;--line:#33333a;--accent:#6ea6ff;--ok:#4ecb71}}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 system-ui,sans-serif;color:var(--ink);background:var(--bg);padding:18px}
h1{font-size:19px;margin:0 0 4px}
.sub{color:var(--ink2);font-size:12.5px;margin:0 0 14px}
.sub a{color:var(--accent)}
input,button{font:inherit}
input{padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--ink)}
#tok{width:280px}
button{padding:8px 14px;border:none;border-radius:8px;background:var(--accent);color:#fff;font-weight:600;cursor:pointer}
button:disabled{opacity:.5;cursor:default}
.wrap{max-width:1000px;margin:0 auto}
.bar{display:flex;gap:10px;align-items:center;margin:12px 0;flex-wrap:wrap}
#q{width:240px}
.tblwrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:6px 10px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}
th{background:var(--panel);position:sticky;top:0;z-index:1}
td input[type=time]{width:102px}
td input.hw{width:70px}
td input.nt{width:220px}
tr.dirty td{background:rgba(240,180,0,.08)}
.tag{font-size:10px;padding:1px 7px;border-radius:999px;border:1px solid var(--line);color:var(--ink2)}
.st{width:24px;text-align:center}
.st.ok{color:var(--ok)}.st.bad{color:var(--bad)}
.muted{color:var(--ink2)}#err{color:var(--bad)}
</style>
</head>
<body>
<div class="wrap">
<h1>Horarios por ruta</h1>
<p class="sub">primera salida · última salida · minutos entre combis — se muestra al seleccionar la ruta en el mapa público ·
<a href="/system">sistema</a> · <a href="/system/map">editor de rutas</a></p>
<div id="auth"><input id="tok" type="password" placeholder="token"><button onclick="go()">Entrar</button> <span id="err"></span></div>
<div id="ed" hidden>
  <div class="bar">
    <input id="q" type="search" placeholder="filtrar ruta…">
    <button id="saveall" onclick="saveAll()" disabled>Guardar cambios</button>
    <span class="muted" id="summary"></span>
  </div>
  <div class="tblwrap"><table id="t"></table></div>
</div>
</div>
<script src="/combis/routes.js"></script>
<script>
let TOKEN = '', SCHED = {}, PENDING = {}, DIRTY = new Set();
const feats = (typeof ROUTES !== 'undefined' ? ROUTES.features : [])
  .slice().sort((a, b) => a.properties.name.localeCompare(b.properties.name, 'es', {numeric: true}));

function esc(s) { return String(s ?? '').replace(/</g, '&lt;'); }

function vals(id) {
  if (PENDING[id]) return PENDING[id];
  const s = SCHED[id] || {};
  return {fr: s.first_run || '', lr: s.last_run || '', hw: s.headway_min ?? '', nt: s.notes || ''};
}

function row(f) {
  const p = f.properties, v = vals(p.id);
  return '<tr data-id="' + esc(p.id) + '"' + (DIRTY.has(p.id) ? ' class="dirty"' : '') + '>' +
    '<td>' + esc(p.name) + (p.kind === 'foránea' ? ' <span class="tag">foránea</span>' : '') + '</td>' +
    '<td><input type="time" class="fr" value="' + esc(v.fr) + '"></td>' +
    '<td><input type="time" class="lr" value="' + esc(v.lr) + '"></td>' +
    '<td><input type="number" class="hw" min="1" max="240" placeholder="min" value="' + esc(v.hw) + '"></td>' +
    '<td><input type="text" class="nt" maxlength="160" placeholder="notas (opcional)" value="' + esc(v.nt) + '"></td>' +
    '<td class="st"></td></tr>';
}

function render() {
  const q = (document.getElementById('q').value || '').toLowerCase();
  const rows = feats.filter(f => f.properties.name.toLowerCase().includes(q));
  document.getElementById('t').innerHTML =
    '<tr><th>ruta</th><th>primera</th><th>última</th><th>cada (min)</th><th>notas</th><th></th></tr>' +
    rows.map(row).join('');
  document.querySelectorAll('#t tr[data-id] input').forEach(inp =>
    inp.addEventListener('input', e => {
      const tr = e.target.closest('tr');
      PENDING[tr.dataset.id] = {
        fr: tr.querySelector('.fr').value, lr: tr.querySelector('.lr').value,
        hw: tr.querySelector('.hw').value, nt: tr.querySelector('.nt').value,
      };
      tr.classList.add('dirty');
      tr.querySelector('.st').textContent = '';
      DIRTY.add(tr.dataset.id);
      syncBar();
    }));
  syncBar();
}

function syncBar() {
  const n = Object.keys(SCHED).length;
  document.getElementById('summary').textContent =
    n + ' de ' + feats.length + ' rutas con horario' + (DIRTY.size ? ' · ' + DIRTY.size + ' sin guardar' : '');
  document.getElementById('saveall').disabled = DIRTY.size === 0;
}

async function saveOne(id) {
  const v = vals(id);
  const body = {route_id: id, first_run: v.fr, last_run: v.lr,
                headway_min: v.hw === '' ? null : +v.hw, notes: (v.nt || '').trim()};
  const tr = document.querySelector('#t tr[data-id="' + CSS.escape(id) + '"]');
  const st = tr && tr.querySelector('.st');
  try {
    const r = await fetch('/api/horarios', {method: 'POST',
      headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + TOKEN},
      body: JSON.stringify(body)});
    if (!r.ok) throw new Error((await r.json()).error || r.status);
    if (!body.first_run && !body.last_run && body.headway_min === null && !body.notes) delete SCHED[id];
    else SCHED[id] = {first_run: body.first_run || null, last_run: body.last_run || null,
                      headway_min: body.headway_min, notes: body.notes || null};
    delete PENDING[id];
    DIRTY.delete(id);
    if (tr) { tr.classList.remove('dirty'); st.className = 'st ok'; st.textContent = '✓'; }
  } catch (e) {
    if (st) { st.className = 'st bad'; st.textContent = '✕'; st.title = e.message; }
  }
  syncBar();
}

async function saveAll() {
  for (const id of [...DIRTY]) await saveOne(id);
}

async function load(token) {
  const r = await fetch('/api/horarios?token=' + encodeURIComponent(token));
  if (!r.ok) throw new Error(r.status);
  SCHED = (await r.json()).schedules || {};
  TOKEN = token;
  document.getElementById('auth').hidden = true;
  document.getElementById('ed').hidden = false;
  render();
}
async function go() {
  const tok = document.getElementById('tok').value.trim();
  try { await load(tok); localStorage.setItem('qc_stats_token', tok); }
  catch (e) { document.getElementById('err').textContent = 'token inválido'; }
}
document.getElementById('q').addEventListener('input', render);
window.addEventListener('beforeunload', e => { if (DIRTY.size) e.preventDefault(); });
const saved = localStorage.getItem('qc_stats_token');
if (saved) load(saved).catch(() => {});
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
