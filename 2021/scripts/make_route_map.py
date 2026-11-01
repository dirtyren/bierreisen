#!/usr/bin/env python3
"""Render 2021/assets/2021-route-map.png — route poster for the Oct–Nov 2021 trip."""
from __future__ import annotations

import json
import math
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patheffects as pe
from matplotlib.collections import PatchCollection
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle

HERE = pathlib.Path(__file__).resolve().parent
DIR_2021 = HERE.parent
ROOT = DIR_2021.parent
DATA = DIR_2021 / "data" / "route-2021.json"
GEO = ROOT / "assets" / "ne_50m_countries.geojson"
OUT = DIR_2021 / "assets" / "2021-route-map.png"

BG, OCEAN, PANEL, BORDER = "#0b0c15", "#05060d", "#151833", "#2a3050"
LAND, LAND_EDGE, GRID = "#2f3758", "#66739f", "#222a4c"
GOLD, TEXT, MUTED, DIM = "#e6a817", "#eef1f6", "#9aa5bc", "#6f7a94"

plt.rcParams.update({
    "font.family": ["Avenir Next", "DejaVu Sans"],
    "text.color": TEXT, "savefig.facecolor": BG, "figure.facecolor": BG,
})

d = json.loads(DATA.read_text())
trip, stops, legs = d["trip"], d["stops"], d["legs"]
by_id = {s["id"]: s for s in stops}
euro = [s for s in stops if s["id"] not in ("poa", "fra_end")]

world = json.loads(GEO.read_text())
PROJ = (10.5, 49.0, 40.0, 52.0)
LON_WIN, LAT_WIN = (7.85, 13.6), (47.2, 50.3)


def rings(geom):
    if geom["type"] == "Polygon":
        yield from geom["coordinates"]
    elif geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            yield from poly


def lcc(lon, lat, lon0, lat0, s1, s2):
    lon = np.radians(np.asarray(lon, dtype=float))
    lat = np.radians(np.asarray(lat, dtype=float))
    l0, p0 = math.radians(lon0), math.radians(lat0)
    p1, p2 = math.radians(s1), math.radians(s2)
    n = math.log(math.cos(p1) / math.cos(p2)) / math.log(
        math.tan(math.pi / 4 + p2 / 2) / math.tan(math.pi / 4 + p1 / 2))
    F = math.cos(p1) * math.tan(math.pi / 4 + p1 / 2) ** n / n
    rho = F / np.tan(math.pi / 4 + lat / 2) ** n
    rho0 = F / math.tan(math.pi / 4 + p0 / 2) ** n
    return rho * np.sin(n * (lon - l0)), rho0 - rho * np.cos(n * (lon - l0))


fig = plt.figure(figsize=(20, 13), dpi=240)
fig.add_artist(Rectangle((0, 0), 1, 1, transform=fig.transFigure, facecolor=BG, zorder=-10))

# ------------------------------------------------------------------ header
fig.text(0.030, 0.955, "BIER REISEN 2021", fontsize=40, fontweight="bold", color=GOLD,
         ha="left", va="center")
fig.text(0.030, 0.908, "29 October – 15 November 2021 · Bamberg to the Allgäu", fontsize=13,
         color=MUTED, ha="left", va="center", style="italic")
fig.text(0.972, 0.945,
         f"18 days · 16 nights · 9 bases\n{round(trip['total_drive_km']):,} km driving · "
         f"{trip['total_drive_minutes'] // 60} h {trip['total_drive_minutes'] % 60:02d} behind the wheel · "
         f"{round(trip['total_flight_km']):,} km flying",
         fontsize=10.5, color=TEXT, ha="right", va="center", fontweight="bold", linespacing=1.7)
fig.add_artist(plt.Line2D([0.030, 0.972], [0.888, 0.888], color=GOLD, lw=1.2, alpha=0.6))

# ------------------------------------------------------------------ map panel
ax = fig.add_axes([0.028, 0.098, 0.585, 0.765])
ax.set_facecolor(OCEAN)
for s in ax.spines.values():
    s.set_color(BORDER)
    s.set_linewidth(0.9)
ax.set_xticks([])
ax.set_yticks([])

w_in = 0.585 * 20
h_in = 0.765 * 13
x0, y0 = lcc([LON_WIN[0], LON_WIN[1]], [LAT_WIN[0], LAT_WIN[0]], *PROJ)
y_bot = float(lcc([PROJ[0]], [LAT_WIN[0]], *PROJ)[1])
y_top = float(lcc([PROJ[0]], [LAT_WIN[1]], *PROJ)[1])
cx = (float(x0[0]) + float(x0[1])) / 2
dx = float(x0[1]) - float(x0[0])
dy = y_top - y_bot
target = w_in / h_in
if dx / dy < target:
    dx = dy * target
else:
    dy = dx / target
cy = (y_top + y_bot) / 2
ax.set_xlim(cx - dx / 2, cx + dx / 2)
ax.set_ylim(cy - dy / 2, cy + dy / 2)
ax.set_aspect("equal", adjustable="box")

