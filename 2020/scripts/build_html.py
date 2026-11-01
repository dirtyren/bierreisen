#!/usr/bin/env python3
"""Generate 2020/2020-bier-reisen.html from 2020/data/route-2020.json.

Same chrome as the 2027 planners: six tabs, dark palette, Leaflet map, day cards,
per-city rankings, beer guide, drive table and suggestions.
"""
from __future__ import annotations

import html
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
DIR_2020 = HERE.parent
DATA = DIR_2020 / "data" / "route-2020.json"
OUT = DIR_2020 / "2020-bier-reisen.html"

d = json.loads(DATA.read_text())
trip = d["trip"]
stops = d["stops"]
days = d["days"]
legs = d["legs"]
matrix = d["matrix"]
venues = d["venues"]
styles = d["styles"]
side_legs = d["side_legs"]

by_id = {s["id"]: s for s in stops}
euro_stops = [s for s in stops if s["id"] != "poa"]

FLAG = {"Germany": "🇩🇪", "Belgium": "🇧🇪", "Netherlands": "🇳🇱", "Brazil": "🇧🇷"}
COUNTRY_COLOR = {"Germany": "#e8b93b", "Belgium": "#43d19e", "Netherlands": "#f5a623", "Brazil": "#54a8f5"}


def esc(s):
    return html.escape(str(s), quote=True)


def fmt_km(km):
    return f"{km:,.0f}".replace(",", ",")


def hhmm(mins):
    return f"{mins // 60} h {mins % 60:02d}"


def leg_for(day):
    if not day["drive"] or "->" not in day["drive"]:
        return None
    a, b = day["drive"].split("->", 1)
    for l in legs:
        if l["from"] == a and l["to"] == b:
            return l
    return None


# ------------------------------------------------------------------ day cards
day_cards = []
for day in days:
    base = by_id.get(day["base"], {})
    nights = base.get("nights", 0)
    leg = leg_for(day)
    if leg and leg["mode"] == "flight":
        pill = (f'<div class="drive-pill">✈️ <strong>{esc(by_id[leg["from"]]["name"])} → '
                f'{esc(by_id[leg["to"]]["name"])}</strong> · {fmt_km(leg["km"])} km · '
                f'{hhmm(leg["minutes"])} in the air</div>')
    elif leg:
        pill = (f'<div class="drive-pill">🚗 <strong>{esc(by_id[leg["from"]]["name"])} → '
                f'{esc(by_id[leg["to"]]["name"])}</strong> · {fmt_km(leg["km"])} km · '
                f'{hhmm(leg["minutes"])}</div>')
    elif day["drive"] in ("flight", "flight-home"):
        pill = '<div class="drive-pill">✈️ <strong>Flight day</strong> · overnight</div>'
    else:
        pill = '<div class="drive-pill in-place">📍 In place · no driving</div>'

    items = "".join(f"<li>{esc(i)}</li>" for i in day["items"])
    nights_chip = (f'<span class="base-chip">{FLAG.get(base.get("country"), "🍺")} '
                   f'{esc(base.get("name", day["base"]))} · '
                   f'{nights} night{"s" if nights != 1 else ""}</span>') if nights else ""
    day_cards.append(f"""
      <article class="day-node" data-day="{day['day']}">
        <div class="day-head">
          <span class="day-num">DAY {day['day']}</span>
          <span class="day-date">{"{:02d}.02.2020".format(day['day'] + 1)}</span>
          {nights_chip}
        </div>
        <h3>{esc(day['title'])}</h3>
        {pill}
        <ul class="day-items">{items}</ul>
      </article>""")

# ------------------------------------------------------------------ map
map_stops = [s for s in euro_stops if s["id"] not in ("muc",)]
marker_js = ",\n".join(
    '[' + f'{s["lat"]:.4f},{s["lon"]:.4f},"{esc(s["name"])}","{esc(s["note"])}",'
           f'"{COUNTRY_COLOR.get(s["country"], "#e6a817")}",{s["nights"]}' + ']'
    for s in map_stops)
route_js = ",\n".join(f'[{s["lat"]:.4f},{s["lon"]:.4f}]' for s in map_stops)

