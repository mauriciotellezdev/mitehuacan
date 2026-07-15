#!/usr/bin/env python3
"""Generate the mitehuacan.mx static site into /site (Cloudflare Pages ready).

Map-first: the homepage goes straight into the interactive map; the only content
page is /combis/acerca/. (Per-route SEO pages were removed by decision 2026-07-14 —
`git log` has the last version if they ever earn their way back.)

  site/index.html               meta-refresh -> /combis/ (CF _redirects does a real 302)
  site/combis/                  the interactive map app (copied from tehuacan/map)
  site/combis/acerca/           about page
  site/_redirects site/robots.txt site/sitemap.xml
"""
import html
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # tehuacan/
REPO = ROOT.parent
SITE = REPO / "site"
DOMAIN = "https://mitehuacan.mx"
SECTION = "combis"
CITY_NAME = "Tehuacán"

# mobile-first: base styles are the phone layout; min-width queries add desktop touches
CSS = """
:root{--bg:#fff;--panel:#f7f7f8;--ink:#1a1a1e;--ink2:#55555e;--line:#e2e2e6;--accent:#0f62fe;--chip:#fff}
@media(prefers-color-scheme:dark){:root{--bg:#17171b;--panel:#1f1f24;--ink:#ececf0;--ink2:#a5a5b0;--line:#33333a;--accent:#6ea6ff;--chip:#26262c}}
*{box-sizing:border-box}
body{margin:0;font:16px/1.55 system-ui,-apple-system,sans-serif;color:var(--ink);background:var(--bg)}
header.site{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:10px;
 padding:0 14px;height:50px;border-bottom:1px solid var(--line);background:var(--panel)}
header.site .brand{color:var(--ink);text-decoration:none;font-weight:700;font-size:17px;flex:none}
header.site .brand span{color:var(--accent)}
header.site nav{display:flex;gap:2px;margin-left:auto}
header.site nav a{color:var(--ink2);text-decoration:none;font-size:14px;padding:6px 10px;border-radius:8px;white-space:nowrap}
header.site nav a.on,header.site nav a:active{color:var(--ink);background:var(--chip)}
.crumbs{font-size:13px;color:var(--ink2);padding:10px 0 0}
.crumbs a{color:var(--ink2);text-decoration:none}
.crumbs a:active,.crumbs a:hover{color:var(--accent)}
.crumbs .sep{margin:0 6px;opacity:.6}
.wrap{max-width:900px;margin:0 auto;padding:0 16px 28px}
h1{font-size:23px;margin:.7em 0 .35em;line-height:1.25}
h2{font-size:18px;margin:1.5em 0 .5em}
p{margin:.5em 0}.muted{color:var(--ink2);font-size:14px}
a{color:var(--accent)}
.btn{display:block;text-align:center;background:var(--accent);color:#fff;padding:12px 20px;border-radius:10px;
 text-decoration:none;font-weight:600;margin:8px 0}
.btn.ghost{background:var(--panel);color:var(--ink);border:1px solid var(--line)}
.btnrow{margin:14px 0}
form#report-form{display:flex;flex-direction:column;gap:10px;max-width:560px}
form#report-form input[type=text],form#report-form textarea{width:100%;padding:11px 12px;
 border:1px solid var(--line);border-radius:10px;background:var(--panel);color:var(--ink);
 font:inherit;font-size:15px}
form#report-form input:focus,form#report-form textarea:focus{outline:2px solid var(--accent);outline-offset:-1px}
form#report-form .btn{margin:0;border:none;cursor:pointer;font:inherit;font-weight:600}
footer.site{margin-top:36px;padding:18px 16px calc(18px + env(safe-area-inset-bottom));
 border-top:1px solid var(--line);font-size:13px;color:var(--ink2)}
footer.site .cols{max-width:900px;margin:0 auto;display:flex;flex-direction:column;gap:8px}
footer.site a{color:var(--ink2)}
@media(min-width:640px){
 h1{font-size:27px}
 .btn{display:inline-block;margin:6px 10px 6px 0}
 footer.site .cols{flex-direction:row;justify-content:space-between}
}
"""

