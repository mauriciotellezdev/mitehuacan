/**
 * GET /system/combis/ — combi line manager. Select or create a line, set its
 * service window (first/last run) and interval, and attach recorded GPS routes
 * (route_drafts; new recordings land in the unattached inbox). Token-gated
 * client-side like /system; all writes go through /api/lineas.
 * Published routes (routes.js) without a line yet are offered as one-click
 * starting points so their slug matches the public map.
 */
const HTML = `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>MiTehuacán · combis</title>
<style>
:root{--bg:#fff;--panel:#f7f7f8;--ink:#1a1a1e;--ink2:#55555e;--line:#e2e2e6;--accent:#0f62fe;--ok:#1a7f37;--bad:#d4351c}
@media(prefers-color-scheme:dark){:root{--bg:#17171b;--panel:#1f1f24;--ink:#ececf0;--ink2:#a5a5b0;--line:#33333a;--accent:#6ea6ff;--ok:#4ecb71}}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 system-ui,sans-serif;color:var(--ink);background:var(--bg);padding:18px}
h1{font-size:19px;margin:0 0 4px}
h2{font-size:13px;margin:0 0 8px;text-transform:uppercase;letter-spacing:.5px;color:var(--ink2)}
.sub{color:var(--ink2);font-size:12.5px;margin:0 0 14px}
.sub a{color:var(--accent)}
input,button,select{font:inherit}
input,select{padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--ink)}
#tok{width:280px}
button{padding:8px 14px;border:none;border-radius:8px;background:var(--accent);color:#fff;font-weight:600;cursor:pointer}
button.ghost{background:var(--panel);color:var(--ink);border:1px solid var(--line);font-weight:500}
button.danger{background:transparent;color:var(--bad);border:1px solid var(--line)}
button:disabled{opacity:.5;cursor:default}
.wrap{max-width:1080px;margin:0 auto}
.cols{display:grid;grid-template-columns:300px 1fr;gap:16px;align-items:start}
@media(max-width:760px){.cols{grid-template-columns:1fr}}
.box{border:1px solid var(--line);border-radius:12px;background:var(--panel);padding:12px}
.list{max-height:70vh;overflow-y:auto;margin:8px -4px 0;padding:0 4px}
.li{display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:8px;cursor:pointer;font-size:13px}
.li:hover{background:var(--bg)}
.li.sel{outline:2px solid var(--accent);outline-offset:-2px;background:var(--bg)}
.li .nm{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.li .hint{font-size:11px;color:var(--ink2);flex:none}
.li.new-line{color:var(--accent);font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin:10px 0}
.field label{display:block;font-size:10.5px;text-transform:uppercase;letter-spacing:.5px;color:var(--ink2);margin-bottom:3px}
.field input{width:100%}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:10px}
.draft{display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid var(--line);border-radius:8px;margin:6px 0;font-size:12.5px;background:var(--bg)}
.draft .meta{flex:1;min-width:0}
.draft .meta small{display:block;color:var(--ink2)}
.draft button{padding:5px 10px;font-size:12px}
.muted{color:var(--ink2)}#err{color:var(--bad)}
#msg{font-size:12.5px;min-height:18px;margin-top:6px}
#msg.ok{color:var(--ok)}#msg.bad{color:var(--bad)}
.empty{font-size:12.5px;color:var(--ink2);padding:8px 2px}
</style>
</head>
<body>
<div class="wrap">
<h1>Líneas de combi</h1>
<p class="sub">selecciona o crea la línea · adjunta rutas grabadas · define primera/última salida y el intervalo ·
<a href="/system">sistema</a> · <a href="/system/map">editor de rutas</a></p>
<div id="auth"><input id="tok" type="password" placeholder="token"><button onclick="go()">Entrar</button> <span id="err"></span></div>

<div id="ed" hidden class="cols">
  <div class="box">
    <h2>Líneas</h2>
    <input id="q" type="search" placeholder="buscar…" style="width:100%">
    <div class="list" id="lines"></div>
  </div>

  <div>
    <div class="box" id="panel" hidden>
      <h2 id="p-title">Línea</h2>
      <div class="grid">
        <div class="field" style="grid-column:1/-1"><label>Nombre (como está pintado en la combi)</label>
          <input id="f-name" maxlength="80"></div>
        <div class="field"><label>Primera salida</label><input id="f-first" type="time"></div>
        <div class="field"><label>Última salida</label><input id="f-last" type="time"></div>
        <div class="field"><label>Cada (min)</label><input id="f-headway" type="number" min="1" max="240" placeholder="min"></div>
        <div class="field"><label>Tarifa (MXN)</label><input id="f-fare" type="number" min="0" max="1000" step="0.5" placeholder="$"></div>
        <div class="field" style="grid-column:1/-1"><label>Notas</label>
          <input id="f-notes" maxlength="160" placeholder="p. ej. domingos cada 20 min"></div>
      </div>
      <div class="row">
        <button id="save" onclick="saveLine()">Guardar línea</button>
        <button class="danger" id="del" onclick="delLine()">Eliminar</button>
        <span class="muted" id="p-slug"></span>
      </div>
      <div id="msg"></div>

      <h2 style="margin-top:18px">Rutas grabadas de esta línea</h2>
      <div id="attached"></div>
    </div>

    <div class="box" style="margin-top:16px">
      <h2>Grabaciones sin asignar</h2>
      <p class="muted" style="font-size:12px;margin:0 0 4px">las rutas recién grabadas en el editor aparecen aquí hasta que las adjuntes a una línea</p>
      <div id="inbox"></div>
    </div>

    <div class="box" style="margin-top:16px">
      <h2>Alertas del servicio</h2>
      <p class="muted" style="font-size:12px;margin:0 0 8px">se muestran en la pestaña Alertas del mapa; desactívalas cuando pase el problema</p>
      <div class="row" style="margin:0 0 8px">
        <input id="a-msg" maxlength="200" placeholder="mensaje, p. ej. desvío por obra en 5 de Mayo…" style="flex:1;min-width:200px">
        <select id="a-line"><option value="">General</option></select>
        <button onclick="addAlert()">Publicar</button>
      </div>
      <div id="a-list"></div>
    </div>
  </div>
</div>
</div>
<script src="/combis/routes.js"></script>
<script>
let TOKEN = '', LINES = [], DRAFTS = [], SEL = null;  // SEL: {slug} | {isNew:true, prefill?}
const PUB = (typeof ROUTES !== 'undefined' ? ROUTES.features : [])
  .map(f => ({id: f.properties.id, name: f.properties.name}))
  .sort((a, b) => a.name.localeCompare(b.name, 'es', {numeric: true}));

const esc = s => String(s ?? '').replace(/</g, '&lt;');
const byId = id => document.getElementById(id);

function renderLines() {
  const q = (byId('q').value || '').toLowerCase();
  const lineSlugs = new Set(LINES.map(l => l.slug));
  const items = [];
  items.push('<div class="li new-line' + (SEL && SEL.isNew && !SEL.prefill ? ' sel' : '') + '" onclick="pick({isNew:true})">+ nueva línea</div>');
  LINES.filter(l => l.name.toLowerCase().includes(q)).forEach(l => {
    const n = DRAFTS.filter(d => d.line_slug === l.slug).length;
    const sched = l.first_run || l.last_run || l.headway_min;
    items.push('<div class="li' + (SEL && SEL.slug === l.slug ? ' sel' : '') + '" onclick="pick({slug:\\'' + esc(l.slug) + '\\'})">' +
      '<span class="nm">' + esc(l.name) + '</span>' +
      '<span class="hint">' + (n ? n + ' grab.' : '') + (sched ? '' : ' · sin horario') + '</span></div>');
  });
  const pubMissing = PUB.filter(r => !lineSlugs.has(r.id) && r.name.toLowerCase().includes(q));
  if (pubMissing.length) {
    items.push('<div class="empty">rutas publicadas sin línea aún — clic para crearla:</div>');
    pubMissing.forEach(r => items.push(
      '<div class="li" onclick="pick({isNew:true, prefill:\\'' + esc(r.id) + '\\'})">' +
      '<span class="nm muted">' + esc(r.name) + '</span><span class="hint">crear</span></div>'));
  }
  byId('lines').innerHTML = items.join('');
}

function pick(sel) {
  SEL = sel;
  byId('panel').hidden = false;
  byId('msg').textContent = '';
  if (sel.isNew) {
    const pub = sel.prefill ? PUB.find(r => r.id === sel.prefill) : null;
    byId('p-title').textContent = 'Nueva línea';
    byId('f-name').value = pub ? pub.name : '';
    byId('f-first').value = ''; byId('f-last').value = '';
    byId('f-headway').value = ''; byId('f-fare').value = ''; byId('f-notes').value = '';
    byId('p-slug').textContent = pub ? 'slug: ' + pub.id : '';
    byId('del').hidden = true;
  } else {
    const l = LINES.find(x => x.slug === sel.slug);
    byId('p-title').textContent = 'Línea';
    byId('f-name').value = l.name;
    byId('f-first').value = l.first_run || '';
    byId('f-last').value = l.last_run || '';
    byId('f-headway').value = l.headway_min ?? '';
    byId('f-fare').value = l.fare_mxn ?? '';
    byId('f-notes').value = l.notes || '';
    byId('p-slug').textContent = 'slug: ' + l.slug;
    byId('del').hidden = false;
  }
  renderLines();
  renderDrafts();
}

function draftRow(d, attachTo) {
  const when = (d.t0 || d.created_at || '').slice(0, 16).replace('T', ' ');
  return '<div class="draft"><div class="meta">' + esc(d.name || d.slug) +
    '<small>' + esc(d.slug) + ' · ' + esc(when) + (d.n_source ? ' · ' + d.n_source + ' pts' : '') +
    ' · ' + esc(d.status) + '</small></div>' +
    (attachTo
      ? '<button onclick="attach(\\'' + esc(d.slug) + '\\', \\'' + esc(attachTo) + '\\')">adjuntar</button>'
      : '<button class="ghost" onclick="attach(\\'' + esc(d.slug) + '\\', null)">quitar</button>') +
    '</div>';
}

function renderDrafts() {
  const inbox = DRAFTS.filter(d => !d.line_slug);
  const curSlug = SEL && !SEL.isNew ? SEL.slug : null;
  byId('inbox').innerHTML = inbox.length
    ? inbox.map(d => draftRow(d, curSlug)).join('')
    : '<div class="empty">no hay grabaciones pendientes</div>';
  if (curSlug) {
    const mine = DRAFTS.filter(d => d.line_slug === curSlug);
    byId('attached').innerHTML = mine.length
      ? mine.map(d => draftRow(d, null)).join('')
      : '<div class="empty">ninguna todavía — adjunta una grabación de la bandeja de abajo</div>';
  } else {
    byId('attached').innerHTML = '<div class="empty">guarda la línea para poder adjuntar grabaciones</div>';
  }
  const inboxBtns = !curSlug && inbox.length;
  if (inboxBtns) byId('inbox').querySelectorAll('button').forEach(b => b.disabled = true);
}

function say(txt, ok) { const m = byId('msg'); m.textContent = txt; m.className = ok ? 'ok' : 'bad'; }

async function api(method, body, qs) {
  const r = await fetch('/api/lineas' + (qs || ''), {method,
    headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + TOKEN},
    body: body ? JSON.stringify(body) : undefined});
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || r.status);
  return d;
}

async function saveLine() {
  const body = {
    slug: SEL && !SEL.isNew ? SEL.slug : (SEL && SEL.prefill) || undefined,
    name: byId('f-name').value.trim(),
    first_run: byId('f-first').value, last_run: byId('f-last').value,
    headway_min: byId('f-headway').value === '' ? null : +byId('f-headway').value,
    fare_mxn: byId('f-fare').value === '' ? null : +byId('f-fare').value,
    notes: byId('f-notes').value.trim(),
  };
  try {
    const d = await api('POST', body);
    await reload();
    pick({slug: d.slug});
    say('guardado', true);
  } catch (e) { say(e.message, false); }
}

async function delLine() {
  if (!SEL || SEL.isNew) return;
  if (!confirm('¿Eliminar la línea "' + byId('f-name').value + '"? Sus grabaciones vuelven a la bandeja.')) return;
  try {
    await api('DELETE', null, '?slug=' + encodeURIComponent(SEL.slug));
    SEL = null;
    byId('panel').hidden = true;
    await reload();
  } catch (e) { say(e.message, false); }
}

async function attach(draftSlug, lineSlug) {
  try {
    await api('PATCH', {draft_slug: draftSlug, line_slug: lineSlug});
    await reload();
  } catch (e) { say(e.message, false); }
}

async function reload() {
  const d = await api('GET');
  LINES = d.lines; DRAFTS = d.drafts;
  renderLines();
  renderDrafts();
  const sel = byId('a-line');
  sel.innerHTML = '<option value="">General</option>' +
    LINES.map(l => '<option value="' + esc(l.slug) + '">' + esc(l.name) + '</option>').join('');
  await loadAlerts();
}

/* ---- service alerts ---- */
let ALERTS = [];
async function alertsApi(method, body, qs) {
  const r = await fetch('/api/alertas' + (qs || ''), {method,
    headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + TOKEN},
    body: body ? JSON.stringify(body) : undefined});
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || r.status);
  return d;
}
async function loadAlerts() {
  try { ALERTS = (await alertsApi('GET')).alerts || []; } catch (e) { ALERTS = []; }
  renderAlerts();
}
function renderAlerts() {
  byId('a-list').innerHTML = ALERTS.length ? ALERTS.map(a => {
    const line = a.line_slug ? (LINES.find(l => l.slug === a.line_slug) || {name: a.line_slug}).name : 'General';
    return '<div class="draft"' + (a.active ? '' : ' style="opacity:.55"') + '><div class="meta">' + esc(a.message) +
      '<small>' + esc(line) + ' · ' + esc((a.created_at || '').slice(0, 16)) + (a.active ? '' : ' · inactiva') + '</small></div>' +
      '<button class="ghost" onclick="toggleAlert(' + a.id + ',' + (a.active ? 0 : 1) + ')">' + (a.active ? 'desactivar' : 'activar') + '</button>' +
      '<button class="danger" onclick="delAlert(' + a.id + ')">borrar</button></div>';
  }).join('') : '<div class="empty">sin alertas</div>';
}
async function addAlert() {
  const msg = byId('a-msg').value.trim();
  if (msg.length < 3) return;
  try {
    await alertsApi('POST', {message: msg, line_slug: byId('a-line').value || null});
    byId('a-msg').value = '';
    await loadAlerts();
  } catch (e) { say(e.message, false); }
}
async function toggleAlert(id, active) {
  try { await alertsApi('PATCH', {id, active: !!active}); await loadAlerts(); } catch (e) { say(e.message, false); }
}
async function delAlert(id) {
  if (!confirm('¿Borrar la alerta definitivamente? (para pausarla usa desactivar)')) return;
  try { await alertsApi('DELETE', null, '?id=' + id); await loadAlerts(); } catch (e) { say(e.message, false); }
}

async function load(token) {
  TOKEN = token;
  await reload();
  byId('auth').hidden = true;
  byId('ed').hidden = false;
}
async function go() {
  const tok = byId('tok').value.trim();
  try { await load(tok); localStorage.setItem('qc_stats_token', tok); }
  catch (e) { TOKEN = ''; byId('err').textContent = 'token inválido'; }
}
byId('q').addEventListener('input', renderLines);
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