# ------------------------------------------------------------------ rankings
def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


city_meta = d.get("city_meta", {})
rank_html, rank_filters = [], []
total_venues = sum(len(v) for v in venues.values())
for city, items in venues.items():
    meta = city_meta.get(city, {})
    flag = meta.get("flag", "🍺")
    cards = []
    for i, v in enumerate(items, 1):
        blob = " ".join([city, v["name"], v.get("note", ""), v.get("order", "")]).lower()
        cards.append(f"""
            <div class="brewery-card" data-city="{slugify(city)}" data-search="{esc(blob)}">
              <span class="rank" title="Rank #{i} in {esc(city)}">{i}</span>
              <div class="card-city-tag">{flag} {esc(city)} · #{i} of {len(items)}</div>
              <h4>{esc(v["name"])}</h4>
              <p class="desc">{esc(v.get("note", ""))}</p>
              <div class="order-this">🍺 <strong>Order this:</strong> {esc(v.get("order", ""))}</div>
            </div>""")
    rank_filters.append(
        f'<button type="button" class="filter-btn" '
        f'onclick="filterRankings(\'{slugify(city)}\', this)">{flag} {esc(city)} ({len(items)})</button>')
    rank_html.append(f"""
      <section class="city-ranking-section" data-city-section="{slugify(city)}">
        <div class="city-section-header">
          <div>
            <h3>{flag} {esc(city)} <span class="city-meta-pill">{esc(meta.get("stop", ""))}</span></h3>
            <p class="city-subnote">{esc(meta.get("subnote", ""))}</p>
          </div>
          <div class="city-famous-pill">🍻 Famous for: <strong>{esc(meta.get("famous", ""))}</strong></div>
        </div>
        <div class="brewery-grid">{''.join(cards)}</div>
      </section>""")

# ------------------------------------------------------------------ beers
style_rows = "".join(
    f"<tr><td>{esc(s['region'])}</td><td>{esc(' · '.join(s['styles']))}</td></tr>" for s in styles)

order_rows = "".join(
    f"<tr><td>{esc(city)}</td><td>{esc(items[0]['name'])}</td>"
    f"<td>{esc(items[0]['note'].split(':')[-1].strip()[:120])}</td></tr>"
    for city, items in venues.items())

# ------------------------------------------------------------------ drives
leg_rows = []
for l in legs:
    mode = "✈️ flight" if l["mode"] == "flight" else "🚗 drive"
    leg_rows.append(
        f"<tr><td>{mode}</td><td>{esc(by_id[l['from']]['name'])}</td>"
        f"<td>{esc(by_id[l['to']]['name'])}</td><td class='num'>{fmt_km(l['km'])}</td>"
        f"<td class='num'>{hhmm(l['minutes'])}</td></tr>")

nodes = matrix["nodes"]
pairs = matrix["pairs"]
head = "".join(f"<th>{esc(by_id[n]['name'].split(' (')[0])}</th>" for n in nodes)
body = []
for a in nodes:
    cells = []
    for b in nodes:
        if a == b:
            cells.append("<td class='diag'>—</td>")
        else:
            key = f"{a}|{b}" if f"{a}|{b}" in pairs else f"{b}|{a}"
            km = pairs.get(key, [0, 0])[0]
            cells.append(f"<td class='num'>{km:.0f}</td>")
    body.append(f"<tr><th>{esc(by_id[a]['name'].split(' (')[0])}</th>{''.join(cells)}</tr>")

# ------------------------------------------------------------------ suggestions
side_rows = "".join(
    f"<tr><td>{esc(by_id[s['from']]['name'])}</td><td>{esc(s['to'])}</td>"
    f"<td class='num'>{s['km']}</td><td class='num'>{hhmm(s['minutes'])}</td></tr>"
    for s in side_legs)

