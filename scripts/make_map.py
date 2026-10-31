#!/usr/bin/env python3
"""Render the beer-trip world map poster from assets/trips.json.

Layout: header -> two regional map panels -> six trip cards.
"""
import json
import math
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PatchCollection
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle
from matplotlib import patheffects as pe

ROOT = pathlib.Path(__file__).resolve().parent.parent
GEO = ROOT / "assets" / "ne_50m_countries.geojson"
if not GEO.exists():
    GEO = pathlib.Path("/Users/ren/.hermes/cache/scratch/ne110.json")
OUT = ROOT / "assets" / "beer-trips-map.png"

# ------------------------------------------------------------------ palette
BG = "#0b0c15"
OCEAN = "#080a14"
PANEL = "#151833"
BORDER = "#2a3050"
LAND = "#293150"
LAND_EDGE = "#49527d"
GRID = "#1e2440"
GOLD = "#e6a817"
TEXT = "#eef1f6"
MUTED = "#9aa5bc"
DIM = "#717c96"

COLORS = {
    "uk": "#f2604f",
    "belgium": "#f5a623",
    "germany_czech": "#43d19e",
    "colorado": "#54a8f5",
    "florida": "#ff7fa3",
    "italy_switzerland": "#b283f8",
}

plt.rcParams.update({
    "font.family": ["Avenir Next", "DejaVu Sans"],
    "text.color": TEXT,
    "savefig.facecolor": BG,
    "figure.facecolor": BG,
})

# ------------------------------------------------------------------ geometry
world = json.loads(GEO.read_text())
STATES = json.loads((ROOT / "assets" / "us_states.geojson").read_text())


def rings(geom):
    if geom["type"] == "Polygon":
        yield from geom["coordinates"]
    elif geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            yield from poly


def lcc(lon, lat, lon0, lat0, s1, s2):
    """Lambert conformal conic (spherical)."""
    lon = np.radians(np.asarray(lon, dtype=float))
    lat = np.radians(np.asarray(lat, dtype=float))
    l0 = math.radians(lon0)
    p0 = math.radians(lat0)
    p1, p2 = math.radians(s1), math.radians(s2)
    n = math.log(math.cos(p1) / math.cos(p2)) / math.log(
        math.tan(math.pi / 4 + p2 / 2) / math.tan(math.pi / 4 + p1 / 2))
    F = math.cos(p1) * math.tan(math.pi / 4 + p1 / 2) ** n / n
    rho = F / np.tan(math.pi / 4 + lat / 2) ** n
    rho0 = F / math.tan(math.pi / 4 + p0 / 2) ** n
    x = rho * np.sin(n * (lon - l0))
    y = rho0 - rho * np.cos(n * (lon - l0))
    return x, y


def draw_land(ax, proj, lon_win, lat_win):
    lon0, lat0, s1, s2 = proj
    patches = []
    for feat in world["features"]:
        for ring in rings(feat["geometry"]):
            arr = np.asarray(ring, dtype=float)
            if len(arr) < 4 or arr[:, 0].max() - arr[:, 0].min() > 200:
                continue
            if (arr[:, 1].max() < lat_win[0] + 1 or arr[:, 1].min() > lat_win[1] - 1
                    or arr[:, 0].max() < lon_win[0] + 1 or arr[:, 0].min() > lon_win[1] - 1):
                continue
            x, y = lcc(arr[:, 0], arr[:, 1], lon0, lat0, s1, s2)
            patches.append(Polygon(np.column_stack([x, y]), closed=True))
    ax.add_collection(PatchCollection(patches, facecolor=LAND, edgecolor=LAND_EDGE,
                                      linewidth=0.4, zorder=1))


