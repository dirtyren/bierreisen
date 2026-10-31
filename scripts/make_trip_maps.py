#!/usr/bin/env python3
"""Render seven print-quality per-trip map posters + JSON sidecars from AI-suggested-trips/*.html.

Usage (from repo root):
    python3 scripts/make_trip_maps.py
"""
from __future__ import annotations

import html as html_lib
import json
import math
import pathlib
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from bs4 import BeautifulSoup
from matplotlib import patheffects as pe
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.colors import LinearSegmentedColormap, to_hex
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOSSIERS = ROOT / "AI-suggested-trips"
OUT_DIR = ROOT / "assets" / "trips"
GEO = ROOT / "assets" / "ne_50m_countries.geojson"
STATES_GEO = ROOT / "assets" / "us_states.geojson"

# ------------------------------------------------------------------ palette (matches make_map.py)
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
TEXT = "#eef1f6"
MUTED = "#9aa5bc"
DIM = "#717c96"

plt.rcParams.update({
    "font.family": ["Avenir Next", "DejaVu Sans"],
    "text.color": TEXT,
    "text.parse_math": False,
    "savefig.facecolor": BG,
    "figure.facecolor": BG,
})

WORLD = json.loads(GEO.read_text(encoding="utf-8"))
STATES = json.loads(STATES_GEO.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ text cleaning & JS/HTML helpers
_EMOJI_RE = re.compile(
    "["
    "\U0001f000-\U0001ffff"
    "\U000e0000-\U000e007f"
    "\u2600-\u27bf"
    "\u2300-\u23ff"
    "\u2b00-\u2bff"
    "\ufe00-\ufe0f"
    "\u200d"
    "]+",
    flags=re.UNICODE,
)


def clean_text(raw: Optional[str]) -> str:
    """Strip emoji, variation selectors and excess whitespace so glyph fallback stays warning-free."""
    if not raw:
        return ""
    s = html_lib.unescape(str(raw))
    s = _EMOJI_RE.sub("", s)
    s = s.replace("\u2022", "·").replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^[\s·|:,\-–—]+", "", s).strip()
    return s


def js_array(html: str, name: str) -> str:
    m = re.search(r"(?:var|const|let)\s+" + re.escape(name) + r"\s*=\s*", html)
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


def objects(block: str) -> List[str]:
    """Split a JS array literal of `{...}` objects into individual object strings."""
    out: List[str] = []
    depth = 0
    start: Optional[int] = None
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


def field(obj: str, key: str) -> Any:
    m = re.search(r"\b" + re.escape(key) + r"\s*:\s*(\"[^\"]*\"|'[^']*'|-?\d+(?:\.\d+)?)", obj)
    if not m:
        return None
    v = m.group(1)
    if v[0] in "\"'":
        return clean_text(v[1:-1])
    return float(v)


def tuples(block: str) -> List[Dict[str, Any]]:
    """Parse `[lat, lng, "name", "meta", icon, day]` style JS tuple literals."""
    out: List[Dict[str, Any]] = []
    pat = re.compile(
        r"\[\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)"
        r"(?:\s*,\s*\"([^\"]*)\")?"
        r"(?:\s*,\s*\"([^\"]*)\")?"
        r"(?:\s*,\s*\w+)?"
        r"(?:\s*,\s*(\d+))?\s*\]"
    )
    for m in pat.finditer(block):
        item: Dict[str, Any] = {
            "lat": float(m.group(1)),
            "lon": float(m.group(2)),
            "name": clean_text(m.group(3) or ""),
        }
        if m.group(4):
            item["meta"] = clean_text(m.group(4))
        if m.group(5):
            item["day"] = int(m.group(5))
        out.append(item)
    return out


def pairs(block: str) -> List[List[float]]:
    return [[float(a), float(b)] for a, b in re.findall(r"\[\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*\]", block)]


# ------------------------------------------------------------------ projection & basemap helpers
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


def fit_lcc_window(
    lons: Sequence[float],
    lats: Sequence[float],
    rect_w_in: float,
    rect_h_in: float,
    pad_each_side: float = 0.095,
) -> Tuple[Tuple[float, float, float, float], Tuple[float, float], Tuple[float, float], Tuple[float, float], Tuple[float, float]]:
    """Fit a Lambert conformal conic projection + aspect-matched window to points with ~8-10% padding."""
    lon_min, lon_max = float(min(lons)), float(max(lons))
    lat_min, lat_max = float(min(lats)), float(max(lats))
    lon0 = 0.5 * (lon_min + lon_max)
    lat0 = 0.5 * (lat_min + lat_max)
    dlat = max(lat_max - lat_min, 1.6)
    proj = (lon0, lat0, lat0 - 0.30 * dlat, lat0 + 0.30 * dlat)

    xs, ys = lcc(lons, lats, *proj)
    xmin, xmax = float(np.min(xs)), float(np.max(xs))
    ymin, ymax = float(np.min(ys)), float(np.max(ys))
    span_x = max(xmax - xmin, 1e-4)
    span_y = max(ymax - ymin, 1e-4)

    cx = 0.5 * (xmin + xmax)
    cy = 0.5 * (ymin + ymax)
    dx = span_x * (1.0 + 2.0 * pad_each_side)
    dy = span_y * (1.0 + 2.0 * pad_each_side)

    target = rect_w_in / rect_h_in
    if dx / dy < target:
        dx = dy * target
    else:
        dy = dx / target

    xlim = (cx - 0.5 * dx, cx + 0.5 * dx)
    ylim = (cy - 0.5 * dy, cy + 0.5 * dy)

    # Geographic search window generous enough for curved LCC corners
    deg_pad_lat = max((lat_max - lat_min) * 1.4, 4.0)
    deg_pad_lon = max((lon_max - lon_min) * 1.4, 5.0)
    lon_win = (lon_min - deg_pad_lon, lon_max + deg_pad_lon)
    lat_win = (lat_min - deg_pad_lat, lat_max + deg_pad_lat)
    return proj, xlim, ylim, lon_win, lat_win


def draw_land(ax, proj: Tuple[float, float, float, float], lon_win: Tuple[float, float], lat_win: Tuple[float, float]):
    lon0, lat0, s1, s2 = proj
    patches = []
    for feat in WORLD["features"]:
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
        patches, facecolor=LAND, edgecolor=LAND_EDGE, linewidth=0.65, zorder=1.0
    ))


def draw_states(ax, proj: Tuple[float, float, float, float], fill: bool = False):
    lon0, lat0, s1, s2 = proj
    patches = []
    for feat in STATES["features"]:
        for ring in rings(feat["geometry"]):
            arr = np.asarray(ring, dtype=float)
            if len(arr) < 4 or arr[:, 0].max() - arr[:, 0].min() > 120:
                continue
            x, y = lcc(arr[:, 0], arr[:, 1], lon0, lat0, s1, s2)
            patches.append(Polygon(np.column_stack([x, y]), closed=True))
    ax.add_collection(PatchCollection(
        patches,
        facecolor=(LAND if fill else "none"),
        edgecolor=LAND_EDGE,
        linewidth=0.65,
        linestyle=(0, (6, 3)) if not fill else "solid",
        zorder=1.8,
    ))


def _nice_deg_step(span_deg: float) -> float:
    if span_deg >= 14.0:
        return 5.0
    if span_deg >= 6.5:
        return 2.0
    if span_deg >= 2.2:
        return 1.0
    return 0.5


def _fmt_deg(val: float, is_lon: bool) -> str:
    hemi = ("W" if val < 0 else "E") if is_lon else ("S" if val < 0 else "N")
    av = abs(val)
    if abs(av - round(av)) < 1e-6:
        return f"{int(round(av))}°{hemi}"
    return f"{av:.1f}°{hemi}"


