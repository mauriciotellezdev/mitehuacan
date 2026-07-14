#!/usr/bin/env python3
"""Generate the quecombi.mx static site into /site (Cloudflare Pages ready).

Structure:
  site/index.html                      landing (brand, QR target base)
  site/tehuacan/index.html             city hub: all routes, grouped, linked
  site/tehuacan/rutas/<slug>/index.html  per-route SEO page + SVG thumbnail
  site/tehuacan/mapa/                  the interactive map app (copied)
  site/_redirects  site/robots.txt  site/sitemap.xml
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

CSS = """
:root{--bg:#fff;--panel:#f7f7f8;--ink:#1a1a1e;--ink2:#55555e;--line:#e2e2e6;--accent:#0f62fe}
@media(prefers-color-scheme:dark){:root{--bg:#17171b;--panel:#1f1f24;--ink:#ececf0;--ink2:#a5a5b0;--line:#33333a;--accent:#6ea6ff}}
*{box-sizing:border-box}body{margin:0;font:16px/1.55 system-ui,-apple-system,sans-serif;color:var(--ink);background:var(--bg)}
.wrap{max-width:860px;margin:0 auto;padding:20px}
header.site{padding:14px 0;border-bottom:1px solid var(--line)}
header.site a{color:var(--ink);text-decoration:none;font-weight:700;font-size:18px}
header.site a span{color:var(--accent)}
h1{font-size:26px;margin:.6em 0 .3em}h2{font-size:19px;margin:1.4em 0 .5em}
p{margin:.5em 0}.muted{color:var(--ink2);font-size:14px}
a{color:var(--accent)}
.btn{display:inline-block;background:var(--accent);color:#fff;padding:11px 22px;border-radius:10px;
 text-decoration:none;font-weight:600;margin:6px 8px 6px 0}
.btn.ghost{background:var(--panel);color:var(--ink);border:1px solid var(--line)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px;padding:0;list-style:none}
.card{border:1px solid var(--line);border-radius:12px;padding:12px;background:var(--panel)}
.card a{text-decoration:none;color:var(--ink);font-weight:600}
.card .sub{font-size:12.5px;color:var(--ink2);margin-top:3px}
.tag{font-size:11px;border:1px solid var(--line);border-radius:999px;padding:1px 8px;color:var(--ink2)}
svg.thumb{width:100%;height:auto;background:var(--panel);border:1px solid var(--line);border-radius:12px}
footer{margin-top:40px;padding:18px 0;border-top:1px solid var(--line);font-size:13px;color:var(--ink2)}
"""


def page(title, desc, body, canonical):
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
<div class="wrap">
<header class="site"><a href="/">Que<span>Combi</span></a></header>
{body}
<footer>QueCombi — mapa libre y gratuito de las combis de México. Datos abiertos (ODbL),
código abierto (AGPL). Hecho con datos de proyectos ciudadanos y OpenStreetMap.
· <a href="/{CITY}/mapa/">Mapa interactivo</a></footer>
</div>
</body>
</html>"""


def svg_thumb(geom, w=560, h=300):
    pts = [c for part in geom["coordinates"] for c in part]
    if not pts:
        return ""
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    span = max(x1 - x0, (y1 - y0) * 1.35, 1e-6)
    pad = span * 0.06
    x0 -= pad; y1 += pad; span += 2 * pad

    def X(lon): return (lon - x0) / span * w
    def Y(lat): return (y1 - lat) / span * w * 0.74  # ~cos(18.46°) aspect fudge

    paths = []
    for part in geom["coordinates"]:
        if len(part) < 2:
            continue
        d = "M" + " L".join(f"{X(c[0]):.1f} {Y(c[1]):.1f}" for c in part)
        paths.append(f'<path d="{d}" fill="none" stroke="var(--accent)" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')
    return (f'<svg class="thumb" viewBox="0 0 {w} {h}" role="img" aria-label="croquis del recorrido">'
            + "".join(paths) + "</svg>")


def main():
    rows = list(csv.DictReader((ROOT / "data" / "master_route_index.csv").open()))
    routes_js = (ROOT / "map" / "routes.js").read_text().split("const ROUTES = ", 1)[1].rstrip().rstrip(";")
    geo_by_id = {f["properties"]["id"]: f for f in json.loads(routes_js)["features"]}

    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / CITY / "rutas").mkdir(parents=True)
    shutil.copytree(ROOT / "map", SITE / CITY / "mapa")

    urls = [f"{DOMAIN}/", f"{DOMAIN}/{CITY}/"]

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

        desc_bits = []
        if places:
            desc_bits.append("pasa por " + ", ".join(places.split(",")[:4]).strip())
        elif colonias:
            desc_bits.append("colonias: " + ", ".join(colonias.split(",")[:4]).strip())
        desc = f"{title_name} en {CITY_NAME}: recorrido, colonias y mapa de la combi. " + \
               (desc_bits[0].capitalize() + "." if desc_bits else "Ruta de transporte público.")

        thumb = svg_thumb(f["geometry"]) if f and f["geometry"]["coordinates"] else \
            '<p class="muted">⚠️ Aún no tenemos el trazo de esta ruta en el mapa — sabemos que existe y estamos por mapearla. ¿La conoces? Ayúdanos.</p>'

        body = f"""
<h1>{html.escape(title_name)} <span class="tag">{kind}</span></h1>
<p class="muted">Combi / transporte colectivo en {CITY_NAME}, Puebla</p>
{thumb}
{'<h2>Pueblos y puntos en el camino</h2><p>' + html.escape(places) + '</p>' if places else ''}
{'<h2>Colonias que atiende</h2><p>' + html.escape(colonias) + '</p>' if colonias else ''}
<p><a class="btn" href="/{CITY}/mapa/">Ver en el mapa interactivo</a>
<a class="btn ghost" href="/{CITY}/">Todas las rutas de {CITY_NAME}</a></p>
<p class="muted">Fuentes: {html.escape(r["sources"])} · datos ciudadanos ·
actualizado 2026-07. ¿Algo cambió? El mapa se corrige con viajes reales — participa desde la app.</p>
"""
        out = SITE / CITY / "rutas" / slug / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page(f"{title_name} ({CITY_NAME}): recorrido, colonias y mapa | QueCombi",
                            desc, body, f"{DOMAIN}/{CITY}/rutas/{slug}/"), encoding="utf-8")
        urls.append(f"{DOMAIN}/{CITY}/rutas/{slug}/")

        card = (f'<li class="card"><a href="/{CITY}/rutas/{slug}/">{html.escape(title_name)}</a>'
                f'<div class="sub">{html.escape(", ".join((places or colonias).split(",")[:3]))}</div></li>')
        (cards_for if kind == "foránea" else cards_local).append(card)

    # ---- city hub
    hub = f"""
<h1>Rutas de combis en {CITY_NAME}</h1>
<p>Las {len(rows)} rutas de transporte colectivo de {CITY_NAME}, Puebla — con recorridos,
colonias y planificador de viajes. Gratis, sin anuncios, datos abiertos.</p>
<p><a class="btn" href="/{CITY}/mapa/">Abrir el mapa interactivo</a></p>
<h2>Rutas locales ({len(cards_local)})</h2>
<ul class="grid">{''.join(cards_local)}</ul>
<h2>Foráneas ({len(cards_for)})</h2>
<ul class="grid">{''.join(cards_for)}</ul>
"""
    (SITE / CITY / "index.html").write_text(
        page(f"Rutas de combis en {CITY_NAME} — mapa y recorridos | QueCombi",
             f"Mapa de las {len(rows)} rutas de combis de {CITY_NAME}: recorridos, colonias, "
             "y planificador ¿en qué combi me voy? Gratis y sin anuncios.",
             hub, f"{DOMAIN}/{CITY}/"), encoding="utf-8")

    # ---- landing
    landing = f"""
<h1>¿En qué combi me voy?</h1>
<p>QueCombi es el mapa libre y gratuito de las combis: busca tu ruta, planea tu viaje
de un punto a otro, y ayuda a mantener el mapa vivo con tus propios viajes.</p>
<p>
<a class="btn" href="/{CITY}/mapa/">Abrir el mapa de {CITY_NAME}</a>
<a class="btn ghost" href="/{CITY}/">Ver las rutas de {CITY_NAME}</a>
</p>
<h2>Apps para tu teléfono</h2>
<p class="muted">Muy pronto: app para Android y iPhone con planificador y modo colaborador.
Mientras tanto, el mapa funciona perfecto desde tu navegador.</p>
<h2>Proyecto abierto</h2>
<p class="muted">Todo el código es libre (AGPL) y los datos son abiertos (ODbL).
Construido sobre el trabajo de proyectos ciudadanos y OpenStreetMap.</p>
"""
    (SITE / "index.html").write_text(
        page("QueCombi — ¿en qué combi me voy? Rutas y mapa de combis",
             "Mapa libre y gratuito de las rutas de combis en México. Busca tu ruta, "
             "planea tu viaje y llega. Empezamos en Tehuacán, Puebla.",
             landing, f"{DOMAIN}/"), encoding="utf-8")

    # ---- redirects (QR slugs), robots, sitemap
    (SITE / "_redirects").write_text(
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
