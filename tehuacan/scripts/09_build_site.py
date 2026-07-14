#!/usr/bin/env python3
"""Generate the quecombi.mx static site into /site (Cloudflare Pages ready).

Layout: shared header (brand + nav) / breadcrumbs / footer on every content page,
mobile-first CSS. Homepage redirects straight into the Tehuacán map (no second
click); the marketing copy lives at /acerca/.

  site/index.html                        meta-refresh -> /tehuacan/mapa/ (CF _redirects does a real 302)
  site/acerca/index.html                 about page (former landing copy)
  site/tehuacan/index.html               city hub: all routes, grouped, linked
  site/tehuacan/rutas/<slug>/index.html  per-route SEO page + embedded live map
  site/tehuacan/mapa/                    the interactive map app (copied)
  site/_redirects site/robots.txt site/sitemap.xml
"""
import csv
import html
import json
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
header.site nav{display:flex;gap:2px;margin-left:auto;overflow-x:auto}
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
.grid{display:grid;grid-template-columns:1fr;gap:10px;padding:0;list-style:none}
.card{border:1px solid var(--line);border-radius:12px;padding:12px;background:var(--panel)}
.card a{text-decoration:none;color:var(--ink);font-weight:600}
.card .sub{font-size:12.5px;color:var(--ink2);margin-top:3px}
.tag{font-size:11px;border:1px solid var(--line);border-radius:999px;padding:1px 8px;color:var(--ink2);vertical-align:middle}
.mapembed{width:100%;height:52vh;min-height:300px;border:1px solid var(--line);border-radius:12px;display:block}
footer.site{margin-top:36px;padding:18px 16px calc(18px + env(safe-area-inset-bottom));
 border-top:1px solid var(--line);font-size:13px;color:var(--ink2)}
footer.site .cols{max-width:900px;margin:0 auto;display:flex;flex-direction:column;gap:8px}
footer.site a{color:var(--ink2)}
@media(min-width:640px){
 h1{font-size:27px}
 .grid{grid-template-columns:repeat(auto-fill,minmax(250px,1fr))}
 .btn{display:inline-block;margin:6px 10px 6px 0}
 .mapembed{height:440px}
 footer.site .cols{flex-direction:row;justify-content:space-between}
}
"""

NAV = f"""<header class="site">
<a class="brand" href="/">Que<span>Combi</span></a>
<nav>
<a href="/{CITY}/mapa/" {{on_mapa}}>Mapa</a>
<a href="/{CITY}/" {{on_rutas}}>Rutas</a>
<a href="/acerca/" {{on_acerca}}>Acerca</a>
</nav>
</header>"""

FOOTER = f"""<footer class="site"><div class="cols">
<div>QueCombi — mapa libre y gratuito de las combis de México.<br>
Datos abiertos (ODbL) · código abierto (AGPL) · hecho con proyectos ciudadanos y OpenStreetMap.<br>
Built with ♥ in Tehuacán · <a href="https://github.com/mauriciotellezdev" rel="me">GitHub</a></div>
<div><a href="/{CITY}/mapa/">Mapa</a> · <a href="/{CITY}/">Rutas de {CITY_NAME}</a> · <a href="/acerca/">Acerca</a></div>
</div></footer>"""


def crumbs(items):
    """items: [(label, href|None)] — last item is the current page (no link)."""
    out = []
    for label, href in items:
        out.append(f'<a href="{href}">{html.escape(label)}</a>' if href else f'<span>{html.escape(label)}</span>')
    return '<nav class="crumbs" aria-label="ruta de navegación">' + '<span class="sep">›</span>'.join(out) + '</nav>'


def page(title, desc, body, canonical, active="", crumb_items=None):
    nav = NAV.format(on_mapa='class="on"' if active == "mapa" else "",
                     on_rutas='class="on"' if active == "rutas" else "",
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
    rows = list(csv.DictReader((ROOT / "data" / "master_route_index.csv").open()))
    routes_js = (ROOT / "map" / "routes.js").read_text().split("const ROUTES = ", 1)[1].rstrip().rstrip(";")
    geo_by_id = {f["properties"]["id"]: f for f in json.loads(routes_js)["features"]}

    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / CITY / "rutas").mkdir(parents=True)
    (SITE / "acerca").mkdir(parents=True)
    shutil.copytree(ROOT / "map", SITE / CITY / "mapa")

    urls = [f"{DOMAIN}/", f"{DOMAIN}/acerca/", f"{DOMAIN}/{CITY}/"]

    # ---- per-route pages
    cards_local, cards_for = [], []
    for r in rows:
        slug = r["route_key"]
        f = geo_by_id.get(slug)
        p = f["properties"] if f else {}
        name = r["display_name"]
        alias = r.get("known_as", "")
        title_name = name + (f" «{alias}»" if alias and alias not in name else "")
        places = (p.get("places") or "").strip()
        colonias = (p.get("colonias") or r.get("colonias", "")).replace("Colonia ", "").strip()
        kind = "foránea" if r["kind"] == "foránea" else "local"
        has_geom = bool(f and f["geometry"]["coordinates"])

        desc_bits = []
        if places:
            desc_bits.append("pasa por " + ", ".join(places.split(",")[:4]).strip())
        elif colonias:
            desc_bits.append("colonias: " + ", ".join(colonias.split(",")[:4]).strip())
        desc = f"{title_name} en {CITY_NAME}: recorrido, colonias y mapa de la combi. " + \
               (desc_bits[0].capitalize() + "." if desc_bits else "Ruta de transporte público.")

        if has_geom:
            mapblock = (f'<iframe class="mapembed" loading="lazy" title="Mapa del recorrido de {html.escape(title_name)}" '
                        f'src="/{CITY}/mapa/?embed=1&ruta={slug}"></iframe>')
        else:
            mapblock = ('<p class="muted">⚠️ Aún no tenemos el trazo de esta ruta en el mapa — sabemos que existe '
                        'y estamos por mapearla. ¿La conoces? Ayúdanos.</p>')

        body = f"""