NAV = f"""<header class="site">
<a class="brand" href="/combis/">mi<span>tehuacan</span>.mx <span style="color:var(--ink2);font-weight:400">· Combis</span></a>
<nav>
<a href="/{SECTION}/" {{on_mapa}}>Mapa</a>
<a href="/{SECTION}/acerca/" {{on_acerca}}>Acerca</a>
</nav>
</header>"""

FOOTER = f"""<footer class="site"><div class="cols">
<div>MiTehuacán Combis — mapa libre y gratuito de las combis de Tehuacán.<br>
Datos abiertos (ODbL) · código abierto (AGPL) · hecho con proyectos ciudadanos y OpenStreetMap.<br>
Built with ♥ in Tehuacán · <a href="https://github.com/mauriciotellezdev" rel="me">GitHub</a></div>
<div><a href="/{SECTION}/">Mapa</a> · <a href="/{SECTION}/acerca/">Acerca</a></div>
</div></footer>"""


def crumbs(items):
    out = []
    for label, href in items:
        out.append(f'<a href="{href}">{html.escape(label)}</a>' if href else f'<span>{html.escape(label)}</span>')
    return '<nav class="crumbs" aria-label="ruta de navegación">' + '<span class="sep">›</span>'.join(out) + '</nav>'


def page(title, desc, body, canonical, active="", crumb_items=None):
    nav = NAV.format(on_mapa='class="on"' if active == "mapa" else "",
                     on_acerca='class="on"' if active == "acerca" else "")
    bc = crumbs(crumb_items) if crumb_items else ""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{canonical}">
<style>{CSS}</style>
</head>
<body>
{nav}
<div class="wrap">
{bc}
{body}
</div>
{FOOTER}
</body>
</html>"""


def main():
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    shutil.copytree(ROOT / "map", SITE / SECTION)
    (SITE / SECTION / "acerca").mkdir(parents=True)

    # ---- acerca
    acerca = f"""
<h1>¿En qué combi me voy?</h1>
<p>MiTehuacán es el mapa libre y gratuito de las combis: busca tu ruta, planea tu viaje
de un punto a otro, y ayuda a mantener el mapa vivo con tus propios viajes.</p>
<div class="btnrow">
<a class="btn" href="/{SECTION}/">Abrir el mapa de {CITY_NAME}</a>
</div>
<h2>Apps para tu teléfono</h2>
<p class="muted">Muy pronto: app para Android y iPhone con planificador y modo colaborador.
Mientras tanto, el mapa funciona perfecto desde tu navegador.</p>
<h2 id="rutas-que-faltan">Rutas que faltan — ¿las conoces?</h2>
<p>Sabemos que estas rutas existen, pero todavía no están en el mapa:</p>
<ul>
<li><strong>Las combis «Tecoxteo» (corredor a Coxcatlán)</strong> — Tehuacán → Tequexco →
San Sebastián Zinacatepec → Coxcatlán; al menos 2 variantes (una conecta desde Ajalpan
y otra pasa de largo por Zinacatepec)</li>
<li><strong>San José</strong> — falta la ruta de San José (¿Buena Vista? ¿las Minas? ¿Monte Chiquito?)</li>
</ul>
<p>¿Conoces una de estas — o cualquier otra que no aparezca en el mapa? Cuéntanos:</p>
<form id="report-form">
<input type="text" name="nombre" maxlength="80" required
 placeholder="Nombre de la ruta (como está pintado en la combi)">
<textarea name="descripcion" maxlength="1500" rows="5" required
 placeholder="¿Por dónde pasa? Calles, colonias, paradas, de dónde sale y a dónde llega…"></textarea>
<input type="text" name="website" tabindex="-1" autocomplete="off" aria-hidden="true"
 style="position:absolute;left:-9999px">
