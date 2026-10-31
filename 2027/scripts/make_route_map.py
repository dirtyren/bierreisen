#!/usr/bin/env python3
"""Render the 2027 Bier Reisen route & itinerary poster (4800 x 3120 px at 240 dpi).

Supports --variant v1|v2|v3 (default: v1). Reads authoritative data for the chosen
variant and basemap from assets/ne_50m_countries.geojson, writing the poster PNG
deterministically with zero stderr output.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
from typing import Any, Dict, List, Optional, Sequence, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patheffects as pe
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.colors import LinearSegmentedColormap, to_hex
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle

HERE = pathlib.Path(__file__).resolve().parent
DIR_2027 = HERE.parent
REPO_ROOT = DIR_2027.parent
DATA_PATH = DIR_2027 / "data" / "route-2027.json"
OUT_PNG = DIR_2027 / "assets" / "2027-route-map.png"
GEO_PATH = REPO_ROOT / "assets" / "ne_50m_countries.geojson"

VARIANT_CONFIGS: Dict[str, Dict[str, Any]] = {
    "v1": {
        "data_path": DATA_PATH,
        "out_png": OUT_PNG,
        "eyebrow": "BIERREISEN   ·   2027 ROUTE & ITINERARY POSTER",
        "title": "BIER REISEN 2027",
        "version_tag": None,
        "headline_stats": "15 days  ·  14 nights  ·  10 bases  ·  2,297 km  ·  27 h driving  ·  3 countries",
        "route_line_1": (
            "Frankfurt Airport → Bruges (2 nights) → Ghent (1) → Bamberg (2) → "
            "Pivovar Permon, Sokolov (1) → Plzeň (2)"
        ),
        "route_line_2": (
            "→ Kout na Šumavě (1) → Maxlrain Bierstube, Tuntenhausen (1) → "
            "Andechs/Herrsching (1) → Munich (2) → Nuremberg (1) → Frankfurt Airport"
        ),
        "meta_line": "Authoritative data: 2027/data/route-2027.json  ·  OSRM car routing",
        "leg_bends": {
            ("fra", "bruges"): 0.06,
            ("bruges", "ghent"): 0.10,
            ("ghent", "bamberg"): 0.15,
            ("bamberg", "sokolov"): 0.06,
            ("sokolov", "plzen"): 0.08,
            ("plzen", "kout"): -0.08,
            ("kout", "maxlrain"): -0.05,
            ("maxlrain", "andechs"): -0.10,
            ("andechs", "munich"): 0.12,
            ("munich", "nuremberg"): 0.05,
            ("nuremberg", "fra"): 0.08,
        },
        "preferred_angles": {
            "fra": [-120, -140, -95, 180, -75],
            "bruges": [110, 90, 135, 160, 70, 180],
            "ghent": [-130, -110, -150, -90, 180],
            "bamberg": [70, 50, 90, 35, 115],
            "sokolov": [85, 105, 65, 125, 45],
            "plzen": [10, 0, 28, -15, 45],
            "kout": [-10, 0, -28, 15, -45],
            "maxlrain": [-25, -45, -10, 0, -70],
            "andechs": [180, -155, -135, 160, -115],
            "munich": [62, 55, 68, 48, 74],
            "nuremberg": [180, 165, -165, 145, -145],
        },
        "long_days": (4, 10),
        "ledger_day_tags": {4: "[LONGEST LEG]", 10: "[LONG DRIVE]"},
        "must_drink": (
            "Flemish red (Bruges) · Gruut herb beer (Ghent) · Rauchbier & aU Ungespundetes (Bamberg) · "
            "Permon IPA 15° (Sokolov) · Tank Pilsner (Plzeň) · Kout 12° (Kout na Šumavě) · "
            "Maxlrainer Helles (Maxlrain) · Doppelbock Dunkel (Andechs) · Holzfass Edelstoff & Aventinus (Munich) · Rotbier (Nuremberg)"
        ),
        "totals_line": (
            "15 days · 14 nights · 10 bases · 11 driving legs · 2,296.5 km (2,297 km) · "
            "27 h 01 driving (1,621 min) · Germany, Belgium & Czechia · Best season May–Sep"
        ),
    },
    "v2": {
        "data_path": DIR_2027 / "v2" / "data" / "route-2027-v2.json",
        "out_png": DIR_2027 / "v2" / "assets" / "2027-route-map-v2.png",
        "eyebrow": "BIERREISEN   ·   2027 ROUTE & ITINERARY POSTER   ·   COLOGNE IN, NUREMBERG OUT",
        "title": "BIER REISEN 2027",
        "version_tag": "V2",
        "headline_stats": "15 days  ·  14 nights  ·  10 bases  ·  2,298 km  ·  27 h driving  ·  3 countries",
        "route_line_1": (
            "Frankfurt Airport → Bruges (2N) → Ghent (1N) → Cologne (1N, new) → "
            "Bamberg (2N) → Pivovar Permon, Sokolov (1N)"
        ),
        "route_line_2": (
            "→ Plzeň (2N) → Kout na Šumavě (1N) → Maxlrain Bierstube (1N) → "
            "Andechs/Herrsching (1N) → Munich (2N) → Frankfurt Airport"
        ),
        "meta_line": (
            "Changed vs v1: Nuremberg night removed, Cologne night added between Ghent & Bamberg  ·  "
            "2027/v2/data/route-2027-v2.json"
        ),
        "leg_bends": {
            ("fra", "bruges"): 0.08,
            ("bruges", "ghent"): 0.10,
            ("ghent", "cologne"): 0.12,
            ("cologne", "bamberg"): 0.12,
            ("bamberg", "sokolov"): 0.06,
            ("sokolov", "plzen"): 0.08,
            ("plzen", "kout"): -0.08,
            ("kout", "maxlrain"): -0.05,
            ("maxlrain", "andechs"): -0.10,
            ("andechs", "munich"): 0.12,
            ("munich", "fra"): 0.07,
        },
        "preferred_angles": {
            "fra": [-120, -140, -95, 180, -75],
            "bruges": [110, 90, 135, 160, 70, 180],
            "ghent": [-130, -110, -150, -90, 180],
            "cologne": [95, 115, 75, 135, 55, 180],
            "bamberg": [70, 50, 90, 35, 115],
            "sokolov": [85, 105, 65, 125, 45],
            "plzen": [10, 0, 28, -15, 45],
            "kout": [-10, 0, -28, 15, -45],
            "maxlrain": [-25, -45, -10, 0, -70],
            "andechs": [180, -155, -135, 160, -115],
            "munich": [25, 42, 10, 55, 0],
        },
        "long_days": (5,),
        "ledger_day_tags": {4: "[NEW IN V2]", 5: "[LONG DAY]"},
        "must_drink": (
            "Flemish red (Bruges) · Gruut herb beer (Ghent) · Kölsch in 0.2 L Stangen (Cologne) · "
            "Rauchbier & aU (Bamberg) · Permon IPA 15° (Sokolov) · Tank Pilsner (Plzeň) · "
            "Kout 12° (Kout na Šumavě) · Maxlrainer Helles (Maxlrain) · Doppelbock Dunkel (Andechs) · Holzfass Edelstoff (Munich)"
        ),
        "totals_line": (
            "15 days · 14 nights · 10 bases · 11 driving legs · 2,298.3 km (2,298 km) · "
            "27 h 04 driving (1,624 min) · Germany, Belgium & Czechia · Best season May–Sep"
        ),
    },
    "v3": {
        "data_path": DIR_2027 / "v3" / "data" / "route-2027-v3.json",
        "out_png": DIR_2027 / "v3" / "assets" / "2027-route-map-v3.png",
        "eyebrow": "BIERREISEN   ·   2027 ROUTE & ITINERARY POSTER   ·   WÜRZBURG BREWERY NIGHT",
        "title": "BIER REISEN 2027",
        "version_tag": "V3",
        "headline_stats": "16 days  ·  15 nights  ·  11 bases  ·  2,307.5 km  ·  27 h 08  ·  3 countries",
        "route_line_1": (
            "Frankfurt Airport → Bruges (2N) → Ghent (1N) → Cologne (1N) → "
            "Würzburg (1N, new) → Bamberg (2N)"
        ),
        "route_line_2": (
            "→ Pivovar Permon, Sokolov (1N) → Plzeň (2N) → Kout na Šumavě (1N) → "
            "Maxlrain (1N) → Andechs/Herrsching (1N) → Munich (2N) → Frankfurt Airport"
        ),
        "meta_line": (
            "Changed vs v2: Würzburg night added between Cologne & Bamberg — no middle leg exceeds 3 h 15  ·  "
            "2027/v3/data/route-2027-v3.json"
        ),
        "leg_bends": {
            ("fra", "bruges"): 0.08,
            ("bruges", "ghent"): 0.10,
            ("ghent", "cologne"): 0.12,
            ("cologne", "wurzburg"): 0.16,
            ("wurzburg", "bamberg"): 0.16,
            ("bamberg", "sokolov"): 0.06,
            ("sokolov", "plzen"): 0.08,
            ("plzen", "kout"): -0.08,
            ("kout", "maxlrain"): -0.05,
            ("maxlrain", "andechs"): -0.10,
            ("andechs", "munich"): 0.12,
            ("munich", "fra"): 0.07,
        },
        "preferred_angles": {
            "fra": [-155, -140, 180, -125, -170],
            "bruges": [110, 90, 135, 160, 70, 180],
            "ghent": [-130, -110, -150, -90, 180],
            "cologne": [95, 115, 75, 135, 55, 180],
            "wurzburg": [-95, -115, -75, -130, 105],
            "bamberg": [65, 45, -60, 85, -80],
            "sokolov": [85, 105, 65, 125, 45],
            "plzen": [10, 0, 28, -15, 45],
            "kout": [-10, 0, -28, 15, -45],
            "maxlrain": [-25, -45, -10, 0, -70],
            "andechs": [180, -155, -135, 160, -115],
            "munich": [25, 42, 10, 55, 0],
        },
        "long_days": (),
        "new_days": (5, 6),
        "ledger_day_tags": {5: "[NEW IN V3]", 6: "[NEW IN V3]"},
        "map_callout": {
            "x0": 0.590,
            "y0": 0.820,
            "w": 0.390,
            "h": 0.156,
            "heading": "WHY WÜRZBURG (STOP #5 · 1N)  —  GHENT → BAMBERG BREAKER",
            "line1": "Splits Ghent → Bamberg (old 6h51) into 3 short days: 3:06 · 3:02 · 1:03",
            "line2": "Wine-capital pivot to Franconian lager: 1643 Hofbräu, Goldene Gans & Ochsenfurt",
            "line3": "Every middle leg on the 16-day loop stays under 3 h 15 (max 3:11).",
        },
        "must_drink": (
            "Flemish red (Bruges) · Gruut (Ghent) · Kölsch (Cologne) · Hofbräu Pils, Schwarzbier & Goldene Gans (Würzburg) · "
            "Rauchbier & aU (Bamberg) · Permon IPA 15° (Sokolov) · Tank Pilsner (Plzeň) · "
            "Kout 12° · Maxlrainer Helles · Doppelbock (Andechs) · Holzfass Edelstoff (Munich)"
        ),
        "totals_line": (
            "16 days · 15 nights · 11 bases · 12 driving legs · 2,307.5 km · "
            "27 h 08 driving (1,628 min) · Every middle leg under 3 h 15 · Germany, Belgium & Czechia"
        ),
    },
}

# Palette matching scripts/make_trip_maps.py
BG = "#0b0c15"
OCEAN = "#080a14"
PANEL = "#151833"
PANEL_ALT = "#1a1e3d"
BORDER = "#2a3050"
LAND = "#293150"
LAND_EDGE = "#49527d"
GRID = "#1e2440"
GRID_LAND = "#364068"
GOLD = "#e6a817"
LEG_TEXT = "#f5d76e"
TEXT = "#eef1f6"
MUTED = "#9aa5bc"
DIM = "#717c96"

RAMP = ["#f5a623", "#ff7a59", "#38d399", "#54a8f5", "#b283f8"]

plt.rcParams.update({
    "font.family": ["Avenir Next", "DejaVu Sans"],
    "text.color": TEXT,
    "text.parse_math": False,
    "savefig.facecolor": BG,
    "figure.facecolor": BG,
})


def rings(geom: Dict[str, Any]):
    if geom["type"] == "Polygon":
        yield from geom["coordinates"]
    elif geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            yield from poly


def lcc(lon, lat, lon0: float, lat0: float, s1: float, s2: float):
    """Lambert conformal conic (spherical)."""
    lon = np.radians(np.asarray(lon, dtype=float))
    lat = np.radians(np.asarray(lat, dtype=float))
    l0 = math.radians(lon0)
    p0 = math.radians(lat0)
    if abs(s2 - s1) < 1e-4:
        s1, s2 = lat0 - 1.0, lat0 + 1.0
    p1, p2 = math.radians(s1), math.radians(s2)
    n = math.log(math.cos(p1) / math.cos(p2)) / math.log(
        math.tan(math.pi / 4 + p2 / 2) / math.tan(math.pi / 4 + p1 / 2)
    )
    F = math.cos(p1) * math.tan(math.pi / 4 + p1 / 2) ** n / n
    rho = F / np.tan(math.pi / 4 + lat / 2) ** n
    rho0 = F / np.tan(math.pi / 4 + p0 / 2) ** n
    x = rho * np.sin(n * (lon - l0))
    y = rho0 - rho * np.cos(n * (lon - l0))
    return x, y


def _km_per_unit(proj: Tuple[float, float, float, float]) -> float:
    lon0, lat0, s1, s2 = proj
    _, y_a = lcc([lon0], [lat0 - 0.5], lon0, lat0, s1, s2)
    _, y_b = lcc([lon0], [lat0 + 0.5], lon0, lat0, s1, s2)
    return 111.32 / abs(float(np.ravel(y_b - y_a)[0]))


def fmt_hmm(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    return f"{h}:{m:02d}"


def fmt_km_round(km: float) -> int:
    return int(math.floor(km + 0.5))


def make_cmap(ramp: Sequence[str]) -> LinearSegmentedColormap:
    return LinearSegmentedColormap.from_list("route2027", list(ramp), N=256)


def stop_color(cmap: LinearSegmentedColormap, idx: int, total: int) -> str:
    t = 0.0 if total <= 1 else idx / (total - 1.0)
    return to_hex(cmap(t))


def day_color(cmap: LinearSegmentedColormap, day: int, total_days: int) -> str:
    t = 0.0 if total_days <= 1 else (day - 1.0) / (total_days - 1.0)
    return to_hex(cmap(t))


def quad_bezier(
    p0: Tuple[float, float],
    p2: Tuple[float, float],
    bend_perp: float = 0.0,
    n_pts: int = 64,
) -> Tuple[np.ndarray, np.ndarray]:
    """Quadratic Bezier from p0 to p2 with perpendicular midpoint deflection `bend_perp` (fraction of chord)."""
    x0, y0 = p0
    x2, y2 = p2
    dx, dy = x2 - x0, y2 - y0
    chord = math.hypot(dx, dy)
    if chord < 1e-9 or abs(bend_perp) < 1e-6:
        t = np.linspace(0.0, 1.0, n_pts)
        return x0 + t * dx, y0 + t * dy
    # Left-hand unit normal (-dy, dx) / chord
    nx, ny = -dy / chord, dx / chord
    # For quadratic Bezier, midpoint B(0.5) = 0.5*(p0+p2) + 0.5*(p1 - 0.5*(p0+p2)), so offset control by 2*bend
    cx = 0.5 * (x0 + x2) + 2.0 * bend_perp * chord * nx
    cy = 0.5 * (y0 + y2) + 2.0 * bend_perp * chord * ny
    t = np.linspace(0.0, 1.0, n_pts)
    omt = 1.0 - t
    bx = omt * omt * x0 + 2.0 * omt * t * cx + t * t * x2
    by = omt * omt * y0 + 2.0 * omt * t * cy + t * t * y2
    return bx, by


def draw_land(ax, world: Dict[str, Any], proj: Tuple[float, float, float, float], lon_win: Tuple[float, float], lat_win: Tuple[float, float]):
    lon0, lat0, s1, s2 = proj
    patches = []
    for feat in world["features"]:
        for ring in rings(feat["geometry"]):
            arr = np.asarray(ring, dtype=float)
            if len(arr) < 4 or arr[:, 0].max() - arr[:, 0].min() > 200:
                continue
            if (arr[:, 1].max() < lat_win[0] - 8 or arr[:, 1].min() > lat_win[1] + 8
                    or arr[:, 0].max() < lon_win[0] - 10 or arr[:, 0].min() > lon_win[1] + 10):
                continue
            x, y = lcc(arr[:, 0], arr[:, 1], lon0, lat0, s1, s2)
            patches.append(Polygon(np.column_stack([x, y]), closed=True))
    ax.add_collection(PatchCollection(
        patches, facecolor=LAND, edgecolor=LAND_EDGE, linewidth=0.70, zorder=1.0
    ))


def _in_axes_boxes(ax, x_data: float, y_data: float, axes_boxes: Sequence[Tuple[float, float, float, float]], pad: float = 0.024) -> bool:
    ax_pt = ax.transAxes.inverted().transform(ax.transData.transform((x_data, y_data)))
    fx, fy = float(ax_pt[0]), float(ax_pt[1])
    for bx0, by0, bx1, by1 in axes_boxes:
        if (bx0 - pad <= fx <= bx1 + pad) and (by0 - pad <= fy <= by1 + pad):
            return True
    return False


def draw_graticule(
    ax,
    proj: Tuple[float, float, float, float],
    lon_win: Tuple[float, float],
    lat_win: Tuple[float, float],
    xlim: Tuple[float, float],
    ylim: Tuple[float, float],
    skip_axes_boxes: Sequence[Tuple[float, float, float, float]] = (),
) -> List[Any]:
    lon0, lat0, s1, s2 = proj
    tick_texts: List[Any] = []
    lats_dense = np.linspace(lat_win[0] - 5, lat_win[1] + 5, 160)
    lons_dense = np.linspace(lon_win[0] - 8, lon_win[1] + 8, 160)

    lon_vals = np.arange(math.floor(lon_win[0]) - 2, math.ceil(lon_win[1]) + 3, 2.0)
    for lon in lon_vals:
        is_major = abs(lon % 4.0) < 1e-4
        x, y = lcc(np.full_like(lats_dense, lon), lats_dense, lon0, lat0, s1, s2)
        ax.plot(x, y, color=GRID, lw=(0.72 if is_major else 0.42), zorder=0.2)
        ax.plot(x, y, color=GRID_LAND, lw=(0.56 if is_major else 0.34), alpha=(0.45 if is_major else 0.25), zorder=1.3)
        inside = (y > ylim[0]) & (y < ylim[1]) & (x > xlim[0] + 0.05 * (xlim[1] - xlim[0])) & (x < xlim[1] - 0.05 * (xlim[1] - xlim[0]))
        if inside.any():
            idx = int(np.where(inside)[0][0])
            tx = float(x[idx])
            ty = float(ylim[0] + 0.011 * (ylim[1] - ylim[0]))
            if not _in_axes_boxes(ax, tx, ty, skip_axes_boxes):
                hemi = "W" if lon < 0 else "E"
                tick_texts.append(ax.text(
                    tx, ty, f"{int(round(abs(lon)))}°{hemi}",
                    fontsize=6.2, color=DIM, ha="center", va="bottom", zorder=5.0,
                    path_effects=[pe.withStroke(linewidth=2.4, foreground=OCEAN)],
                ))

    lat_vals = np.arange(math.floor(lat_win[0]) - 2, math.ceil(lat_win[1]) + 3, 1.0)
    for lat in lat_vals:
        is_major = abs(lat % 2.0) < 1e-4
        x, y = lcc(lons_dense, np.full_like(lons_dense, lat), lon0, lat0, s1, s2)
        ax.plot(x, y, color=GRID, lw=(0.72 if is_major else 0.42), zorder=0.2)
        ax.plot(x, y, color=GRID_LAND, lw=(0.56 if is_major else 0.34), alpha=(0.45 if is_major else 0.25), zorder=1.3)
        inside = (x > xlim[0]) & (x < xlim[1]) & (y > ylim[0] + 0.05 * (ylim[1] - ylim[0])) & (y < ylim[1] - 0.05 * (ylim[1] - ylim[0]))
        if inside.any() and is_major:
            idx = int(np.where(inside)[0][0])
            tx = float(xlim[0] + 0.010 * (xlim[1] - xlim[0]))
            ty = float(y[idx])
            if not _in_axes_boxes(ax, tx, ty, skip_axes_boxes):
                hemi = "S" if lat < 0 else "N"
                tick_texts.append(ax.text(
                    tx, ty, f"{int(round(abs(lat)))}°{hemi}",
                    fontsize=6.2, color=DIM, ha="left", va="center", zorder=5.0,
                    path_effects=[pe.withStroke(linewidth=2.4, foreground=OCEAN)],
                ))
    return tick_texts


def draw_scale_bar(ax, proj: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    km_per_unit = _km_per_unit(proj)
    xlim = ax.get_xlim()
    panel_km = (xlim[1] - xlim[0]) * km_per_unit
    target_km = 0.14 * panel_km
    candidates = [25, 50, 100, 150, 200]
    km = min(candidates, key=lambda c: abs(c - target_km))
    frac = (km / km_per_unit) / (xlim[1] - xlim[0])

    x_center = 0.955 - 0.5 * frac
    y_bar = 0.042
    half = 0.5 * frac

    box_x0 = x_center - half - 0.018
    box_x1 = x_center + half + 0.018
    box_y0 = y_bar - 0.018
    box_y1 = y_bar + 0.052
    ax.add_patch(FancyBboxPatch(
        (box_x0, box_y0), box_x1 - box_x0, box_y1 - box_y0,
        boxstyle="round,pad=0,rounding_size=0.010",
        transform=ax.transAxes,
        facecolor=BG, edgecolor=BORDER, linewidth=0.75, alpha=0.92, zorder=8.8,
    ))
    ax.plot(
        [x_center - half, x_center + half], [y_bar, y_bar],
        transform=ax.transAxes, color=TEXT, lw=1.8, solid_capstyle="butt", zorder=9.0,
    )
    for xx in (x_center - half, x_center, x_center + half):
        tick_h = 0.011 if xx != x_center else 0.007
        ax.plot([xx, xx], [y_bar, y_bar + tick_h], transform=ax.transAxes, color=TEXT, lw=1.4, zorder=9.0)
    ax.text(
        x_center, y_bar + 0.018, f"{km} km",
        transform=ax.transAxes, fontsize=7.4, fontweight="bold", color=MUTED,
        ha="center", va="bottom", zorder=9.1,
    )
    return (box_x0, box_y0, box_x1, box_y1)


def draw_map_legend(ax, cmap: LinearSegmentedColormap, n_stops: int = 11) -> Tuple[float, float, float, float]:
    w, h = 0.285, 0.165
    x0, y0 = 0.020, 0.022
    ax.add_patch(FancyBboxPatch(
        (x0, y0), w, h,
        boxstyle="round,pad=0,rounding_size=0.012",
        transform=ax.transAxes,
        facecolor=BG, edgecolor=BORDER, linewidth=0.85, alpha=0.94, zorder=8.8,
    ))
    top_y = y0 + h - 0.023
    ax.text(x0 + 0.014, top_y, "ROUTE & STOP LEGEND", transform=ax.transAxes,
            fontsize=6.9, fontweight="bold", color=GOLD, ha="left", va="center", zorder=9.0)

    bar_y = top_y - 0.027
    bar_x0, bar_x1 = x0 + 0.052, x0 + w - 0.052
    n_seg = 48
    bx = np.linspace(bar_x0, bar_x1, n_seg + 1)
    for k in range(n_seg):
        ax.add_patch(Rectangle(
            (bx[k], bar_y - 0.0055), bx[k + 1] - bx[k] + 0.0005, 0.011,
            transform=ax.transAxes, facecolor=cmap(k / max(n_seg - 1, 1)), edgecolor="none", zorder=9.0,
        ))
    ax.text(x0 + 0.014, bar_y, "S1", transform=ax.transAxes, fontsize=6.5, fontweight="bold",
            color=to_hex(cmap(0.0)), ha="left", va="center", zorder=9.0)
    ax.text(x0 + w - 0.014, bar_y, f"S{n_stops}", transform=ax.transAxes, fontsize=6.5, fontweight="bold",
            color=to_hex(cmap(1.0)), ha="right", va="center", zorder=9.0)

    r1_y = bar_y - 0.031
    ax.scatter([x0 + 0.026], [r1_y], transform=ax.transAxes, s=135, c=[to_hex(cmap(0.3))],
               edgecolors=BG, linewidths=1.3, zorder=9.1)
    ax.text(x0 + 0.026, r1_y, "4", transform=ax.transAxes, fontsize=6.0, fontweight="bold",
            color=BG, ha="center", va="center", zorder=9.2)
    ax.text(x0 + 0.046, r1_y, f"Visit-order stop badge (1–{n_stops})", transform=ax.transAxes,
            fontsize=6.5, color=TEXT, ha="left", va="center", zorder=9.0)

    r2_y = r1_y - 0.030
    ax.add_patch(FancyBboxPatch(
        (x0 + 0.014, r2_y - 0.009), 0.025, 0.018,
        boxstyle="round,pad=0,rounding_size=0.004",
        transform=ax.transAxes, facecolor=GOLD, edgecolor="none", zorder=9.1,
    ))
    ax.text(x0 + 0.0265, r2_y, "2N", transform=ax.transAxes, fontsize=5.6, fontweight="bold",
            color=BG, ha="center", va="center", zorder=9.2)
    ax.add_patch(FancyBboxPatch(
        (x0 + 0.044, r2_y - 0.009), 0.025, 0.018,
        boxstyle="round,pad=0,rounding_size=0.004",
        transform=ax.transAxes, facecolor=PANEL_ALT, edgecolor=GOLD, linewidth=0.7, zorder=9.1,
    ))
    ax.text(x0 + 0.0565, r2_y, "1N", transform=ax.transAxes, fontsize=5.6, fontweight="bold",
            color=TEXT, ha="center", va="center", zorder=9.2)
    ax.text(x0 + 0.077, r2_y, "Nights per base chip", transform=ax.transAxes,
            fontsize=6.5, color=TEXT, ha="left", va="center", zorder=9.0)

    r3_y = r2_y - 0.029
    ax.text(x0 + 0.014, r3_y, "160 km · 1:59", transform=ax.transAxes, fontsize=6.2,
            fontweight="bold", color=LEG_TEXT, ha="left", va="center", zorder=9.1)
    ax.text(x0 + 0.116, r3_y, "OSRM leg distance & drive time", transform=ax.transAxes,
            fontsize=6.4, color=MUTED, ha="left", va="center", zorder=9.0)

    return (x0, y0, x0 + w, y0 + h)


def draw_map_callout(ax, ccfg: Dict[str, Any]) -> Tuple[float, float, float, float]:
    x0, y0, w, h = float(ccfg["x0"]), float(ccfg["y0"]), float(ccfg["w"]), float(ccfg["h"])
    ax.add_patch(FancyBboxPatch(
        (x0, y0), w, h,
        boxstyle="round,pad=0,rounding_size=0.012",
        transform=ax.transAxes,
        facecolor=BG, edgecolor=GOLD, linewidth=0.95, alpha=0.94, zorder=8.8,
    ))
    top_y = y0 + h - 0.026
    ax.text(x0 + 0.018, top_y, ccfg["heading"], transform=ax.transAxes,
            fontsize=7.3, fontweight="bold", color=GOLD, ha="left", va="center", zorder=9.0)
    ax.text(x0 + 0.018, top_y - 0.038, ccfg["line1"], transform=ax.transAxes,
            fontsize=6.9, fontweight="bold", color=TEXT, ha="left", va="center", zorder=9.0)
    ax.text(x0 + 0.018, top_y - 0.072, ccfg["line2"], transform=ax.transAxes,
            fontsize=6.7, color=LEG_TEXT, ha="left", va="center", zorder=9.0)
    ax.text(x0 + 0.018, top_y - 0.105, ccfg["line3"], transform=ax.transAxes,
            fontsize=6.7, fontweight="bold", color="#7fe0c8", ha="left", va="center", zorder=9.0)
    return (x0, y0, x0 + w, y0 + h)


def boxes_overlap(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float], pad: float = 0.0) -> bool:
    return (min(a[2] + pad, b[2] + pad) > max(a[0] - pad, b[0] - pad)) and (
        min(a[3] + pad, b[3] + pad) > max(a[1] - pad, b[1] - pad)
    )


def circle_hits_box(cx: float, cy: float, r: float, box: Tuple[float, float, float, float]) -> bool:
    nx = max(box[0], min(cx, box[2]))
    ny = max(box[1], min(cy, box[3]))
    return (cx - nx) ** 2 + (cy - ny) ** 2 < r * r


def fit_text_px(
    fig,
    ax,
    text: str,
    max_px: float,
    fontsize: float,
    fontweight: str = "normal",
    word_trim: bool = False,
) -> str:
    renderer = fig.canvas.get_renderer()
    probe = ax.text(0, 0, text, fontsize=fontsize, fontweight=fontweight)
    w = probe.get_window_extent(renderer=renderer).width
    if w <= max_px:
        probe.remove()
        return text
    cand = text
    while len(cand) > 12:
        if not word_trim and " · " in cand:
            cand = cand.rsplit(" · ", 1)[0]
            trial = cand if " · " in cand else cand + "…"
        else:
            cand = cand.rsplit(" ", 1)[0]
            trial = cand.rstrip(" ,;:·-") + "…"
        probe.set_text(trial)
        if probe.get_window_extent(renderer=renderer).width <= max_px:
            probe.remove()
            return trial
    probe.remove()
    return cand


def render(variant: str = "v1", out_png: Optional[pathlib.Path] = None) -> pathlib.Path:
    cfg = VARIANT_CONFIGS[variant]
    data_path: pathlib.Path = DATA_PATH if variant == "v1" else cfg["data_path"]
    target_png: pathlib.Path = out_png if out_png is not None else (OUT_PNG if variant == "v1" else cfg["out_png"])

    data = json.loads(data_path.read_text(encoding="utf-8"))
    world = json.loads(GEO_PATH.read_text(encoding="utf-8"))

    stops: List[Dict[str, Any]] = sorted(data["stops"], key=lambda s: int(s["order"]))
    stop_by_id = {s["id"]: s for s in stops}
    legs: List[Dict[str, Any]] = data["legs"]
    days_list: List[Dict[str, Any]] = data["days"]

    W, H, DPI = 20.0, 13.0, 240
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    fig.add_artist(Rectangle((0, 0), 1, 1, transform=fig.transFigure, facecolor=BG, zorder=-10))

    cmap = make_cmap(RAMP)
    n_stops = len(stops)
    n_days = int(data["trip"]["days"])

    # ------------------------------------------------------------------ 1. HEADER
    fig.text(
        0.025, 0.969,
        cfg["eyebrow"],
        fontsize=8.6, fontweight="bold", color=DIM, ha="left", va="center",
    )
    title_artist = fig.text(
        0.025, 0.935,
        cfg["title"],
        fontsize=28.0, fontweight="bold", color=GOLD, ha="left", va="center",
    )
    fig.text(
        0.025, 0.900,
        cfg["headline_stats"],
        fontsize=11.4, fontweight="bold", color=TEXT, ha="left", va="center",
    )

    fig.text(
        0.975, 0.946,
        cfg["route_line_1"],
        fontsize=8.6, fontweight="bold", color=to_hex(cmap(0.25)), ha="right", va="center",
    )
    fig.text(
        0.975, 0.922,
        cfg["route_line_2"],
        fontsize=8.6, fontweight="bold", color=to_hex(cmap(0.65)), ha="right", va="center",
    )
    fig.text(
        0.975, 0.898,
        cfg["meta_line"],
        fontsize=8.4, color=MUTED, ha="right", va="center",
    )
    fig.add_artist(plt.Line2D([0.025, 0.975], [0.880, 0.880], color=GOLD, lw=1.1, alpha=0.68))

    # ------------------------------------------------------------------ 2. MAP PANEL
    map_rect = [0.025, 0.082, 0.595, 0.784]
    ax_map = fig.add_axes(map_rect)
    ax_map.set_facecolor(OCEAN)
    for sp in ax_map.spines.values():
        sp.set_color(BORDER)
        sp.set_linewidth(1.0)

    lons = [float(s["lon"]) for s in stops]
    lats = [float(s["lat"]) for s in stops]
    lon0 = 0.5 * (min(lons) + max(lons))
    lat0 = 0.5 * (min(lats) + max(lats))
    dlat = max(lats) - min(lats)
    proj = (lon0, lat0, lat0 - 0.30 * dlat, lat0 + 0.30 * dlat)

    sx_arr, sy_arr = lcc(lons, lats, *proj)
    xmin, xmax = float(np.min(sx_arr)), float(np.max(sx_arr))
    ymin, ymax = float(np.min(sy_arr)), float(np.max(sy_arr))
    span_x = xmax - xmin
    span_y = ymax - ymin

    # Aspect-matched window with balanced margins around Flanders (NW), Bohemia (E), and Upper Bavaria (S)
    target_aspect = (map_rect[2] * W) / (map_rect[3] * H)
    pad_l, pad_r = 0.115 * span_x, 0.155 * span_x
    pad_b, pad_t = 0.175 * span_y, 0.185 * span_y
    dx = span_x + pad_l + pad_r
    dy = span_y + pad_b + pad_t
    if dx / dy < target_aspect:
        extra_x = dy * target_aspect - dx
        pad_l += 0.44 * extra_x
        pad_r += 0.56 * extra_x
        dx = dy * target_aspect
    else:
        extra_y = dx / target_aspect - dy
        pad_b += 0.50 * extra_y
        pad_t += 0.50 * extra_y
        dy = dx / target_aspect

    xlim = (xmin - pad_l, xmax + pad_r)
    ylim = (ymin - pad_b, ymax + pad_t)
    ax_map.set_xlim(*xlim)
    ax_map.set_ylim(*ylim)
    ax_map.set_aspect("equal", adjustable="box")
    ax_map.set_xticks([])
    ax_map.set_yticks([])

    lon_win = (min(lons) - 6.0, max(lons) + 6.0)
    lat_win = (min(lats) - 4.5, max(lats) + 4.5)

    leg_box = draw_map_legend(ax_map, cmap, n_stops=n_stops)
    sc_box = draw_scale_bar(ax_map, proj)
    forbidden_axes = [leg_box, sc_box]
    if cfg.get("map_callout"):
        forbidden_axes.append(draw_map_callout(ax_map, cfg["map_callout"]))

    tick_texts = draw_graticule(ax_map, proj, lon_win, lat_win, xlim, ylim, skip_axes_boxes=forbidden_axes)
    draw_land(ax_map, world, proj, lon_win, lat_win)

    # Subtle country watermarks in open areas
    bavaria_pos = (10.95, 48.95) if variant in ("v2", "v3") else (12.15, 48.72)
    watermarks = [
        ("BELGIUM", 4.65, 50.45),
        ("NETHERLANDS", 5.55, 51.95),
        ("LUXEMBOURG", 6.10, 49.75),
        ("FRANCE", 4.80, 49.05),
        ("GERMANY", 9.15, 51.45),
        ("BAVARIA", *bavaria_pos),
        ("CZECHIA", 14.15, 50.10),
        ("AUSTRIA", 13.45, 47.62),
    ]
    for w_txt, w_lon, w_lat in watermarks:
        wx, wy = lcc([w_lon], [w_lat], *proj)
        wxf, wyf = float(wx[0]), float(wy[0])
        if xlim[0] < wxf < xlim[1] and ylim[0] < wyf < ylim[1]:
            ax_map.text(
                wxf, wyf, w_txt,
                fontsize=7.8, fontweight="bold", color="#4f5b87", alpha=0.52,
                ha="center", va="center", zorder=1.6,
            )

    stop_xy: Dict[str, Tuple[float, float]] = {
        stops[i]["id"]: (float(sx_arr[i]), float(sy_arr[i])) for i in range(n_stops)
    }

    leg_bends: Dict[Tuple[str, str], float] = cfg["leg_bends"]

    leg_curves: List[Tuple[np.ndarray, np.ndarray, str, Dict[str, Any]]] = []
    for idx_l, leg in enumerate(legs):
        p0 = stop_xy[leg["from"]]
        p2 = stop_xy[leg["to"]]
        bend = leg_bends.get((leg["from"], leg["to"]), 0.0)
        bx, by = quad_bezier(p0, p2, bend_perp=bend, n_pts=72)
        lcol = to_hex(cmap((idx_l + 0.5) / len(legs)))
        is_final_return = (idx_l == len(legs) - 1)

        # Halo + stroke
        ax_map.plot(bx, by, color=BG, lw=5.4, alpha=0.84, solid_capstyle="round", zorder=3.0)
        if is_final_return:
            ax_map.plot(bx, by, color=lcol, lw=2.5, alpha=0.92, linestyle=(0, (7, 4)), zorder=3.3)
        else:
            t_seg = np.linspace(idx_l / len(legs), (idx_l + 1) / len(legs), len(bx) - 1)
            pts = np.column_stack([bx, by]).reshape(-1, 1, 2)
            segs = np.concatenate([pts[:-1], pts[1:]], axis=1)
            lc = LineCollection(
                segs,
                colors=[cmap(float(tv)) for tv in t_seg],
                linewidths=2.8,
                capstyle="round",
                joinstyle="round",
                alpha=0.95,
                zorder=3.2,
            )
            ax.add_collection(lc) if False else ax_map.add_collection(lc)

        # Directional chevron at t ~ 0.56
        mid_i = 40
        ax_map.annotate(
            "",
            xy=(float(bx[mid_i + 1]), float(by[mid_i + 1])),
            xytext=(float(bx[mid_i - 1]), float(by[mid_i - 1])),
            arrowprops=dict(arrowstyle="-|>", color=lcol, lw=1.4, mutation_scale=10.5),
            zorder=3.6,
        )
        leg_curves.append((bx, by, lcol, leg))

    # Draw numbered stop badges (1..11 in visit order) directly at projected stop coords
    BADGE_R_PX = 27.5
    badge_cols = [stop_color(cmap, i, n_stops) for i in range(n_stops)]
    ax_map.scatter(sx_arr, sy_arr, s=360, c=badge_cols, alpha=0.22, edgecolors="none", zorder=5.8)
    ax_map.scatter(sx_arr, sy_arr, s=220, c=badge_cols, edgecolors=BG, linewidths=1.8, zorder=6.2)
    for i in range(n_stops):
        ax_map.text(
            float(sx_arr[i]), float(sy_arr[i]), str(i + 1),
            fontsize=7.6, fontweight="bold", color=BG,
            ha="center", va="center", zorder=6.5,
        )

    # Force initial draw so renderer & pixel transforms are exact
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    if cfg["version_tag"]:
        t_ext = title_artist.get_window_extent(renderer=renderer)
        tag_probe = fig.text(0, 0, cfg["version_tag"], fontsize=11.0, fontweight="bold")
        tag_w_px = float(tag_probe.get_window_extent(renderer=renderer).width) + 28.0
        tag_h_px = float(tag_probe.get_window_extent(renderer=renderer).height) + 16.0
        tag_probe.remove()
        tx0_px = float(t_ext.x1) + 24.0
        ty_mid_px = 0.5 * float(t_ext.y0 + t_ext.y1)
        f_p0 = fig.transFigure.inverted().transform((tx0_px, ty_mid_px - 0.5 * tag_h_px))
        f_p1 = fig.transFigure.inverted().transform((tx0_px + tag_w_px, ty_mid_px + 0.5 * tag_h_px))
        fig.add_artist(FancyBboxPatch(
            (float(f_p0[0]), float(f_p0[1])),
            float(f_p1[0] - f_p0[0]),
            float(f_p1[1] - f_p0[1]),
            boxstyle="round,pad=0,rounding_size=0.004",
            transform=fig.transFigure,
            facecolor="#e94560",
            edgecolor=GOLD,
            linewidth=1.1,
            zorder=5,
        ))
        fig.text(
            0.5 * float(f_p0[0] + f_p1[0]),
            0.5 * float(f_p0[1] + f_p1[1]),
            cfg["version_tag"],
            fontsize=11.0,
            fontweight="bold",
            color="#ffffff",
            ha="center",
            va="center",
            zorder=6,
        )

    map_win = ax_map.get_window_extent(renderer=renderer)
    px0, py0, px1, py1 = float(map_win.x0), float(map_win.y0), float(map_win.x1), float(map_win.y1)

    occupied_px: List[Tuple[str, Tuple[float, float, float, float]]] = []
    for ax0_f, ay0_f, ax1_f, ay1_f in forbidden_axes:
        q0 = ax_map.transAxes.transform((ax0_f, ay0_f))
        q1 = ax_map.transAxes.transform((ax1_f, ay1_f))
        occupied_px.append(("ui_box", (float(q0[0]), float(q0[1]), float(q1[0]), float(q1[1]))))
    for tt in tick_texts:
        tbb = tt.get_window_extent(renderer=renderer)
        occupied_px.append(("tick", (float(tbb.x0) - 2, float(tbb.y0) - 2, float(tbb.x1) + 2, float(tbb.y1) + 2)))

    badge_centers_px: List[Tuple[float, float]] = [
        tuple(map(float, ax_map.transData.transform((float(sx_arr[i]), float(sy_arr[i])))))
        for i in range(n_stops)
    ]

    # Sample all polyline points in pixel space so labels strictly avoid crossing route lines
    route_sample_px: List[Tuple[float, float]] = []
    for bx, by, _, _ in leg_curves:
        pts_px = ax_map.transData.transform(np.column_stack([bx, by]))
        for p_px in pts_px:
            route_sample_px.append((float(p_px[0]), float(p_px[1])))

    def is_box_valid(cand: Tuple[float, float, float, float], margin_edge: float = 12.0) -> bool:
        if cand[0] < px0 + margin_edge or cand[2] > px1 - margin_edge:
            return False
        if cand[1] < py0 + margin_edge or cand[3] > py1 - margin_edge:
            return False
        for bcx, bcy in badge_centers_px:
            if circle_hits_box(bcx, bcy, BADGE_R_PX + 4.0, cand):
                return False
        for _, ob in occupied_px:
            if boxes_overlap(cand, ob, pad=3.0):
                return False
        return True

    def route_hits_count(cand: Tuple[float, float, float, float]) -> int:
        cnt = 0
        for rpx, rpy in route_sample_px:
            if (cand[0] - 3.0 <= rpx <= cand[2] + 3.0) and (cand[1] - 3.0 <= rpy <= cand[3] + 3.0):
                cnt += 1
        return cnt

    # Short display names for map clarity + night chip text
    stop_display: Dict[str, Tuple[str, str]] = {
        "fra": ("Frankfurt Airport", "START/END"),
        "bruges": ("Bruges", "2N"),
        "ghent": ("Ghent", "1N"),
        "cologne": ("Cologne", "1N"),
        "wurzburg": ("Würzburg", "1N"),
        "bamberg": ("Bamberg", "2N"),
        "sokolov": ("Permon · Sokolov", "1N"),
        "plzen": ("Plzeň", "2N"),
        "kout": ("Kout na Šumavě", "1N"),
        "maxlrain": ("Maxlrain", "1N"),
        "andechs": ("Andechs", "1N"),
        "munich": ("Munich", "2N"),
        "nuremberg": ("Nuremberg", "1N"),
    }

    preferred_angles: Dict[str, List[float]] = cfg["preferred_angles"]

    # Place all 11 stop labels + 2N/1N night chips
    for i, s in enumerate(stops):
        sid = s["id"]
        label_txt, chip_txt = stop_display[sid]
        bcx, bcy = badge_centers_px[i]
        is_two_night = (chip_txt == "2N")
        is_airport = (sid == "fra")

        # Measure text + chip size in pixels using temporary artists
        t_probe = ax_map.text(0, 0, label_txt, fontsize=8.8, fontweight="bold")
        c_probe = ax_map.text(0, 0, chip_txt, fontsize=6.6, fontweight="bold")
        tw = float(t_probe.get_window_extent(renderer=renderer).width)
        th = float(t_probe.get_window_extent(renderer=renderer).height)
        cw = float(c_probe.get_window_extent(renderer=renderer).width) + 14.0
        ch = max(th + 4.0, 22.0)
        t_probe.remove()
        c_probe.remove()

        gap_px = 8.0
        total_w = tw + gap_px + cw
        total_h = max(th + 8.0, ch + 4.0)

        angs = list(preferred_angles.get(sid, [])) + [a for a in range(0, 360, 15)]
        chosen_box: Optional[Tuple[float, float, float, float]] = None
        best_score = float("inf")

        for r_dist in (36.0, 44.0, 54.0, 66.0, 80.0):
            for deg in angs:
                rad = math.radians(deg)
                ax_px = bcx + r_dist * math.cos(rad)
                ay_px = bcy + r_dist * math.sin(rad)
                # Anchor box outward from badge center along (cos, sin)
                if math.cos(rad) >= 0.25:
                    bx0 = ax_px
                elif math.cos(rad) <= -0.25:
                    bx0 = ax_px - total_w
                else:
                    bx0 = ax_px - 0.5 * total_w

                if math.sin(rad) >= 0.25:
                    by0 = ay_px
                elif math.sin(rad) <= -0.25:
                    by0 = ay_px - total_h
                else:
                    by0 = ay_px - 0.5 * total_h

                cand = (bx0 - 4.0, by0 - 3.0, bx0 + total_w + 4.0, by0 + total_h + 3.0)
                if not is_box_valid(cand):
                    continue
                rhits = route_hits_count(cand)
                pref_rank = angs.index(deg) if deg in angs[:6] else 8
                score = r_dist * 0.7 + rhits * 28.0 + pref_rank * 6.0
                if score < best_score:
                    best_score = score
                    chosen_box = (bx0, by0, bx0 + total_w, by0 + total_h)
            if chosen_box is not None and best_score < 60.0:
                break

        assert chosen_box is not None, f"Could not place stop label for {sid}"
        bx0, by0, bx1, by1 = chosen_box
        cy_mid = 0.5 * (by0 + by1)

        # Draw leader line if slightly offset
        nearest_x = max(bx0, min(bcx, bx1))
        nearest_y = max(by0, min(bcy, by1))
        if math.hypot(nearest_x - bcx, nearest_y - bcy) > BADGE_R_PX + 15.0:
            p_start = ax_map.transData.inverted().transform((bcx, bcy))
            p_end = ax_map.transData.inverted().transform((nearest_x, nearest_y))
            ax_map.plot(
                [p_start[0], p_end[0]], [p_start[1], p_end[1]],
                color=badge_cols[i], lw=0.95, alpha=0.75, zorder=5.5,
            )

        # Convert pixel positions to data coords for crisp rendering
        txt_data = ax_map.transData.inverted().transform((bx0, cy_mid))
        ax_map.text(
            float(txt_data[0]), float(txt_data[1]), label_txt,
            fontsize=8.8, fontweight="bold", color=TEXT,
            ha="left", va="center", zorder=8.3,
            path_effects=[pe.withStroke(linewidth=3.8, foreground=BG)],
        )

        # Night chip pill right next to stop name
        chip_x0_px = bx0 + tw + gap_px
        chip_y0_px = cy_mid - 0.5 * ch
        c_p0 = ax_map.transAxes.inverted().transform((chip_x0_px, chip_y0_px))
        c_p1 = ax_map.transAxes.inverted().transform((chip_x0_px + cw, chip_y0_px + ch))
        chip_fc = GOLD if is_two_night else ( BORDER if is_airport else PANEL_ALT )
        chip_ec = GOLD if is_two_night else ( MUTED if is_airport else stop_color(cmap, i, n_stops) )
        chip_tc = BG if is_two_night else TEXT

        ax_map.add_patch(FancyBboxPatch(
            (float(c_p0[0]), float(c_p0[1])),
            float(c_p1[0] - c_p0[0]),
            float(c_p1[1] - c_p0[1]),
            boxstyle="round,pad=0,rounding_size=0.004",
            transform=ax_map.transAxes,
            facecolor=chip_fc,
            edgecolor=chip_ec,
            linewidth=0.85,
            zorder=8.4,
        ))
        ax_map.text(
            0.5 * float(c_p0[0] + c_p1[0]),
            0.5 * float(c_p0[1] + c_p1[1]),
            chip_txt,
            transform=ax_map.transAxes,
            fontsize=6.4,
            fontweight="bold",
            color=chip_tc,
            ha="center",
            va="center",
            zorder=8.5,
        )

        occupied_px.append((f"stop:{sid}", (bx0 - 4.0, by0 - 3.0, bx1 + 4.0, by1 + 3.0)))

    # Place all 11 leg labels (`km · h:mm`) offset cleanly off each route segment
    for idx_l, (bx, by, lcol, leg) in enumerate(leg_curves):
        leg_str = f"{fmt_km_round(float(leg['km']))} km · {fmt_hmm(int(leg['minutes']))}"
        l_probe = ax_map.text(0, 0, leg_str, fontsize=7.2, fontweight="bold")
        lw_px = float(l_probe.get_window_extent(renderer=renderer).width) + 12.0
        lh_px = float(l_probe.get_window_extent(renderer=renderer).height) + 8.0
        l_probe.remove()

        curve_px = ax_map.transData.transform(np.column_stack([bx, by]))
        n_pts = len(curve_px)

        best_leg_cfg: Optional[Tuple[float, float, Tuple[float, float], Tuple[float, float, float, float]]] = None
        best_leg_cost = float("inf")

        # Try fractional positions along the leg curve (centered near middle, expanding outward)
        t_indices = [36, 30, 42, 24, 48, 20, 52, 16, 56]
        gap_clearances = [10.0, 15.0, 22.0, 30.0, 40.0, 52.0, 66.0]

        for ti in t_indices:
            mx_px, my_px = float(curve_px[ti, 0]), float(curve_px[ti, 1])
            tx_vec = float(curve_px[min(n_pts - 1, ti + 2), 0] - curve_px[max(0, ti - 2), 0])
            ty_vec = float(curve_px[min(n_pts - 1, ti + 2), 1] - curve_px[max(0, ti - 2), 1])
            tlen = max(math.hypot(tx_vec, ty_vec), 1e-6)
            nx_u, ny_u = -ty_vec / tlen, tx_vec / tlen

            # Support distance of box half-extents along unit normal so box strictly clears the line
            support_px = 0.5 * abs(nx_u) * lw_px + 0.5 * abs(ny_u) * lh_px

            # Prefer outward side matching curve bend first
            bend_val = leg_bends.get((leg["from"], leg["to"]), 0.0)
            sides = [1.0, -1.0] if bend_val >= 0 else [-1.0, 1.0]

            for gap_c in gap_clearances:
                pd = support_px + gap_c
                for sgn in sides:
                    cx_l = mx_px + sgn * pd * nx_u
                    cy_l = my_px + sgn * pd * ny_u
                    cand = (cx_l - 0.5 * lw_px, cy_l - 0.5 * lh_px, cx_l + 0.5 * lw_px, cy_l + 0.5 * lh_px)
                    if not is_box_valid(cand, margin_edge=10.0):
                        continue
                    rhits = route_hits_count(cand)
                    t_pen = abs(ti - 36) * 0.9
                    side_pen = 0.0 if sgn == sides[0] else 6.0
                    cost = gap_c * 0.95 + rhits * 45.0 + t_pen + side_pen
                    if cost < best_leg_cost:
                        best_leg_cost = cost
                        best_leg_cfg = (cx_l, cy_l, (mx_px, my_px), cand)
                if best_leg_cfg is not None and best_leg_cost < 20.0:
                    break

        assert best_leg_cfg is not None, f"Could not place leg label for {leg['from']}->{leg['to']}"
        cx_l, cy_l, (mx_px, my_px), lbox = best_leg_cfg

        # Subtle tick connecting leg midpoint to offset leg label when offset > 22 px
        nx_box = max(lbox[0], min(mx_px, lbox[2]))
        ny_box = max(lbox[1], min(my_px, lbox[3]))
        if math.hypot(nx_box - mx_px, ny_box - my_px) > 10.0:
            p_m = ax_map.transData.inverted().transform((mx_px, my_px))
            p_b = ax_map.transData.inverted().transform((nx_box, ny_box))
            ax_map.plot(
                [p_m[0], p_b[0]], [p_m[1], p_b[1]],
                color=lcol, lw=0.85, alpha=0.70, zorder=5.2,
                path_effects=[pe.withStroke(linewidth=2.0, foreground=BG)],
            )

        b_ax0 = ax_map.transAxes.inverted().transform((lbox[0], lbox[1]))
        b_ax1 = ax_map.transAxes.inverted().transform((lbox[2], lbox[3]))
        ax_map.add_patch(FancyBboxPatch(
            (float(b_ax0[0]), float(b_ax0[1])),
            float(b_ax1[0] - b_ax0[0]),
            float(b_ax1[1] - b_ax0[1]),
            boxstyle="round,pad=0,rounding_size=0.004",
            transform=ax_map.transAxes,
            facecolor=BG,
            edgecolor=lcol,
            linewidth=0.70,
            alpha=0.88,
            zorder=7.6,
        ))
        l_data = ax_map.transData.inverted().transform((cx_l, cy_l))
        ax_map.text(
            float(l_data[0]), float(l_data[1]), leg_str,
            fontsize=7.1, fontweight="bold", color=LEG_TEXT,
            ha="center", va="center", zorder=7.8,
            path_effects=[pe.withStroke(linewidth=2.4, foreground=BG)],
        )
        occupied_px.append((f"leg:{leg['from']}->{leg['to']}", lbox))

    # ------------------------------------------------------------------ 3. SIDE PANEL: 15-DAY LEDGER
    ledger_rect = [0.638, 0.082, 0.337, 0.784]
    ax_led = fig.add_axes(ledger_rect)
    ax_led.set_xlim(0, 1)
    ax_led.set_ylim(0, 1)
    ax_led.axis("off")

    ax_led.add_patch(FancyBboxPatch(
        (0.002, 0.002), 0.996, 0.996,
        boxstyle="round,pad=0,rounding_size=0.016",
        facecolor=PANEL, edgecolor=BORDER, linewidth=1.0, zorder=0,
    ))
    ax_led.text(0.036, 0.966, f"{n_days}-DAY ITINERARY LEDGER", fontsize=10.5, fontweight="bold",
                color=GOLD, ha="left", va="center", zorder=2)
    ax_led.text(0.964, 0.966, "DAY · BASE · DRIVE / IN PLACE",
                fontsize=8.0, fontweight="bold", color=MUTED, ha="right", va="center", zorder=2)
    ax_led.plot([0.030, 0.970], [0.938, 0.938], color=BORDER, lw=0.9, zorder=2)

    leg_by_day = {int(l["day"]): l for l in legs}
    short_stop_lbl = {
        "fra": "FRA",
        "bruges": "Bruges",
        "ghent": "Ghent",
        "cologne": "Cologne",
        "wurzburg": "Würzburg",
        "bamberg": "Bamberg",
        "sokolov": "Sokolov (Permon)",
        "plzen": "Plzeň",
        "kout": "Kout na Šumavě",
        "maxlrain": "Maxlrain",
        "andechs": "Andechs / Herrsching",
        "munich": "Munich",
        "nuremberg": "Nuremberg",
    }

    top_band, bot_band = 0.926, 0.014
    row_h = (top_band - bot_band) / len(days_list)
    led_win = ax_led.get_window_extent(renderer=renderer)
    max_text_px = float(led_win.width) * (0.838 if variant == "v3" else 0.820)

    long_days = cfg["long_days"]
    new_days = cfg.get("new_days", ())
    ledger_day_tags: Dict[int, str] = cfg["ledger_day_tags"]
    top_fs = 8.9 if variant == "v3" else 9.2
    sub_fs = 7.6 if variant == "v3" else 7.9
    chip_fs = 8.0 if variant == "v3" else 8.2

    for idx_d, d_entry in enumerate(days_list):
        dnum = int(d_entry["day"])
        base_id = d_entry["base"]
        base_stop = stop_by_id[base_id]
        yc = top_band - (idx_d + 0.5) * row_h
        y_low = yc - 0.45 * row_h
        rcol = day_color(cmap, dnum, n_days)
        is_long = dnum in long_days
        is_new = dnum in new_days

        if is_long:
            ax_led.add_patch(FancyBboxPatch(
                (0.020, y_low), 0.960, 0.90 * row_h,
                boxstyle="round,pad=0,rounding_size=0.008",
                facecolor="#2b1c28", edgecolor="#e94560", linewidth=0.65, alpha=0.80, zorder=1,
            ))
        elif is_new:
            ax_led.add_patch(FancyBboxPatch(
                (0.020, y_low), 0.960, 0.90 * row_h,
                boxstyle="round,pad=0,rounding_size=0.008",
                facecolor="#132a33", edgecolor="#38d399", linewidth=0.65, alpha=0.82, zorder=1,
            ))
        elif idx_d % 2 == 0:
            ax_led.add_patch(FancyBboxPatch(
                (0.020, y_low), 0.960, 0.90 * row_h,
                boxstyle="round,pad=0,rounding_size=0.008",
                facecolor=PANEL_ALT, edgecolor="none", alpha=0.65, zorder=1,
            ))

        chip_h = min(0.62 * row_h, 0.041)
        ax_led.add_patch(FancyBboxPatch(
            (0.034, yc - 0.5 * chip_h), 0.074, chip_h,
            boxstyle="round,pad=0,rounding_size=0.009",
            facecolor=rcol, edgecolor="none", zorder=2,
        ))
        ax_led.text(
            0.071, yc, f"D{dnum}",
            fontsize=chip_fs, fontweight="bold", color=BG,
            ha="center", va="center", zorder=3,
        )

        nights_n = int(base_stop["nights"])
        base_lbl = short_stop_lbl[base_id]
        nights_tag = f" ({nights_n}N)" if nights_n > 0 else " (fly home)"
        top_str = f"{base_lbl}{nights_tag}  ·  {d_entry['title']}"
        top_fitted = fit_text_px(fig, ax_led, top_str, max_text_px, top_fs, fontweight="bold")

        if dnum in leg_by_day:
            lg = leg_by_day[dnum]
            drv_prefix = f"{short_stop_lbl[lg['from']]} → {short_stop_lbl[lg['to']]}  ·  {fmt_km_round(float(lg['km']))} km · {fmt_hmm(int(lg['minutes']))}"
            if dnum in ledger_day_tags:
                drv_prefix += f"  {ledger_day_tags[dnum]}"
            # Add concise highlight from non-distance items
            extra_items = [it for it in d_entry["items"] if " km / " not in it]
            sub_raw = f"{drv_prefix}  ·  {extra_items[0]}" if extra_items else drv_prefix
            sub_col = LEG_TEXT if is_long else ("#8ef0d4" if is_new else MUTED)
        else:
            sub_raw = f"In place  ·  {' · '.join(d_entry['items'][:2])}"
            sub_col = "#7fe0c8"

        sub_fitted = fit_text_px(
            fig, ax_led, sub_raw, max_text_px, sub_fs, fontweight="normal", word_trim=(variant != "v1")
        )

        ax_led.text(
            0.126, yc + 0.19 * row_h, top_fitted,
            fontsize=top_fs, fontweight="bold", color=TEXT,
            ha="left", va="center", zorder=3,
        )
        ax_led.text(
            0.126, yc - 0.21 * row_h, sub_fitted,
            fontsize=sub_fs, color=sub_col,
            ha="left", va="center", zorder=3,
        )

    # ------------------------------------------------------------------ 4. FOOTER
    fig.add_artist(plt.Line2D([0.025, 0.975], [0.066, 0.066], color=GOLD, lw=0.95, alpha=0.62))

    must_drink = cfg["must_drink"]
    totals_line = cfg["totals_line"]

    fig.text(0.025, 0.044, "MUST-DRINK BEERS", fontsize=8.3, fontweight="bold", color=GOLD, ha="left", va="center")
    fig.text(0.122, 0.044, must_drink, fontsize=8.1, color=TEXT, ha="left", va="center")

    fig.text(0.025, 0.020, "ROUTE TOTALS", fontsize=8.0, fontweight="bold", color=MUTED, ha="left", va="center")
    fig.text(0.122, 0.020, totals_line, fontsize=8.1, color=MUTED, ha="left", va="center")

    fig.text(
        0.975, 0.020,
        "Lambert Conformal Conic  ·  Natural Earth 1:50m",
        fontsize=7.6, color=DIM, ha="right", va="center",
    )

    target_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        target_png,
        dpi=DPI,
        facecolor=BG,
        metadata={"Software": "bierreisen/2027/scripts/make_route_map.py", "Creation Time": None},
    )
    plt.close(fig)
    return target_png


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the 2027 Bier Reisen route poster.")
    parser.add_argument(
        "--variant",
        choices=("v1", "v2", "v3"),
        default="v1",
        help="Planner variant to render (default: v1).",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    render(variant=args.variant)