def draw_graticule(ax, proj, lon_win, lat_win, lims):
    lon0, lat0, s1, s2 = proj
    xlim, ylim = lims
    lats = np.linspace(lat_win[0], lat_win[1], 80)
    for lon in range(int(lon_win[0]) // 10 * 10, int(lon_win[1]) + 10, 10):
        x, y = lcc(np.full_like(lats, lon), lats, lon0, lat0, s1, s2)
        ax.plot(x, y, color=GRID, lw=0.5, zorder=0)
        inside = (y > ylim[0]) & (y < ylim[1])
        if inside.any():
            i = np.where(inside)[0][0]
            ax.text(x[i], ylim[0] + 0.012 * (ylim[1] - ylim[0]),
                    f"{abs(lon)}°{'W' if lon < 0 else 'E'}", fontsize=5.4, color=DIM,
                    ha="center", va="bottom", zorder=6)
    lons = np.linspace(lon_win[0], lon_win[1], 80)
    for lat in range(int(lat_win[0]) // 10 * 10, int(lat_win[1]) + 10, 10):
        x, y = lcc(lons, np.full_like(lons, lat), lon0, lat0, s1, s2)
        ax.plot(x, y, color=GRID, lw=0.5, zorder=0)
        inside = (x > xlim[0]) & (x < xlim[1])
        if inside.any():
            i = np.where(inside)[0][0]
            ax.text(xlim[0] + 0.008 * (xlim[1] - xlim[0]), y[i], f"{lat}°N",
                    fontsize=5.4, color=DIM, ha="left", va="center", zorder=6)


def scale_bar(ax, proj, km=500, y=0.045, x=0.965):
    """Draw a simple scale bar in the bottom-right corner of the panel."""
    lon0, lat0, s1, s2 = proj
    _, y_a = lcc([lon0], [lat0], lon0, lat0, s1, s2)
    _, y_b = lcc([lon0], [lat0 + 1.0], lon0, lat0, s1, s2)
    km_per_unit = 111.32 / abs(float(np.ravel(y_b - y_a)[0]))
    xlim = ax.get_xlim()
    frac = (km / km_per_unit) / (xlim[1] - xlim[0])
    half = frac / 2
    ax.plot([x - half, x + half], [y, y], transform=ax.transAxes, color=MUTED, lw=1.6,
            solid_capstyle="butt", zorder=9,
            path_effects=[pe.withStroke(linewidth=3.2, foreground=BG)])
    for xx in (x - half, x + half):
        ax.plot([xx, xx], [y, y + 0.012], transform=ax.transAxes, color=MUTED, lw=1.6, zorder=9,
                path_effects=[pe.withStroke(linewidth=3.2, foreground=BG)])
    ax.text(x, y + 0.022, f"{km} km", transform=ax.transAxes, fontsize=6.4, color=MUTED,
            ha="center", va="bottom", zorder=9,
            path_effects=[pe.withStroke(linewidth=3, foreground=BG)])


def draw_states(ax, proj, lon_win, lat_win):
    lon0, lat0, s1, s2 = proj
    patches = []
    for feat in STATES["features"]:
        for ring in rings(feat["geometry"]):
            arr = np.asarray(ring, dtype=float)
            if len(arr) < 4:
                continue
            x, y = lcc(arr[:, 0], arr[:, 1], lon0, lat0, s1, s2)
            patches.append(Polygon(np.column_stack([x, y]), closed=True))
    ax.add_collection(PatchCollection(patches, facecolor="none", edgecolor="#333b5e",
                                      linewidth=0.32, zorder=2))


def lcc_window(proj, lon, lat, rect_w_in, rect_h_in, pad=0.0):
    lon0, lat0, s1, s2 = proj
    x0, y0 = lcc([lon[0], lon[1]], [lat[0], lat[1]], lon0, lat0, s1, s2)
    xr, yr = (x0.min(), x0.max()), (y0.min(), y0.max())
    cx, cy = sum(xr) / 2, sum(yr) / 2
    dx, dy = (xr[1] - xr[0]) * (1 + pad), (yr[1] - yr[0]) * (1 + pad)
    target = rect_w_in / rect_h_in
    if dx / dy < target:
        dx = dy * target
    else:
        dy = dx / target
    return (cx - dx / 2, cx + dx / 2), (cy - dy / 2, cy + dy / 2)


# ------------------------------------------------------------------ figure

W, H = 22.0, 15.0
fig = plt.figure(figsize=(W, H), dpi=200)
fig.add_artist(Rectangle((0, 0), 1, 1, transform=fig.transFigure, facecolor=BG, zorder=-10))

trips = json.loads((ROOT / "assets" / "trips.json").read_text())
by_id = {t["id"]: t for t in trips}

# ---- header
fig.text(0.026, 0.958, "BIERREISEN", fontsize=48, fontweight="bold", color=GOLD,
         ha="left", va="center")
fig.text(0.026, 0.916, "six beer pilgrimages, planned day by day", fontsize=14,
         color=MUTED, ha="left", va="center", style="italic")
fig.text(0.974, 0.945,
         "6 TRIPS   ·   73 DAYS   ·   203 CURATED STOPS   ·   7 COUNTRIES   ·   2 CONTINENTS",
         fontsize=10.5, color=TEXT, ha="right", va="center", fontweight="bold")
fig.text(0.974, 0.918, "distilled from the HTML dossiers in /AI-suggested-trips",
         fontsize=8.6, color=DIM, ha="right", va="center")
fig.add_artist(plt.Line2D([0.026, 0.974], [0.902, 0.902], color=GOLD, lw=1.2, alpha=0.6))

# ---- map panels
PANELS = [
    dict(name="North America", ids=["colorado", "florida"],
         rect=[0.026, 0.315, 0.464, 0.570],
         lon=(-106.8, -75.5), lat=(24.5, 43.0), proj=(-91.0, 33.5, 25.0, 45.0),
         note="2 trips · 82 stops · one-way car rentals", states=True),
    dict(name="Europe", ids=["uk", "belgium", "germany_czech", "italy_switzerland"],
         rect=[0.510, 0.315, 0.464, 0.570],
         lon=(-11.0, 20.0), lat=(41.0, 60.2), proj=(4.0, 50.0, 40.0, 58.0),
         note="4 trips · 121 stops · rail, road & one Bernina Express"),
]

# Denver packs 13 taprooms into four walkable blocks; give it a zoom inset.
ZOOM = dict(trip="colorado", rect=(0.331, 0.606, 0.148, 0.094),
            lon=(-105.33, -104.86), lat=(39.665, 39.815),
            title="DENVER METRO  ×8")

# The UK dossier's stop order zig-zags between day clusters; draw the roadbook
# spine instead so the route stays readable at map scale.
ROADBOOK = {
    "uk": [(51.51, -0.12), (51.75, -1.26), (51.98, -1.49), (52.81, -1.63), (53.48, -2.23),
           (53.80, -1.55), (52.95, -1.15), (51.83, -3.03), (51.48, -3.18), (51.67, -4.70),
           (52.93, -4.13), (53.26, -4.09), (55.95, -3.19), (55.86, -4.26), (56.16, -5.23),
           (55.62, -3.06), (57.68, -4.04)],
}

LABELS = {
    "uk": dict(num="1", name="UNITED KINGDOM", xy=(54.7, -4.4), off=(2, 20), ha="center"),
    "belgium": dict(num="2", name="BELGIUM", xy=(50.9, 4.3), off=(-24, 4), ha="right"),
    "germany_czech": dict(num="3", name="BAVARIA & BOHEMIA", xy=(49.5, 11.8), off=(10, -26), ha="left"),
    "italy_switzerland": dict(num="6", name="ITALY & SWITZERLAND", xy=(43.2, 11.9), off=(-10, -18), ha="right"),
    "colorado": dict(num="4", name="COLORADO", xy=(39.9, -105.4), off=(-20, 12), ha="right"),
    "florida": dict(num="5", name="FLORIDA", xy=(27.5, -80.6), off=(16, -10), ha="left"),
}

NUM = {"uk": 1, "belgium": 2, "germany_czech": 3, "colorado": 4, "florida": 5,
       "italy_switzerland": 6}

panel_axes = {}
badges = {}

for p in PANELS:
    ax = fig.add_axes(p["rect"])
    panel_axes[p["name"]] = ax
    ax.set_facecolor(OCEAN)
    for s in ax.spines.values():
        s.set_color(BORDER)
        s.set_linewidth(0.9)

    lon0, lat0, s1, s2 = p["proj"]
    lims = lcc_window(p["proj"], p["lon"], p["lat"], p["rect"][2] * W, p["rect"][3] * H)
    ax.set_xlim(*lims[0])
    ax.set_ylim(*lims[1])
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])

    draw_graticule(ax, p["proj"], p["lon"], p["lat"], lims)
    draw_land(ax, p["proj"], p["lon"], p["lat"])
    if p.get("states"):
        draw_states(ax, p["proj"], p["lon"], p["lat"])

    for tid in p["ids"]:
        t = by_id[tid]
        color = COLORS[tid]
        path = ROADBOOK.get(tid, t["path"])
        if path:
            xs, ys = lcc([q[1] for q in path], [q[0] for q in path], lon0, lat0, s1, s2)
            ax.plot(xs, ys, color=color, lw=1.8, alpha=0.5, zorder=3,
                    solid_capstyle="round", solid_joinstyle="round")
        sx, sy = lcc([s["lon"] for s in t["stops"]], [s["lat"] for s in t["stops"]],
                     lon0, lat0, s1, s2)
        ax.scatter(sx, sy, s=30, c=color, alpha=0.9, linewidths=0.5,
                   edgecolors="#0b0c15", zorder=4)
        lab = LABELS[tid]
        bx, by = lcc([lab["xy"][1]], [lab["xy"][0]], lon0, lat0, s1, s2)
        badges[tid] = (float(np.ravel(bx)[0]), float(np.ravel(by)[0]), ax)
        ax.scatter([bx], [by], s=470, c=color, edgecolors="#0b0c15", linewidths=2.2, zorder=6)
        ax.text(bx, by, lab["num"], fontsize=11.5, fontweight="bold", color="#0b0c15",
                ha="center", va="center", zorder=7)
        ax.annotate(lab["name"], xy=(bx, by), xytext=lab["off"], textcoords="offset points",
                    fontsize=8.8, fontweight="bold", color=color, ha=lab["ha"], va="center",
                    zorder=8, path_effects=[pe.withStroke(linewidth=3.4, foreground=BG)])

    # panel caption
    ax.text(0.022, 0.968, p["name"].upper(), transform=ax.transAxes, fontsize=10,
            fontweight="bold", color=TEXT, va="top", ha="left", zorder=9,
            bbox=dict(boxstyle="round,pad=0.45", facecolor="#0b0c15", edgecolor=BORDER,
                      linewidth=0.7, alpha=0.94))
    ax.text(0.024, 0.902, p["note"], transform=ax.transAxes, fontsize=7.6, color=MUTED,
            va="top", ha="left", zorder=9,
            path_effects=[pe.withStroke(linewidth=2.6, foreground="#0b0c15")])
    scale_bar(ax, p["proj"], km=500)

