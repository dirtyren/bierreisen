#!/usr/bin/env python3
"""Render three regional posters (USA / Europe / UK) for the README.

Reads assets/trips.json and renders:
  assets/maps/usa.png      Colorado + Florida, two panels
  assets/maps/europe.png   Belgium, Bavaria & Bohemia, Italy & Switzerland
  assets/maps/uk.png       Great Britain alone
"""
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

ROOT = pathlib.Path(__file__).resolve().parent.parent
GEO = ROOT / "assets" / "ne_50m_countries.geojson"
STATES = ROOT / "assets" / "us_states.geojson"
TRIPS = ROOT / "assets" / "trips.json"
OUT = ROOT / "assets" / "maps"

# ------------------------------------------------------------------ palette
BG = "#0b0c15"
OCEAN = "#080a14"
PANEL = "#151833"
BORDER = "#2a3050"
LAND = "#293150"
LAND_EDGE = "#49527d"
GRID = "#1c2340"
GOLD = "#e6a817"
TEXT = "#eef1f6"
MUTED = "#9aa5bc"
DIM = "#6f7a94"

COLORS = {
    "uk": "#f2604f",
    "belgium": "#f5a623",
    "germany_czech": "#43d19e",
    "colorado": "#54a8f5",
    "florida": "#ff7fa3",
    "italy_switzerland": "#b283f8",
}
BEERS = {
    "uk": "Landlord · Jaipur IPA · Jarl",
    "belgium": "Westvleteren 12 · Cantillon · Orval",
    "germany_czech": "Schlenkerla · Mahr's aU · Kout 12°",
    "colorado": "Bierstadt Pils · Funkwerks Saison",
    "florida": "Jai Alai · Hunahpu's · Maple Bacon",
    "italy_switzerland": "Tipopils · Re Ale · Xyauyù",
}

plt.rcParams.update({
    "font.family": ["Avenir Next", "DejaVu Sans"],
    "text.color": TEXT,
    "savefig.facecolor": BG,
    "figure.facecolor": BG,
})

world = json.loads(GEO.read_text())
states = json.loads(STATES.read_text())
trips = {t["id"]: t for t in json.loads(TRIPS.read_text())}


# ------------------------------------------------------------------ geometry
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


def window(proj, lon, lat, w_in, h_in, pad=0.0):
    x, y = lcc([lon[0], lon[1]], [lat[0], lat[1]], *proj)
    xr, yr = (float(x.min()), float(x.max())), (float(y.min()), float(y.max()))
    cx, cy = sum(xr) / 2, sum(yr) / 2
    dx = (xr[1] - xr[0]) * (1 + pad)
    dy = (yr[1] - yr[0]) * (1 + pad)
    target = w_in / h_in
    if dx / dy < target:
        dx = dy * target
    else:
        dy = dx / target
    return (cx - dx / 2, cx + dx / 2), (cy - dy / 2, cy + dy / 2)


def draw_land(ax, proj, lon_win, lat_win, states_too=False):
    patches = []
    for feat in world["features"]:
        for ring in rings(feat["geometry"]):
            arr = np.asarray(ring, dtype=float)
            if len(arr) < 4 or arr[:, 0].max() - arr[:, 0].min() > 200:
                continue
            if (arr[:, 1].max() < lat_win[0] - 1 or arr[:, 1].min() > lat_win[1] + 1
                    or arr[:, 0].max() < lon_win[0] - 1 or arr[:, 0].min() > lon_win[1] + 1):
                continue
            x, y = lcc(arr[:, 0], arr[:, 1], *proj)
            patches.append(Polygon(np.column_stack([x, y]), closed=True))
    ax.add_collection(PatchCollection(patches, facecolor=LAND, edgecolor=LAND_EDGE,
                                      linewidth=0.5, zorder=1))
    if states_too:
        sp = []
        for feat in states["features"]:
            for ring in rings(feat["geometry"]):
                arr = np.asarray(ring, dtype=float)
                if len(arr) < 4:
                    continue
                x, y = lcc(arr[:, 0], arr[:, 1], *proj)
                sp.append(Polygon(np.column_stack([x, y]), closed=True))
        ax.add_collection(PatchCollection(sp, facecolor="none", edgecolor="#3a4368",
                                          linewidth=0.4, zorder=2))


