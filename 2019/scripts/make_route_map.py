#!/usr/bin/env python3
"""Render 2019/assets/2019-route-map.png — Munich and its surroundings by rail (Dec 2019)."""
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
DIR_2019 = HERE.parent
ROOT = DIR_2019.parent
DATA = DIR_2019 / "data" / "route-2019.json"
GEO = ROOT / "assets" / "ne_50m_countries.geojson"
OUT = DIR_2019 / "assets" / "2019-route-map.png"

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
euro = stops[:]

world = json.loads(GEO.read_text())
PROJ = (11.4, 49.0, 40.0, 52.0)
LON_WIN, LAT_WIN = (10.55, 12.15), (47.80, 50.10)


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
fig.text(0.030, 0.955, "BIER REISEN 2019", fontsize=40, fontweight="bold", color=GOLD,
         ha="left", va="center")
fig.text(0.030, 0.908, "12–21 December 2019 · Munich and its surroundings, entirely by rail", fontsize=13,
         color=MUTED, ha="left", va="center", style="italic")
fig.text(0.972, 0.945,
         f"10 days · 9 nights · 1 base\n{round(trip['total_drive_km']):,} km by train · "
         f"{trip['total_drive_minutes'] // 60} h {trip['total_drive_minutes'] % 60:02d} on the move · "
         f"no car",
         fontsize=10.5, color=TEXT, ha="right", va="center", fontweight="bold", linespacing=1.7)
fig.add_artist(plt.Line2D([0.030, 0.972], [0.888, 0.888], color=GOLD, lw=1.2, alpha=0.6))

# ------------------------------------------------------------------ map panel
ax = fig.add_axes([0.030, 0.130, 0.300, 0.730])
ax.set_facecolor(OCEAN)
for s in ax.spines.values():
    s.set_color(BORDER)
    s.set_linewidth(0.9)
ax.set_xticks([])
ax.set_yticks([])

w_in = 0.300 * 20
h_in = 0.730 * 13
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

for name, lon, lat in (("GERMANY", 10.95, 48.95), ("AUSTRIA", 12.06, 47.86),
                       ("CZECHIA", 12.05, 49.75)):
    px, py = lcc([lon], [lat], *PROJ)
    ax.text(float(px[0]), float(py[0]), name, fontsize=7.2, color=DIM, ha="center", va="center",
            fontweight="bold", alpha=0.85, zorder=5)

# ------------------------------------------------------------------ route
seen = set()
for leg in legs:
    key = tuple(sorted([leg["from"], leg["to"]]))
    if key in seen:
        continue
    seen.add(key)
    sa, sb = by_id[key[0]], by_id[key[1]]
    gx, gy = lcc([sa["lon"], sb["lon"]], [sa["lat"], sb["lat"]], *PROJ)
    ax.plot(gx, gy, color=GOLD, lw=1.7, alpha=0.70, zorder=3, linestyle=(0, (5, 3)))

OFFSETS = {
    "muc_airport": (13, 8, "left"), "munich": (13, 3, "left"), "andechs": (-13, -8, "right"),
    "aying": (13, 11, "left"), "bamberg": (13, 8, "left"),
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
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.55, alpha=0.75,
                                shrinkA=1, shrinkB=6),
                path_effects=[pe.withStroke(linewidth=3.2, foreground=BG)])

# scale bar
x_rng = ax.get_xlim()[1] - ax.get_xlim()[0]
y_unit = abs(float(lcc([PROJ[0]], [PROJ[1] + 1], *PROJ)[1]) - float(lcc([PROJ[0]], [PROJ[1]], *PROJ)[1]))
km_per_unit = 111.32 / y_unit
frac = (50 / km_per_unit) / x_rng
sx, sy = 0.965 - frac, 0.945
ax.plot([sx, sx + frac], [sy, sy], transform=ax.transAxes, color=MUTED, lw=1.3, zorder=9,
        path_effects=[pe.withStroke(linewidth=3, foreground=BG)])
for xx in (sx, sx + frac):
    ax.plot([xx, xx], [sy, sy + 0.009], transform=ax.transAxes, color=MUTED, lw=1.3, zorder=9,
            path_effects=[pe.withStroke(linewidth=3, foreground=BG)])
ax.text(sx + frac / 2, sy - 0.020, "50 km", transform=ax.transAxes, fontsize=6.6, color=MUTED,
        ha="center", va="top", zorder=9, path_effects=[pe.withStroke(linewidth=3, foreground=BG)])



# ------------------------------------------------------------------ ledger
axr = fig.add_axes([0.360, 0.130, 0.610, 0.730])
axr.set_xlim(0, 1)
axr.set_ylim(0, 1)
axr.axis("off")
RAIL = {
    "muc_airport": ("S1 / S8 · 38 km · 41 min", "Airport line, 20-minute headway"),
    "munich": ("the base for nine nights", "Hotel, then everything on foot or by U-Bahn"),
    "andechs": ("S8 + bus 951 · 45 km · 1 h 10", "Herrsching, then the hill to the monastery"),
    "aying": ("S5 · 32 km · 45 min", "One stop past Höhenkirchen, then a kilometre on foot"),
    "bamberg": ("ICE via Nürnberg · 250 km · 3 h 20", "Rauchbier and back the same evening"),
}

