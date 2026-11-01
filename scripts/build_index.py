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

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "index.html"


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def km(n) -> str:
    return f"{round(float(n)):,}".replace(",", ",")


# ------------------------------------------------------------------ trips
YEARS = [
    {
        "key": "2027", "href": "2027/2027-bier-reisen.html", "poster": "2027/assets/2027-route-map.png",
        "data": "2027/data/route-2027.json", "status": "planned", "tone": "planned",
        "title": "The 2027 plan", "subtitle": "Frankfurt → Bruges → Ghent → Bamberg → Sokolov → Plzeň → Kout → Maxlrain → Andechs → Munich → Nuremberg → FRA",
        "blurb": "Two nights in Bruges, two in Bamberg, both Czech brewing towns and a night at a Franconian castle brewery — the trip this whole archive was built for.",
        "tags": ["planned", "car", "germany", "czechia", "belgium"],
        "mode": "car",
        "extra": '<a class="variant" href="2027/v2/2027-bier-reisen-v2.html">v2 · Cologne night</a>'
                 '<a class="variant" href="2027/v3/2027-bier-reisen-v3.html">v3 · Würzburg</a>',
    },
    {
        "key": "2026", "href": "2026/2026-bier-reisen.html", "poster": "2026/assets/2026-route-map.png",
        "data": "2026/data/route-2026.json", "status": "travelled", "tone": "done",
        "title": "Franconia, Bohemia and the Alps", "subtitle": "Merkendorf → Plzeň → České Budějovice → Bad Reichenhall → Munich",
        "blurb": "Three nights in a village brewery, two with Budvar, three under the Watzmann with Salzburg across the border, and four in Munich.",
        "tags": ["travelled", "car", "germany", "czechia"],
        "mode": "car",
    },
    {
        "key": "2024", "href": "2024/2024-bier-reisen.html", "poster": "2024/assets/2024-route-map.png",
        "data": "2024/data/route-2024.json", "status": "travelled", "tone": "done",
        "title": "Franconia, Bohemia and Advent", "subtitle": "Memmelsdorf → Plzeň → České Budějovice → Berchtesgaden → Munich",
        "blurb": "Late November: Christmas markets opening, brewery tours half empty, and the other Budweiser in its home town.",
        "tags": ["travelled", "car", "germany", "czechia"],
        "mode": "car",
    },
    {
        "key": "2021", "href": "2021/2021-bier-reisen.html", "poster": "2021/assets/2021-route-map.png",
        "data": "2021/data/route-2021.json", "status": "travelled", "tone": "done",
        "title": "Bamberg to the Allgäu", "subtitle": "Bamberg → Nuremberg → Essing → Traunstein → Schönram → Berchtesgaden → Nesselwang → Missen-Wilhams → Munich",
        "blurb": "Village breweries and two nights sleeping above the brewhouse, then a week in Munich.",
        "tags": ["travelled", "car", "germany"],
        "mode": "car",
    },
    {
        "key": "2020", "href": "2020/2020-bier-reisen.html", "poster": "2020/assets/2020-route-map.png",
        "data": "2020/data/route-2020.json", "status": "travelled", "tone": "done",
        "title": "The first European loop", "subtitle": "Munich → Bamberg → Düsseldorf → La Trappe → Antwerp → Brussels → Bruges → Westvleteren → Chimay → Zwiefaltendorf → Munich",
        "blurb": "The trip that started it: Altbier, Trappists, lambic and a Swabian village brewery on the Danube.",
        "tags": ["travelled", "car", "germany", "belgium", "netherlands"],
        "mode": "car",
    },
    {
        "key": "2019", "href": "2019/2019-bier-reisen.html", "poster": "2019/assets/2019-route-map.png",
        "data": "2019/data/route-2019.json", "status": "travelled", "tone": "done",
        "title": "Munich by rail", "subtitle": "Munich · Andechs · Aying · Bamberg",
        "blurb": "The first one, and the only one without a car: nine nights in one hotel, with day returns to a monastery, a village brewery and a Rauchbier town.",
        "tags": ["travelled", "rail", "germany"],
        "mode": "rail",
    },
]