def _in_axes_boxes(ax, x_data: float, y_data: float, axes_boxes: Sequence[Tuple[float, float, float, float]], pad: float = 0.022) -> bool:
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
):
    """Draw 5°/10° major graticule plus adaptive minor graticule when zoomed tightly."""
    lon0, lat0, s1, s2 = proj
    # Estimate visible degree span from panel corners
    km_per_unit = _km_per_unit(proj)
    vis_lat_deg = (ylim[1] - ylim[0]) * km_per_unit / 111.32
    vis_lon_deg = (xlim[1] - xlim[0]) * km_per_unit / max(111.32 * math.cos(math.radians(lat0)), 25.0)

    lat_step = _nice_deg_step(vis_lat_deg)
    lon_step = _nice_deg_step(vis_lon_deg)

    lats_dense = np.linspace(lat_win[0] - 5, lat_win[1] + 5, 160)
    lons_dense = np.linspace(lon_win[0] - 8, lon_win[1] + 8, 160)

    lon_start = math.floor((lon_win[0] - 4) / lon_step) * lon_step
    lon_vals = np.arange(lon_start, lon_win[1] + 4 + lon_step, lon_step)
    # Ensure multiples of 5 are always present
    lon_5 = np.arange(math.floor((lon_win[0] - 4) / 5.0) * 5.0, lon_win[1] + 9.0, 5.0)
    all_lons = sorted({round(float(v), 4) for v in np.concatenate([lon_vals, lon_5])})

    for lon in all_lons:
        is_major = abs(lon % 5.0) < 1e-4 or abs(lon % 5.0 - 5.0) < 1e-4
        x, y = lcc(np.full_like(lats_dense, lon), lats_dense, lon0, lat0, s1, s2)
        ax.plot(x, y, color=GRID, lw=(0.75 if is_major else 0.45), zorder=0.2)
        ax.plot(x, y, color=GRID_LAND, lw=(0.60 if is_major else 0.36), alpha=(0.48 if is_major else 0.28), zorder=1.3)
        inside = (y > ylim[0]) & (y < ylim[1]) & (x > xlim[0] + 0.04 * (xlim[1] - xlim[0])) & (x < xlim[1] - 0.04 * (xlim[1] - xlim[0]))
        if inside.any() and (is_major or abs(lon / lon_step - round(lon / lon_step)) < 1e-3):
            idx = np.where(inside)[0][0]
            tx = float(x[idx])
            ty = float(ylim[0] + 0.010 * (ylim[1] - ylim[0]))
            if not _in_axes_boxes(ax, tx, ty, skip_axes_boxes):
                ax.text(
                    tx, ty,
                    _fmt_deg(lon, is_lon=True),
                    fontsize=6.2, color=DIM, ha="center", va="bottom", zorder=5.2,
                    path_effects=[pe.withStroke(linewidth=2.4, foreground=OCEAN)],
                )

    lat_start = math.floor((lat_win[0] - 4) / lat_step) * lat_step
    lat_vals = np.arange(lat_start, lat_win[1] + 4 + lat_step, lat_step)
    lat_5 = np.arange(math.floor((lat_win[0] - 4) / 5.0) * 5.0, lat_win[1] + 9.0, 5.0)
    all_lats = sorted({round(float(v), 4) for v in np.concatenate([lat_vals, lat_5])})

    for lat in all_lats:
        is_major = abs(lat % 5.0) < 1e-4 or abs(lat % 5.0 - 5.0) < 1e-4
        x, y = lcc(lons_dense, np.full_like(lons_dense, lat), lon0, lat0, s1, s2)
        ax.plot(x, y, color=GRID, lw=(0.75 if is_major else 0.45), zorder=0.2)
        ax.plot(x, y, color=GRID_LAND, lw=(0.60 if is_major else 0.36), alpha=(0.48 if is_major else 0.28), zorder=1.3)
        inside = (x > xlim[0]) & (x < xlim[1]) & (y > ylim[0] + 0.05 * (ylim[1] - ylim[0])) & (y < ylim[1] - 0.05 * (ylim[1] - ylim[0]))
        if inside.any() and (is_major or abs(lat / lat_step - round(lat / lat_step)) < 1e-3):
            idx = np.where(inside)[0][0]
            tx = float(xlim[0] + 0.010 * (xlim[1] - xlim[0]))
            ty = float(y[idx])
            if not _in_axes_boxes(ax, tx, ty, skip_axes_boxes):
                ax.text(
                    tx, ty,
                    _fmt_deg(lat, is_lon=False),
                    fontsize=6.2, color=DIM, ha="left", va="center", zorder=5.2,
                    path_effects=[pe.withStroke(linewidth=2.4, foreground=OCEAN)],
                )


def _km_per_unit(proj: Tuple[float, float, float, float]) -> float:
    lon0, lat0, s1, s2 = proj
    _, y_a = lcc([lon0], [lat0 - 0.5], lon0, lat0, s1, s2)
    _, y_b = lcc([lon0], [lat0 + 0.5], lon0, lat0, s1, s2)
    return 111.32 / abs(float(np.ravel(y_b - y_a)[0]))


def draw_scale_bar(ax, proj: Tuple[float, float, float, float], corner: str = "bottom-right") -> Tuple[float, float, float, float]:
    """Draw an automatically sized metric scale bar and return its axes-fraction bbox."""
    km_per_unit = _km_per_unit(proj)
    xlim = ax.get_xlim()
    panel_km = (xlim[1] - xlim[0]) * km_per_unit
    target_km = 0.14 * panel_km
    candidates = [10, 20, 25, 50, 100, 150, 200, 250, 500]
    km = min(candidates, key=lambda c: abs(c - target_km))
    frac = (km / km_per_unit) / (xlim[1] - xlim[0])

    if corner == "bottom-left":
        x_center = 0.045 + 0.5 * frac
    else:
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
        facecolor=BG, edgecolor=BORDER, linewidth=0.7, alpha=0.90, zorder=8.8,
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
        transform=ax.transAxes, fontsize=7.2, fontweight="bold", color=MUTED,
        ha="center", va="bottom", zorder=9.1,
    )
    return (box_x0, box_y0, box_x1, box_y1)


# ------------------------------------------------------------------ dossier extraction
def _match_stop_days_by_name(stops: List[Dict[str, Any]], day_names: Dict[int, List[str]], default_days: int) -> None:
    """Assign `day` to stops by matching itinerary venue names against marker names."""
    for s in stops:
        if s.get("day"):
            continue
        sname = s["name"].lower()
        tokens = [w for w in re.split(r"[^a-z0-9]+", sname) if len(w) >= 4 and w not in {"brewing", "brewery", "beer", "company", "craft", "house", "pub", "bar"}]
        best_day = None
        for d, names in day_names.items():
            for raw_n in names:
                nl = raw_n.lower()
                if sname in nl or nl in sname:
                    best_day = d
                    break
                if tokens and any(tok in nl for tok in tokens[:2]):
                    best_day = d
                    break
            if best_day is not None:
                break
        if best_day is not None:
            s["day"] = best_day

    # Fallback: interpolate remaining stops by proximity to matched stops
    matched = [s for s in stops if s.get("day")]
    for s in stops:
        if not s.get("day"):
            if matched:
                nearest = min(matched, key=lambda m: (m["lat"] - s["lat"]) ** 2 + (m["lon"] - s["lon"]) ** 2)
                s["day"] = nearest["day"]
            else:
                s["day"] = 1


def extract_uk() -> Dict[str, Any]:
    fn = "uk_beer_trip.html"
    h = (DOSSIERS / fn).read_text(encoding="utf-8")
    soup = BeautifulSoup(h, "lxml")

    raw_stops = tuples(js_array(h, "stops"))
    stops = [
        {"lat": s["lat"], "lon": s["lon"], "name": s["name"], "day": s.get("day", 1)}
        for s in raw_stops
    ]
    path = [[s["lat"], s["lon"]] for s in stops]

    ledger = []
    for node in soup.select("div.day-node"):
        dnum = int(re.search(r"\d+", node.select_one(".day-num").get_text()).group())
        loc = clean_text(node.select_one(".location").get_text(" ", strip=True))
        region = clean_text(node.select_one(".region-badge").get_text(" ", strip=True))
        bolds = [clean_text(b.get_text(" ", strip=True)) for b in node.select(".stops strong")]
        stops_txt = clean_text(node.select_one(".stops").get_text(" ", strip=True))
        if len(bolds) >= 3:
            hl = " · ".join(bolds)
        elif bolds:
            # Extract compact `Venue (Town/Year)` segments before em-dash descriptions
            seg_items = []
            for raw_seg in stops_txt.split("|"):
                seg = clean_text(raw_seg)
                if not seg or re.match(r"^(Fly |Drive |Afternoon |Return )", seg, re.I):
                    continue
                seg = re.sub(r"^(Evening|Morning|Afternoon)\s*:\s*", "", seg, flags=re.I)
                seg_short = re.split(r"\s+[—–-]\s+", seg)[0].strip()
                seg_short = re.sub(r",\s*Anglesey", "", seg_short)
                if seg_short:
                    seg_items.append(seg_short)
            hl = " · ".join(seg_items) if seg_items else " · ".join(bolds)
        else:
            hl = stops_txt
        place_lbl = f"{loc}  ·  {region}" if "(" in loc else f"{loc} ({region})"
        ledger.append({"day": dnum, "place": place_lbl, "highlights": hl})

    return {
        "slug": "uk-beer-pilgrimage",
        "source_file": fn,
        "title": "12-Day UK Beer Pilgrimage",
        "days": 12,
        "countries": "England, Wales & Scotland",
        "unit_label": "stops",
        "route_summary": "London → Oxford → Burton → Manchester → Nottingham → Wales → Edinburgh → Highlands",
        "stops": stops,
        "path": path,
        "day_ledger": ledger,
        "key_stops": [
            "Ye Olde Cheshire Cheese",
            "Hook Norton Brewery",
            "Ye Olde Trip to Jerusalem",
            "Cloudwater Brew Co",
            "Timothy Taylor's",
            "Skirrid Mountain Inn",
            "Tenby Brewing Co",
            "Purple Moose Brewery",
            "The Sheep Heid Inn",
            "Fyne Ales",
        ],
        "signature_beers": "Timothy Taylor Landlord (4.3%) · Thornbridge Jaipur IPA (5.9%) · Fyne Ales Jarl (3.8%) · Tiny Rebel CWTCH (4.6%) · Fuller's London Pride (4.1%) · Traquair Bear Ale (5.0%)",
        "season_budget": "May–Jun or Sep–Oct  ·  £150–250 / day (~$190–315)  ·  Tube in London (Days 1–2), rental car Days 3–12",
        "ramp": ["#f2604f", "#f5a623", "#38d399", "#54a8f5"],
        "is_us": False,
        "legend_corner": "top-left",
        "scale_corner": "bottom-right",
        "watermarks": [
            ("ENGLAND", -1.4, 52.4),
            ("WALES", -3.75, 52.35),
            ("SCOTLAND", -4.2, 56.85),
            ("IRELAND", -7.6, 53.4),
            ("NORTH SEA", 1.1, 55.2),
        ],
    }


