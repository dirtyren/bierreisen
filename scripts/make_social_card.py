#!/usr/bin/env python3
"""Render the Open Graph / social card (1200x630) for the catalog."""
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "og-card.png"

BG, GOLD, TEXT, MUTED = "#0b0c15", "#e6a817", "#eef1f6", "#9aa5bc"

fig = plt.figure(figsize=(12, 6.3), dpi=100)
fig.patch.set_facecolor(BG)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1200)
ax.set_ylim(0, 630)
ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1200, 630, facecolor=BG, edgecolor="none"))

# gold rule + mark
ax.plot([72, 72], [150, 470], color=GOLD, lw=3, solid_capstyle="butt")

ax.text(112, 462, "Bier Reisen", fontsize=64, color=TEXT, fontweight="bold",
        family="DejaVu Serif", va="center")
ax.text(112, 372, "Five beer trips taken.", fontsize=40, color=GOLD,
        family="DejaVu Serif", va="center")
ax.text(112, 312, "One being planned.", fontsize=40, color=GOLD,
        family="DejaVu Serif", va="center")

ax.text(112, 214, "Itineraries · route maps · brewery rankings · every distance measured",
        fontsize=19, color=MUTED, family="DejaVu Sans", va="center")

ax.text(112, 96, "renreisen.duckdns.org", fontsize=19, color=TEXT,
        family="DejaVu Sans", va="center", alpha=.9)

fig.savefig(OUT, dpi=100, facecolor=BG)
plt.close(fig)
print(f"wrote {OUT.relative_to(ROOT)} · {OUT.stat().st_size // 1024} KB")
