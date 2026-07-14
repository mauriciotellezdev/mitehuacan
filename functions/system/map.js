/**
 * GET /system/map — private route editor: load recorded positions, trim to the
 * ride, simplify (Douglas-Peucker), optionally align to streets (OSRM demo
 * match), name it, save as a draft (D1) or download GeoJSON.
 * Token model identical to /system (localStorage qc_stats_token). noindex.
 */
const HTML = `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>QueCombi · editor de rutas</title>
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<style>
:root{--bg:#fff;--panel:#f7f7f8;--ink:#1a1a1e;--ink2:#55555e;--line:#e2e2e6;--accent:#0f62fe;--chip:#fff}
@media(prefers-color-scheme:dark){:root{--bg:#17171b;--panel:#1f1f24;--ink:#ececf0;--ink2:#a5a5b0;--line:#33333a;--accent:#6ea6ff;--chip:#26262c}}
*{box-sizing:border-box}body{margin:0;font:13.5px/1.45 system-ui,sans-serif;color:var(--ink);background:var(--bg);display:flex;height:100dvh}
#panel{width:340px;min-width:300px;background:var(--panel);border-right:1px solid var(--line);padding:14px;overflow-y:auto}
#map{flex:1}
h1{font-size:16px;margin:0 0 10px}h2{font-size:13px;margin:16px 0 6px;color:var(--ink2);text-transform:uppercase;letter-spacing:.4px}
label{display:block;font-size:12px;color:var(--ink2);margin:8px 0 3px}
input,select{width:100%;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--chip);color:var(--ink);font:inherit}
input[type=range]{padding:0}
button{padding:8px 12px;border:none;border-radius:8px;background:var(--accent);color:#fff;font:inherit;font-weight:600;cursor:pointer;margin:6px 6px 0 0}
button.ghost{background:var(--chip);color:var(--ink);border:1px solid var(--line)}
button:disabled{opacity:.45;cursor:default}
.muted{color:var(--ink2);font-size:12px}
#stats{font-size:12px;color:var(--ink2);margin-top:6px}
.draft{border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin:6px 0;background:var(--chip);font-size:12.5px}
.draft b{display:block}
.draft button{padding:3px 8px;font-size:11.5px;margin:4px 4px 0 0}
#err{color:#d4351c;font-size:12px;margin-top:6px}
</style>
</head>
<body>
<div id="panel">
<h1>Editor de rutas</h1>

<div id="auth"><label>token</label><input id="tok" type="password"><button onclick="saveTok()">Entrar</button><div id="err"></div></div>

<div id="tool" hidden>
<h2>1 · Cargar puntos</h2>
<label>dispositivo</label><input id="device" value="16905583">
<label>desde (local)</label><input id="t0" type="datetime-local">
<label>hasta (local)</label><input id="t1" type="datetime-local">
<button onclick="load()">Cargar</button>
<div id="stats"></div>

<h2>2 · Recortar</h2>
<label>inicio: <span id="l0">0</span></label><input id="trim0" type="range" min="0" max="0" value="0" oninput="update()">
<label>fin: <span id="l1">0</span></label><input id="trim1" type="range" min="0" max="0" value="0" oninput="update()">

<h2>3 · Simplificar</h2>
<label>tolerancia: <span id="leps">5</span> m (quita puntos entre tramos rectos)</label>
<input id="eps" type="range" min="0" max="30" value="5" oninput="update()">

<h2>4 · Alinear a calles</h2>
<button class="ghost" id="alignBtn" onclick="align()">Alinear (OSRM)</button>
<button class="ghost" id="unalignBtn" onclick="ALIGNED=null;update()" disabled>Quitar alineación</button>
<div class="muted">usa el servidor demo de OSRM — si falla, guarda sin alinear; Valhalla propio llega en Tier 1</div>

<h2>5 · Nombrar y guardar</h2>
<label>nombre (como está pintado en la combi)</label><input id="name" placeholder="Tecoxteo — Coxcatlán">
<label>slug</label><input id="slug" placeholder="tecoxteo-coxcatlan-ida">
<button onclick="save()">Guardar borrador</button>
<button class="ghost" onclick="download()">Descargar .geojson</button>
<div id="msg" class="muted"></div>

<h2>Borradores guardados</h2>
<div id="drafts" class="muted">…</div>
</div>
</div>
<div id="map"></div>
<script>
let TOKEN = localStorage.getItem('qc_stats_token') || '';
let RAW = [], ALIGNED = null, EDITED = [];
const $ = id => document.getElementById(id);

const dark = matchMedia('(prefers-color-scheme: dark)').matches;
const map = new maplibregl.Map({container:'map',
  style: dark ? 'https://tiles.openfreemap.org/styles/dark' : 'https://tiles.openfreemap.org/styles/positron',
  center:[-97.396,18.462], zoom:12});
map.addControl(new maplibregl.NavigationControl(), 'top-right');
map.on('load', () => {
  map.addSource('raw', {type:'geojson', data: fc([])});
  map.addSource('edited', {type:'geojson', data: fc([])});
  map.addLayer({id:'raw', type:'line', source:'raw',
    paint:{'line-color':'#888', 'line-width':2, 'line-dasharray':[2,2], 'line-opacity':.7}});
  map.addLayer({id:'edited', type:'line', source:'edited',
    layout:{'line-cap':'round','line-join':'round'},
    paint:{'line-color':'#6ea6ff', 'line-width':4}});
  map.addLayer({id:'edited-pts', type:'circle', source:'edited',
    paint:{'circle-radius':3, 'circle-color':'#6ea6ff', 'circle-stroke-width':1,
           'circle-stroke-color': dark ? '#141419' : '#fff'}});
});
function fc(coords){return {type:'Feature',properties:{},geometry:{type:'LineString',coordinates:coords.length>1?coords:[[0,0],[0,0]]}}}

function saveTok(){ TOKEN = $('tok').value.trim(); localStorage.setItem('qc_stats_token', TOKEN); boot(); }
async function boot(){
  const r = await fetch('/api/route-drafts', {headers:{Authorization:'Bearer '+TOKEN}});
  if (!r.ok) { $('err').textContent = TOKEN ? 'token inválido' : ''; return; }
  $('auth').hidden = true; $('tool').hidden = false;
  renderDrafts((await r.json()).drafts);
  const now = new Date(Date.now() - new Date().getTimezoneOffset()*60000);
  $('t1').value = now.toISOString().slice(0,16);
  $('t0').value = new Date(now - 6*3600e3).toISOString().slice(0,16);
}

async function load(){
  const r = await fetch('/api/rides?device=' + encodeURIComponent($('device').value.trim()) +
    '&from=' + toUTC($('t0').value) + '&to=' + toUTC($('t1').value),
    {headers:{Authorization:'Bearer '+TOKEN}});
  const d = await r.json();
  RAW = (d.positions||[]).map(p => [p.lon, p.lat]);
  ALIGNED = null;
  $('stats').textContent = RAW.length + ' puntos crudos';
  $('trim0').max = $('trim1').max = Math.max(0, RAW.length-1);
  $('trim0').value = 0; $('trim1').value = Math.max(0, RAW.length-1);
  update();
  if (RAW.length > 1) {
    const b = RAW.reduce((b,c)=>b.extend(c), new maplibregl.LngLatBounds(RAW[0], RAW[0]));
    map.fitBounds(b, {padding: 70});
  }
}
function toUTC(local){ return new Date(local).toISOString(); }

// Douglas-Peucker in meter space
function simplify(pts, epsM){
  if (epsM <= 0 || pts.length < 3) return pts.slice();
  const mlon = 111320*Math.cos(18.46*Math.PI/180), mlat = 110570;
  const P = pts.map(c => [c[0]*mlon, c[1]*mlat]);
  const keep = new Array(pts.length).fill(false); keep[0] = keep[pts.length-1] = true;
  const stack = [[0, pts.length-1]];
  while (stack.length){
    const [a, b] = stack.pop();
    let maxD = 0, idx = -1;
    const [ax, ay] = P[a], [bx, by] = P[b];
    const dx = bx-ax, dy = by-ay, len2 = dx*dx+dy*dy;
    for (let i = a+1; i < b; i++){
      let t = len2 ? ((P[i][0]-ax)*dx + (P[i][1]-ay)*dy)/len2 : 0;
      t = Math.max(0, Math.min(1, t));
      const d = Math.hypot(P[i][0]-(ax+t*dx), P[i][1]-(ay+t*dy));
      if (d > maxD){ maxD = d; idx = i; }
    }
    if (maxD > epsM){ keep[idx] = true; stack.push([a, idx], [idx, b]); }
  }
  return pts.filter((_, i) => keep[i]);
}

function update(){
  let a = +$('trim0').value, b = +$('trim1').value;
  if (a > b) [a, b] = [b, a];
  $('l0').textContent = a; $('l1').textContent = b; $('leps').textContent = $('eps').value;
  const base = ALIGNED || RAW.slice(a, b+1);
  EDITED = ALIGNED ? ALIGNED : simplify(base, +$('eps').value);
  $('unalignBtn').disabled = !ALIGNED;
  map.getSource('raw') && map.getSource('raw').setData(fc(RAW));
  map.getSource('edited') && map.getSource('edited').setData(fc(EDITED));
  $('stats').textContent = RAW.length + ' crudos → ' + EDITED.length + ' editados' + (ALIGNED ? ' (alineados a calles)' : '');
}

async function align(){
  let a = +$('trim0').value, b = +$('trim1').value;
  if (a > b) [a, b] = [b, a];
  const pts = simplify(RAW.slice(a, b+1), Math.max(3, +$('eps').value));
  if (pts.length < 2) return;
  $('alignBtn').disabled = true; $('msg').textContent = 'alineando…';
  try {
    const out = [];
    for (let i = 0; i < pts.length; i += 90){
      const chunk = pts.slice(Math.max(0, i-1), i+90);
      const coords = chunk.map(c => c[0].toFixed(6)+','+c[1].toFixed(6)).join(';');
      const radiuses = chunk.map(() => 25).join(';');
      const r = await fetch('https://router.project-osrm.org/match/v1/driving/' + coords +
        '?overview=full&geometries=geojson&radiuses=' + radiuses);
      const d = await r.json();
      if (d.code !== 'Ok' || !d.matchings || !d.matchings.length) throw new Error(d.code || 'sin match');
      d.matchings.forEach(m => out.push(...m.geometry.coordinates));
    }
    ALIGNED = out;
    $('msg').textContent = 'alineado: ' + out.length + ' puntos sobre calles';
  } catch (e){
    $('msg').textContent = 'no se pudo alinear (' + e.message + ') — puedes guardar sin alinear';
  }
  $('alignBtn').disabled = false;
  update();
}

async function save(){
  if (EDITED.length < 2) { $('msg').textContent = 'carga y edita puntos primero'; return; }
  const body = {slug: $('slug').value, name: $('name').value, device: $('device').value.trim(),
    t0: $('t0').value, t1: $('t1').value, n_source: RAW.length, coordinates: EDITED};
  const r = await fetch('/api/route-drafts', {method:'POST',
    headers:{'Content-Type':'application/json', Authorization:'Bearer '+TOKEN}, body: JSON.stringify(body)});
  const d = await r.json();
  $('msg').textContent = r.ok ? 'guardado: ' + d.slug + ' — impórtalo con 14_import_drafts.py' : 'error: ' + (d.error||r.status);
  if (r.ok) boot();
}

function download(){
  if (EDITED.length < 2) return;
  const gj = {type:'FeatureCollection', properties:{name: $('name').value, source:'field ride (editor)'},
    features:[{type:'Feature', properties:{name: $('name').value, kind:'route_line'},
      geometry:{type:'LineString', coordinates: EDITED}}]};
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(gj)], {type:'application/geo+json'}));
  a.download = ($('slug').value || 'ruta') + '.geojson';
  a.click();
}

function renderDrafts(list){
  $('drafts').innerHTML = (list && list.length) ? '' : 'ninguno todavía';
  (list||[]).forEach(d => {
    const el = document.createElement('div');
    el.className = 'draft';
    el.innerHTML = '<b>' + d.name + '</b>' + d.slug + ' · ' + (d.n_source||'?') + ' pts crudos · ' + d.created_at + ' · ' + d.status +
      '<br><button class="ghost" data-a="load">Cargar</button><button class="ghost" data-a="del">Borrar</button>';
    el.querySelector('[data-a=load]').onclick = async () => {
      const r = await fetch('/api/route-drafts?slug=' + d.slug, {headers:{Authorization:'Bearer '+TOKEN}});
      const row = await r.json();
      RAW = JSON.parse(row.geometry); ALIGNED = null;
      $('name').value = row.name; $('slug').value = row.slug;
      $('trim0').max = $('trim1').max = RAW.length-1; $('trim0').value = 0; $('trim1').value = RAW.length-1;
      update();
      const b = RAW.reduce((b,c)=>b.extend(c), new maplibregl.LngLatBounds(RAW[0], RAW[0]));
      map.fitBounds(b, {padding:70});
    };
    el.querySelector('[data-a=del]').onclick = async () => {
      await fetch('/api/route-drafts?slug=' + d.slug, {method:'DELETE', headers:{Authorization:'Bearer '+TOKEN}});
      boot();
    };
    $('drafts').appendChild(el);
  });
}

if (TOKEN) boot();
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