def extract_belgium() -> Dict[str, Any]:
    fn = "belgian.html"
    h = (DOSSIERS / fn).read_text(encoding="utf-8")

    stops = []
    for o in objects(js_array(h, "PLACES")):
        lat, lon, name = field(o, "lat"), field(o, "lng"), field(o, "name")
        day = field(o, "day")
        if lat is not None and lon is not None and name:
            stops.append({
                "lat": float(lat),
                "lon": float(lon),
                "name": str(name),
                "city": str(field(o, "city") or ""),
                "rating": float(field(o, "rating") or 0.0),
                "day": int(day) if day is not None else 1,
            })

    path = pairs(js_array(h, "routePoints"))

    # Parse TRIP_DAYS top-level objects
    td_block = js_array(h, "TRIP_DAYS")
    # TRIP_DAYS has nested `stops: [{...}]`, so extract top-level objects from inside `[`..`]`
    inner = td_block[1:-1]
    ledger = []
    for dobj in objects(inner):
        dnum = int(field(dobj, "day"))
        dtitle = str(field(dobj, "title") or "")
        dregion = str(field(dobj, "region") or "")
        s_block_m = re.search(r"stops\s*:\s*\[(.*?)\]", dobj, re.S)
        s_names = []
        if s_block_m:
            for so in objects(s_block_m.group(1)):
                nm = field(so, "name")
                if nm:
                    s_names.append(str(nm))
        ledger.append({
            "day": dnum,
            "place": f"{dtitle} · {dregion}",
            "highlights": " · ".join(s_names),
        })

    return {
        "slug": "belgian-beer-pilgrimage",
        "source_file": fn,
        "title": "Belgian Beer Pilgrimage",
        "days": 9,
        "countries": "Belgium, Germany & Czechia",
        "unit_label": "stops",
        "route_summary": "Frankfurt → Brussels → Pajottenland → Hainaut → West Flanders → Bruges → Antwerp → Ardennes → Chimay → Cologne → Pilsen",
        "stops": stops,
        "path": path,
        "day_ledger": ledger,
        "key_stops": [
            "Cantillon Brewery",
            "Brasserie Dupont",
            "Rodenbach Brewery",
            "De Garre",
            "Westvleteren / In de Vrede",
            "Kulminator",
            "Orval Abbey",
            "Chimay (Scourmont Abbey)",
            "Päffgen Brauhaus",
            "Pilsner Urquell",
        ],
        "extra_labels": [("Frankfurt (Start)", 50.1109, 8.6821)],
        "signature_beers": "Westvleteren 12 (10.2%) · Cantillon Gueuze Bio (5.0%) · Drie Fonteinen Oude Geuze (6.0%) · Saison Dupont (6.5%) · Orval (6.2%) · Rodenbach Grand Cru (6.0%)",
        "season_budget": "Apr–May or Sep–Oct  ·  Tours €5–20 (book Cantillon, Dupont & Westvleteren ahead)  ·  Train Frankfurt → Brussels, car Days 2–9",
        "ramp": ["#f5a623", "#ff7a59", "#b283f8", "#43d19e"],
        "is_us": False,
        "legend_corner": "bottom-left",
        "scale_corner": "bottom-right",
        "watermarks": [
            ("BELGIUM", 4.6, 50.65),
            ("GERMANY", 9.6, 51.35),
            ("CZECHIA", 13.7, 50.15),
            ("FRANCE", 3.4, 49.0),
            ("NETHERLANDS", 5.3, 52.15),
        ],
    }


def extract_bavaria_bohemia() -> Dict[str, Any]:
    fn = "germany_czech_beer_trip.html"
    h = (DOSSIERS / fn).read_text(encoding="utf-8")
    soup = BeautifulSoup(h, "lxml")

    stops = []
    for o in objects(js_array(h, "places")):
        lat, lon, name, desc = field(o, "lat"), field(o, "lng"), field(o, "name"), field(o, "desc")
        if lat is not None and lon is not None and name:
            dm = re.search(r"Day\s+(\d+)", str(desc or ""))
            day = int(dm.group(1)) if dm else 1
            stops.append({
                "lat": float(lat),
                "lon": float(lon),
                "name": str(name),
                "day": day,
            })

    path = pairs(js_array(h, "routeCoords"))

    ledger = []
    for node in soup.select("div.day-node"):
        dnum = int(re.search(r"\d+", node.select_one(".day-number").get_text()).group())
        place = clean_text(node.select_one("h3").get_text(" ", strip=True))
        b_div = node.select_one(".breweries")
        # Split on <br> to extract concise stop highlights without tip italics
        raw_html = b_div.decode_contents() if b_div else ""
        raw_html = re.sub(r"<em\b[^>]*>.*?</em>", "", raw_html, flags=re.S)
        chunks = [clean_text(BeautifulSoup(c, "lxml").get_text(" ", strip=True)) for c in re.split(r"<br\s*/?>", raw_html)]
        cleaned_chunks = []
        for c in chunks:
            if not c:
                continue
            c = re.sub(r"^(Morning-Lunch|Late Morning|Afternoon drive|Morning|Lunch|Afternoon|Evening|Nightcap|Drive east|Optional|Travel|Airport)\s*:\s*", "", c, flags=re.I)
            if re.match(r"^Through (beautiful|western)\b", c, re.I) or re.match(r"^Even Frankfurt Airport\b", c, re.I):
                continue
            c = re.sub(r"\s*\((?:tradition|if Starkbierfest|if time allows|for the experience)[^)]*\)?", "", c, flags=re.I).strip()
            c = re.sub(r"^Final Weißwurst breakfast at ", "Weißwurst breakfast: ", c)
            c = re.sub(r"\s+or Weltenburg Abbey via Danube boat", "", c)
            c = c.replace("Beim Gloser or Beim Bannes (Windischeschenbach)", "Beim Gloser & Beim Bannes")
            # Keep main name + concise note before verbose sentence
            if " - " in c:
                lhs, rhs = c.split(" - ", 1)
                rhs_short = rhs.split(".")[0].strip()
                c = f"{lhs.strip()} ({rhs_short})" if len(chunks) <= 2 else lhs.strip()
            cleaned_chunks.append(c)
        ledger.append({
            "day": dnum,
            "place": place,
            "highlights": " · ".join(cleaned_chunks[:5]),
        })

    return {
        "slug": "bavaria-bohemia",
        "source_file": fn,
        "title": "14-Day Bavaria & Bohemia Beer Pilgrimage",
        "days": 14,
        "countries": "Germany & Czechia",
        "unit_label": "stops",
        "route_summary": "Frankfurt → Bamberg → Franconia → Zoigl → Chodovar → Pilsen → Žatec → Kout → Regensburg → Munich → Andechs",
        "stops": stops,
        "path": path,
        "day_ledger": ledger,
        "day_overrides": {14: (50.0379, 8.5622)},
        "key_stops": [
            "Frankfurt Airport",
            "Schlenkerla",
            "Aufseß (4 breweries)",
            "Zoigl Windischeschenbach",
            "Pilsner Urquell",
            "Falkon Žatec",
            "Kout na Šumavě",
            "Kneitinger Regensburg",
            "Augustiner-Keller",
            "Kloster Andechs",
        ],
        "signature_beers": "Schlenkerla Märzen Rauchbier (5.1%) · Mahr's \"aU\" Kellerbier (5.2%) · Koutská 12° Ležák (5.0%) · Plzeňský Prazdroj 12° (4.4%) · Augustiner Edelstoff (5.6%) · Andechs Doppelbock (7.1%)",
        "season_budget": "May–Sep beer-garden season (Annafest late July)  ·  Czech pints €1.50–2.50, Bavaria Ticket €29/day  ·  Trains, Brauereienweg trails & car",
        "ramp": ["#f5a623", "#43d19e", "#38bdf8", "#b283f8"],
        "is_us": False,
        "legend_corner": "bottom-left",
        "scale_corner": "bottom-right",
        "watermarks": [
            ("GERMANY  ·  BAVARIA & FRANCONIA", 9.35, 49.15),
            ("CZECHIA  ·  BOHEMIA", 13.95, 49.45),
            ("AUSTRIA", 13.2, 47.95),
        ],
    }


def extract_colorado() -> Dict[str, Any]:
    fn = "colorado_beer_trip.html"
    h = (DOSSIERS / fn).read_text(encoding="utf-8")
    soup = BeautifulSoup(h, "lxml")

    stops = []
    for o in objects(js_array(h, "markers")):
        lat, lon, name, city = field(o, "lat"), field(o, "lng"), field(o, "name"), field(o, "city")
        if lat is not None and lon is not None and name:
            nm = re.sub(r"\s*★.*$", "", str(name)).strip()
            stops.append({
                "lat": float(lat),
                "lon": float(lon),
                "name": nm,
                "city": str(city or ""),
            })

    path = pairs(js_array(h, "route"))

    ledger = []
    day_names: Dict[int, List[str]] = {}
    for card in soup.select("div.day-card"):
        dnum = int(re.search(r"\d+", card.select_one(".day-num").get_text()).group())
        place = clean_text(card.select_one("h3").get_text(" ", strip=True))
        bolds = [clean_text(b.get_text(" ", strip=True)) for b in card.select(".stops b")]
        day_names[dnum] = bolds
        stops_html = card.select_one(".stops").decode_contents()
        lines = [clean_text(BeautifulSoup(ln, "lxml").get_text(" ", strip=True)) for ln in re.split(r"<br\s*/?>", stops_html)]
        if len(bolds) <= 2:
            short_lines = []
            for ln in lines:
                if not ln:
                    continue
                if re.match(r"^Land at DEN", ln, re.I):
                    short_lines.append("DEN → Union Station (LoDo)")
                else:
                    short_lines.append(ln.split(" - ")[0].strip())
            hl = " · ".join(short_lines[:4])
        else:
            hl = " · ".join(bolds)
        ledger.append({"day": dnum, "place": place, "highlights": hl})

    # Assign day to stops cleanly
    if stops:
        stops[0]["day"] = 1  # DEN Airport
    _match_stop_days_by_name(stops, day_names, 12)

    return {
        "slug": "colorado-craft-beer",
        "source_file": fn,
        "title": "Colorado Craft Beer Odyssey",
        "days": 12,
        "countries": "Colorado, United States",
        "unit_label": "stops",
        "route_summary": "DEN → Denver (RiNo, S. Broadway) → Golden → Boulder → Niwot & Longmont → Fort Collins → DEN",
        "stops": stops,
        "path": path,
        "day_ledger": ledger,
        "day_overrides": {12: (39.8561, -104.6737)},
        "key_stops": [
            "Denver International Airport",
            "Bierstadt Lagerhaus",
            "TRVE Brewing",
            "Cannonball Creek Brewing",
            "Mountain Sun Pub",
            "Avery Brewing Co",
            "Fritz Family Brewers",
            "Left Hand Brewing",
            "Odell Brewing Co",
            "Purpose Brewing",
        ],
        "signature_beers": "Bierstadt Slow Pour Pils (4.8%) · Funkwerks Saison (6.8%) · Odell IPA (7.0%) · Left Hand Milk Stout Nitro (6.0%) · Great Divide Yeti (9.5%) · Avery Tweak (16.3%)",
        "season_budget": "Jun–Sep patio season (GABF week in Sep)  ·  A-Line train DEN → Union Station ($10.50), rental car Days 5–12 (Golden → Fort Collins)",
        "ramp": ["#ff6b8b", "#f5a623", "#4ecdc4", "#43d19e"],
        "is_us": True,
        "state_inset": True,
        "legend_corner": "top-left",
        "scale_corner": "bottom-left",
        "watermarks": [
            ("FRONT RANGE  ·  COLORADO", -105.45, 40.32),
        ],
    }