def graticule(ax, proj, lon_win, lat_win, lims):
    lats = np.linspace(lat_win[0], lat_win[1], 60)
    for lon in range(int(lon_win[0]) // 5 * 5, int(lon_win[1]) + 5, 5):
        x, y = lcc(np.full_like(lats, lon), lats, *proj)
        ax.plot(x, y, color=GRID, lw=0.5, zorder=0)
        inside = (y > lims[1][0]) & (y < lims[1][1])
        if inside.any():
            i = np.where(inside)[0][0]
            ax.text(x[i], lims[1][0] + 0.012 * (lims[1][1] - lims[1][0]),
                    f"{abs(lon)}°{'W' if lon < 0 else 'E'}", fontsize=5.6, color=DIM,
                    ha="center", va="bottom", zorder=6)
    lons = np.linspace(lon_win[0], lon_win[1], 60)
    for lat in range(int(lat_win[0]) // 5 * 5, int(lat_win[1]) + 5, 5):
        x, y = lcc(lons, np.full_like(lons, lat), *proj)
        ax.plot(x, y, color=GRID, lw=0.5, zorder=0)
        inside = (x > lims[0][0]) & (x < lims[0][1])
        if inside.any():
            i = np.where(inside)[0][0]
            ax.text(lims[0][0] + 0.008 * (lims[0][1] - lims[0][0]), y[i], f"{lat}°N",
                    fontsize=5.6, color=DIM, ha="left", va="center", zorder=6)


def scale_bar(ax, proj, km=500, x=0.955, y=0.045):
    _, y0 = lcc([proj[0]], [proj[1]], *proj)
    _, y1 = lcc([proj[0]], [proj[1] + 1], *proj)
    km_per_unit = 111.32 / abs(float(np.ravel(y1 - y0)[0]))
    xlim = ax.get_xlim()
    frac = (km / km_per_unit) / (xlim[1] - xlim[0])
    half = frac / 2
    for xx in (x - half, x + half):
        ax.plot([xx, xx], [y, y + 0.012], transform=ax.transAxes, color=MUTED, lw=1.4,
                zorder=9, path_effects=[pe.withStroke(linewidth=3, foreground=BG)])
    ax.plot([x - half, x + half], [y, y], transform=ax.transAxes, color=MUTED, lw=1.4,
            zorder=9, path_effects=[pe.withStroke(linewidth=3, foreground=BG)])
    ax.text(x, y + 0.022, f"{km} km", transform=ax.transAxes, fontsize=6.4, color=MUTED,
            ha="center", va="bottom", zorder=9,
            path_effects=[pe.withStroke(linewidth=3, foreground=BG)])


def panel(fig, rect, proj, lon_win, lat_win, title=None, note=None, states_too=False, km=500):
    ax = fig.add_axes(rect)
    ax.set_facecolor(OCEAN)
    for s in ax.spines.values():
        s.set_color(BORDER)
        s.set_linewidth(0.9)
    lims = window(proj, lon_win, lat_win, rect[2] * fig.get_size_inches()[0],
                  rect[3] * fig.get_size_inches()[1])
    ax.set_xlim(*lims[0])
    ax.set_ylim(*lims[1])
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    graticule(ax, proj, lon_win, lat_win, lims)
    draw_land(ax, proj, lon_win, lat_win, states_too=states_too)
    if title:
        ax.text(0.025, 0.965, title, transform=ax.transAxes, fontsize=10.5, fontweight="bold",
                color=TEXT, va="top", ha="left", zorder=9,
                bbox=dict(boxstyle="round,pad=0.42", facecolor="#0b0c15", edgecolor=BORDER,
                          linewidth=0.6, alpha=0.93))
    if note:
        ax.text(0.028, 0.905, note, transform=ax.transAxes, fontsize=7.4, color=MUTED,
                va="top", ha="left", zorder=9,
                path_effects=[pe.withStroke(linewidth=2.6, foreground=BG)])
    scale_bar(ax, proj, km=km)
    return ax


def plot_trip(ax, trip, proj, label_every=0, font=7.4):
    color = COLORS[trip["id"]]
    if trip["path"]:
        xs, ys = lcc([q[1] for q in trip["path"]], [q[0] for q in trip["path"]], *proj)
        ax.plot(xs, ys, color=color, lw=2.0, alpha=0.55, zorder=3,
                solid_capstyle="round", solid_joinstyle="round")
    sx, sy = lcc([s["lon"] for s in trip["stops"]], [s["lat"] for s in trip["stops"]], *proj)
    ax.scatter(sx, sy, s=30, c=color, alpha=0.9, linewidths=0.5, edgecolors="#0b0c15", zorder=4)

    if label_every:
        placed = []
        for i in range(0, len(trip["stops"]), label_every):
            s = trip["stops"][i]
            px, py = float(sx[i]), float(sy[i])
            for dx, dy, ha in ((10, 0, "left"), (-10, 0, "right"), (0, 12, "center"), (0, -12, "center")):
                ok = True
                for (qx, qy) in placed:
                    if abs(qx - px) < 0.06 * (ax.get_xlim()[1] - ax.get_xlim()[0]) and \
                       abs(qy - py) < 0.035 * (ax.get_ylim()[1] - ax.get_ylim()[0]):
                        ok = False
                        break
                if not ok:
                    continue
                ax.annotate(s["name"], xy=(px, py), xytext=(dx, dy), textcoords="offset points",
                            fontsize=font, color=TEXT, ha=ha, va="center", zorder=8,
                            path_effects=[pe.withStroke(linewidth=3, foreground=BG)])
                placed.append((px, py))
                break


def header(fig, title, subtitle, stats):
    fig.text(0.028, 0.958, title, fontsize=40, fontweight="bold", color=GOLD,
             ha="left", va="center")
    fig.text(0.028, 0.912, subtitle, fontsize=12.5, color=MUTED, ha="left", va="center",
             style="italic")
    fig.text(0.972, 0.945, stats, fontsize=10.5, color=TEXT, ha="right", va="center",
             fontweight="bold")
    fig.add_artist(plt.Line2D([0.028, 0.972], [0.893, 0.893], color=GOLD, lw=1.2, alpha=0.6))


def card(fig, rect, trip, color):
    ax = fig.add_axes(rect)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0.004, 0.03), 0.992, 0.94,
                                boxstyle="round,pad=0,rounding_size=0.05",
                                facecolor=PANEL, edgecolor=BORDER, linewidth=0.8))
    ax.add_patch(FancyBboxPatch((0.004, 0.03), 0.010, 0.94,
                                boxstyle="round,pad=0,rounding_size=0.02",
                                facecolor=color, edgecolor="none"))
    ax.text(0.055, 0.74, trip["title"], fontsize=13.5, fontweight="bold", color=TEXT,
            ha="left", va="center")
    ax.text(0.055, 0.50, f"{trip['days']} days  ·  {len(trip['stops'])} stops  ·  {trip['countries']}",
            fontsize=8.6, color=MUTED, ha="left", va="center")
    ax.text(0.055, 0.30, trip["route"], fontsize=8.2, color=color, ha="left", va="center",
            fontweight="bold")
    ax.text(0.055, 0.12, BEERS[trip["id"]], fontsize=8.0, color=DIM, ha="left", va="center",
            style="italic")