# ---- Denver zoom inset
from matplotlib.patches import ConnectionPatch

z = ZOOM
axz = fig.add_axes(z["rect"])
axz.set_facecolor("#12162c")
for s in axz.spines.values():
    s.set_color("#4d5785")
    s.set_linewidth(1.0)
projz = (-105.10, 39.74, 38.0, 42.0)
lims = lcc_window(projz, z["lon"], z["lat"], z["rect"][2] * W, z["rect"][3] * H)
axz.set_xlim(*lims[0])
axz.set_ylim(*lims[1])
axz.set_aspect("equal", adjustable="box")
axz.set_xticks([]), axz.set_yticks([])

co_patches = []
for feat in STATES["features"]:
    if feat["properties"].get("name") not in ("Colorado",):
        continue
    for ring in rings(feat["geometry"]):
        arr = np.asarray(ring, dtype=float)
        if len(arr) < 4:
            continue
        x, y = lcc(arr[:, 0], arr[:, 1], *projz)
        co_patches.append(Polygon(np.column_stack([x, y]), closed=True))
axz.add_collection(PatchCollection(co_patches, facecolor=LAND, edgecolor=LAND_EDGE, lw=0.6, zorder=1))

ct = by_id[z["trip"]]
zs = [s for s in ct["stops"] if z["lon"][0] <= s["lon"] <= z["lon"][1] and z["lat"][0] <= s["lat"] <= z["lat"][1]]
zx, zy = lcc([s["lon"] for s in zs], [s["lat"] for s in zs], *projz)
axz.scatter(zx, zy, s=42, c=COLORS["colorado"], alpha=0.95, linewidths=0.7,
            edgecolors="#0b0c15", zorder=4)