def extract_florida() -> Dict[str, Any]:
    fn = "florida_brewery_trip.html"
    h = (DOSSIERS / fn).read_text(encoding="utf-8")
    soup = BeautifulSoup(h, "lxml")

    stops = []
    for arr_name, region in (("miami", "South Florida"), ("orlando", "Central Florida"), ("tampa", "Tampa Bay")):
        for s in tuples(js_array(h, arr_name)):
            stops.append({
                "lat": s["lat"],
                "lon": s["lon"],
                "name": s["name"],
                "region": region,
            })

    poly_m = re.search(r"L\.polyline\(\s*(\[\s*\[.*?\]\s*\])\s*,\s*\{", h)
    path = pairs(poly_m.group(1)) if poly_m else [[s["lat"], s["lon"]] for s in stops]

    ledger = []
    day_names: Dict[int, List[str]] = {}
    for card in soup.select("div.day-card"):
        dnum = int(re.search(r"\d+", card.select_one(".day-number").get_text()).group())
        dtitle = clean_text(card.select_one(".day-title").get_text(" ", strip=True))
        dloc = clean_text(card.select_one(".day-location").get_text(" ", strip=True))
        city_short = dloc.split("-")[0].split("→")[0].strip()
        snames = [clean_text(el.get_text(" ", strip=True)) for el in card.select(".stop-name")]
        day_names[dnum] = snames
        # Filter generic travel items when plenty of brewery names exist
        beer_stops = [n for n in snames if not re.match(r"^(Arrive|Depart|Drive to)\b", n, re.I)]
        ledger.append({
            "day": dnum,
            "place": f"{city_short}: {dtitle}" if city_short and city_short.lower() not in dtitle.lower() else dtitle,
            "highlights": " · ".join(beer_stops or snames),
        })

    _match_stop_days_by_name(stops, day_names, 12)

    return {
        "slug": "florida-brewery-trail",
        "source_file": fn,
        "title": "Florida Brewery Trail",
        "days": 12,
        "countries": "Florida, United States",
        "unit_label": "stops",
        "route_summary": "MIA → Miami (Wynwood, Doral, Coral Gables) → Fort Lauderdale → Orlando → Tampa → St. Petersburg → Dunedin → TPA",
        "stops": stops,
        "path": path,
        "day_ledger": ledger,
        "key_stops": [
            "J Wakefield Brewing",
            "Tripping Animals",
            "Titanic Brewery",
            "Funky Buddha",
            "Sideward Brewing",
            "Crooked Can",
            "Cigar City Brewing",
            "Cycle Brewing",
            "Dunedin Brewery",
        ],
        "signature_beers": "Cigar City Jai Alai IPA (7.5%) · Hunahpu's Imperial Stout (11.8%) · Angry Chair German Choc Cupcake (11%) · Funky Buddha Maple Bacon Coffee Porter (6.4%) · Cycle Crank BA Stout (12%)",
        "season_budget": "Nov–Apr (avoid summer heat & humidity)  ·  $3,500–5,500 / 12 days excl. flights ($7–9 pints)  ·  One-way rental MIA → TPA + rideshare",
        "ramp": ["#ff7fa3", "#f5a623", "#4ecdc4", "#ff9f43"],
        "is_us": True,
        "legend_corner": "bottom-left",
        "scale_corner": "top-right",
        "watermarks": [
            ("FLORIDA", -81.55, 27.35),
            ("GULF OF MEXICO", -82.85, 26.55),
            ("ATLANTIC OCEAN", -79.95, 27.65),
        ],
    }


def extract_italy_grand() -> Dict[str, Any]:
    fn = "Italy_Switzerland_14Day_Trip.html"
    h = (DOSSIERS / fn).read_text(encoding="utf-8")
    soup = BeautifulSoup(h, "lxml")

    stops = []
    city_day_badges = {
        "Rome (FCO)": (1, "D1–3, 13–14"),
        "Florence": (4, "D4–6"),
        "Pisa": (6, "D6"),
        "Venice": (7, "D7–8"),
        "Milan": (9, "D9–10"),
        "Tirano (Bernina start)": (11, "D11"),
        "St. Moritz": (12, "D11–12"),
    }
    for o in objects(js_array(h, "cities")):
        lat, lon, name = field(o, "lat"), field(o, "lng"), field(o, "name")
        if lat is not None and lon is not None and name:
            d_num, badge_lbl = city_day_badges.get(str(name), (1, "D1"))
            stops.append({
                "lat": float(lat),
                "lon": float(lon),
                "name": str(name),
                "day": d_num,
                "badge": badge_lbl,
            })

    route = pairs(js_array(h, "route"))
    return_route = pairs(js_array(h, "returnRoute"))
    path = route + return_route[1:]

    day_places = {
        1: "Rome — Arrival & Trastevere",
        2: "Rome — Ancient Imperial Core",
        3: "Rome — Vatican & Historic Center",
        4: "Rome → Florence",
        5: "Florence — Renaissance Icons",
        6: "Florence & Pisa Day Trip",
        7: "Florence → Venice",
        8: "Venice — Lagoon Islands & Ghetto",
        9: "Venice → Milan",
        10: "Milan — Castles, Brera & Lambrate",
        11: "Milan → St. Moritz (Bernina Railway)",
        12: "St. Moritz & Upper Engadin",
        13: "St. Moritz → Rome (Appian Way)",
        14: "Rome — Borghese, Coppedè & FCO",
    }

    ledger = []
    for card in soup.select("#flowchart .place-card"):
        nm_el = card.select_one(".name")
        desc_el = card.select_one(".desc")
        if not nm_el or not desc_el:
            continue
        nm = clean_text(nm_el.get_text(" ", strip=True))
        m = re.match(r"Day\s+(\d+)$", nm)
        if not m:
            continue
        dnum = int(m.group(1))
        desc = clean_text(desc_el.get_text(" ", strip=True))
        # Condense sentences with clean separator (preserve "St.")
        parts = [p.strip().rstrip(".") for p in re.split(r"(?<!\bSt)\.\s+", desc) if p.strip()]
        hl = " · ".join(parts[:4])
        ledger.append({
            "day": dnum,
            "place": day_places.get(dnum, f"Day {dnum}"),
            "highlights": hl,
        })

    return {
        "slug": "italy-switzerland-grand-tour",
        "source_file": fn,
        "title": "14-Day Italy & Switzerland Grand Tour",
        "days": 14,
        "countries": "Italy & Switzerland",
        "unit_label": "cities",
        "route_summary": "Rome → Florence → Pisa → Venice → Milan → Tirano → St. Moritz → Rome",
        "stops": stops,
        "path": route,
        "return_path": return_route,
        "day_ledger": ledger,
        "city_badges": True,
        "key_stops": [s["name"] for s in stops],
        "signature_beers": "Birrificio Italiano Tipopils · Birra del Borgo ReAle · Baladin Xyauyù & Nazionale · Birrificio Lambrate Ghisa & Montestella · Orzo Bruno · Engadiner Bier",
        "season_budget": "May–Jun or Sep–Oct  ·  €2,500–4,000 pp excl. flights (22+ craft beer bars)  ·  Frecciarossa high-speed rail + UNESCO Bernina Railway",
        "ramp": ["#b283f8", "#54a8f5", "#43d19e", "#ff8c42"],
        "is_us": False,
        "legend_corner": "bottom-left",
        "scale_corner": "bottom-right",
        "watermarks": [
            ("ITALY", 11.4, 43.0),
            ("SWITZERLAND", 8.9, 46.65),
            ("TYRRHENIAN SEA", 10.3, 41.8),
            ("ADRIATIC SEA", 13.2, 44.3),
        ],
    }