axr.text(0.0, 0.985, "THE LEDGER", fontsize=10.5, fontweight="bold", color=TEXT, va="top")
axr.text(0.0, 0.935, "10 days · 9 nights · one hotel · four destinations on the timetable",
         fontsize=8.2, color=MUTED, va="top")
axr.add_patch(Rectangle((0.0, 0.892), 1.0, 0.0012, transform=axr.transAxes, facecolor=BORDER,
                        edgecolor="none"))

row_y = 0.840
for i, s in enumerate(euro, 1):
    axr.add_patch(plt.Circle((0.016, row_y), 0.020, transform=axr.transAxes,
                             facecolor=GOLD, edgecolor="none", zorder=4))
    axr.text(0.016, row_y, str(i), fontsize=6.4, color="#0b0c15", fontweight="bold",
             ha="center", va="center", zorder=5)
    axr.text(0.050, row_y + 0.008, s["name"], fontsize=9.6, fontweight="bold", color=TEXT, va="center")
    axr.text(0.050, row_y - 0.022, s["city"] + ", " + s["country"], fontsize=7.2, color=DIM, va="center")
    rail, detail = RAIL.get(s["id"], ("", ""))
    axr.text(0.520, row_y + 0.008, rail, fontsize=8.4, color=TEXT, va="center", alpha=0.95)
    axr.text(0.520, row_y - 0.022, detail, fontsize=7.0, color=MUTED, va="center", style="italic")
    nights = f"{s['nights']}N" if s["nights"] else "visit"
    axr.text(0.985, row_y, nights, fontsize=9.0, color=GOLD if s["nights"] else DIM, va="center",
             ha="right", fontweight="bold" if s["nights"] else "normal")
    axr.plot([0.0, 1.0], [row_y - 0.042, row_y - 0.042], color=BORDER, lw=0.5, alpha=0.6)
    row_y -= 0.108

axr.text(0.0, row_y + 0.020, "WHY ONE BASE", fontsize=8.6, fontweight="bold", color=TEXT, va="top")
tips = [
    ("Nine nights, one hotel.", "Munich is the hub: every destination here is a day return, so there is "
     "no packing between them."),
    ("The Deutschland-Ticket arithmetic.", "S-Bahn and regional trains inside the city and out to "
     "Herrsching, Aying or the airport; the ICE to Bamberg is the one ticket bought separately."),
    ("Rauchbier in a day.", "Bamberg is 250 km and about 3 h 20 each way — leave at seven, drink at "
     "eleven, be back in Munich for dinner."),
]
yy = row_y - 0.030
for head, body in tips:
    axr.text(0.0, yy, head, fontsize=8.0, fontweight="bold", color=GOLD, va="top")
    axr.text(0.0, yy - 0.026, body, fontsize=7.4, color=MUTED, va="top", wrap=False)
    yy -= 0.075

axr.text(0.0, 0.020, "No car: every leg is a scheduled S-Bahn, bus or ICE service from the December 2019 "
         "timetable.", fontsize=7.0, color=DIM, va="bottom", style="italic")


# transfer list
axt = fig.add_axes([0.360, 0.030, 0.610, 0.078])
axt.set_xlim(0, 1)
axt.set_ylim(0, 1)
axt.axis("off")
axt.add_patch(FancyBboxPatch((0.0, 0.02), 1.0, 0.96, boxstyle="round,pad=0,rounding_size=0.10",
                             facecolor=PANEL, edgecolor=BORDER, linewidth=0.7))
axt.text(0.022, 0.80, "RAIL FROM MUNICH", fontsize=7.6, fontweight="bold", color=TEXT, va="center")
lines = [("Bamberg (ICE)", 250, 200), ("Andechs (S8 + bus)", 45, 70), ("Aying (S5)", 32, 45)]
yy = 0.52
for i, (name, km, mins) in enumerate(lines):
    x0 = 0.022 + i * 0.330
    axt.text(x0, yy, name, fontsize=7.0, color=MUTED, va="center")
    axt.text(x0, yy - 0.22, f"{km:,.0f} km · {mins // 60} h {mins % 60:02d}", fontsize=7.6, color=GOLD,
             va="center", fontweight="bold")

fig.text(0.030, 0.020, "No car: every link is a scheduled S-Bahn, bus or ICE service from the December "
         "2019 timetable. Lines are schematic, not track geometry.", fontsize=7.2, color=DIM, ha="left", va="bottom")
fig.text(0.972, 0.020, "basemap: Natural Earth 1:50m · rail links schematic", fontsize=7.2, color=DIM, ha="right", va="bottom")

OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, dpi=240, facecolor=BG)
plt.close(fig)
print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")