for name, (la, lo), (dx, dy) in [
        ("RiNo", (39.768, -104.979), (0, 20)),
        ("S. Broadway", (39.722, -104.988), (6, -16)),
        ("Golden", (39.757, -105.221), (-4, 16))]:
    px, py = lcc([lo], [la], *projz)
    axz.annotate(name, xy=(px, py), xytext=(dx, dy), textcoords="offset points",
                 fontsize=6.4, color=TEXT, ha="center", va="center", zorder=6,
                 path_effects=[pe.withStroke(linewidth=2.6, foreground="#0a0d18")])
axz.add_patch(Rectangle((0.0, 0.0), 1.0, 1.0, transform=axz.transAxes, fill=False,
                        edgecolor=GOLD, lw=0.0, zorder=8))
zoom_ratio = ((z["rect"][2] * W) / (lims[0][1] - lims[0][0])) / (
    (0.464 * W) / (panel_axes["North America"].get_xlim()[1] - panel_axes["North America"].get_xlim()[0]))
axz.text(0.035, 0.955, f"DENVER METRO  ×{zoom_ratio:.0f}", transform=axz.transAxes, fontsize=7.4, fontweight="bold",
         color=TEXT, va="top", ha="left", zorder=7,
         path_effects=[pe.withStroke(linewidth=2.6, foreground="#0a0d18")])
