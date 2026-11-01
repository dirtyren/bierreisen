#!/usr/bin/env python3
"""Build the blog: one post per trip, per city and per brewery, in EN / PT-BR / DE.

Content lives in blog/data/<slug>.json. Every text field is either a string (same in
all languages) or a {"en": ..., "pt": ..., "de": ...} object.
"""
from __future__ import annotations

import html
import json
import pathlib
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from blog_strings import LANG_ATTR, LANGS, SECTION_KEY, SITE, TYPE_KEY, UI  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "blog" / "data"
TEMPLATE = (ROOT / "scripts" / "blog_template.html").read_text()
INDEX_TEMPLATE = (ROOT / "scripts" / "blog_index_template.html").read_text()
OG_LOCALE = {"en": "en_GB", "pt": "pt_BR", "de": "de_DE"}

REQUIRED = ("slug", "type", "name", "coords", "lede", "sections")

# Country and region names in the `where` line are content, not interface copy, so
# they are localised at render time rather than duplicated in every JSON file.
PLACES = {
    "Germany": ("Germany", "Alemanha", "Deutschland"),
    "Belgium": ("Belgium", "Bélgica", "Belgien"),
    "Netherlands": ("Netherlands", "Países Baixos", "Niederlande"),
    "Czechia": ("Czechia", "Tchéquia", "Tschechien"),
    "Austria": ("Austria", "Áustria", "Österreich"),
    "Italy": ("Italy", "Itália", "Italien"),
    "Bavaria": ("Bavaria", "Baviera", "Bayern"),
    "West Flanders": ("West Flanders", "Flandres Ocidental", "Westflandern"),
    "East Flanders": ("East Flanders", "Flandres Oriental", "Ostflandern"),
    "North Rhine-Westphalia": ("North Rhine-Westphalia", "Renânia do Norte-Vestfália", "Nordrhein-Westfalen"),
    "Brussels-Capital Region": ("Brussels-Capital Region", "Região de Bruxelas-Capital",
                                "Region Brüssel-Hauptstadt"),
}
MONTHS = {
    "January": ("janeiro", "Januar"), "February": ("fevereiro", "Februar"),
    "March": ("março", "März"), "April": ("abril", "April"), "May": ("maio", "Mai"),
    "June": ("junho", "Juni"), "July": ("julho", "Juli"), "August": ("agosto", "August"),
    "September": ("setembro", "September"), "October": ("outubro", "Oktober"),
    "November": ("novembro", "November"), "December": ("dezembro", "Dezember"),
}
MONTH_RE = "|".join(MONTHS)


def localize_where(where: str, lang: str) -> str:
    if lang == "en" or not where:
        return where
    import re as _re
    out = where
    for token, (_en, pt, de) in PLACES.items():
        out = _re.sub(rf"(?<![\w-]){_re.escape(token)}(?![\w-])", pt if lang == "pt" else de, out)
    for en_m, (pt_m, de_m) in MONTHS.items():
        out = _re.sub(rf"\b{en_m}\b", pt_m if lang == "pt" else de_m, out)
    out = out.replace(" and ", " e " if lang == "pt" else " und ")
    out = out.replace("planned", "planejada" if lang == "pt" else "geplant")
    if lang == "pt":
        out = _re.sub(rf"\b({MONTH_RE}) (\d{{4}})", r"\1 de \2", out)
    return out


def t(v, lang: str) -> str:
    if isinstance(v, dict):
        return v.get(lang) or v.get("en") or ""
    return "" if v is None else str(v)


def e(v) -> str:
    return html.escape(str(v), quote=True)


def post_path(lang: str, slug: str) -> str:
    return f"blog/{lang}/{slug}/index.html"


def post_url(lang: str, slug: str) -> str:
    return f"{SITE}/{post_path(lang, slug)}"


def index_path(lang: str) -> str:
    return f"blog/{lang}/index.html"


