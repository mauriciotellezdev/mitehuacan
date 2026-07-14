#!/usr/bin/env python3
"""Generate the quecombi.mx static site into /site (Cloudflare Pages ready).

Map-first: the homepage goes straight into the interactive map; the only content
page is /acerca/. (Per-route SEO pages were removed by decision 2026-07-14 —
`git log` has the last version if they ever earn their way back.)

  site/index.html               meta-refresh -> /tehuacan/mapa/ (CF _redirects does a real 302)
  site/acerca/index.html        about page
  site/tehuacan/mapa/           the interactive map app (copied from tehuacan/map)
  site/_redirects site/robots.txt site/sitemap.xml
"""
import html
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # tehuacan/
REPO = ROOT.parent
SITE = REPO / "site"
DOMAIN = "https://quecombi.mx"
CITY = "tehuacan"
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
<a class="brand" href="/">Que<span>Combi</span></a>
<nav>
<a href="/{CITY}/mapa/" {{on_mapa}}>Mapa</a>
<a href="/acerca/" {{on_acerca}}>Acerca</a>
</nav>
</header>"""

FOOTER = f"""<footer class="site"><div class="cols">
<div>QueCombi — mapa libre y gratuito de las combis de México.<br>
Datos abiertos (ODbL) · código abierto (AGPL) · hecho con proyectos ciudadanos y OpenStreetMap.<br>
Built with ♥ in Tehuacán · <a href="https://github.com/mauriciotellezdev" rel="me">GitHub</a></div>
<div><a href="/{CITY}/mapa/">Mapa</a> · <a href="/acerca/">Acerca</a></div>
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
    (SITE / "acerca").mkdir(parents=True)
    shutil.copytree(ROOT / "map", SITE / CITY / "mapa")

    # ---- acerca
    acerca = f"""
<h1>¿En qué combi me voy?</h1>
<p>QueCombi es el mapa libre y gratuito de las combis: busca tu ruta, planea tu viaje
de un punto a otro, y ayuda a mantener el mapa vivo con tus propios viajes.</p>
<div class="btnrow">
<a class="btn" href="/{CITY}/mapa/">Abrir el mapa de {CITY_NAME}</a>
</div>
<h2>Apps para tu teléfono</h2>
<p class="muted">Muy pronto: app para Android y iPhone con planificador y modo colaborador.
Mientras tanto, el mapa funciona perfecto desde tu navegador.</p>
<h2>Proyecto abierto</h2>
<p class="muted">Todo el código es libre (AGPL) y los datos son abiertos (ODbL).
Construido sobre el trabajo de proyectos ciudadanos y OpenStreetMap.
Problemas de seguridad: security@quecombi.mx</p>
"""
    (SITE / "acerca" / "index.html").write_text(
        page("Acerca de QueCombi — rutas y mapa de combis",
             "QueCombi: mapa libre y gratuito de las rutas de combis en México. "
             "Código abierto, datos abiertos. Empezamos en Tehuacán, Puebla.",
             acerca, f"{DOMAIN}/acerca/", active="acerca",
             crumb_items=[("Inicio", "/"), ("Acerca", None)]), encoding="utf-8")

    # ---- homepage: straight into the map, zero clicks
    (SITE / "index.html").write_text(f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>QueCombi — mapa de combis</title>
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url=/{CITY}/mapa/">
<link rel="canonical" href="{DOMAIN}/{CITY}/mapa/">
</head>
<body><p>Abriendo el mapa… <a href="/{CITY}/mapa/">continuar</a></p></body>
</html>""", encoding="utf-8")

    # ---- redirects (homepage + QR stickers), robots, sitemap
    (SITE / "_redirects").write_text(
        f"/ /{CITY}/mapa/ 302\n"
        f"# QR stickers: never break a printed code. Sticker IDs map here forever.\n"
        f"/qr/* /{CITY}/mapa/?qr=:splat 302\n"
        f"# legacy: route pages removed 2026-07 -> deep-link into the map\n"
        f"/{CITY}/rutas/* /{CITY}/mapa/?ruta=:splat 301\n"
        f"/{CITY}/ /{CITY}/mapa/ 302\n", encoding="utf-8")
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n", encoding="utf-8")
    urls = [f"{DOMAIN}/{CITY}/mapa/", f"{DOMAIN}/acerca/"]
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")

    n_pages = len(list(SITE.rglob("index.html")))
    print(f"site built: {n_pages} pages -> {SITE}")


if __name__ == "__main__":
    main()