def extract_italy_classic() -> Dict[str, Any]:
    fn = "italy_switzerland_trip.html"
    h = (DOSSIERS / fn).read_text(encoding="utf-8")
    soup = BeautifulSoup(h, "lxml")

    city_day_badges = {
        "Roma (FCO)": (14, "D1 / D14"),
        "Roma": (2, "D1–3"),
        "Firenze": (4, "D4–5"),
        "Pisa": (6, "D6"),
        "Milano": (8, "D7–9"),
        "St. Moritz": (10, "D10–11"),
        "Venezia": (12, "D12–13"),
    }
    stops = []
    for o in objects(js_array(h, "cities")):
        lat, lon, name = field(o, "lat"), field(o, "lng"), field(o, "name")
        if lat is not None and lon is not None and name:
            d_num, badge_lbl = city_day_badges.get(str(name), (1, "D1"))
            stops.append({
                "lat": float(lat),
                "lon": float(lon),
                "name": str(name),
                "day": d_num,
                "badge": badge_lbl,
            })

    gems = []
    for o in objects(js_array(h, "gems")):
        lat, lon, name = field(o, "lat"), field(o, "lng"), field(o, "name")
        if lat is not None and lon is not None and name:
            gems.append({"lat": float(lat), "lon": float(lon), "name": str(name)})

    path = pairs(js_array(h, "route"))

    day_places = {
        1: "Roma (FCO) — Arrival & Trastevere",
        2: "Roma — Colosseum & San Clemente",
        3: "Roma — Vatican, Aventine & Craft Beer",
        4: "Roma → Firenze",
        5: "Firenze — Accademia & Oltrarno",
        6: "Firenze → Pisa (Overnight)",
        7: "Pisa → Milano",
        8: "Milano — Last Supper & Lambiczoon",
        9: "Milano — Sforza & Monumentale",
        10: "Milano → St. Moritz (Bernina Express)",
        11: "St. Moritz — Muottas Muragl & Val Roseg",
        12: "St. Moritz → Venezia",
        13: "Venezia — San Marco, Ghetto & Bacari",
        14: "Venezia → Roma (FCO Departure)",
    }

    ledger = []
    for li in soup.select("#tips .tip-box li"):
        txt = clean_text(li.get_text(" ", strip=True))
        m = re.match(r"Day\s+(\d+)\s*:\s*(.+)$", txt)
        if not m:
            continue
        dnum = int(m.group(1))
        body = m.group(2).strip()
        parts = [p.strip().rstrip(".") for p in re.split(r"(?<!\bSt)\.\s+", body) if p.strip()]
        ledger.append({
            "day": dnum,
            "place": day_places.get(dnum, f"Day {dnum}"),
            "highlights": " · ".join(parts[:4]),
        })

    return {
        "slug": "italy-switzerland-classic",
        "source_file": fn,
        "title": "14-Day Italy & Switzerland — Classic Loop",
        "days": 14,
        "countries": "Italy & Switzerland",
        "unit_label": "cities",
        "route_summary": "Roma (FCO) → Roma → Firenze → Pisa → Milano → St. Moritz → Venezia → Roma (FCO)",
        "stops": stops,
        "gems": gems,
        "path": path,
        "day_ledger": ledger,
        "city_badges": True,
        "key_stops": [s["name"] for s in stops],
        "signature_beers": "Tipopils (5.2%) · ReAle (6.4%) · Baladin Nazionale (6.5%) · Archea Dubbel (7.5%) · Lambrate Montestella (5.0%) · Orzo Bruno Chiara (4.8%) · Engadiner Bündner Lager (4.8%)",
        "season_budget": "May–Jun or Sep–Oct  ·  €2,600–4,100 pp excl. flights (trains €250–400)  ·  Frecciarossa + Bernina Express + EuroCity via Chur",
        "ramp": ["#fb568a", "#f5a623", "#38bdf8", "#34d399"],
        "is_us": False,
        "legend_corner": "bottom-left",
        "scale_corner": "bottom-right",
        "watermarks": [
            ("ITALY", 11.4, 43.0),
            ("SWITZERLAND", 8.9, 46.65),
            ("TYRRHENIAN SEA", 10.3, 41.8),
            ("ADRIATIC SEA", 13.2, 44.3),
        ],
    }


# ------------------------------------------------------------------ rendering helpers
def make_cmap(ramp: Sequence[str]) -> LinearSegmentedColormap:
    return LinearSegmentedColormap.from_list("trip_ramp", list(ramp), N=256)


def day_color(cmap: LinearSegmentedColormap, day: int, total_days: int) -> str:
    t = 0.0 if total_days <= 1 else (max(1, min(day, total_days)) - 1.0) / (total_days - 1.0)
    return to_hex(cmap(t))


def densify_xy(xs: np.ndarray, ys: np.ndarray, n_target: int = 320) -> Tuple[np.ndarray, np.ndarray]:
    if len(xs) < 2:
        return xs, ys
    dx = np.diff(xs)
    dy = np.diff(ys)
    seg_len = np.hypot(dx, dy)
    cum = np.concatenate([[0.0], np.cumsum(seg_len)])
    total = cum[-1]
    if total <= 1e-9:
        return xs, ys
    s_new = np.linspace(0.0, total, n_target)
    return np.interp(s_new, cum, xs), np.interp(s_new, cum, ys)


def draw_gradient_route(
    ax,
    xs: np.ndarray,
    ys: np.ndarray,
    cmap: LinearSegmentedColormap,
    return_xy: Optional[Tuple[np.ndarray, np.ndarray]] = None,
):
    if len(xs) >= 2:
        xd, yd = densify_xy(xs, ys, 340)
        ax.plot(xd, yd, color=BG, lw=5.4, alpha=0.80, solid_capstyle="round", solid_joinstyle="round", zorder=3.0)
        pts = np.column_stack([xd, yd]).reshape(-1, 1, 2)
        segs = np.concatenate([pts[:-1], pts[1:]], axis=1)
        t_vals = np.linspace(0.0, 1.0 if return_xy is None else 0.85, len(segs))
        lc = LineCollection(
            segs,
            colors=[cmap(t) for t in t_vals],
            linewidths=2.8,
            capstyle="round",
            joinstyle="round",
            alpha=0.92,
            zorder=3.2,
        )
        ax.add_collection(lc)

        # Subtle directional chevrons along longer legs
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        min_leg = 0.09 * math.hypot(xlim[1] - xlim[0], ylim[1] - ylim[0])
        for i in range(len(xs) - 1):
            leg = math.hypot(xs[i + 1] - xs[i], ys[i + 1] - ys[i])
            if leg < min_leg:
                continue
            mx = 0.52 * xs[i] + 0.48 * xs[i + 1]
            my = 0.52 * ys[i] + 0.48 * ys[i + 1]
            dx_s = (xs[i + 1] - xs[i]) * 0.001
            dy_s = (ys[i + 1] - ys[i]) * 0.001
            col = to_hex(cmap((i + 0.5) / max(len(xs) - 1, 1)))
            ax.annotate(
                "",
                xy=(mx + dx_s, my + dy_s),
                xytext=(mx - dx_s, my - dy_s),
                arrowprops=dict(arrowstyle="-|>", color=col, lw=1.4, mutation_scale=11),
                zorder=3.5,
            )

    if return_xy is not None and len(return_xy[0]) >= 2:
        rx, ry = return_xy
        ax.plot(rx, ry, color=BG, lw=3.8, alpha=0.70, zorder=2.8)
        ax.plot(
            rx, ry, color=to_hex(cmap(0.95)), lw=1.9, alpha=0.80,
            linestyle=(0, (6, 4)), zorder=2.9,
        )


def _repel_points_px(
    anchors_px: List[Tuple[float, float]],
    min_dist_px: float,
    panel_bbox_px: Tuple[float, float, float, float],
    forbidden_px: List[Tuple[float, float, float, float]],
) -> List[Tuple[float, float]]:
    """Deterministic iterative repulsion so day badges never overlap each other or panel edges."""
    pos = [np.array([x, y], dtype=float) for x, y in anchors_px]
    orig = [np.array([x, y], dtype=float) for x, y in anchors_px]
    x0, y0, x1, y1 = panel_bbox_px
    pad = 28.0

    # Break exact initial ties deterministically in a small spiral
    for i in range(len(pos)):
        for j in range(i + 1, len(pos)):
            if np.linalg.norm(pos[i] - pos[j]) < 2.0:
                ang = 0.9 * j
                pos[j] = pos[j] + np.array([math.cos(ang), math.sin(ang)]) * 8.0

    for _ in range(90):
        for i in range(len(pos)):
            for j in range(i + 1, len(pos)):
                delta = pos[j] - pos[i]
                dist = float(np.linalg.norm(delta))
                if dist < min_dist_px:
                    if dist < 1e-4:
                        direction = np.array([1.0, 0.0])
                    else:
                        direction = delta / dist
                    push = 0.52 * (min_dist_px - dist) * direction
                    pos[i] -= push
                    pos[j] += push
            # Gentle spring back toward anchor
            pos[i] += 0.08 * (orig[i] - pos[i])
            # Keep inside panel
            pos[i][0] = float(np.clip(pos[i][0], x0 + pad, x1 - pad))
            pos[i][1] = float(np.clip(pos[i][1], y0 + pad, y1 - pad))
            # Push out of forbidden UI boxes (legend / scale / inset)
            for fx0, fy0, fx1, fy1 in forbidden_px:
                if (fx0 - 20 <= pos[i][0] <= fx1 + 20) and (fy0 - 20 <= pos[i][1] <= fy1 + 20):
                    cx, cy = 0.5 * (fx0 + fx1), 0.5 * (fy0 + fy1)
                    if abs(pos[i][0] - cx) > abs(pos[i][1] - cy):
                        pos[i][0] = fx1 + 22 if pos[i][0] >= cx else fx0 - 22
                    else:
                        pos[i][1] = fy1 + 22 if pos[i][1] >= cy else fy0 - 22
                    pos[i][0] = float(np.clip(pos[i][0], x0 + pad, x1 - pad))
                    pos[i][1] = float(np.clip(pos[i][1], y0 + pad, y1 - pad))

    return [(float(p[0]), float(p[1])) for p in pos]


def _boxes_overlap_area(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float], pad: float = 4.0) -> float:
    ox = max(0.0, min(a[2] + pad, b[2] + pad) - max(a[0] - pad, b[0] - pad))
    oy = max(0.0, min(a[3] + pad, b[3] + pad) - max(a[1] - pad, b[1] - pad))
    return ox * oy