def first_sentence(text: str, limit: int = 158) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    stop = max(cut.rfind(". "), cut.rfind("; "), cut.rfind(", "))
    return (cut[:stop] if stop > 90 else cut[:limit - 1]).rstrip(" ,;.") + "…"


def teaser(text: str, limit: int = 150) -> str:
    """Cut at a word boundary; never mid-word."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut:
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(" ,;:.") + "…"


def maps_for(entity: dict) -> str:
    if entity.get("maps"):
        return entity["maps"]
    lat, lon = entity["coords"]
    q = f"{entity['name']} {entity.get('where', '')}".strip()
    return ("https://www.google.com/maps/search/?api=1&query="
            + urllib.parse.quote_plus(q) + f"&center={lat},{lon}&zoom=16")


def check_links(entity: dict, lang: str) -> str:
    name = entity["name"]
    where = entity.get("where", "")
    q = urllib.parse.quote_plus(f"{name} {where}".strip())
    out = [("Google Maps", f"https://www.google.com/maps/search/?api=1&query={q}"),
           ("Untappd", f"https://untappd.com/search?q={urllib.parse.quote_plus(name)}"),
           ("RateBeer", f"https://www.ratebeer.com/search?q={urllib.parse.quote_plus(name)}"),
           ("BeerAdvocate", f"https://www.beeradvocate.com/search/?q={urllib.parse.quote_plus(name)}")]
    return "".join(f'<a href="{u}" target="_blank" rel="noopener noreferrer">{e(n)}</a>'
                   for n, u in out)


def section_html(entity: dict, lang: str) -> str:
    parts = []
    for sec in entity["sections"]:
        parts.append(f"    <h2>{e(t(sec['h'], lang))}</h2>")
        for p in sec.get("p", []):
            parts.append(f"    <p>{t(p, lang)}</p>")
    return "\n".join(parts)


def list_html(items, lang: str) -> str:
    return "".join(f"<li>{t(i, lang)}</li>" for i in items)


def glance_html(entity: dict, lang: str) -> str:
    rows = []
    for stat in entity.get("stats", [])[:6]:
        rows.append(f'<div><b>{e(t(stat["v"], lang))}</b> <span>{e(t(stat["k"], lang))}</span></div>')
    return "".join(rows)


def meta_html(entity: dict, lang: str, ui: dict) -> str:
    bits = [e(ui[TYPE_KEY[entity["type"]]])]
    if entity.get("where"):
        bits.append(e(localize_where(entity["where"], lang)))
    trips = entity.get("trips") or []
    if entity["type"] == "trip":
        tr = entity.get("trip_stats", "")
        if tr:
            bits.append(e(tr))
    elif trips:
        label = ui["planned"] if entity["type"] == "trip" else ui["visited"]
        bits.append(f'{e(label)} {e(", ".join(trips))}')
    return " · ".join(bits)


def related_html(entity: dict, lang: str, by_slug: dict) -> str:
    out = []
    for slug in entity.get("related", [])[:4]:
        other = by_slug.get(slug)
        if not other:
            continue
        title = t(other["name"], lang)
        kind = t(UI[lang][TYPE_KEY[other["type"]]], lang)
        out.append(f'<li><a href="../../{lang}/{slug}/index.html">{e(title)}</a> '
                   f'<span>— {e(kind)}</span></li>')
    return "".join(out)


def switch_html(lang: str, slug: str | None) -> str:
    out = []
    for other in LANGS:
        label = {"en": "EN", "pt": "PT", "de": "DE"}[other]
        href = f"../../{other}/{slug}/index.html" if slug else f"../{other}/index.html"
        cur = ' aria-current="page"' if other == lang else ""
        out.append(f'<a href="{href}" hreflang="{LANG_ATTR[other]}" lang="{LANG_ATTR[other]}"{cur}>'
                   f'{label}</a>')
    return "".join(out)


def hreflang_block(slug: str | None) -> str:
    rows = []
    for lang in LANGS:
        href = post_url(lang, slug) if slug else f"{SITE}/{index_path(lang)}"
        rows.append(f'<link rel="alternate" hreflang="{LANG_ATTR[lang]}" href="{href}">')
    href = f"{SITE}/blog/{slug}/" if slug else f"{SITE}/blog/"
    rows.append(f'<link rel="alternate" hreflang="x-default" href="{href}">')
    return "\n".join(rows)


def jsonld(entity: dict, lang: str, title: str, desc: str, image: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": desc,
        "inLanguage": LANG_ATTR[lang],
        "image": image,
        "author": {"@type": "Person", "name": "Ren"},
        "publisher": {"@type": "Organization", "name": "Bier Reisen"},
        "mainEntityOfPage": post_url(lang, entity["slug"]),
        "about": {"@type": "Place", "name": entity["name"],
                  "geo": {"@type": "GeoCoordinates", "latitude": entity["coords"][0],
                          "longitude": entity["coords"][1]}},
    }
    return json.dumps(data, ensure_ascii=False)


def render_post(entity: dict, lang: str, by_slug: dict) -> str:
    ui = UI[lang]
    slug = entity["slug"]
    name = t(entity["name"], lang)
    lede = t(entity["lede"], lang)
    title = f"{name} — Bier Reisen"
    image_rel = f"../../../blog/assets/{slug}.png"
    image_abs = f"{SITE}/blog/assets/{slug}.png"
    if entity["type"] == "trip":
        image_rel = "../../../" + entity["image"].lstrip("/")
        image_abs = f"{SITE}/{entity['image'].lstrip('/')}"

    lat, lon = entity["coords"]
    coords = f"{abs(lat):.4f}° {'N' if lat >= 0 else 'S'} · {abs(lon):.4f}° {'E' if lon >= 0 else 'W'}"

    nearby = entity.get("nearby_text")
    if nearby:
        nearby_html = t(nearby, lang)
    else:
        links = []
        for trip in entity.get("trips", [])[:4]:
            trip_slug = f"trip-{trip}"
            other = by_slug.get(trip_slug)
            label = f"{trip}" if not other else t(other["name"], lang)
            links.append(f'<a href="../../{lang}/{trip_slug}/index.html">{e(label)}</a>')
        nearby_html = f'{e(ui["nearby"])}: ' + " · ".join(links) if links else ""

    page = (TEMPLATE
            .replace("__LANG_ATTR__", LANG_ATTR[lang])
            .replace("__TITLE__", e(title))
            .replace("__DESC__", e(first_sentence(lede)))
            .replace("__OG_TITLE__", e(title))
            .replace("__OG_DESC__", e(first_sentence(lede)))
            .replace("__OG_IMAGE__", e(image_abs))
            .replace("__OG_LOCALE__", OG_LOCALE[lang])
            .replace("__CANONICAL__", post_url(lang, slug))
            .replace("__HREFLANG__", hreflang_block(slug))
            .replace("__JSONLD__", jsonld(entity, lang, title, first_sentence(lede), image_abs))
            .replace("__BASE__", "../../../")
            .replace("__BLOG__", "../../")
            .replace("__SKIP__", e(ui["skip"]))
            .replace("__CRUMB_LABEL__", e(ui["crumb_label"]))
            .replace("__BLOG_LABEL__", e(ui["blog_label"]))
            .replace("__CRUMB_HERE__", e(name))
            .replace("__LANG_LABEL__", e(ui["lang_label"] if "lang_label" in ui else "Language"))
            .replace("__SWITCH__", switch_html(lang, slug))
            .replace("__H1__", e(name))
            .replace("__LEDE__", e(lede))
            .replace("__META__", meta_html(entity, lang, ui))
            .replace("__IMAGE__", e(image_rel))
            .replace("__IMAGE_ALT__", e(t(entity.get("image_alt", name), lang)))
            .replace("__CAPTION__", e(t(entity.get("caption", ui["caption_default"]), lang)))
            .replace("__GLANCE__", glance_html(entity, lang))
            .replace("__SECTIONS__", section_html(entity, lang))
            .replace("__ORDER_H__", e(ui["order_h"]))
            .replace("__ORDER__", list_html(entity.get("order", []), lang))
            .replace("__EAT_H__", e(ui["eat_h"]))
            .replace("__EAT__", list_html(entity.get("eat", []), lang))
            .replace("__TIPS_H__", e(ui["tips_h"]))
            .replace("__TIPS__", list_html(entity.get("tips", []), lang))
            .replace("__WHERE_H__", e(ui["where_h"]))
            .replace("__MAPS__", e(maps_for(entity)))
            .replace("__MAPS_LABEL__", e(ui["maps_label"]))
            .replace("__COORDS__", e(coords))
            .replace("__NEARBY__", nearby_html)
            .replace("__CHECK__", f'<span style="color:var(--dim)">{e(ui["check_label"])}:</span> '
                                  + check_links(entity, lang))
            .replace("__NEXT_H__", e(ui["next_h"]))
            .replace("__RELATED__", related_html(entity, lang, by_slug))
            .replace("__FOOT_A__", e(ui["foot_a"]))
            .replace("__FOOT_INDEX__", e(ui["foot_index"]))
            .replace("__FOOT_ARCHIVE__", e(ui["foot_archive"])))
    return page


def render_index(entities: list[dict], lang: str) -> str:
    ui = UI[lang]
    order = {"trip": 0, "city": 1, "brewery": 2}
    entities = sorted(entities, key=lambda x: (order[x["type"]], -int(x.get("trips", ["0"])[0][:4] or 0), x["slug"]))
    rows = []
    for ent in entities:
        name = t(ent["name"], lang)
        kind = ui[TYPE_KEY[ent["type"]]]
        where = localize_where(t(ent.get("where", ""), lang), lang)
        lede = teaser(t(ent["lede"], lang), 150)
        plate = ROOT / "blog" / "assets" / f"{ent['slug']}.png"
        image = (f"../assets/{ent['slug']}.png" if plate.exists()
                 else f"../../{ent['image'].lstrip('/')}")
        rows.append(
            f'<li class="post" data-type="{ent["type"]}" '
            f'data-search="{e((name + " " + where + " " + t(ent["lede"], lang)).lower())}">'
            f'<a class="thumb" href="{ent["slug"]}/index.html" tabindex="-1" aria-hidden="true">'
            f'<img src="{e(image)}" alt="" loading="lazy"></a>'
            f'<div><p class="kind">{e(kind)}{" · " + e(where) if where else ""}</p>'
            f'<h3><a href="{ent["slug"]}/index.html">{e(name)}</a></h3>'
            f'<p class="teaser">{e(lede)}</p></div></li>')

    page = (INDEX_TEMPLATE
            .replace("__LANG_ATTR__", LANG_ATTR[lang])
            .replace("__TITLE__", e(ui["index_title"]))
            .replace("__DESC__", e(ui["index_desc"]))
            .replace("__CANONICAL__", f"{SITE}/{index_path(lang)}")
            .replace("__HREFLANG__", hreflang_block(None))
            .replace("__BASE__", "../../")
            .replace("__SKIP__", e(ui["skip"]))
            .replace("__LANG_LABEL__", e(ui.get("lang_label", "Language")))
            .replace("__SWITCH__", switch_html(lang, None))
            .replace("__H1__", e(ui["index_h1"]))
            .replace("__LEDE__", e(ui["index_lede"]))
            .replace("__SEARCH_PH__", e(ui["search_ph"]))
            .replace("__F_ALL__", e(ui["f_all"]))
            .replace("__F_TRIP__", e(ui["f_trip"]))
            .replace("__F_CITY__", e(ui["f_city"]))
            .replace("__F_BREWERY__", e(ui["f_brewery"]))
            .replace("__COUNT__", e(ui["count"]))
            .replace("__EMPTY_A__", e(ui["empty_a"]))
            .replace("__EMPTY_B__", e(ui["empty_b"]))
            .replace("__READ__", e(ui["read"]))
            .replace("__POSTS__", "".join(rows))
            .replace("__N_ALL__", str(len(entities)))
            .replace("__N_TRIP__", str(sum(1 for x in entities if x["type"] == "trip")))
            .replace("__N_CITY__", str(sum(1 for x in entities if x["type"] == "city")))
            .replace("__N_BREWERY__", str(sum(1 for x in entities if x["type"] == "brewery"))))
    return page


def main() -> int:
    files = sorted(DATA.glob("*.json"))
    entities, problems = [], []
    for f in files:
        ent = json.loads(f.read_text())
        missing = [k for k in REQUIRED if k not in ent]
        if missing:
            problems.append(f"{f.name}: missing {missing}")
            continue
        for key in ("lede", "sections"):
            pass
        entities.append(ent)
    if problems:
        print("\n".join(problems))
        return 1

    by_slug = {x["slug"]: x for x in entities}
    dupes = len(entities) - len(by_slug)
    if dupes:
        print(f"duplicate slugs: {dupes}")
        return 1

    written = 0
    for lang in LANGS:
        out_dir = ROOT / "blog" / lang
        for ent in entities:
            page = render_post(ent, lang, by_slug)
            dest = ROOT / post_path(lang, ent["slug"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(page, encoding="utf-8")
            written += 1
        idx = ROOT / index_path(lang)
        idx.parent.mkdir(parents=True, exist_ok=True)
        idx.write_text(render_index(entities, lang), encoding="utf-8")
        written += 1

    # /blog/ — language detected in the browser, with a static fallback
    root = ROOT / "blog" / "index.html"
    root.write_text(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Notes from the road — Bier Reisen</title>
<meta name="robots" content="noindex">
<link rel="canonical" href="{SITE}/blog/en/">
<link rel="alternate" hreflang="en" href="{SITE}/blog/en/">
<link rel="alternate" hreflang="pt-BR" href="{SITE}/blog/pt/">
<link rel="alternate" hreflang="de" href="{SITE}/blog/de/">
<link rel="alternate" hreflang="x-default" href="{SITE}/blog/en/">
<link rel="icon" href="../assets/favicon.svg" type="image/svg+xml">
<meta http-equiv="refresh" content="0;url=en/">
<style>body{{margin:0;background:#0b0c15;color:#eef1f6;font:17px/1.6 "Avenir Next",system-ui,sans-serif;
display:grid;place-items:center;min-height:100dvh}}a{{color:#e6a817}}ul{{list-style:none;padding:0}}
li{{margin:.4rem 0}}</style>
</head>
<body>
<main>
<p>Choose a language:</p>
<ul>
<li><a href="en/" hreflang="en">English</a></li>
<li><a href="pt/" hreflang="pt-BR">Português (Brasil)</a></li>
<li><a href="de/" hreflang="de">Deutsch</a></li>
</ul>
</main>
<script>
(function () {{
  var q = new URLSearchParams(location.search).get('lang');
  var stored = null;
  try {{ stored = localStorage.getItem('bierreisen:lang'); }} catch (e) {{}}
  var pick = q || stored || (navigator.language || 'en');
  var lang = pick.toLowerCase().indexOf('pt') === 0 ? 'pt' : pick.toLowerCase().indexOf('de') === 0 ? 'de' : 'en';
  if (lang !== 'en') location.replace(lang + '/');
}})();
</script>
</body>
</html>
""", encoding="utf-8")

    counts = {k: sum(1 for x in entities if x["type"] == k) for k in ("trip", "city", "brewery")}
    print(f"wrote {written} pages · {counts['trip']} trips · {counts['city']} cities · "
          f"{counts['brewery']} breweries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