def footer(fig, text):
    fig.text(0.028, 0.018, text, fontsize=7.4, color=DIM, ha="left", va="bottom")
    fig.text(0.972, 0.018, "basemap: Natural Earth 1:50m · routes from each dossier's map data",
             fontsize=7.4, color=DIM, ha="right", va="bottom")


# ------------------------------------------------------------------ USA
def make_usa():
    fig = plt.figure(figsize=(20, 13), dpi=240)
    fig.add_artist(Rectangle((0, 0), 1, 1, transform=fig.transFigure, facecolor=BG, zorder=-10))
    us = [trips["colorado"], trips["florida"]]
    header(fig, "USA", "Colorado and Florida, two separate beer trails",
           f"2 trips · {us[0]['days'] + us[1]['days']} days · "
           f"{len(us[0]['stops']) + len(us[1]['stops'])} stops · United States")

    ax1 = panel(fig, [0.030, 0.315, 0.300, 0.545],
                (-105.4, 39.0, 33.0, 45.0), (-105.45, -104.55), (39.55, 40.75),
                title="COLORADO", note="39 stops · Denver to Fort Collins", states_too=True, km=50)
    plot_trip(ax1, us[0], (-105.4, 39.0, 33.0, 45.0), label_every=6)

    ax2 = panel(fig, [0.350, 0.315, 0.300, 0.545],
                (-84.5, 27.0, 24.0, 32.0), (-83.2, -79.6), (24.8, 30.9),
                title="FLORIDA", note="43 stops · Miami to Dunedin", km=100)
    plot_trip(ax2, us[1], (-84.5, 27.0, 24.0, 32.0), label_every=7)

    ax3 = fig.add_axes([0.670, 0.315, 0.300, 0.545])
    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.axis("off")
    ax3.text(0.0, 0.96, "THE TWO TRAILS", fontsize=10, fontweight="bold", color=TEXT,
             ha="left", va="top")
    ax3.text(0.0, 0.885,
             "Colorado is a mountain loop out of Denver: RiNo taprooms, then Golden, Boulder\n"
             "and Fort Collins along the Front Range. Florida is a one-way drive from Miami\n"
             "through Orlando to Tampa Bay, built around barrel-aged stouts and pastry sours.",
             fontsize=8.6, color=MUTED, ha="left", va="top", linespacing=1.7)
    card(fig, [0.030, 0.085, 0.300, 0.195], us[0], COLORS["colorado"])
    card(fig, [0.350, 0.085, 0.300, 0.195], us[1], COLORS["florida"])
    # legend
    ax3.plot([0.0, 0.06], [0.34, 0.34], color=COLORS["colorado"], lw=2.0, alpha=0.8,
             transform=ax3.transAxes, clip_on=False)
    ax3.text(0.075, 0.34, "itinerary route", fontsize=8.2, color=MUTED, va="center")
    ax3.scatter([0.032], [0.26], s=34, c=TEXT, edgecolors="#0b0c15", linewidths=0.5,
                transform=ax3.transAxes, clip_on=False)
    ax3.text(0.075, 0.26, "brewery / pub stop", fontsize=8.2, color=MUTED, va="center")
    ax3.text(0.0, 0.13, "Both trips start and end at the airport they fly into: DEN for Colorado,\n"
             "MIA in and TPA out for Florida. Each has a 4800×3120 trip sheet with the full\n"
             "day-by-day ledger, per-city rankings and beer tables.",
             fontsize=8.4, color=MUTED, ha="left", va="top", linespacing=1.7)

    footer(fig, "Open assets/trips/colorado-craft-beer.png and florida-brewery-trail.png for the full trip sheets.")
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "usa.png", dpi=240, facecolor=BG)
    plt.close(fig)