def place_halo_labels(
    fig,
    ax,
    label_specs: List[Tuple[str, float, float, str]],
    stop_px_pts: List[Tuple[float, float]],
    occupied_boxes_px: List[Tuple[float, float, float, float]],
    panel_bbox_px: Tuple[float, float, float, float],
):
    """Place 6-10 key stop labels with dark halos, guaranteed inside the map panel and collision-free."""
    renderer = fig.canvas.get_renderer()
    px0, py0, px1, py1 = panel_bbox_px
    edge_pad = 22.0

    # Candidate (dx_pt, dy_pt, ha, va) around the stop
    candidates: List[Tuple[float, float, str, str]] = []
    for r_pt in (11, 17, 25, 34, 45):
        for deg in (25, -25, 155, -155, 0, 180, 55, -55, 125, -125, 85, -85):
            rad = math.radians(deg)
            dx = r_pt * math.cos(rad)
            dy = r_pt * math.sin(rad)
            ha = "left" if dx > 4 else ("right" if dx < -4 else "center")
            va = "bottom" if dy > 6 else ("top" if dy < -6 else "center")
            candidates.append((dx, dy, ha, va))

    for text_str, sx, sy, accent_col in label_specs:
        anchor_disp = ax.transData.transform((sx, sy))
        best_cfg = None
        best_score = float("inf")
        best_ext = None

        probe = ax.annotate(
            text_str,
            xy=(sx, sy),
            xytext=(12, 8),
            textcoords="offset points",
            fontsize=8.6,
            fontweight="bold",
            color=TEXT,
            zorder=8.2,
            path_effects=[pe.withStroke(linewidth=3.6, foreground=BG)],
        )

        for dx, dy, ha, va in candidates:
            probe.xyann = (dx, dy)
            probe.set_ha(ha)
            probe.set_va(va)
            bb = probe.get_window_extent(renderer=renderer)
            cand_box = (float(bb.x0), float(bb.y0), float(bb.x1), float(bb.y1))

            # Hard boundary check: never allow a label near or beyond panel border
            if (cand_box[0] < px0 + edge_pad or cand_box[2] > px1 - edge_pad
                    or cand_box[1] < py0 + edge_pad or cand_box[3] > py1 - edge_pad):
                continue

            score = 0.16 * math.hypot(dx, dy)
            # Penalize overlapping existing boxes (badges, legend, scale bar, prior labels)
            for ob in occupied_boxes_px:
                ov = _boxes_overlap_area(cand_box, ob, pad=6.0)
                if ov > 0:
                    score += 5000.0 + 3.0 * ov

            # Penalize covering stop dots
            for pt_x, pt_y in stop_px_pts:
                if (cand_box[0] - 5 <= pt_x <= cand_box[2] + 5) and (cand_box[1] - 5 <= pt_y <= cand_box[3] + 5):
                    score += 95.0

            # Slight preference for outward placement away from dense centroid
            if score < best_score:
                best_score = score
                best_cfg = (dx, dy, ha, va)
                best_ext = cand_box
                if score < 6.0:
                    break

        probe.remove()

        if best_cfg is None:
            # Fallback clamped toward panel center
            cx_disp, cy_disp = 0.5 * (px0 + px1), 0.5 * (py0 + py1)
            dx = 14.0 if anchor_disp[0] < cx_disp else -14.0
            dy = 10.0 if anchor_disp[1] < cy_disp else -10.0
            ha = "left" if dx > 0 else "right"
            va = "bottom" if dy > 0 else "top"
            best_cfg = (dx, dy, ha, va)

        dx, dy, ha, va = best_cfg
        use_leader = math.hypot(dx, dy) >= 15.0
        ann = ax.annotate(
            text_str,
            xy=(sx, sy),
            xytext=(dx, dy),
            textcoords="offset points",
            ha=ha,
            va=va,
            fontsize=8.6,
            fontweight="bold",
            color=TEXT,
            zorder=8.2,
            arrowprops=(
                dict(arrowstyle="-", color=MUTED, lw=0.85, alpha=0.80, shrinkA=1, shrinkB=4)
                if use_leader else None
            ),
            path_effects=[pe.withStroke(linewidth=3.8, foreground=BG)],
        )
        bb_final = ann.get_window_extent(renderer=renderer)
        occupied_boxes_px.append((float(bb_final.x0), float(bb_final.y0), float(bb_final.x1), float(bb_final.y1)))
        # Highlight key stop ring
        ax.scatter([sx], [sy], s=110, facecolors="none", edgecolors=TEXT, linewidths=1.1, alpha=0.85, zorder=5.0)


def draw_map_legend(
    ax,
    cmap: LinearSegmentedColormap,
    days: int,
    unit_label: str,
    corner: str = "bottom-left",
    has_return: bool = False,
    has_gems: bool = False,
) -> Tuple[float, float, float, float]:
    """Draw a compact route/stop legend with a Start -> Finish day color ramp."""
    w = 0.255
    extra_h = (0.026 if has_return else 0.0) + (0.026 if has_gems else 0.0)
    h = 0.128 + extra_h
    x0 = 0.022 if "left" in corner else (0.978 - w)
    y0 = 0.024 if "bottom" in corner else (0.976 - h)

    ax.add_patch(FancyBboxPatch(
        (x0, y0), w, h,
        boxstyle="round,pad=0,rounding_size=0.012",
        transform=ax.transAxes,
        facecolor=BG, edgecolor=BORDER, linewidth=0.8, alpha=0.93, zorder=8.8,
    ))

    # Gradient bar: Day 1 -> Day N
    top_y = y0 + h - 0.024
    ax.text(x0 + 0.014, top_y, "ROUTE & DAY ORDER", transform=ax.transAxes,
            fontsize=6.8, fontweight="bold", color=GOLD, ha="left", va="center", zorder=9.0)

    bar_y = top_y - 0.027
    bar_x0, bar_x1 = x0 + 0.048, x0 + w - 0.052
    n_seg = 48
    bx = np.linspace(bar_x0, bar_x1, n_seg + 1)
    for k in range(n_seg):
        ax.add_patch(Rectangle(
            (bx[k], bar_y - 0.0055), bx[k + 1] - bx[k] + 0.0005, 0.011,
            transform=ax.transAxes, facecolor=cmap(k / max(n_seg - 1, 1)), edgecolor="none", zorder=9.0,
        ))
    ax.text(x0 + 0.014, bar_y, "D1", transform=ax.transAxes, fontsize=6.5, fontweight="bold",
            color=to_hex(cmap(0.0)), ha="left", va="center", zorder=9.0)
    ax.text(x0 + w - 0.014, bar_y, f"D{days}", transform=ax.transAxes, fontsize=6.5, fontweight="bold",
            color=to_hex(cmap(1.0)), ha="right", va="center", zorder=9.0)

    row1_y = bar_y - 0.030
    ax.scatter([x0 + 0.024], [row1_y], transform=ax.transAxes, s=38, c=[to_hex(cmap(0.25))],
               edgecolors=BG, linewidths=0.8, zorder=9.1)
    ax.text(x0 + 0.040, row1_y, f"Mapped {unit_label[:-1] if unit_label == 'stops' else 'city'}",
            transform=ax.transAxes, fontsize=6.6, color=TEXT, ha="left", va="center", zorder=9.0)

    ax.scatter([x0 + 0.142], [row1_y], transform=ax.transAxes, s=115, c=[to_hex(cmap(0.65))],
               edgecolors=BG, linewidths=1.2, zorder=9.1)
    ax.text(x0 + 0.142, row1_y, "5", transform=ax.transAxes, fontsize=5.8, fontweight="bold",
            color=BG, ha="center", va="center", zorder=9.2)
    ax.text(x0 + 0.160, row1_y, "Day badge", transform=ax.transAxes, fontsize=6.6, color=TEXT,
            ha="left", va="center", zorder=9.0)

    row2_y = row1_y - 0.027
    ax.scatter([x0 + 0.024], [row2_y], transform=ax.transAxes, s=38, c=[to_hex(cmap(0.8))],
               edgecolors=BG, linewidths=0.8, zorder=9.1)
    ax.scatter([x0 + 0.024], [row2_y], transform=ax.transAxes, s=88, facecolors="none",
               edgecolors=TEXT, linewidths=1.0, zorder=9.1)
    ax.text(x0 + 0.040, row2_y, "Key labeled stop", transform=ax.transAxes,
            fontsize=6.6, color=MUTED, ha="left", va="center", zorder=9.0)

    cur_y = row2_y
    if has_return:
        cur_y -= 0.025
        ax.plot([x0 + 0.015, x0 + 0.035], [cur_y, cur_y], transform=ax.transAxes,
                color=to_hex(cmap(0.95)), lw=1.6, linestyle=(0, (4, 3)), zorder=9.1)
        ax.text(x0 + 0.042, cur_y, "Return rail/air leg to Rome", transform=ax.transAxes,
                fontsize=6.4, color=MUTED, ha="left", va="center", zorder=9.0)
    if has_gems:
        cur_y -= 0.025
        ax.scatter([x0 + 0.024], [cur_y], transform=ax.transAxes, marker="D", s=26,
                   c="#b283f8", edgecolors=BG, linewidths=0.7, zorder=9.1)
        ax.text(x0 + 0.040, cur_y, "Hidden gem landmark", transform=ax.transAxes,
                fontsize=6.4, color=MUTED, ha="left", va="center", zorder=9.0)

    return (x0, y0, x0 + w, y0 + h)


