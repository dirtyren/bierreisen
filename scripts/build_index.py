#!/usr/bin/env python3
"""Generate the trilingual catalog: index.html (EN), pt/index.html, de/index.html.

Numbers come from each trip's own data file; copy and interface strings come from
scripts/index_strings.py. The planned trip is 2027 v3 (the Würzburg route).
"""
from __future__ import annotations

import html
import json
import pathlib

from index_strings import IDEAS, LANG_ATTR, LANGS, SITE, TRIPS, UI

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = (ROOT / "scripts" / "index_template.html").read_text()

PATHS = {"en": "", "pt": "pt/", "de": "de/"}
# internal links name the file so the switcher also works from file:// or a bare
# static host without directory indexes; canonical/hreflang keep the clean URL.
LINKS = {"en": "index.html", "pt": "pt/index.html", "de": "de/index.html"}
OG_LOCALE = {"en": "en_GB", "pt": "pt_BR", "de": "de_DE"}


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def km(n) -> str:
    return f"{round(float(n)):,}"


# ------------------------------------------------------------------ trips
YEARS = [
    {
        "key": "2027", "href": "2027/v3/2027-bier-reisen-v3.html",
        "poster": "2027/v3/assets/2027-route-map-v3.png",
        "data": "2027/v3/data/route-2027-v3.json", "status": "planned", "thumb": "2027-v3",
        "tags": ["planned", "car", "germany", "czechia", "belgium"],
        "mode": "car",
        "variants": [("2027/2027-bier-reisen.html", "v1"),
                     ("2027/v2/2027-bier-reisen-v2.html", "v2")],
        "variant_labels": {
            "en": ["v1, the original route", "v2, with a Cologne night"],
            "pt": ["v1, a rota original", "v2, com uma noite em Colônia"],
            "de": ["v1, die ursprüngliche Route", "v2, mit einer Nacht in Köln"],
        },
    },
    {
        "key": "2026", "href": "2026/2026-bier-reisen.html", "poster": "2026/assets/2026-route-map.png",
        "data": "2026/data/route-2026.json", "status": "travelled",
        "tags": ["travelled", "car", "germany", "czechia"], "mode": "car",
    },
    {
        "key": "2024", "href": "2024/2024-bier-reisen.html", "poster": "2024/assets/2024-route-map.png",
        "data": "2024/data/route-2024.json", "status": "travelled",
        "tags": ["travelled", "car", "germany", "czechia"], "mode": "car",
    },
    {
        "key": "2021", "href": "2021/2021-bier-reisen.html", "poster": "2021/assets/2021-route-map.png",
        "data": "2021/data/route-2021.json", "status": "travelled",
        "tags": ["travelled", "car", "germany"], "mode": "car",
    },
    {
        "key": "2020", "href": "2020/2020-bier-reisen.html", "poster": "2020/assets/2020-route-map.png",
        "data": "2020/data/route-2020.json", "status": "travelled",
        "tags": ["travelled", "car", "germany", "belgium", "netherlands"], "mode": "car",
    },
    {
        "key": "2019", "href": "2019/2019-bier-reisen.html", "poster": "2019/assets/2019-route-map.png",
        "data": "2019/data/route-2019.json", "status": "travelled",
        "tags": ["travelled", "rail", "germany"], "mode": "rail",
    },
]

IDEAS_ORDER = [
    ("uk", "uk", "uk_beer_trip.html", ["idea", "rail", "uk"]),
    ("belgian", "belgium", "belgian.html", ["idea", "car", "belgium"]),
    ("bavaria-bohemia", "germany_czech", "germany_czech_beer_trip.html", ["idea", "car", "germany", "czechia"]),
    ("colorado", "colorado", "colorado_beer_trip.html", ["idea", "car", "usa"]),
    ("florida", "florida", "florida_brewery_trip.html", ["idea", "car", "usa"]),
    ("italy-grand-tour", "italy_switzerland", "Italy_Switzerland_14Day_Trip.html", ["idea", "rail", "italy"]),
]


def drive_km(data: dict) -> float:
    trip = data["trip"]
    if trip.get("total_drive_km"):
        return float(trip["total_drive_km"])
    return sum(float(l["km"]) for l in data.get("legs", []) if l.get("mode", "drive") == "drive")


def trip_facts(t: dict, ui: dict) -> dict:
    d = load(t["data"])["trip"]
    return {
        **t,
        "days": d["days"],
        "nights": d["nights"],
        "distance": km(drive_km(load(t["data"]))),
        "mode_label": ui["d_km_rail"] if t["mode"] == "rail" else ui["d_km_drive"],
        "status_label": ui["status_planned"] if t["status"] == "planned" else ui["status_travelled"],
    }


