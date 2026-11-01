#!/usr/bin/env python3
"""Generate index.html — the catalog page for every trip in this repository.

Reads the numbers from each year's data file (never hand-typed) and the six
AI-drafted trips from assets/trips.json, then writes a single self-contained
index.html that references the thumbnails in assets/thumbs/.
"""
from __future__ import annotations

import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "index.html"


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def km(n) -> str:
    return f"{round(float(n)):,}"


# ------------------------------------------------------------------ trips
YEARS = [
    {
        "key": "2027", "href": "2027/2027-bier-reisen.html", "poster": "2027/assets/2027-route-map.png",
        "data": "2027/data/route-2027.json", "status": "planned",
        "title": "The 2027 plan",
        "subtitle": "Frankfurt → Bruges → Ghent → Bamberg → Sokolov → Plzeň → Kout na Šumavě → Maxlrain → Andechs → Munich → Nuremberg → Frankfurt",
        "blurb": "Two nights in Bruges, two in Bamberg, both Czech brewing towns and a night at a Franconian "
                 "castle brewery. The trip this whole archive has been building towards.",
        "tags": ["planned", "car", "germany", "czechia", "belgium"],
        "mode": "car",
        "extra": '<a class="variant" href="2027/v2/2027-bier-reisen-v2.html">v2, with a Cologne night</a>'
                 '<a class="variant" href="2027/v3/2027-bier-reisen-v3.html">v3, with Würzburg</a>',
    },
    {
        "key": "2026", "href": "2026/2026-bier-reisen.html", "poster": "2026/assets/2026-route-map.png",
        "data": "2026/data/route-2026.json", "status": "travelled",
        "title": "Franconia, Bohemia and the Alps",
        "subtitle": "Frankfurt → Merkendorf → Plzeň → České Budějovice → Bad Reichenhall → Munich",
        "blurb": "Three nights in a village brewery, two with Budvar, three under the Watzmann with Salzburg "
                 "across the border, then four in Munich.",
        "tags": ["travelled", "car", "germany", "czechia"],
        "mode": "car",
    },
    {
        "key": "2024", "href": "2024/2024-bier-reisen.html", "poster": "2024/assets/2024-route-map.png",
        "data": "2024/data/route-2024.json", "status": "travelled",
        "title": "Franconia, Bohemia and Advent",
        "subtitle": "Frankfurt → Memmelsdorf → Plzeň → České Budějovice → Berchtesgaden → Munich",
        "blurb": "Late November: Christmas markets opening, brewery tours half empty, and the other Budweiser "
                 "in its home town.",
        "tags": ["travelled", "car", "germany", "czechia"],
        "mode": "car",
    },
    {
        "key": "2021", "href": "2021/2021-bier-reisen.html", "poster": "2021/assets/2021-route-map.png",
        "data": "2021/data/route-2021.json", "status": "travelled",
        "title": "Bamberg to the Allgäu",
        "subtitle": "Frankfurt → Bamberg → Nuremberg → Essing → Traunstein → Schönram → Berchtesgaden → Nesselwang → Missen-Wilhams → Munich",
        "blurb": "Village breweries and two nights sleeping above the brewhouse, then a week in Munich at the "
                 "end of October.",
        "tags": ["travelled", "car", "germany"],
        "mode": "car",
    },
    {
        "key": "2020", "href": "2020/2020-bier-reisen.html", "poster": "2020/assets/2020-route-map.png",
        "data": "2020/data/route-2020.json", "status": "travelled",
        "title": "The first European loop",
        "subtitle": "Munich → Bamberg → Düsseldorf → La Trappe → Antwerp → Brussels → Bruges → Westvleteren → Chimay → Zwiefaltendorf → Munich",
        "blurb": "The trip that started it: Altbier, Trappists, lambic, and a Swabian village brewery on the "
                 "Danube on the way home.",
        "tags": ["travelled", "car", "germany", "belgium", "netherlands"],
        "mode": "car",
    },
    {
        "key": "2019", "href": "2019/2019-bier-reisen.html", "poster": "2019/assets/2019-route-map.png",
        "data": "2019/data/route-2019.json", "status": "travelled",
        "title": "Munich by rail",
        "subtitle": "Munich · Andechs · Aying · Bamberg",
        "blurb": "The first one, and the only one without a car: nine nights in one hotel, with day returns to "
                 "a monastery, a village brewery and a Rauchbier town.",
        "tags": ["travelled", "rail", "germany"],
        "mode": "rail",
    },
]