# ------------------------------------------------------------------ Europe
def make_europe():
    fig = plt.figure(figsize=(20, 13), dpi=240)
    fig.add_artist(Rectangle((0, 0), 1, 1, transform=fig.transFigure, facecolor=BG, zorder=-10))
    ids = ["belgium", "germany_czech", "italy_switzerland"]
    stops = sum(len(trips[i]["stops"]) for i in ids)
    days = sum(trips[i]["days"] for i in ids)
    header(fig, "EUROPE", "Belgium, Bavaria & Bohemia, Italy & Switzerland",
           f"3 trips · {days} days · {stops} stops · Belgium, Germany, Czechia, Italy, Switzerland")

    proj = (6.0, 47.0, 40.0, 52.0)
    ax = panel(fig, [0.030, 0.105, 0.445, 0.765], proj, (-1.0, 15.5), (41.4, 53.6), km=200)
    for tid in ids:
        plot_trip(ax, trips[tid], proj)

    for name, lon, lat in (("BELGIUM", 4.6, 50.6), ("GERMANY", 9.6, 51.2), ("CZECHIA", 14.3, 49.9),
                           ("ITALY", 12.0, 43.0), ("SWITZERLAND", 8.2, 46.6)):
        x, y = lcc([lon], [lat], *proj)
        ax.text(float(x[0]), float(y[0]), name, fontsize=7.0, color=DIM, ha="center",
                va="center", zorder=5, fontweight="bold", alpha=0.85)

    axr = fig.add_axes([0.500, 0.105, 0.470, 0.765])
    axr.set_xlim(0, 1)
    axr.set_ylim(0, 1)
    axr.axis("off")
    axr.text(0.0, 0.985, "THREE ROUTES", fontsize=10.5, fontweight="bold", color=TEXT,
             ha="left", va="top")
    axr.text(0.0, 0.925,
             "One continental panel, three separate trips. The Belgian route runs Brussels to\n"
             "Pilsen, so it finishes in Czechia; Bavaria & Bohemia covers Franconian village\n"
             "breweries, the Zoigl country and the birth of pilsner; Italy & Switzerland is a\n"
             "culture-first loop with a craft-beer thread from Rome to St. Moritz.",
             fontsize=8.6, color=MUTED, ha="left", va="top", linespacing=1.7)

    for i, tid in enumerate(ids):
        card(fig, [0.500, 0.600 - i * 0.170, 0.470, 0.150], trips[tid], COLORS[tid])

    footer(fig, "Each route has its own 4800×3120 trip sheet in assets/trips/.")
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "europe.png", dpi=240, facecolor=BG)
    plt.close(fig)


