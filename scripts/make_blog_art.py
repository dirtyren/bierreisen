#!/usr/bin/env python3
"""Render a plate for every blog post: name, descriptor, coordinates, locator map.

Plates are language-neutral (the proper noun plus numbers), so one file serves the
EN / PT / DE versions of a post.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon, Rectangle

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "blog" / "data"
OUT = ROOT / "blog" / "assets"
GEO = ROOT / "assets" / "ne_50m_countries.geojson"

INK, PANEL, RULE, GOLD = "#0b0c15", "#101224", "#2b3254", "#e6a817"
TEXT, MUTED, DIM = "#eef1f6", "#a8b2c6", "#8d97ad"

W, H, DPI = 16, 9, 100
SERIF = fm.FontProperties(fname="/System/Library/Fonts/Supplemental/Charter.ttc")
SANS = fm.FontProperties(fname="/System/Library/Fonts/Avenir Next.ttc")

TRIP_FILE = {
    "2019": "2019/data/route-2019.json", "2020": "2020/data/route-2020.json",
    "2021": "2021/data/route-2021.json", "2024": "2024/data/route-2024.json",
    "2026": "2026/data/route-2026.json", "2027": "2027/v3/data/route-2027-v3.json",
}

_cache = {}


def context_stops(entity: dict) -> list[tuple[float, float, str]]:
    """Stops of the most recent trip this place belongs to, in route order."""
    trips = entity.get("trips") or []
    if not trips:
        return []
    year = sorted(trips)[-1]
    rel = TRIP_FILE.get(year)
    if not rel:
        return []
    if year not in _cache:
        d = json.loads((ROOT / rel).read_text())
        stops = sorted(d.get("stops", []), key=lambda s: s.get("order", 0))
        _cache[year] = [(float(s["lat"]), float(s["lon"]), s.get("name", "")) for s in stops
                        if s.get("lat") is not None]
    return _cache[year]


def countries() -> list[list[list[float]]]:
    if "rings" not in _cache:
        gj = json.loads(GEO.read_text())
        rings = []
        for feat in gj["features"]:
            geom = feat["geometry"]
            polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
            for poly in polys:
                for ring in poly:
                    rings.append(ring)
        _cache["rings"] = rings
    return _cache["rings"]


def fmt_coord(v: float, pos: str, neg: str) -> str:
    return f"{abs(v):.4f}° {pos if v >= 0 else neg}"


def plate(entity: dict) -> pathlib.Path:
    slug = entity["slug"]
    lat, lon = entity["coords"]
    span = entity.get("span", 0.18 if entity["type"] == "brewery" else 0.55)

    fig = plt.figure(figsize=(W, H), dpi=DPI)
    fig.patch.set_facecolor(INK)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W * DPI)
    ax.set_ylim(0, H * DPI)
    ax.axis("off")

    # rules
    ax.plot([90, 90], [212, 660], color=GOLD, lw=2.4, solid_capstyle="butt")
    ax.plot([90, W * DPI - 90], [128, 128], color=RULE, lw=1.1)
    ax.text(90, 84, "BIER REISEN", fontproperties=SANS, fontsize=13, color=DIM,
            va="center", ha="left", alpha=.9)
    ax.text(W * DPI - 90, 84, "renreisen.duckdns.org", fontproperties=SANS, fontsize=13,
            color=DIM, va="center", ha="right", alpha=.9)

    # name, fitted to the left column
    # trips carry a long editorial name; the plate leads with the year instead
    name = entity["trips"][0] if entity["type"] == "trip" else entity["name"]
    size = 104
    while size > 46:
        t = ax.text(0, 0, name, fontproperties=SERIF, fontsize=size, color=TEXT,
                    va="center", ha="left", alpha=0)
        fig.canvas.draw()
        w = t.get_window_extent().width
        t.remove()
        if w <= 640:
            break
        size -= 4
    ax.text(136, 522, name, fontproperties=SERIF, fontsize=size, color=TEXT, va="center")

    kind = {"brewery": "Brewery", "city": "City", "trip": "Trip"}.get(entity["type"], entity["type"])
    where = entity.get("where", "")
    ax.text(136, 424, f"{kind} · {where}" if where else kind, fontproperties=SANS,
            fontsize=25, color=GOLD, va="center")
    subtitle = entity["name"] if entity["type"] == "trip" else entity.get("subtitle_en")
    if subtitle:
        ax.text(136, 362, subtitle, fontproperties=SANS, fontsize=19,
                color=MUTED, va="center")
    ax.text(136, 300, f"{fmt_coord(lat, 'N', 'S')}   {fmt_coord(lon, 'E', 'W')}",
            fontproperties=SANS, fontsize=16, color=DIM, va="center")

    # locator: the place in its route context
    box = [1000, 212, 510, 510]
    ax.add_patch(Rectangle((box[0], box[1]), box[2], box[3], facecolor="#070810",
                           edgecolor=RULE, lw=1.2, zorder=1))
    stops = context_stops(entity)
    if stops:
        lats = [x[0] for x in stops] + [lat]
        lons = [x[1] for x in stops] + [lon]
        pad = max(0.22, 0.06 * max(max(lats) - min(lats), max(lons) - min(lons)))
        x0, x1 = min(lons) - pad, max(lons) + pad
        y0, y1 = min(lats) - pad, max(lats) + pad
        # keep the panel's aspect: widen the narrow axis
        target = box[2] / box[3] * (abs(y1 - y0) / max(abs(x1 - x0), 1e-6)) * 0.98
        if target > 1:
            extra = (abs(x1 - x0) * target - abs(x1 - x0)) / 2
            x0, x1 = x0 - extra, x1 + extra
        else:
            extra = (abs(y1 - y0) / target - abs(y1 - y0)) / 2
            y0, y1 = y0 - extra, y1 + extra
    else:
        span = entity.get("span", 0.4)
        x0, x1 = lon - span, lon + span
        y0, y1 = lat - span * 0.72, lat + span * 0.72

    def px(lonv, latv):
        return (box[0] + (lonv - x0) / (x1 - x0) * box[2],
                box[1] + (latv - y0) / (y1 - y0) * box[3])

    clip = Rectangle((box[0], box[1]), box[2], box[3], transform=ax.transData,
                     facecolor="none", edgecolor="none")
    ax.add_patch(clip)
    for ring in countries():
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        if max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1:
            continue
        pts = [px(a, b) for a, b in ring]
        patch = Polygon(pts, closed=True, facecolor=PANEL, edgecolor=RULE, lw=1.0, zorder=2)
        patch.set_clip_path(clip)
        ax.add_patch(patch)

    # route lines and other stops
    if stops:
        for a, b in zip(stops, stops[1:]):
            ax.plot([px(a[1], a[0])[0], px(b[1], b[0])[0]],
                    [px(a[1], a[0])[1], px(b[1], b[0])[1]],
                    color=GOLD, lw=1.1, alpha=.35, zorder=3,
                    solid_capstyle="round")
        for slat, slon, _name in stops:
            sx, sy = px(slon, slat)
            ax.plot([sx], [sy], marker="o", ms=5, mfc="#5b6485", mec="#070810", mew=.8, zorder=4)

    cx, cy = px(lon, lat)
    if entity["type"] != "trip":
        ax.plot([cx], [cy], marker="o", ms=8, mfc=INK, mec=GOLD, mew=1.4, zorder=6)
        ax.plot([cx], [cy], marker="o", ms=15, mfc="none", mec=GOLD, mew=.9, alpha=.45, zorder=6)
        ax.plot([cx], [cy], marker="o", ms=11, mfc=GOLD, mec=INK, mew=1.6, zorder=7)

    # mask everything outside the panel, so the map reads as an inset
    for mx, my, mw, mh in (
        (0, 0, W * DPI, box[1]),
        (0, box[1] + box[3], W * DPI, H * DPI - (box[1] + box[3])),
        (0, box[1], box[0], box[3]),
        (box[0] + box[2], box[1], W * DPI - (box[0] + box[2]), box[3]),
    ):
        ax.add_patch(Rectangle((mx, my), mw, mh, facecolor=INK, edgecolor="none", zorder=15))

    # frame on top of the clipped map
    ax.add_patch(Rectangle((box[0], box[1]), box[2], box[3], facecolor="none",
                           edgecolor=RULE, lw=1.2, zorder=10))

    # scale bar sized to the frame
    km = abs(x1 - x0) * 0.2 * 111.32 * math.cos(math.radians((y0 + y1) / 2))
    bar = box[2] * 0.2
    ax.add_patch(Rectangle((box[0] + 22, box[1] + 22), bar, 5, facecolor=GOLD, edgecolor="none", zorder=6))
    ax.text(box[0] + 22, box[1] + 38, f"{km:.0f} km", fontproperties=SANS, fontsize=11,
            color=DIM, va="bottom", zorder=6)

    for txt in ax.texts:
        txt.set_zorder(20)

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{slug}.png"
    fig.savefig(path, dpi=DPI, facecolor=INK)
    plt.close(fig)
    return path


def main() -> None:
    written = []
    for f in sorted(DATA.glob("*.json")):
        entity = json.loads(f.read_text())
        written.append(plate(entity))
    print(f"rendered {len(written)} plates → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