def draw_colorado_locator_inset(fig, map_rect: List[float], corridor_lons: Sequence[float], corridor_lats: Sequence[float]) -> Tuple[float, float, float, float]:
    """Add a compact US-state locator inset in the bottom-right corner of the Colorado map panel."""
    iw = 0.145 * map_rect[2] / 0.595 * 0.595  # in figure fraction
    ih = 0.145
    ix = map_rect[0] + map_rect[2] - iw - 0.012
    iy = map_rect[1] + 0.016
    ax_in = fig.add_axes([ix, iy, iw, ih], zorder=9)
    ax_in.set_facecolor(OCEAN)
    for sp in ax_in.spines.values():
        sp.set_color(LAND_EDGE)
        sp.set_linewidth(0.85)

    proj_in = (-105.55, 39.0, 37.0, 41.0)
    lon_b, lat_b = (-110.2, -101.0), (36.3, 41.7)
    x_c, y_c = lcc([lon_b[0], lon_b[1], lon_b[0], lon_b[1]], [lat_b[0], lat_b[0], lat_b[1], lat_b[1]], *proj_in)
    ax_in.set_xlim(float(np.min(x_c)), float(np.max(x_c)))
    ax_in.set_ylim(float(np.min(y_c)), float(np.max(y_c)))
    ax_in.set_aspect("equal", adjustable="box")
    ax_in.set_xticks([])
    ax_in.set_yticks([])

    other_patches, co_patches = [], []
    for feat in STATES["features"]:
        st_name = feat["properties"].get("name", "")
        for ring in rings(feat["geometry"]):
            arr = np.asarray(ring, dtype=float)
            if len(arr) < 4 or arr[:, 0].max() - arr[:, 0].min() > 100:
                continue
            x, y = lcc(arr[:, 0], arr[:, 1], *proj_in)
            poly = Polygon(np.column_stack([x, y]), closed=True)
            if st_name == "Colorado":
                co_patches.append(poly)
            else:
                other_patches.append(poly)
    ax_in.add_collection(PatchCollection(other_patches, facecolor="#1d233c", edgecolor=LAND_EDGE, linewidth=0.55, zorder=1))
    ax_in.add_collection(PatchCollection(co_patches, facecolor=LAND, edgecolor=GOLD, linewidth=0.95, zorder=2))

    bx, by = lcc(
        [min(corridor_lons) - 0.15, max(corridor_lons) + 0.15, max(corridor_lons) + 0.15, min(corridor_lons) - 0.15, min(corridor_lons) - 0.15],
        [min(corridor_lats) - 0.12, min(corridor_lats) - 0.12, max(corridor_lats) + 0.12, max(corridor_lats) + 0.12, min(corridor_lats) - 0.12],
        *proj_in,
    )
    ax_in.plot(bx, by, color=GOLD, lw=1.5, zorder=4)
    sx, sy = lcc(corridor_lons, corridor_lats, *proj_in)
    ax_in.scatter(sx, sy, s=5, c="#54a8f5", zorder=5)

    for lbl, lo, la in [("COLORADO", -106.3, 38.7), ("WY", -106.0, 41.32), ("NM", -106.0, 36.62), ("UT", -109.55, 39.0), ("KS", -101.55, 38.7), ("NE", -101.55, 41.25)]:
        lx, ly = lcc([lo], [la], *proj_in)
        ax_in.text(
            float(lx[0]), float(ly[0]), lbl,
            fontsize=(6.2 if lbl == "COLORADO" else 5.2),
            fontweight="bold",
            color=(TEXT if lbl == "COLORADO" else DIM),
            ha="center", va="center", zorder=6,
            path_effects=[pe.withStroke(linewidth=2.0, foreground="#121629")],
        )
    ax_in.text(
        0.04, 0.94, "US STATE CONTEXT",
        transform=ax_in.transAxes, fontsize=5.8, fontweight="bold", color=GOLD,
        ha="left", va="top", zorder=7,
        path_effects=[pe.withStroke(linewidth=2.2, foreground="#121629")],
    )

    # Convert inset figure coords to map-axes fraction bbox so labels avoid it
    mx0, my0, mw, mh = map_rect
    return ((ix - mx0) / mw, (iy - my0) / mh, (ix + iw - mx0) / mw, (iy + ih - my0) / mh)


def _fit_text_to_px_width(fig, ax, text: str, max_px: float, fontsize: float, fontweight: str = "normal") -> str:
    """Ensure a string never exceeds `max_px` in rendered pixel width."""
    renderer = fig.canvas.get_renderer()
    probe = ax.text(0, 0, text, fontsize=fontsize, fontweight=fontweight)
    w = probe.get_window_extent(renderer=renderer).width
    if w <= max_px:
        probe.remove()
        return text

    # Trim cleanly on " · " segments first if available, else word boundary
    candidate = text
    while len(candidate) > 12:
        if " · " in candidate:
            candidate = candidate.rsplit(" · ", 1)[0]
            clean_cand = candidate.rstrip(" ,;·-")
            # When >= 2 complete " · "-delimited items remain, omit ellipsis for clean editorial copy
            trial = clean_cand if " · " in clean_cand else (clean_cand + "…")
        else:
            candidate = candidate.rsplit(" ", 1)[0]
            trial = candidate.rstrip(" ,;·-") + "…"
        probe.set_text(trial)
        if probe.get_window_extent(renderer=renderer).width <= max_px:
            probe.remove()
            return trial
    probe.remove()
    return candidate