IDEAS = [
    {"key": "uk", "file": "uk_beer_trip.html", "poster": "assets/trips/uk-beer-pilgrimage.png",
     "title": "UK Beer Pilgrimage", "subtitle": "London → Oxford → Burton → Manchester → Nottingham → Wales → Edinburgh",
     "blurb": "Thirty-two stops from the London pubs to the Highlands, on trains and the odd bus.",
     "tags": ["idea", "rail", "uk"], "mode": "rail"},
    {"key": "belgian", "meta": "belgium", "file": "belgian.html", "poster": "assets/trips/belgian-beer-pilgrimage.png",
     "title": "Belgian Beer Pilgrimage", "subtitle": "Brussels → Antwerp → Ghent → Bruges → the Trappists",
     "blurb": "Forty-two stops of lambic, Trappist and Flemish red — the densest beer country on earth.",
     "tags": ["idea", "car", "belgium"], "mode": "car"},
    {"key": "bavaria-bohemia", "meta": "germany_czech", "file": "germany_czech_beer_trip.html", "poster": "assets/trips/bavaria-bohemia.png",
     "title": "Bavaria & Bohemia", "subtitle": "Munich → Bamberg → Plzeň → Prague",
     "blurb": "Franconian village breweries, the Zoigl country and the birth of pilsner in one loop.",
     "tags": ["idea", "car", "germany", "czechia"], "mode": "car"},
    {"key": "colorado", "file": "colorado_beer_trip.html", "poster": "assets/trips/colorado-craft-beer.png",
     "title": "Colorado Craft Beer Odyssey", "subtitle": "Denver → Golden → Boulder → Fort Collins",
     "blurb": "Thirty-nine stops along the Front Range, from RiNo taprooms to the mountain breweries.",
     "tags": ["idea", "car", "usa"], "mode": "car"},
    {"key": "florida", "file": "florida_brewery_trip.html", "poster": "assets/trips/florida-brewery-trail.png",
     "title": "Florida Brewery Trail", "subtitle": "Miami → Orlando → Tampa Bay",
     "blurb": "Forty-three stops built around barrel-aged stouts, pastry sours and air conditioning.",
     "tags": ["idea", "car", "usa"], "mode": "car"},
    {"key": "italy-grand-tour", "meta": "italy_switzerland", "file": "Italy_Switzerland_14Day_Trip.html", "poster": "assets/trips/italy-switzerland-grand-tour.png",
     "title": "Italy & Switzerland Grand Tour", "subtitle": "Rome → Florence → Pisa → Venice → Milan → St. Moritz",
     "blurb": "A culture-first loop with a craft-beer thread — Tipopils, Re Ale and the Alps.",
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
    mode_label = "by rail" if t["mode"] == "rail" else "driving"
    return {
        **t,
        "days": d["days"],
        "nights": d["nights"],
        "bases": d.get("bases", 0),
        "distance": km(drive_km(data)),
        "mode_label": mode_label,
        "status_label": "Planned" if t["status"] == "planned" else "Travelled",
        "search": " ".join([t["key"], t["title"], t["subtitle"], t["blurb"], " ".join(t["tags"])]).lower(),
    }


def idea_card(t: dict, meta: dict) -> dict:
    return {
        **t,
        "href": f"AI-suggested-trips/{t['file']}",
        "days": meta.get("days", 0),
        "stops": len(meta.get("stops", [])),
        "search": " ".join([t["title"], t["subtitle"], t["blurb"], " ".join(t["tags"]), "idea"]).lower(),
    }


year_trips = [year_card(t) for t in YEARS]
trips_meta = {t["id"]: t for t in load("assets/trips.json")}
ideas = [idea_card(t, trips_meta[t.get("meta", t["key"])]) for t in IDEAS]

travelled = [t for t in year_trips if t["status"] == "travelled"]
total_days = sum(t["days"] for t in travelled)
total_km = sum(drive_km(load(t["data"])) for t in travelled)
countries = sorted({c for t in travelled for c in load(t["data"])["trip"].get("countries", [])
                    if c not in ("Brazil", "Italy", "Austria", "Netherlands")})
# Austria/Netherlands are real trip countries; keep them, drop only the origin
countries = sorted({c for t in travelled for c in load(t["data"])["trip"].get("countries", [])
                    if c != "Brazil"})

# ------------------------------------------------------------------ cards
def card_html(c: dict, kind: str) -> str:
    if kind == "trip":
        stats = (f'<li><strong>{c["days"]}</strong> days</li>'
                 f'<li><strong>{c["nights"]}</strong> nights</li>'
                 f'<li><strong>{c["distance"]}</strong> km {c["mode_label"]}</li>')
        variants = f'<div class="variants">{c["extra"]}</div>' if c.get("extra") else ""
        badge = c["status_label"]
        badge_cls = "badge planned" if c["status"] == "planned" else "badge"
        cta = f'<a class="btn" href="{esc(c["href"])}">Open dossier →</a>'
        poster = f'<a class="ghost" href="{esc(c["poster"])}" target="_blank" rel="noopener">Poster ↗</a>'
    else:
        stats = (f'<li><strong>{c["days"]}</strong> days</li>'
                 f'<li><strong>{c["stops"]}</strong> stops</li>')
        variants = ""
        badge = "Idea"
        badge_cls = "badge idea"
        cta = f'<a class="btn" href="{esc(c["href"])}">Open dossier →</a>'
        poster = f'<a class="ghost" href="{esc(c["poster"])}" target="_blank" rel="noopener">Poster ↗</a>'

    return f'''
        <article class="card" data-kind="{kind}" data-tags="{' '.join(c["tags"])}" data-search="{esc(c["search"])}">
          <a class="thumb" href="{esc(c["href"])}" aria-hidden="true" tabindex="-1">
            <img src="assets/thumbs/{c['key']}.jpg" alt="Route poster for {esc(c['title'])}" loading="lazy" width="960" height="624">
            <span class="{badge_cls}">{badge}{' · ' + c['key'] if kind == 'trip' else ''}</span>
          </a>
          <div class="body">
            <h3><a href="{esc(c["href"])}">{esc(c['title'])}</a></h3>
            <p class="route">{esc(c['subtitle'])}</p>
            <p class="blurb">{esc(c['blurb'])}</p>
            <ul class="stats">{stats}</ul>
            <div class="actions">{cta}{poster}</div>
            {variants}
          </div>
        </article>'''

trip_cards = "".join(card_html(c, "trip") for c in year_trips)
idea_cards = "".join(card_html(c, "idea") for c in ideas)
n_all = len(year_trips) + len(ideas)
n_travelled = len(travelled)
n_planned = len(year_trips) - n_travelled
n_ideas = len(ideas)
n_rail = sum(1 for c in year_trips + ideas if "rail" in c["tags"])

TEMPLATE = (ROOT / "scripts" / "index_template.html").read_text()

html_out = (TEMPLATE
            .replace("__TRIP_CARDS__", trip_cards)
            .replace("__IDEA_CARDS__", idea_cards)
            .replace("__N_ALL__", str(n_all))
            .replace("__N_TRAVELLED__", str(n_travelled))
            .replace("__N_PLANNED__", str(n_planned))
            .replace("__N_IDEAS__", str(n_ideas))
            .replace("__N_RAIL__", str(n_rail))
            .replace("__TOTAL_DAYS__", str(total_days))
            .replace("__TOTAL_KM__", km(total_km))
            .replace("__COUNTRIES__", str(len(countries))))

OUT.write_text(html_out, encoding="utf-8")
print(f"wrote index.html ({len(html_out)//1024} KB) · {n_all} cards · "
      f"{total_days} travelled days · {km(total_km)} km · {len(countries)} countries")