trips_meta = {t["id"]: t for t in load("assets/trips.json")}


def entry_html(t: dict, lang: str, ui: dict, base: str) -> str:
    copy = TRIPS[t["key"]][lang]
    cls = "entry planned" if t["status"] == "planned" else "entry"
    facts = (f'<span><b>{t["days"]}</b> {ui["d_days"]}</span>'
             f'<span><b>{t["nights"]}</b> {ui["d_nights"]}</span>'
             f'<span><b>{t["distance"]}</b> {t["mode_label"]}</span>')
    variants = ""
    if t.get("variants"):
        labels = t["variant_labels"][lang]
        links = "".join(f'<a class="variant" href="{base}{esc(h)}">{esc(label)}</a>'
                        for (h, _), label in zip(t["variants"], labels))
        variants = f'<p class="variants">{links}</p>'
    search = " ".join([t["key"], copy["title"], TRIPS[t["key"]]["en"]["title"],
                       copy["route"], copy["blurb"], " ".join(t["tags"])]).lower()
    return (
        f'\n      <li class="{cls}" data-tags="{" ".join(t["tags"])}" data-search="{esc(search)}">'
        f'\n        <a class="entry-poster" href="{base}{esc(t["href"])}" aria-hidden="true" tabindex="-1">'
        f'\n          <img src="{base}assets/thumbs/{t.get("thumb", t["key"])}.jpg" alt="" loading="lazy" width="960" height="624">'
        f'\n        </a>'
        f'\n        <div class="entry-body">'
        f'\n          <p class="entry-meta"><span class="yr">{t["key"]}</span>'
        f' <span class="dot" aria-hidden="true"></span> {t["status_label"]}</p>'
        f'\n          <h3><a href="{base}{esc(t["href"])}">{esc(copy["title"])}</a></h3>'
        f'\n          <p class="route">{esc(copy["route"])}</p>'
        f'\n          <p class="blurb">{esc(copy["blurb"])}</p>'
        f'\n          <p class="facts">{facts}</p>'
        f'\n          <p class="links"><a class="open" href="{base}{esc(t["href"])}">{esc(ui["open"])}</a>'
        f'<a class="quiet" href="{base}{esc(t["poster"])}" target="_blank" rel="noopener">'
        f'{esc(ui["poster"])}</a></p>'
        f'\n          {variants}'
        f'\n        </div>'
        f'\n      </li>')


def shelf_html(key: str, meta_id: str, file: str, tags: list, lang: str, ui: dict, base: str) -> str:
    meta = trips_meta[meta_id]
    title = IDEAS[key][lang]
    search = " ".join([title, IDEAS[key]["en"], " ".join(tags)]).lower()
    href = f"AI-suggested-trips/{file}"
    return (
        f'\n      <li class="shelf-item" data-tags="{" ".join(tags)}" data-search="{esc(search)}">'
        f'\n        <a href="{base}{esc(href)}">'
        f'\n          <img src="{base}assets/thumbs/{key}.jpg" alt="" loading="lazy" width="960" height="624">'
        f'\n          <h3>{esc(title)}</h3>'
        f'\n          <p>{meta.get("days", 0)} {ui["d_days"]} · {len(meta.get("stops", []))} {ui["d_stops"]}</p>'
        f'\n        </a>'
        f'\n      </li>')


def hreflang_block() -> str:
    rows = [f'<link rel="alternate" hreflang="{LANG_ATTR[l]}" href="{SITE}/{PATHS[l]}">' for l in LANGS]
    rows.append(f'<link rel="alternate" hreflang="x-default" href="{SITE}/">')
    return "\n".join(rows)


def lang_switch(lang: str, base: str) -> str:
    out = []
    for other in LANGS:
        label = {"en": "EN", "pt": "PT", "de": "DE"}[other]
        href = f"{base}{LINKS[other]}"
        current = ' aria-current="page"' if other == lang else ""
        out.append(f'<a href="{href}" hreflang="{LANG_ATTR[other]}" lang="{LANG_ATTR[other]}"{current}>{label}</a>')
    return "".join(out)


stats = {"days": 0, "km": 0.0}
for t in YEARS:
    if t["status"] == "travelled":
        d = load(t["data"])["trip"]
        stats["days"] += d["days"]
        stats["km"] += drive_km(load(t["data"]))

