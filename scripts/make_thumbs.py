#!/usr/bin/env python3
"""Build web-sized thumbnails for index.html from the route posters.

Writes 960px-wide JPEGs into assets/thumbs/ (quality 82) so the catalog page
stays light: twelve 4800px PNGs would be ~7 MB.
"""
import pathlib

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "thumbs"

POSTERS = {
    "2019": ROOT / "2019/assets/2019-route-map.png",
    "2020": ROOT / "2020/assets/2020-route-map.png",
    "2021": ROOT / "2021/assets/2021-route-map.png",
    "2024": ROOT / "2024/assets/2024-route-map.png",
    "2026": ROOT / "2026/assets/2026-route-map.png",
    "2027": ROOT / "2027/assets/2027-route-map.png",
    "2027-v2": ROOT / "2027/v2/assets/2027-route-map-v2.png",
    "2027-v3": ROOT / "2027/v3/assets/2027-route-map-v3.png",
    "uk": ROOT / "assets/trips/uk-beer-pilgrimage.png",
    "belgian": ROOT / "assets/trips/belgian-beer-pilgrimage.png",
    "bavaria-bohemia": ROOT / "assets/trips/bavaria-bohemia.png",
    "colorado": ROOT / "assets/trips/colorado-craft-beer.png",
    "florida": ROOT / "assets/trips/florida-brewery-trail.png",
    "italy-grand-tour": ROOT / "assets/trips/italy-switzerland-grand-tour.png",
    "italy-classic": ROOT / "assets/trips/italy-switzerland-classic.png",
}

WIDTH = 960
HERO = {"hero-europe": (ROOT / "assets/maps/europe.png", 1920)}
OUT.mkdir(parents=True, exist_ok=True)

for key, (src, width) in HERO.items():
    im = Image.open(src).convert("RGB")
    h = round(im.height * width / im.width)
    im = im.resize((width, h), Image.LANCZOS)
    dst = OUT / f"{key}.jpg"
    im.save(dst, "JPEG", quality=76, optimize=True, progressive=True)
    print(f"{dst.relative_to(ROOT)}  {width}x{h}  {dst.stat().st_size // 1024} KB")

for key, src in POSTERS.items():
    if not src.exists():
        print(f"skip {key}: {src} missing")
        continue
    im = Image.open(src).convert("RGB")
    h = round(im.height * WIDTH / im.width)
    im = im.resize((WIDTH, h), Image.LANCZOS)
    dst = OUT / f"{key}.jpg"
    im.save(dst, "JPEG", quality=82, optimize=True, progressive=True)
    print(f"{dst.relative_to(ROOT)}  {WIDTH}x{h}  {dst.stat().st_size // 1024} KB")
