"""Extract trip geometry + stop lists from the seven AI-suggested trip HTML files."""
import json, re, pathlib

D = pathlib.Path("/Users/ren/dev/bierreisen/AI-suggested-trips")
OUT = pathlib.Path("/Users/ren/dev/bierreisen/assets/trips.json")


def js_array(html, name):
    m = re.search(r"(?:var|const|let)\s+" + name + r"\s*=\s*", html)
    assert m, f"{name} not found"
    i, depth = m.end(), 0
    while i < len(html):
        ch = html[i]
        if ch in "[{(":
            depth += 1
        elif ch in "]})":
            depth -= 1
            if depth == 0:
                i += 1
                break
        i += 1
    return html[m.end():i].strip()


def objects(block):
    """Split a JS array literal of `{...}` objects into individual object strings."""
    out, depth, start = [], 0, None
    for i, ch in enumerate(block):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                out.append(block[start:i + 1])
                start = None
    return out


def field(obj, key):
    m = re.search(key + r"\s*:\s*(\"[^\"]*\"|'[^']*'|-?\d+(?:\.\d+)?)", obj)
    if not m:
        return None
    v = m.group(1)
    return v[1:-1] if v[0] in "\"'" else float(v)


def tuples(block):
    """[lat, lng, "name", ...] arrays."""
    out = []
    for m in re.finditer(r"\[\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*(?:,\s*\"([^\"]*)\")?", block):
        out.append({"lat": float(m.group(1)), "lon": float(m.group(2)), "name": m.group(3) or ""})
    return out


def pairs(block, names=None):
    return [[float(a), float(b)] for a, b in re.findall(r"\[\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*\]", block)]


trips = []

# ---------------------------------------------------------------- UK
h = (D / "uk_beer_trip.html").read_text()
stops = [{"lat": s["lat"], "lon": s["lon"], "name": s["name"]} for s in tuples(js_array(h, "stops"))]
trips.append({
    "id": "uk", "file": "uk_beer_trip.html",
    "title": "UK Beer Pilgrimage",
    "subtitle": "England, Wales & Scotland by rail and road",
    "days": 12, "countries": "England · Wales · Scotland",
    "route": "London → Oxford → Burton → Manchester → Nottingham → Wales → Edinburgh",
    "anchor": [54.0, -2.6],
    "stops": stops, "path": [[s["lat"], s["lon"]] for s in stops],
})

# ---------------------------------------------------------------- Belgium (+ Germany, Czech)
h = (D / "belgian.html").read_text()
places = []
for o in objects(js_array(h, "PLACES")):
    lat, lon, name = field(o, "lat"), field(o, "lng"), field(o, "name")
    if lat and lon and name:
        places.append({"lat": lat, "lon": lon, "name": name,
                       "city": field(o, "city"), "rating": field(o, "rating")})
trips.append({
    "id": "belgium", "file": "belgian.html",
    "title": "Belgian Beer Pilgrimage",
    "subtitle": "Lambic, Trappist & Flemish red — ending in Pilsen",
    "days": 9, "countries": "Belgium · Germany · Czechia",
    "route": "Brussels → Pajottenland → Hainaut → West Flanders → Antwerp → Ardennes → Chimay → Pilsen",
    "anchor": [50.75, 4.6],
    "stops": places, "path": pairs(js_array(h, "routePoints")),
})

# ---------------------------------------------------------------- Germany / Czech
h = (D / "germany_czech_beer_trip.html").read_text()
places = []
for o in objects(js_array(h, "places")):
    lat, lon, name = field(o, "lat"), field(o, "lng"), field(o, "name")
    if lat and lon and name:
        places.append({"lat": lat, "lon": lon, "name": re.sub(r"^[^\w]+ ", "", str(name))})
trips.append({
    "id": "germany_czech", "file": "germany_czech_beer_trip.html",
    "title": "Bavaria & Bohemia",
    "subtitle": "Franconian village breweries, Zoigl & the birth of Pilsner",
    "days": 14, "countries": "Germany · Czechia",
    "route": "Frankfurt → Bamberg → Franconia → Zoigl country → Pilsen → Munich → Andechs",
    "anchor": [49.9, 11.6],
    "stops": places, "path": pairs(js_array(h, "routeCoords")),
})

# ---------------------------------------------------------------- Colorado
h = (D / "colorado_beer_trip.html").read_text()
places = []
for o in objects(js_array(h, "markers")):
    lat, lon, name = field(o, "lat"), field(o, "lng"), field(o, "name")
    if lat and lon and name:
        places.append({"lat": lat, "lon": lon, "name": name, "city": field(o, "city")})
trips.append({
    "id": "colorado", "file": "colorado_beer_trip.html",
    "title": "Colorado Craft Beer Odyssey",
    "subtitle": "Denver to Fort Collins — 30+ taprooms in the Rockies",
    "days": 12, "countries": "United States",
    "route": "Denver → Golden → Boulder → Longmont → Fort Collins → Denver",
    "anchor": [39.9, -105.4],
    "stops": places, "path": pairs(js_array(h, "route")),
})

# ---------------------------------------------------------------- Florida
h = (D / "florida_brewery_trip.html").read_text()
places = []
for arr in ("miami", "orlando", "tampa"):
    for s in tuples(js_array(h, arr)):
        places.append(s)
fl_path = [[25.79, -80.20], [25.81, -80.36], [26.09, -80.13], [26.17, -80.13], [28.54, -81.38],
           [28.76, -81.34], [28.60, -81.36], [27.95, -82.46], [27.77, -82.64], [27.80, -82.79],
           [27.95, -82.46], [28.02, -82.79]]
trips.append({
    "id": "florida", "file": "florida_brewery_trip.html",
    "title": "Florida Brewery Trail",
    "subtitle": "Miami → Orlando → Tampa Bay, one-way by car",
    "days": 12, "countries": "United States",
    "route": "Miami → Fort Lauderdale → Orlando → Tampa → St. Pete → Dunedin",
    "anchor": [27.9, -81.9],
    "stops": places, "path": fl_path,
})

# ---------------------------------------------------------------- Italy / Switzerland
h = (D / "Italy_Switzerland_14Day_Trip.html").read_text()
places = []
for o in objects(js_array(h, "cities")):
    lat, lon, name = field(o, "lat"), field(o, "lng"), field(o, "name")
    if lat and lon and name:
        places.append({"lat": lat, "lon": lon, "name": name})
trips.append({
    "id": "italy_switzerland", "file": "Italy_Switzerland_14Day_Trip.html",
    "title": "Italy & Switzerland",
    "subtitle": "Grand tour with a craft-beer thread through every city",
    "days": 14, "countries": "Italy · Switzerland",
    "route": "Rome → Florence → Pisa → Venice → Milan → St. Moritz → Rome",
    "anchor": [44.4, 11.4],
    "stops": places, "path": pairs(js_array(h, "route")),
})

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(trips, indent=1, ensure_ascii=False))

for t in trips:
    lats = [s["lat"] for s in t["stops"]]
    lons = [s["lon"] for s in t["stops"]]
    print(f'{t["id"]:20} days={t["days"]:2}  stops={len(t["stops"]):3}  '
          f'lat {min(lats):6.2f}..{max(lats):6.2f}  lon {min(lons):7.2f}..{max(lons):7.2f}  '
          f'path={len(t["path"])}')
print("total stops:", sum(len(t["stops"]) for t in trips))