<button type="submit" class="btn" id="report-send">Enviar</button>
<p class="muted" id="report-status"></p>
</form>
<script>
document.getElementById('report-form').addEventListener('submit', async e => {{
  e.preventDefault();
  const f = e.target, st = document.getElementById('report-status');
  const data = {{nombre: f.nombre.value.trim(), descripcion: f.descripcion.value.trim(),
               website: f.website.value, ciudad: 'tehuacan'}};
  if (!data.nombre || !data.descripcion) return;
  document.getElementById('report-send').disabled = true;
  st.textContent = 'Enviando…';
  try {{
    const r = await fetch('/api/reportes', {{method: 'POST',
      headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(data)}});
    if (!r.ok) throw new Error(r.status);
    st.textContent = '¡Gracias! Tu reporte nos ayuda a completar el mapa.';
    f.reset();
  }} catch (err) {{
    st.innerHTML = 'No se pudo enviar ahora mismo. Copia tu reporte y mándalo cuando tengas conexión:<br><br>' +
      '<code style="user-select:all;display:block;padding:8px;border:1px solid var(--line);border-radius:8px">Ruta: ' +
      data.nombre.replace(/</g,'&lt;') + ' — ' + data.descripcion.replace(/</g,'&lt;') + '</code>';
  }}
  document.getElementById('report-send').disabled = false;
}});
</script>

<h2>Proyecto abierto</h2>
<p class="muted">Todo el código es libre (AGPL) y los datos son abiertos (ODbL).
Construido sobre el trabajo de proyectos ciudadanos.
Problemas de seguridad: security@mitehuacan.mx</p>
<h2>Créditos y licencias</h2>
<p class="muted">Mapa base © <a href="https://www.openstreetmap.org/copyright">colaboradores de OpenStreetMap</a> (ODbL) ·
teselas de <a href="https://openfreemap.org">OpenFreeMap</a> ·
búsqueda de direcciones vía Photon/Nominatim (datos OSM) ·
geometrías de rutas derivadas de proyectos ciudadanos
(<a href="http://rutastehuacan.th1.mx/">rutastehuacan</a>, <a href="https://queruta.mx/">queruta</a>) ·
datos de MiTehuacán publicados bajo ODbL.</p>
"""
    (SITE / SECTION / "acerca" / "index.html").write_text(
        page("Acerca de MiTehuacán — rutas y mapa de combis",
             "MiTehuacán: mapa libre y gratuito de las rutas de combis en México. "
             "Código abierto, datos abiertos. Empezamos en Tehuacán, Puebla.",
             acerca, f"{DOMAIN}/{SECTION}/acerca/", active="acerca",
             crumb_items=[("Inicio", "/"), ("Acerca", None)]), encoding="utf-8")

    # ---- homepage: straight into the map, zero clicks
    (SITE / "index.html").write_text(f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>MiTehuacán — mapa de combis</title>
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url=/{SECTION}/">
<link rel="canonical" href="{DOMAIN}/{SECTION}/">
</head>
<body><p>Abriendo el mapa… <a href="/{SECTION}/">continuar</a></p></body>
</html>""", encoding="utf-8")

    # ---- redirects (homepage + QR stickers), robots, sitemap
    (SITE / "_redirects").write_text(
        f"/ /{SECTION}/ 302\n"
        f"# QR stickers: never break a printed code. Sticker IDs map here forever.\n"
        f"/qr/* /{SECTION}/?qr=:splat 302\n"
        f"# legacy: route pages removed 2026-07 -> deep-link into the map\n"
        f"/tehuacan/rutas/* /{SECTION}/?ruta=:splat 301\n"
        f"/tehuacan/mapa/* /{SECTION}/ 301\n"
        f"/tehuacan/ /{SECTION}/ 301\n"
        f"/acerca/ /{SECTION}/acerca/ 301\n"
        , encoding="utf-8")
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n", encoding="utf-8")
    urls = [f"{DOMAIN}/{SECTION}/", f"{DOMAIN}/{SECTION}/acerca/"]
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")

    n_pages = len(list(SITE.rglob("index.html")))
    print(f"site built: {n_pages} pages -> {SITE}")


if __name__ == "__main__":
    main()