axz.text(0.035, 0.865, f"{len(zs)} taprooms, four walkable blocks", transform=axz.transAxes,
         fontsize=6.2, color=MUTED, va="top", ha="left", zorder=7,
         path_effects=[pe.withStroke(linewidth=2.6, foreground="#0a0d18")])

bx, by, ax_main = badges["colorado"]
ax_main.scatter([bx], [by], s=760, facecolors="none", edgecolors="#ffffff", alpha=0.35,
                linewidths=1.0, zorder=5)
fig.add_artist(ConnectionPatch(xyA=(bx, by), coordsA="data", axesA=ax_main,
                               xyB=(0.0, 0.5), coordsB="axes fraction", axesB=axz,
                               color="#c9d2e6", lw=0.9, alpha=0.55, zorder=9,
                               linestyle=(0, (4, 4))))

# ---- trip cards
CARD_TEXT = {
    "uk": dict(
        meta="12 days · 32 stops · England, Wales & Scotland",
        route="London → Cotswolds → Manchester → Cardiff → Edinburgh",
        sig="Cask ale: Landlord, Jaipur IPA, Jarl, London Pride",
        foot="May–Jun or Sep–Oct  ·  £150–250 per day"),
    "belgium": dict(
        meta="9 days · 42 stops · Belgium, Germany, Czechia",
        route="Brussels → West Flanders → Antwerp → Ardennes → Pilsen",
        sig="Westvleteren 12, Cantillon Gueuze, Orval, Saison Dupont",
        foot="Apr–Jun or Sep–Oct  ·  book Trappist visits ahead"),
    "germany_czech": dict(
        meta="14 days · 40 stops · Germany, Czechia",
        route="Frankfurt → Bamberg → Franconia → Pilsen → Munich",
        sig="Schlenkerla Rauchbier, Mahr's aU, Kout 12°, Pilsner Urquell",
        foot="May–Sep, beer-garden season  ·  Annafest late July"),
    "colorado": dict(
        meta="12 days · 39 stops · United States",
        route="Denver → Golden → Boulder → Longmont → Fort Collins",
        sig="Bierstadt slow-pour Pils, Funkwerks Saison, Odell IPA",
        foot="Jun–Sep patio season  ·  GABF week in September"),
    "florida": dict(
        meta="12 days · 43 stops · United States",
        route="Miami → Orlando → Tampa → St. Pete → Dunedin",
        sig="Jai Alai IPA, Hunahpu's, Maple Bacon Coffee Porter",
        foot="Nov–Apr, avoid summer  ·  ≈ $290–460 per day"),
    "italy_switzerland": dict(
        meta="14 days · 26 beer stops · Italy, Switzerland",
        route="Rome → Florence → Pisa → Venice → Milan → St. Moritz",
        sig="Tipopils, Re Ale, Xyauyù, Archea Dubbel",
        foot="May–Jun or Sep–Oct  ·  ≈ €180–285 per day"),
}