lats = np.linspace(LAT_WIN[0], LAT_WIN[1], 40)
for lon in (8, 9, 10, 11, 12, 13, 14):
    gx, gy = lcc(np.full_like(lats, lon), lats, *PROJ)
    ax.plot(gx, gy, color=GRID, lw=0.5, zorder=0)
lons = np.linspace(LON_WIN[0], LON_WIN[1], 40)
for lat in (47, 48, 49, 50):
    gx, gy = lcc(lons, np.full_like(lons, lat), *PROJ)
    ax.plot(gx, gy, color=GRID, lw=0.5, zorder=0)

def clip_ring(ring, lon0, lat0, lon1, lat1):
    """Sutherland–Hodgman clip of a lon/lat ring to a rectangle."""
    pts = [(float(a), float(b)) for a, b in np.asarray(ring)[:, :2]]
    if len(pts) < 3:
        return []
    for edge in range(4):
        out = []
        if not pts:
            return []
        prev = pts[-1]
        for cur in pts:
            def inside(p, e=edge):
                return (p[0] >= lon0 if e == 0 else p[0] <= lon1 if e == 1 else
                        p[1] >= lat0 if e == 2 else p[1] <= lat1)
            def cut(p, q, e=edge):
                if e < 2:
                    t = (lon0 - p[0]) / (q[0] - p[0]) if q[0] != p[0] else 0
                else:
                    t = (lat0 - p[1]) / (q[1] - p[1]) if q[1] != p[1] else 0
                return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))
            if inside(cur):
                if not inside(prev):
                    out.append(cut(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(cut(prev, cur))
            prev = cur
        pts = out
    return pts


land_patches = []
for feat in world["features"]:
    for ring in rings(feat["geometry"]):
        arr = np.asarray(ring, dtype=float)
        if len(arr) < 4 or arr[:, 0].max() - arr[:, 0].min() > 200:
            continue
        if (arr[:, 1].max() < LAT_WIN[0] - 1 or arr[:, 1].min() > LAT_WIN[1] + 1
                or arr[:, 0].max() < LON_WIN[0] - 1 or arr[:, 0].min() > LON_WIN[1] + 1):
            continue
        px, py = lcc(arr[:, 0], arr[:, 1], *PROJ)
        land_patches.append(Polygon(np.column_stack([px, py]), closed=True))
ax.add_collection(PatchCollection(land_patches, facecolor=LAND, edgecolor=LAND_EDGE,
                                  linewidth=0.5, zorder=1))

for name, lon, lat in (("GERMANY", 10.6, 50.2), ("AUSTRIA", 13.4, 47.45), ("CZECHIA", 13.3, 49.9),
                       ("ITALY", 12.4, 47.3)):
    px, py = lcc([lon], [lat], *PROJ)
    ax.text(float(px[0]), float(py[0]), name, fontsize=7.2, color=DIM, ha="center", va="center",
            fontweight="bold", alpha=0.85, zorder=5)

# ------------------------------------------------------------------ route
for leg in legs:
    if leg["mode"] != "drive" or not leg.get("geometry"):
        continue
    gx, gy = lcc([p[1] for p in leg["geometry"]], [p[0] for p in leg["geometry"]], *PROJ)
    ax.plot(gx, gy, color=GOLD, lw=1.9, alpha=0.62, zorder=3, solid_capstyle="round")

OFFSETS = {
    "fra": (13, 8, "left"), "bamberg": (12, 6, "left"), "nuremberg": (12, -12, "left"),
    "essing": (12, 7, "left"), "traunstein": (-13, 2, "right"), "petting": (13, 12, "left"),
    "berchtesgaden": (12, -11, "left"), "nesselwang": (12, 9, "left"),
    "missen": (-11, -17, "right"), "munich": (13, 6, "left"),
}

DISPLACE = {}

for i, s in enumerate(euro, 1):
    px, py = lcc([s["lon"]], [s["lat"]], *PROJ)
    px, py = float(px[0]), float(py[0])
    ddx, ddy = DISPLACE.get(s["id"], (0.0, 0.0))
    bx, by = lcc([s["lon"] + ddx], [s["lat"] + ddy], *PROJ)
    bx, by = float(bx[0]), float(by[0])
    if ddx or ddy:
        ax.plot([px, bx], [py, by], color=MUTED, lw=0.65, alpha=0.6, zorder=5,
                path_effects=[pe.withStroke(linewidth=2.4, foreground=BG)])
        ax.scatter([px], [py], s=13, facecolors="none", edgecolors=GOLD, linewidths=0.9, zorder=6)
    size = 115 if s["nights"] else 88
    ax.scatter([bx], [by], s=size, c=GOLD, edgecolors="#0b0c15", linewidths=0.8, zorder=6)
    ax.annotate(str(i), xy=(bx, by), xytext=(0, -0.4), textcoords="offset points", fontsize=7.0,
                fontweight="bold", color="#0b0c15", ha="center", va="center", zorder=7)
    dx_l, dy_l, ha = OFFSETS.get(s["id"], (10, 6, "left"))
    label = s["name"].replace(" (arrival)", "").replace(" (return)", " · return").replace(" (lunch)", "")
    ax.annotate(label, xy=(bx, by), xytext=(dx_l, dy_l), textcoords="offset points",
                fontsize=7.6, color=TEXT, ha=ha, va="center", zorder=8, fontweight="bold",
                path_effects=[pe.withStroke(linewidth=3.2, foreground=BG)])

# scale bar
x_rng = ax.get_xlim()[1] - ax.get_xlim()[0]
y_unit = abs(float(lcc([PROJ[0]], [PROJ[1] + 1], *PROJ)[1]) - float(lcc([PROJ[0]], [PROJ[1]], *PROJ)[1]))
km_per_unit = 111.32 / y_unit
frac = (100 / km_per_unit) / x_rng
sx, sy = 0.955 - frac, 0.045
ax.plot([sx, sx + frac], [sy, sy], transform=ax.transAxes, color=MUTED, lw=1.6, zorder=9,
        path_effects=[pe.withStroke(linewidth=3, foreground=BG)])
for xx in (sx, sx + frac):
    ax.plot([xx, xx], [sy, sy + 0.011], transform=ax.transAxes, color=MUTED, lw=1.6, zorder=9,
            path_effects=[pe.withStroke(linewidth=3, foreground=BG)])
ax.text(sx + frac / 2, sy + 0.02, "100 km", transform=ax.transAxes, fontsize=6.6, color=MUTED,
        ha="center", va="bottom", zorder=9, path_effects=[pe.withStroke(linewidth=3, foreground=BG)])

ax.text(0.022, 0.100, "THE ROUTE", transform=ax.transAxes, fontsize=9.5, fontweight="bold",
        color=TEXT, va="bottom", zorder=9)
ax.text(0.022, 0.030, "Frankfurt → Bamberg → Nuremberg → Essing → Traunstein → Schönram →\n"
        "Berchtesgaden → Nesselwang → Missen-Wilhams → Munich → Frankfurt",
        transform=ax.transAxes, fontsize=7.4, color=MUTED, va="bottom", zorder=9, linespacing=1.6,
        path_effects=[pe.withStroke(linewidth=2.6, foreground=BG)])

# ------------------------------------------------------------------ ledger
axr = fig.add_axes([0.632, 0.098, 0.340, 0.765])
axr.set_xlim(0, 1)
axr.set_ylim(0, 1)
axr.axis("off")
axr.text(0.0, 0.995, "THE LEDGER", fontsize=10, fontweight="bold", color=TEXT, va="top")
axr.text(0.0, 0.945, "18 days · 16 nights · 9 bases · 2 countries", fontsize=8.2, color=MUTED, va="top")

leg_in = {(l["from"], l["to"]): l for l in legs}
row_y = 0.888
for i, s in enumerate(euro, 1):
    axr.add_patch(plt.Circle((0.018, row_y - 0.003), 0.013, transform=axr.transAxes,
                             facecolor=GOLD, edgecolor="none", zorder=4))
    axr.text(0.018, row_y - 0.003, str(i), fontsize=5.6, color="#0b0c15", fontweight="bold",
             ha="center", va="center", zorder=5)
    axr.text(0.048, row_y, s["name"], fontsize=8.4, fontweight="bold", color=TEXT, va="center")
    nights = f"{s['nights']}N" if s["nights"] else "visit"
    axr.text(0.985, row_y, nights, fontsize=8.0, color=GOLD if s["nights"] else DIM, va="center",
             ha="right", fontweight="bold" if s["nights"] else "normal")
    axr.text(0.048, row_y - 0.030, s["city"] + ", " + s["country"], fontsize=6.8, color=DIM, va="center")
    row_y -= 0.058

# transfer list
axr.add_patch(FancyBboxPatch((0.0, 0.012), 1.0, 0.150, boxstyle="round,pad=0,rounding_size=0.02",
                             facecolor=PANEL, edgecolor=BORDER, linewidth=0.7))
axr.text(0.030, 0.132, "LONGEST TRANSFERS", fontsize=7.4, fontweight="bold", color=TEXT, va="center")
lines = [("Berchtesgaden → Nesselwang", 279.9, 200), ("Essing → Traunstein", 230.5, 157),
         ("Frankfurt → Bamberg", 213.3, 138)]
yy = 0.100
for name, km, mins in lines:
    axr.text(0.030, yy, name, fontsize=7.0, color=MUTED, va="center")
    axr.text(0.985, yy, f"{km:,.0f} km · {mins // 60} h {mins % 60:02d}", fontsize=7.0, color=GOLD,
             va="center", ha="right", fontweight="bold")
    yy -= 0.032

fig.text(0.030, 0.020, "Distances: OSRM car routing. Flights: great-circle, 10,665 km POA→FRA and "
         "10,665 km FRA→POA.", fontsize=7.2, color=DIM, ha="left", va="bottom")
fig.text(0.972, 0.020, "basemap: Natural Earth 1:50m", fontsize=7.2, color=DIM, ha="right", va="bottom")

OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, dpi=240, facecolor=BG)
plt.close(fig)
print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")