# ------------------------------------------------------------------ UK
def make_uk():
    fig = plt.figure(figsize=(15, 17.5), dpi=240)
    fig.add_artist(Rectangle((0, 0), 1, 1, transform=fig.transFigure, facecolor=BG, zorder=-10))
    t = trips["uk"]
    header(fig, "UNITED KINGDOM", "England, Wales and Scotland in twelve days",
           f"{t['days']} days · {len(t['stops'])} stops · 3 nations")

    proj = (0.0, 54.0, 48.0, 58.0)
    ax = panel(fig, [0.05, 0.13, 0.90, 0.745], proj, (-7.6, 1.9), (49.8, 58.6), km=100)
    plot_trip(ax, t, proj, label_every=3, font=7.6)

    for name, lon, lat in (("SCOTLAND", -4.4, 57.3), ("ENGLAND", -1.9, 52.6),
                           ("WALES", -3.9, 52.3), ("IRELAND", -8.6, 53.3)):
        x, y = lcc([lon], [lat], *proj)
        ax.text(float(x[0]), float(y[0]), name, fontsize=9.5, color=DIM, ha="center",
                va="center", zorder=5, fontweight="bold", alpha=0.8)

    axr = fig.add_axes([0.05, 0.035, 0.90, 0.075])
    axr.set_xlim(0, 1)
    axr.set_ylim(0, 1)
    axr.axis("off")
    axr.text(0.0, 0.80, t["route"], fontsize=9.0, color=TEXT, va="center")
    axr.text(0.0, 0.35, f"Best poured: {BEERS['uk']}   ·   May–Jun or Sep–Oct   ·   £150–250 per day",
             fontsize=8.6, color=MUTED, va="center", style="italic")

    footer(fig, "Full trip sheet: assets/trips/uk-beer-pilgrimage.png")
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "uk.png", dpi=240, facecolor=BG)
    plt.close(fig)


if __name__ == "__main__":
    make_usa()
    make_europe()
    make_uk()
    for name in ("usa", "europe", "uk"):
        p = OUT / f"{name}.png"
        print(f"wrote {p.relative_to(ROOT)} ({p.stat().st_size // 1024} KB)")