order = ["uk", "belgium", "germany_czech", "colorado", "florida", "italy_switzerland"]
card_w, card_h = 0.308, 0.128
x0s = [0.026, 0.346, 0.666]
y0s = [0.170, 0.028]

for i, tid in enumerate(order):
    col, row = i % 3, i // 3
    t = by_id[tid]
    color = COLORS[tid]
    ax = fig.add_axes([x0s[col], y0s[row], card_w, card_h])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0.004, 0.02), 0.992, 0.96,
                                boxstyle="round,pad=0,rounding_size=0.05",
                                facecolor=PANEL, edgecolor=BORDER, linewidth=0.8))
    ax.add_patch(FancyBboxPatch((0.004, 0.02), 0.011, 0.96,
                                boxstyle="round,pad=0,rounding_size=0.02",
                                facecolor=color, edgecolor="none"))
    ax.text(0.055, 0.780, str(i + 1), fontsize=18, fontweight="bold", color=BG,
            ha="center", va="center", zorder=5,
            bbox=dict(boxstyle="circle,pad=0.36", facecolor=color, edgecolor="none"))
    ax.text(0.100, 0.800, t["title"], fontsize=14.5, fontweight="bold", color=TEXT,
            ha="left", va="center")
    ax.text(0.100, 0.590, CARD_TEXT[tid]["meta"], fontsize=8.9, color=MUTED,
            ha="left", va="center")
    ax.text(0.100, 0.420, CARD_TEXT[tid]["route"], fontsize=8.9, color=color,
            ha="left", va="center", fontweight="bold")
    ax.text(0.100, 0.250, CARD_TEXT[tid]["sig"], fontsize=8.7, color=TEXT,
            ha="left", va="center")
    ax.text(0.100, 0.085, CARD_TEXT[tid]["foot"], fontsize=8.0, color=DIM,
            ha="left", va="center", style="italic")

fig.text(0.974, 0.008, "basemap: Natural Earth 1:110m  ·  routes traced from each dossier's Leaflet map data",
         fontsize=7.0, color=DIM, ha="right", va="bottom")
fig.text(0.026, 0.008, "Open any trip's HTML file for the interactive version — markers, day plans, rankings and beer tables.",
         fontsize=7.0, color=DIM, ha="left", va="bottom")

OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, dpi=200, facecolor=BG)
print("wrote", OUT, OUT.stat().st_size // 1024, "KB")