drive_km = trip["total_drive_km"]
drive_min = trip["total_drive_minutes"]
flight_km = trip["total_flight_km"]

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bier Reisen 2020 — 17-Day European Beer Trip</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
:root{{--bg:#0b0c15;--panel:#151833;--border:#2a3050;--gold:#e6a817;--text:#eef1f6;--muted:#9aa5bc}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--text);font-family:'Avenir Next','Segoe UI',system-ui,sans-serif;line-height:1.55}}
.header{{padding:2.4rem 2rem 1.6rem;text-align:center;border-bottom:2px solid var(--gold);
  background:linear-gradient(135deg,#0f0c29,#1b1e3d,#0b0c15)}}
.header h1{{font-size:2.3rem;color:var(--gold);font-weight:800;letter-spacing:.02em}}
.header .dates{{color:var(--muted);margin-top:.35rem;font-size:1rem}}
.route{{color:var(--text);margin-top:.7rem;font-size:.92rem;opacity:.9}}
.stats{{margin-top:.9rem;display:inline-block;padding:.45rem 1rem;border:1px solid var(--border);
  border-radius:999px;font-size:.86rem;color:var(--gold);font-weight:700}}
.links{{margin-top:1rem;display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;font-size:.85rem}}
.links a{{color:var(--muted);text-decoration:none;border-bottom:1px dotted var(--border)}}
.links a:hover{{color:var(--gold)}}
.tabs{{display:flex;justify-content:center;flex-wrap:wrap;gap:.2rem;background:#0d0f1c;
  border-bottom:1px solid var(--border);position:sticky;top:0;z-index:500}}
.tab{{background:none;border:none;color:var(--muted);padding:.95rem 1.3rem;font:inherit;font-weight:600;
  cursor:pointer;border-bottom:3px solid transparent}}
.tab:hover{{color:var(--gold)}}
.tab.active{{color:var(--gold);border-bottom-color:var(--gold);background:rgba(230,168,23,.06)}}
.tab-content{{display:none;max-width:1180px;margin:0 auto;padding:2rem 1.4rem 4rem}}
.tab-content.active{{display:block}}
h2.section{{font-size:1.35rem;color:var(--gold);margin:0 0 .4rem}}
p.lede{{color:var(--muted);margin-bottom:1.6rem;font-size:.95rem}}
.day-node{{background:var(--panel);border:1px solid var(--border);border-left:3px solid var(--gold);
  border-radius:12px;padding:1.1rem 1.3rem;margin:0 auto .9rem;max-width:820px}}
.day-head{{display:flex;align-items:center;gap:.7rem;flex-wrap:wrap;margin-bottom:.4rem}}
.day-num{{background:var(--gold);color:#0b0c15;font-weight:800;font-size:.75rem;padding:.18rem .6rem;
  border-radius:999px;letter-spacing:.06em}}
.day-date{{color:var(--muted);font-size:.78rem;letter-spacing:.08em}}
.base-chip{{font-size:.75rem;color:var(--muted);border:1px solid var(--border);border-radius:999px;padding:.15rem .6rem}}
.day-node h3{{font-size:1.05rem;margin:.15rem 0 .5rem;color:var(--text)}}
.drive-pill{{font-size:.84rem;color:var(--gold);background:rgba(230,168,23,.07);border:1px solid rgba(230,168,23,.25);
  border-radius:8px;padding:.4rem .7rem;display:inline-block;margin-bottom:.6rem}}
.drive-pill.in-place{{color:var(--muted);background:rgba(154,165,188,.06);border-color:var(--border)}}
.day-items{{margin-left:1.1rem;color:var(--muted);font-size:.9rem}}
.day-items li{{margin:.2rem 0}}
#map-container{{height:620px;border-radius:12px;border:1px solid var(--border)}}
.section-intro{{margin-bottom:1.3rem}}
.city-ranking-section{{margin-bottom:2.4rem}}
.city-section-header{{display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:.9rem;
  margin-bottom:1.1rem;padding-bottom:.7rem;border-bottom:1px solid var(--border)}}
.city-section-header h3{{font-size:1.15rem;color:var(--text);margin:0}}
.city-subnote{{color:var(--muted);font-size:.86rem;margin-top:.35rem;max-width:54ch}}
.city-meta-pill{{font-size:.73rem;font-weight:600;color:var(--muted);background:rgba(21,24,51,.9);
  border:1px solid var(--border);padding:.14rem .55rem;border-radius:999px;vertical-align:middle;margin-left:.4rem}}
.city-famous-pill{{background:rgba(230,168,23,.13);border:1px solid rgba(230,168,23,.42);color:var(--gold);
  padding:.36rem .8rem;border-radius:999px;font-size:.82rem}}
.brewery-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:1.05rem}}
.brewery-card{{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:1.15rem 1.2rem;
  position:relative;display:flex;flex-direction:column;gap:.45rem;box-shadow:0 8px 20px rgba(5,8,20,.35);
  transition:border-color .2s,transform .2s}}
.brewery-card:hover{{border-color:rgba(230,168,23,.5);transform:translateY(-2px)}}
.brewery-card .rank{{position:absolute;top:-11px;right:14px;background:var(--gold);color:#0b0c15;width:30px;
  height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;
  font-size:.82rem;box-shadow:0 4px 10px rgba(0,0,0,.4)}}
.card-city-tag{{color:#43d19e;font-size:.71rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em}}
.brewery-card h4{{font-size:1rem;color:var(--text)}}
.brewery-card .desc{{color:var(--muted);font-size:.86rem;line-height:1.5;flex:1}}
.order-this{{background:rgba(8,10,20,.55);border:1px solid rgba(230,168,23,.28);border-radius:8px;
  padding:.5rem .65rem;font-size:.81rem;color:#f0d98a;line-height:1.45}}
.region-filter{{display:flex;gap:.45rem;margin-bottom:1.4rem;flex-wrap:wrap;align-items:center}}
.filter-btn{{padding:.42rem .9rem;border:1px solid var(--border);background:var(--panel);color:var(--text);
  border-radius:999px;font-family:inherit;font-size:.83rem;font-weight:600;cursor:pointer;
  transition:background .18s,color .18s,border-color .18s}}
.filter-btn:hover{{border-color:rgba(230,168,23,.5);color:var(--gold)}}
.filter-btn.active{{background:var(--gold);color:#0b0c15;border-color:var(--gold)}}
.search-input{{padding:.45rem .9rem;border-radius:999px;border:1px solid var(--border);
  background:var(--panel);color:var(--text);font-family:inherit;font-size:.86rem;min-width:290px}}
table{{width:100%;border-collapse:collapse;font-size:.88rem;margin-bottom:1.4rem}}
th,td{{padding:.55rem .7rem;border-bottom:1px solid var(--border);text-align:left}}
th{{color:var(--gold);font-weight:700;background:rgba(21,24,51,.9);position:sticky;top:52px}}
td.num,th.num{{text-align:right;font-variant-numeric:tabular-nums}}
td.diag{{color:#3a4368;text-align:center}}
.matrix-wrap{{overflow-x:auto;border:1px solid var(--border);border-radius:10px}}
.totals{{display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0 2rem}}
.total{{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:.8rem 1.1rem;min-width:150px}}
.total b{{display:block;color:var(--gold);font-size:1.25rem}}
.total span{{color:var(--muted);font-size:.78rem;letter-spacing:.06em;text-transform:uppercase}}
.legend{{display:flex;gap:1.2rem;flex-wrap:wrap;margin:.8rem 0 0;font-size:.82rem;color:var(--muted)}}
.dot{{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:.35rem}}
</style>
</head>
<body>
<header class="header">
  <h1>🍺 Bier Reisen 2020</h1>
  <div class="dates">2 – 18 February 2020 · the trip that started it</div>
  <div class="route">Porto Alegre → Munich → Bamberg → Düsseldorf → La Trappe → Antwerp → Brussels →
    Ghent → Bruges → Westvleteren → Chimay → Zwiefaltendorf → Munich → Porto Alegre</div>
  <div class="stats">17 days · 14 nights · 10 bases · {fmt_km(drive_km)} km driving · {fmt_km(flight_km)} km flying · 4 countries</div>
  <div class="links">
    <a href="assets/2020-route-map.png" target="_blank" rel="noopener">🗺️ Route poster (PNG)</a>
    <a href="data/route-2020.json" target="_blank" rel="noopener">📄 Route data (JSON)</a>
  </div>
</header>

<nav class="tabs">
  <button class="tab active" onclick="showTab('itinerary',this)">📋 Itinerary</button>
  <button class="tab" onclick="showTab('map',this)">🗺️ Map</button>
  <button class="tab" onclick="showTab('rankings',this)">🏆 Rankings</button>
  <button class="tab" onclick="showTab('beers',this)">📖 Beer Guide</button>
  <button class="tab" onclick="showTab('drives',this)">🚗 Drive Times</button>
  <button class="tab" onclick="showTab('suggest',this)">💡 Suggestions</button>
</nav>

<section id="itinerary" class="tab-content active">
  <h2 class="section">17 days, day by day</h2>
  <p class="lede">The trip as it happened: two flights, twelve driving legs, fourteen nights and ten bases
    across Brazil, Germany, the Netherlands and Belgium.</p>
  {''.join(day_cards)}
</section>

<section id="map" class="tab-content">
  <h2 class="section">The route in Europe</h2>
  <p class="lede">Numbered in visit order, from Munich to the airport. The Porto Alegre legs are flights and
    sit outside this frame.</p>
  <div id="map-container"></div>
  <div class="legend">
    <span><span class="dot" style="background:#e8b93b"></span>Germany</span>
    <span><span class="dot" style="background:#f5a623"></span>Netherlands</span>
    <span><span class="dot" style="background:#43d19e"></span>Belgium</span>
  </div>
</section>

<section id="rankings" class="tab-content">
  <div class="section-intro">
    <h2 class="section">🏆 Per-City Brewery &amp; Bar Rankings</h2>
    <p class="lede">{total_venues} venues across {len(venues)} stops, ranked 1..n per city, with what to
      order at each one — the beer worth the detour, not just the closest bar.</p>
  </div>

  <div class="region-filter" id="ranking-filters">
    <button type="button" class="filter-btn active" onclick="filterRankings('all', this)">All stops ({total_venues})</button>
    {''.join(rank_filters)}
    <input type="search" id="venue-search" class="search-input" placeholder="🔍 Search venues, styles, notes..."
           oninput="searchRankings()" aria-label="Search venues" />
  </div>

  <div id="rankings-container">{''.join(rank_html)}</div>
</section>

<section id="beers" class="tab-content">
  <h2 class="section">Beer guide</h2>
  <p class="lede">Five beer regions in seventeen days: Bavarian lager, Franconian smoke, Rhenish Altbier,
    Trappist and lambic, and a Swabian village brewery on the way home.</p>
  <table><thead><tr><th>Region</th><th>Styles to look for</th></tr></thead><tbody>{style_rows}</tbody></table>
  <h2 class="section" style="margin-top:2rem">What to order, stop by stop</h2>
  <table><thead><tr><th>Stop</th><th>Start here</th><th>Why</th></tr></thead><tbody>{order_rows}</tbody></table>
</section>

<section id="drives" class="tab-content">
  <h2 class="section">Drive times</h2>
  <p class="lede">Every distance below is OSRM car routing, measured after the fact. The two flights are
    great-circle distances; the times are in the air, not door to door.</p>
  <div class="totals">
    <div class="total"><b>{fmt_km(drive_km)} km</b><span>driving</span></div>
    <div class="total"><b>{hhmm(drive_min)}</b><span>behind the wheel</span></div>
    <div class="total"><b>{fmt_km(flight_km)} km</b><span>flying</span></div>
    <div class="total"><b>{len(legs)}</b><span>legs</span></div>
  </div>
  <table><thead><tr><th>Mode</th><th>From</th><th>To</th><th class="num">km</th><th class="num">time</th></tr></thead>
  <tbody>{''.join(leg_rows)}</tbody></table>
  <h2 class="section" style="margin-top:2rem">Distance matrix</h2>
  <p class="lede">Car kilometres between every pair of land stops, from <code>matrix.pairs</code>.</p>
  <div class="matrix-wrap"><table><thead><tr><th>From \\ To</th>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>
</section>

<section id="suggest" class="tab-content">
  <h2 class="section">If you had one more day</h2>
  <p class="lede">Detours that were on the list and did not fit — measured from the nearest base.</p>
  <table><thead><tr><th>From</th><th>Detour</th><th class="num">km</th><th class="num">time</th></tr></thead>
  <tbody>{side_rows}</tbody></table>
  <h2 class="section" style="margin-top:2rem">What this trip taught us</h2>
  <ul style="color:var(--muted);margin-left:1.2rem;font-size:.92rem;line-height:1.9">
    <li>February in Franconia and Bavaria is quiet and cheap — but check <em>Ruhetag</em>, small breweries close Mondays.</li>
    <li>Düsseldorf's Altbier houses pour faster than you can drink; the coaster on the glass is how you stop the round.</li>
    <li>Trappist visits are appointment-only — La Trappe and Westvleteren both need planning weeks ahead.</li>
    <li>Chimay's Auberge de Poteaupré is the best-value night of the trip: brewery, cheese and forest in one place.</li>
    <li>The 6 h 54 Chimay → Zwiefaltendorf transfer is the one day worth splitting next time (Strasbourg or Baden-Baden).</li>
  </ul>
</section>

<script>
var mapReady = false;
function showTab(id, btn) {{
  document.querySelectorAll('.tab-content').forEach(function (s) {{ s.classList.remove('active'); }});
  document.querySelectorAll('.tab').forEach(function (b) {{ b.classList.remove('active'); }});
  document.getElementById(id).classList.add('active');
  if (btn) btn.classList.add('active');
  if (id === 'map') setTimeout(initMap, 60);
}}
function initMap() {{
  if (mapReady) {{ window.tripMap.invalidateSize(); return; }}
  if (typeof L === 'undefined') return;
  mapReady = true;
  var map = L.map('map-container');
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
    attribution: 'Tiles &copy; Esri', maxZoom: 16
  }}).addTo(map);
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
    maxZoom: 16
  }}).addTo(map);
  var stops = [
{marker_js}
  ];
  var pts = [];
  stops.forEach(function (s, i) {{
    var icon = L.divIcon({{className: 'pin', html: '<div style="width:22px;height:22px;border-radius:50%;background:' + s[4] +
      ';color:#0b0c15;font-weight:800;font-size:11px;display:flex;align-items:center;justify-content:center;border:2px solid #0b0c15">' + (i + 1) + '</div>', iconSize: [22, 22], iconAnchor: [11, 11]}});
    L.marker([s[0], s[1]], {{icon: icon}}).addTo(map)
      .bindPopup('<strong style="color:#e6a817">' + s[2] + '</strong><br><span style="font-size:.85em">' + s[3] + '</span>');
    pts.push([s[0], s[1]]);
  }});
  L.polyline(pts, {{color: '#e6a817', weight: 2, opacity: .55, dashArray: '6,8'}}).addTo(map);
  map.invalidateSize();
  map.fitBounds(L.latLngBounds(pts).pad(0.06));
  window.tripMap = map;
}}

var currentRankingCity = 'all';
function filterRankings(citySlug, btnEl) {{
  currentRankingCity = citySlug;
  document.querySelectorAll('#ranking-filters .filter-btn').forEach(function (b) {{ b.classList.remove('active'); }});
  if (btnEl) btnEl.classList.add('active');
  applyRankingFilter();
}}
function searchRankings() {{ applyRankingFilter(); }}
function applyRankingFilter() {{
  var input = document.getElementById('venue-search');
  var q = (input && input.value ? input.value : '').trim().toLowerCase();
  document.querySelectorAll('.city-ranking-section').forEach(function (sec) {{
    var cityMatch = (currentRankingCity === 'all' || sec.dataset.citySection === currentRankingCity);
    var visible = 0;
    sec.querySelectorAll('.brewery-card').forEach(function (card) {{
      var textMatch = !q || (card.dataset.search || '').indexOf(q) !== -1;
      var show = cityMatch && textMatch;
      card.style.display = show ? '' : 'none';
      if (show) visible++;
    }});
    sec.style.display = visible > 0 ? '' : 'none';
  }});
}}
</script>
</body>
</html>
"""

OUT.write_text(HTML, encoding="utf-8")
print(f"wrote {OUT.relative_to(DIR_2020.parent)} ({OUT.stat().st_size // 1024} KB)")