<h1>{html.escape(title_name)} <span class="tag">{kind}</span></h1>
<p class="muted">Combi / transporte colectivo en {CITY_NAME}, Puebla</p>
{mapblock}
{'<h2>Pueblos y puntos en el camino</h2><p>' + html.escape(places) + '</p>' if places else ''}
{'<h2>Colonias que atiende</h2><p>' + html.escape(colonias) + '</p>' if colonias else ''}
<div class="btnrow">
<a class="btn" href="/{CITY}/mapa/?ruta={slug}">Ver en el mapa completo</a>
<a class="btn ghost" href="/{CITY}/">Todas las rutas de {CITY_NAME}</a>
</div>
<p class="muted">Fuentes: {html.escape(r["sources"])} · datos ciudadanos · actualizado 2026-07.
¿Algo cambió? El mapa se corrige con viajes reales — participa desde la app.</p>
"""
        out = SITE / CITY / "rutas" / slug / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page(f"{title_name} ({CITY_NAME}): recorrido, colonias y mapa | QueCombi",
                            desc, body, f"{DOMAIN}/{CITY}/rutas/{slug}/", active="rutas",
                            crumb_items=[("Inicio", "/"), (CITY_NAME, f"/{CITY}/"), (title_name, None)]),
                       encoding="utf-8")
        urls.append(f"{DOMAIN}/{CITY}/rutas/{slug}/")

        card = (f'<li class="card"><a href="/{CITY}/rutas/{slug}/">{html.escape(title_name)}</a>'
                f'<div class="sub">{html.escape(", ".join((places or colonias).split(",")[:3]))}</div></li>')
        (cards_for if kind == "foránea" else cards_local).append(card)

    # ---- city hub
    hub = f"""
<h1>Rutas de combis en {CITY_NAME}</h1>
<p>Las {len(rows)} rutas de transporte colectivo de {CITY_NAME}, Puebla — con recorridos,
colonias y planificador de viajes. Gratis, sin anuncios, datos abiertos.</p>
<div class="btnrow"><a class="btn" href="/{CITY}/mapa/">Abrir el mapa interactivo</a></div>
<h2>Rutas locales ({len(cards_local)})</h2>
<ul class="grid">{''.join(cards_local)}</ul>
<h2>Foráneas ({len(cards_for)})</h2>
<ul class="grid">{''.join(cards_for)}</ul>
"""
    (SITE / CITY / "index.html").write_text(
        page(f"Rutas de combis en {CITY_NAME} — mapa y recorridos | QueCombi",
             f"Mapa de las {len(rows)} rutas de combis de {CITY_NAME}: recorridos, colonias, "
             "y planificador ¿en qué combi me voy? Gratis y sin anuncios.",
             hub, f"{DOMAIN}/{CITY}/", active="rutas",
             crumb_items=[("Inicio", "/"), (CITY_NAME, None)]), encoding="utf-8")

    # ---- acerca (former landing copy)
    acerca = f"""
<h1>¿En qué combi me voy?</h1>
<p>QueCombi es el mapa libre y gratuito de las combis: busca tu ruta, planea tu viaje
de un punto a otro, y ayuda a mantener el mapa vivo con tus propios viajes.</p>
<div class="btnrow">
<a class="btn" href="/{CITY}/mapa/">Abrir el mapa de {CITY_NAME}</a>
<a class="btn ghost" href="/{CITY}/">Ver las rutas de {CITY_NAME}</a>
</div>
<h2>Apps para tu teléfono</h2>
<p class="muted">Muy pronto: app para Android y iPhone con planificador y modo colaborador.
Mientras tanto, el mapa funciona perfecto desde tu navegador.</p>
<h2>Proyecto abierto</h2>
<p class="muted">Todo el código es libre (AGPL) y los datos son abiertos (ODbL).
Construido sobre el trabajo de proyectos ciudadanos y OpenStreetMap.
Encontraste un problema de seguridad: security@quecombi.mx</p>
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
        f"/qr/* /{CITY}/mapa/?qr=:splat 302\n", encoding="utf-8")
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n", encoding="utf-8")
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")

    n_pages = len(list(SITE.rglob("index.html")))
    print(f"site built: {n_pages} pages, {len(urls)} sitemap urls -> {SITE}")


if __name__ == "__main__":
    main()