IDEAS = [
    {"key": "uk", "meta": "uk", "file": "uk_beer_trip.html",
     "title": "UK Beer Pilgrimage",
     "tags": ["idea", "rail", "uk"], "mode": "rail"},
    {"key": "belgian", "meta": "belgium", "file": "belgian.html",
     "title": "Belgian Beer Pilgrimage",
     "tags": ["idea", "car", "belgium"], "mode": "car"},
    {"key": "bavaria-bohemia", "meta": "germany_czech", "file": "germany_czech_beer_trip.html",
     "title": "Bavaria & Bohemia",
     "tags": ["idea", "car", "germany", "czechia"], "mode": "car"},
    {"key": "colorado", "meta": "colorado", "file": "colorado_beer_trip.html",
     "title": "Colorado Craft Beer Odyssey",
     "tags": ["idea", "car", "usa"], "mode": "car"},
    {"key": "florida", "meta": "florida", "file": "florida_brewery_trip.html",
     "title": "Florida Brewery Trail",
     "tags": ["idea", "car", "usa"], "mode": "car"},
    {"key": "italy-grand-tour", "meta": "italy_switzerland", "file": "Italy_Switzerland_14Day_Trip.html",
     "title": "Italy & Switzerland Grand Tour",
     "tags": ["idea", "rail", "italy"], "mode": "rail"},
]


def drive_km(data: dict) -> float:
    trip = data["trip"]
    if trip.get("total_drive_km"):
        return float(trip["total_drive_km"])
    return sum(float(l["km"]) for l in data.get("legs", []) if l.get("mode", "drive") == "drive")


def year_card(t: dict) -> dict:
    data = load(t["data"])
    d = data["trip"]
    return {
        **t,
        "days": d["days"],
        "nights": d["nights"],
        "distance": km(drive_km(data)),
        "mode_label": "by rail" if t["mode"] == "rail" else "driving",
        "status_label": "Planned" if t["status"] == "planned" else "Travelled",
        "search": " ".join([t["key"], t["title"], t["subtitle"], t["blurb"], " ".join(t["tags"])]).lower(),
    }


def idea_card(t: dict, meta: dict) -> dict:
    return {
        **t,
        "href": f"AI-suggested-trips/{t['file']}",
        "days": meta.get("days", 0),
        "stops": len(meta.get("stops", [])),
        "search": " ".join([t["title"], " ".join(t["tags"]), "idea", "draft"]).lower(),
    }


year_trips = [year_card(t) for t in YEARS]
trips_meta = {t["id"]: t for t in load("assets/trips.json")}
ideas = [idea_card(t, trips_meta[t["meta"]]) for t in IDEAS]

travelled = [t for t in year_trips if t["status"] == "travelled"]
total_days = sum(t["days"] for t in travelled)
total_km = sum(drive_km(load(t["data"])) for t in travelled)
countries = sorted({c for t in travelled for c in load(t["data"])["trip"].get("countries", [])
                    if c != "Brazil"})

n_all = len(year_trips) + len(ideas)
n_travelled = len(travelled)
n_planned = len(year_trips) - n_travelled
n_ideas = len(ideas)
n_rail = sum(1 for c in year_trips + ideas if "rail" in c["tags"])