def render_poster(trip: Dict[str, Any]) -> pathlib.Path:
    W, H, DPI = 20.0, 13.0, 240
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    fig.add_artist(Rectangle((0, 0), 1, 1, transform=fig.transFigure, facecolor=BG, zorder=-10))

    cmap = make_cmap(trip["ramp"])
    days = int(trip["days"])
    stops = trip["stops"]
    unit = trip["unit_label"]

    # ------------------------------------------------------------------ 1. HEADER (top ~12%)
    fig.text(
        0.025, 0.968,
        "BIERREISEN   ·   ROUTE & ITINERARY SHEET",
        fontsize=8.6, fontweight="bold", color=DIM, ha="left", va="center",
    )
    fig.text(
        0.025, 0.935,
        trip["title"],
        fontsize=27.5, fontweight="bold", color=GOLD, ha="left", va="center",
    )
    facts_line = f"{days} days   ·   {len(stops)} {unit}   ·   {trip['countries']}"
    fig.text(
        0.025, 0.900,
        facts_line,
        fontsize=11.8, fontweight="bold", color=TEXT, ha="left", va="center",
    )

    fig.text(
        0.975, 0.936,
        trip["route_summary"],
        fontsize=9.4, fontweight="bold", color=to_hex(cmap(0.35)), ha="right", va="center",
    )
    fig.text(
        0.975, 0.900,
        f"Source dossier: AI-suggested-trips/{trip['source_file']}",
        fontsize=9.0, color=MUTED, ha="right", va="center",
    )
    fig.add_artist(plt.Line2D([0.025, 0.975], [0.880, 0.880], color=GOLD, lw=1.1, alpha=0.65))

    # ------------------------------------------------------------------ 2. MAP PANEL (left ~62%)
    map_rect = [0.025, 0.082, 0.595, 0.784]
    ax_map = fig.add_axes(map_rect)
    ax_map.set_facecolor(OCEAN)
    for sp in ax_map.spines.values():
        sp.set_color(BORDER)
        sp.set_linewidth(1.0)

    all_lats = [s["lat"] for s in stops] + [p[0] for p in trip["path"]]
    all_lons = [s["lon"] for s in stops] + [p[1] for p in trip["path"]]
    if trip.get("return_path"):
        all_lats += [p[0] for p in trip["return_path"]]
        all_lons += [p[1] for p in trip["return_path"]]

    proj, xlim, ylim, lon_win, lat_win = fit_lcc_window(
        all_lons, all_lats, map_rect[2] * W, map_rect[3] * H, pad_each_side=0.095
    )
    ax_map.set_xlim(*xlim)
    ax_map.set_ylim(*ylim)
    ax_map.set_aspect("equal", adjustable="box")
    ax_map.set_xticks([])
    ax_map.set_yticks([])

    # Legend, scale bar & optional state locator inset (drawn onto high zorder; boxes used to skip graticule ticks)
    forbidden_axes_boxes = []
    leg_box = draw_map_legend(
        ax_map, cmap, days, unit,
        corner=trip.get("legend_corner", "bottom-left"),
        has_return=bool(trip.get("return_path")),
        has_gems=bool(trip.get("gems")),
    )
    forbidden_axes_boxes.append(leg_box)

    sc_box = draw_scale_bar(ax_map, proj, corner=trip.get("scale_corner", "bottom-right"))
    forbidden_axes_boxes.append(sc_box)

    if trip.get("state_inset"):
        in_box = draw_colorado_locator_inset(fig, map_rect, all_lons, all_lats)
        forbidden_axes_boxes.append(in_box)

    draw_graticule(ax_map, proj, lon_win, lat_win, xlim, ylim, skip_axes_boxes=forbidden_axes_boxes)
    draw_land(ax_map, proj, lon_win, lat_win)
    if trip.get("is_us"):
        draw_states(ax_map, proj)

    # Subtle geographic watermarks
    for w_text, w_lon, w_lat in trip.get("watermarks", []):
        wx, wy = lcc([w_lon], [w_lat], *proj)
        wx_f, wy_f = float(wx[0]), float(wy[0])
        if xlim[0] + 0.05 * (xlim[1] - xlim[0]) < wx_f < xlim[1] - 0.05 * (xlim[1] - xlim[0]) and ylim[0] + 0.05 * (ylim[1] - ylim[0]) < wy_f < ylim[1] - 0.05 * (ylim[1] - ylim[0]):
            ax_map.text(
                wx_f, wy_f, w_text,
                fontsize=8.2, fontweight="bold", color="#4f5b87", alpha=0.55,
                ha="center", va="center", zorder=1.6,
            )

    # Route polyline(s)
    pxs, pys = lcc([p[1] for p in trip["path"]], [p[0] for p in trip["path"]], *proj)
    ret_xy = None
    if trip.get("return_path"):
        rxs, rys = lcc([p[1] for p in trip["return_path"]], [p[0] for p in trip["return_path"]], *proj)
        ret_xy = (rxs, rys)
    draw_gradient_route(ax_map, pxs, pys, cmap, return_xy=ret_xy)

    # Optional secondary hidden-gem markers (Italy Classic)
    if trip.get("gems"):
        gx, gy = lcc([g["lon"] for g in trip["gems"]], [g["lat"] for g in trip["gems"]], *proj)
        ax_map.scatter(gx, gy, marker="D", s=34, c="#b283f8", alpha=0.85, edgecolors=BG, linewidths=0.8, zorder=3.9)

    # Stop dots colored by day
    sx, sy = lcc([s["lon"] for s in stops], [s["lat"] for s in stops], *proj)
    stop_cols = [day_color(cmap, int(s.get("day", 1)), days) for s in stops]
    ax_map.scatter(sx, sy, s=110, c=stop_cols, alpha=0.22, edgecolors="none", zorder=4.0)
    ax_map.scatter(sx, sy, s=50, c=stop_cols, alpha=0.95, edgecolors=BG, linewidths=1.0, zorder=4.3)

    # Force initial draw so renderer & window extents are exact
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    map_win = ax_map.get_window_extent(renderer=renderer)
    panel_bbox_px = (float(map_win.x0), float(map_win.y0), float(map_win.x1), float(map_win.y1))

    forbidden_px: List[Tuple[float, float, float, float]] = []
    for ax0, ay0, ax1, ay1 in forbidden_axes_boxes:
        p0 = ax_map.transAxes.transform((ax0, ay0))
        p1 = ax_map.transAxes.transform((ax1, ay1))
        forbidden_px.append((float(p0[0]), float(p0[1]), float(p1[0]), float(p1[1])))

    occupied_px: List[Tuple[float, float, float, float]] = list(forbidden_px)
    stop_px_pts = [tuple(map(float, ax_map.transData.transform((float(sx[i]), float(sy[i]))))) for i in range(len(stops))]

    # Numbered day badges
    if trip.get("city_badges"):
        # Pill day-range badges near each city
        for i, s in enumerate(stops):
            badge_txt = s.get("badge")
            if not badge_txt:
                continue
            bcol = day_color(cmap, int(s.get("day", 1)), days)
            # Offset badge slightly above-left/right so city dot stays visible
            off_x = -24 if s["name"] in ("Pisa", "Milan", "Milano", "Roma (FCO)") else 22
            off_y = -18 if s["name"] in ("Pisa", "Roma (FCO)", "Rome (FCO)") else 16
            t_b = ax_map.annotate(
                badge_txt,
                xy=(float(sx[i]), float(sy[i])),
                xytext=(off_x, off_y),
                textcoords="offset points",
                fontsize=7.2, fontweight="bold", color=BG,
                ha="center", va="center", zorder=6.5,
                bbox=dict(boxstyle="round,pad=0.28,rounding_size=0.45", facecolor=bcol, edgecolor=BG, linewidth=1.2),
                arrowprops=dict(arrowstyle="-", color=bcol, lw=1.0, alpha=0.85, shrinkA=0, shrinkB=4),
            )
            bb = t_b.get_window_extent(renderer=renderer)
            occupied_px.append((float(bb.x0) - 4, float(bb.y0) - 4, float(bb.x1) + 4, float(bb.y1) + 4))
    else:
        # Compute per-day anchor coordinates (1..days)
        day_anchors_data: List[Tuple[int, float, float]] = []
        overrides = trip.get("day_overrides", {})
        for d in range(1, days + 1):
            if d in overrides:
                ola, olo = overrides[d]
                ox, oy = lcc([olo], [ola], *proj)
                day_anchors_data.append((d, float(ox[0]), float(oy[0])))
                continue
            d_stops = [i for i, s in enumerate(stops) if int(s.get("day", 0)) == d]
            if d_stops:
                mx = float(np.mean([sx[i] for i in d_stops]))
                my = float(np.mean([sy[i] for i in d_stops]))
                day_anchors_data.append((d, mx, my))
            elif len(pxs) >= 2:
                idx = min(len(pxs) - 1, round((d - 1) / max(days - 1, 1) * (len(pxs) - 1)))
                day_anchors_data.append((d, float(pxs[idx]), float(pys[idx])))

        raw_px = [tuple(map(float, ax_map.transData.transform((mx, my)))) for _, mx, my in day_anchors_data]
        repelled_px = _repel_points_px(raw_px, min_dist_px=64.0, panel_bbox_px=panel_bbox_px, forbidden_px=forbidden_px)

        for idx_b, (d, orig_x, orig_y) in enumerate(day_anchors_data):
            rx_px, ry_px = repelled_px[idx_b]
            bx_d, by_d = ax_map.transData.inverted().transform((rx_px, ry_px))
            bcol = day_color(cmap, d, days)
            if math.hypot(rx_px - raw_px[idx_b][0], ry_px - raw_px[idx_b][1]) > 22.0:
                ax_map.plot([orig_x, bx_d], [orig_y, by_d], color=bcol, lw=1.0, alpha=0.75, zorder=5.8)
            ax_map.scatter([bx_d], [by_d], s=265, c=[bcol], edgecolors=BG, linewidths=1.8, zorder=6.4)
            ax_map.text(
                bx_d, by_d, str(d),
                fontsize=7.6, fontweight="bold", color=BG,
                ha="center", va="center", zorder=6.6,
            )
            occupied_px.append((rx_px - 28.0, ry_px - 28.0, rx_px + 28.0, ry_px + 28.0))

    # Place 6-10 haloed key stop labels
    by_name = {s["name"]: (float(sx[i]), float(sy[i]), day_color(cmap, int(s.get("day", 1)), days)) for i, s in enumerate(stops)}
    label_specs: List[Tuple[str, float, float, str]] = []
    for kname in trip["key_stops"]:
        if kname in by_name:
            kx, ky, kcol = by_name[kname]
            label_specs.append((kname, kx, ky, kcol))
    for ename, ela, elo in trip.get("extra_labels", []):
        ex, ey = lcc([elo], [ela], *proj)
        label_specs.append((ename, float(ex[0]), float(ey[0]), to_hex(cmap(0.0))))

    place_halo_labels(fig, ax_map, label_specs, stop_px_pts, occupied_px, panel_bbox_px)

    # ------------------------------------------------------------------ 3. DAY LEDGER (right ~34%)
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

    ax_led.text(0.036, 0.964, "DAY-BY-DAY LEDGER", fontsize=10.5, fontweight="bold",
                color=GOLD, ha="left", va="center", zorder=2)
    ax_led.text(0.964, 0.964, f"{len(trip['day_ledger'])} DAYS  ·  DOSSIER ITINERARY",
                fontsize=8.2, fontweight="bold", color=MUTED, ha="right", va="center", zorder=2)
    ax_led.plot([0.030, 0.970], [0.934, 0.934], color=BORDER, lw=0.9, zorder=2)

    rows = trip["day_ledger"]
    n_rows = len(rows)
    top_band = 0.922
    bot_band = 0.016
    row_h = (top_band - bot_band) / max(n_rows, 1)

    led_win = ax_led.get_window_extent(renderer=renderer)
    max_text_px = float(led_win.width) * 0.822

    place_fs = 9.8 if n_rows >= 14 else (10.3 if n_rows >= 12 else 11.0)
    hl_fs = 8.2 if n_rows >= 14 else (8.6 if n_rows >= 12 else 9.1)
    chip_fs = 8.4 if n_rows >= 14 else 9.0

    for idx_r, row in enumerate(rows):
        dnum = int(row["day"])
        yc = top_band - (idx_r + 0.5) * row_h
        y_low = yc - 0.45 * row_h
        rcol = day_color(cmap, dnum, days)

        if idx_r % 2 == 0:
            ax_led.add_patch(FancyBboxPatch(
                (0.020, y_low), 0.960, 0.90 * row_h,
                boxstyle="round,pad=0,rounding_size=0.008",
                facecolor=PANEL_ALT, edgecolor="none", alpha=0.65, zorder=1,
            ))

        # Coloured day chip
        chip_h = min(0.62 * row_h, 0.044)
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

        place_str = _fit_text_to_px_width(fig, ax_led, row["place"], max_text_px, place_fs, fontweight="bold")
        hl_str = _fit_text_to_px_width(fig, ax_led, row["highlights"], max_text_px, hl_fs, fontweight="normal")

        ax_led.text(
            0.126, yc + 0.19 * row_h, place_str,
            fontsize=place_fs, fontweight="bold", color=TEXT,
            ha="left", va="center", zorder=3,
        )
        ax_led.text(
            0.126, yc - 0.21 * row_h, hl_str,
            fontsize=hl_fs, color=MUTED,
            ha="left", va="center", zorder=3,
        )

    # ------------------------------------------------------------------ 4. FOOTER
    fig.add_artist(plt.Line2D([0.025, 0.975], [0.066, 0.066], color=GOLD, lw=0.95, alpha=0.60))

    fig.text(0.025, 0.044, "SIGNATURE BEERS", fontsize=8.4, fontweight="bold", color=GOLD, ha="left", va="center")
    fig.text(0.118, 0.044, trip["signature_beers"], fontsize=8.6, color=TEXT, ha="left", va="center")

    fig.text(0.025, 0.020, "SEASON & LOGISTICS", fontsize=8.0, fontweight="bold", color=MUTED, ha="left", va="center")
    fig.text(0.118, 0.020, trip["season_budget"], fontsize=8.1, color=MUTED, ha="left", va="center")

    fig.text(
        0.975, 0.020,
        "Lambert Conformal Conic  ·  Natural Earth 1:50m",
        fontsize=7.6, color=DIM, ha="right", va="center",
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_png = OUT_DIR / f"{trip['slug']}.png"
    out_json = OUT_DIR / f"{trip['slug']}.json"

    sidecar = {
        "slug": trip["slug"],
        "source_file": trip["source_file"],
        "title": trip["title"],
        "days": trip["days"],
        "countries": trip["countries"],
        "stops": [
            {"lat": s["lat"], "lon": s["lon"], "name": s["name"], **({"day": s["day"]} if "day" in s else {})}
            for s in trip["stops"]
        ],
        "path": trip["path"],
        "day_ledger": trip["day_ledger"],
        "signature_beers": trip["signature_beers"],
        "season_budget": trip["season_budget"],
    }
    out_json.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    fig.savefig(
        out_png,
        dpi=DPI,
        facecolor=BG,
        metadata={"Software": "bierreisen/make_trip_maps.py", "Creation Time": None},
    )
    plt.close(fig)
    return out_png


def main() -> None:
    extractors = [
        extract_uk,
        extract_belgium,
        extract_bavaria_bohemia,
        extract_colorado,
        extract_florida,
        extract_italy_grand,
        extract_italy_classic,
    ]
    for fn in extractors:
        trip = fn()
        out_png = render_poster(trip)
        kb = out_png.stat().st_size // 1024
        print(f"wrote {out_png.relative_to(ROOT)}  ({kb} KB, {trip['days']} days, {len(trip['stops'])} {trip['unit_label']})")


if __name__ == "__main__":
    main()