written = []
for lang in LANGS:
    ui = UI[lang]
    base = "../" if lang != "en" else ""
    canonical = f"{SITE}/{PATHS[lang]}"

    entries = "".join(entry_html(trip_facts(t, ui), lang, ui, base) for t in YEARS)
    shelf = "".join(
        shelf_html(key, meta_id, file, tags, lang, ui, base)
        for key, meta_id, file, tags in IDEAS_ORDER
    )

    page = (TEMPLATE
            .replace("__LANG_ATTR__", LANG_ATTR[lang])
            .replace("__TITLE__", esc(ui["title"]))
            .replace("__DESC__", esc(ui["desc"]))
            .replace("__OG_TITLE__", esc(ui["og_title"]))
            .replace("__OG_DESC__", esc(ui["og_desc"]))
            .replace("__OG_LOCALE__", OG_LOCALE[lang])
            .replace("__CANONICAL__", canonical)
            .replace("__HREFLANG__", hreflang_block())
            .replace("__BASE__", base)
            .replace("__SKIP__", esc(ui["skip"]))
            .replace("__H1_A__", esc(ui["h1_a"]))
            .replace("__H1_B__", esc(ui["h1_b"]))
            .replace("__STANDFIRST__", ui["standfirst"]
                     .replace("{km}", km(stats["km"]))
                     .replace("{days}", str(stats["days"])))
            .replace("__CTA__", esc(ui["cta"]))
            .replace("__SEARCH_PH__", esc(ui["search_ph"]))
            .replace("__ARIA_SEARCH__", esc(ui["aria_search"]))
            .replace("__ARIA_FILTER__", esc(ui["aria_filter"]))
            .replace("__F_ALL__", esc(ui["f_all"]))
            .replace("__F_TRAVELLED__", esc(ui["f_travelled"]))
            .replace("__F_PLANNED__", esc(ui["f_planned"]))
            .replace("__F_DRAFTS__", esc(ui["f_drafts"]))
            .replace("__F_RAIL__", esc(ui["f_rail"]))
            .replace("__H_TRIPS__", esc(ui["h_trips"]))
            .replace("__N_TRIPS__", esc(ui["n_trips"]))
            .replace("__H_IDEAS__", esc(ui["h_ideas"]))
            .replace("__N_IDEAS__", esc(ui["n_ideas"]))
            .replace("__EMPTY_A__", esc(ui["empty_a"]))
            .replace("__EMPTY_B__", esc(ui["empty_b"]))
            .replace("__FOOT_A__", esc(ui["foot_a"]))
            .replace("__FOOT_HOW__", esc(ui["foot_how"]))
            .replace("__FOOT_DATA__", esc(ui["foot_data"]))
            .replace("__FOOT_POSTERS__", esc(ui["foot_posters"]))
            .replace("__LANG_LABEL__", esc(ui["lang_label"]))
            .replace("__LANGS__", lang_switch(lang, base))
            .replace("__ENTRIES__", entries)
            .replace("__SHELF__", shelf)
            .replace("__JS_COUNT__", json.dumps(ui["count"]))
            .replace("__N_DRAFTS__", str(len(IDEAS_ORDER)))
            .replace("__N_ALL__", str(len(YEARS) + len(IDEAS_ORDER)))
            .replace("__N_TRAVELLED__", str(sum(1 for t in YEARS if t["status"] == "travelled")))
            .replace("__N_PLANNED__", str(sum(1 for t in YEARS if t["status"] == "planned")))
            .replace("__N_RAIL__", str(sum(1 for t in YEARS + [{"tags": t} for _, _, _, t in IDEAS_ORDER]
                                             if "rail" in t["tags"]))))

    out = ROOT / PATHS[lang] / "index.html" if PATHS[lang] else ROOT / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    written.append(out)

# ------------------------------------------------------------------ sitemap
sm = ['<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
      'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
alts = "\n".join(
    f'    <xhtml:link rel="alternate" hreflang="{LANG_ATTR[l]}" href="{SITE}/{PATHS[l]}"/>'
    for l in LANGS)
for lang in LANGS:
    sm.append(f"  <url>\n    <loc>{SITE}/{PATHS[lang]}</loc>\n{alts}\n"
              f"    <priority>1.0</priority><changefreq>weekly</changefreq>\n  </url>")
for t in YEARS:
    sm.append(f"  <url><loc>{SITE}/{t['href']}</loc><priority>0.9</priority>"
              f"<changefreq>monthly</changefreq></url>")
for key, _meta, file, _tags in IDEAS_ORDER:
    sm.append(f"  <url><loc>{SITE}/AI-suggested-trips/{file}</loc><priority>0.6</priority>"
              f"<changefreq>yearly</changefreq></url>")
sm.append("</urlset>")
(ROOT / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")

print("wrote " + ", ".join(str(p.relative_to(ROOT)) for p in written)
      + f" · {len(YEARS)} trips + {len(IDEAS_ORDER)} drafts · {stats['days']} days · {km(stats['km'])} km")