# ------------------------------------------------------------------ markup
def entry_html(c: dict) -> str:
    cls = "entry planned" if c["status"] == "planned" else "entry"
    facts = (f'<span><b>{c["days"]}</b> days</span>'
             f'<span><b>{c["nights"]}</b> nights</span>'
             f'<span><b>{c["distance"]}</b> km {c["mode_label"]}</span>')
    variants = ""
    if c.get("extra"):
        links = re.findall(r'href="([^"]+)"[^>]*>([^<]+)</a>', c["extra"])
        if links:
            variants = ('<p class="variants">' + "".join(
                f'<a class="variant" href="{esc(h)}">{esc(t)}</a>' for h, t in links) + "</p>")
    return (
        f'\n      <li class="{cls}" data-tags="{" ".join(c["tags"])}" data-search="{esc(c["search"])}">'
        f'\n        <a class="entry-poster" href="{esc(c["href"])}" aria-hidden="true" tabindex="-1">'
        f'\n          <img src="assets/thumbs/{c["key"]}.jpg" alt="" loading="lazy" width="960" height="624">'
        f'\n        </a>'
        f'\n        <div class="entry-body">'
        f'\n          <p class="entry-meta"><span class="yr">{c["key"][:4]}</span>'
        f' <span class="dot" aria-hidden="true"></span> {c["status_label"]}</p>'
        f'\n          <h3><a href="{esc(c["href"])}">{esc(c["title"])}</a></h3>'
        f'\n          <p class="route">{esc(c["subtitle"])}</p>'
        f'\n          <p class="blurb">{esc(c["blurb"])}</p>'
        f'\n          <p class="facts">{facts}</p>'
        f'\n          <p class="links"><a class="open" href="{esc(c["href"])}">Open the dossier</a>'
        f'<a class="quiet" href="{esc(c["poster"])}" target="_blank" rel="noopener">Route poster</a></p>'
        f'\n          {variants}'
        f'\n        </div>'
        f'\n      </li>')


def shelf_html(c: dict) -> str:
    return (
        f'\n      <li class="shelf-item" data-tags="{" ".join(c["tags"])}" data-search="{esc(c["search"])}">'
        f'\n        <a href="{esc(c["href"])}">'
        f'\n          <img src="assets/thumbs/{c["key"]}.jpg" alt="" loading="lazy" width="960" height="624">'
        f'\n          <h3>{esc(c["title"])}</h3>'
        f'\n          <p>{c["days"]} days · {c["stops"]} stops</p>'
        f'\n        </a>'
        f'\n      </li>')


entry_cards = "".join(entry_html(c) for c in year_trips)
shelf_cards = "".join(shelf_html(c) for c in ideas)

TEMPLATE = (ROOT / "scripts" / "index_template.html").read_text()

html_out = (TEMPLATE
            .replace("__ENTRIES__", entry_cards)
            .replace("__SHELF__", shelf_cards)
            .replace("__N_ALL__", str(n_all))
            .replace("__N_TRAVELLED__", str(n_travelled))
            .replace("__N_PLANNED__", str(n_planned))
            .replace("__N_IDEAS__", str(n_ideas))
            .replace("__N_RAIL__", str(n_rail))
            .replace("__TOTAL_DAYS__", str(total_days))
            .replace("__TOTAL_KM__", km(total_km)))

OUT.write_text(html_out, encoding="utf-8")

# ------------------------------------------------------------------ sitemap
SITE = "https://renreisen.duckdns.org"
urls = [("/", "1.0", "weekly")] + \
       [(f"/{c['href']}", "0.9", "monthly") for c in year_trips] + \
       [(f"/{c['href']}", "0.6", "yearly") for c in ideas] + \
       [("/README.md", "0.3", "monthly")]
sm = ['<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for path, prio, freq in urls:
    sm.append(f"  <url><loc>{SITE}{path}</loc><priority>{prio}</priority>"
              f"<changefreq>{freq}</changefreq></url>")
sm.append("</urlset>")
(ROOT / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
print(f"wrote index.html ({len(html_out)//1024} KB) · {n_all} entries · "
      f"{total_days} travelled days · {km(total_km)} km · {len(countries)} countries")
