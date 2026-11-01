# DESIGN.md — the catalog page

Scope: `index.html` and `404.html`. The year dossiers have their own internal system (dense, data-first);
this file governs the public front door only.

## Surface

**Mode: Experience.** The archive is the artifact; the interface recedes. A visitor should feel the
accumulation of five trips before they read a single route.

## Ground and colour

| Token | Value | Use |
|---|---|---|
| `--bg` | `#0b0c15` | page ground |
| `--bg-raise` | `#101224` | footer band |
| `--rule` / `--rule-soft` | `#262c48` / `rgba(38,44,72,.62)` | hairlines only; no card borders |
| `--gold` | `#e6a817` | the single accent: years, links, the 2027 marker |
| `--text` | `#eef1f6` | headings and body |
| `--muted` | `#a8b2c6` | routes, secondary copy |
| `--dim` | `#8d97ad` | facts, meta, placeholders — the floor at 4.5:1 |

No second accent. No coloured shadows. Depth comes from a 1px rule and a scale change, never a glow.

## Type

- **Display:** `Charter, "Iowan Old Style", Palatino, Georgia, serif` — roman, never italic in the hero.
- **Text/UI:** `"Avenir Next", "Segoe UI", system-ui` at 17px/1.65.
- Display is set tight (`-.021em`) and large (`clamp(2.5rem, 6.2vw, 5rem)`); body measure is capped at 66ch.

## Composition

- **Ledger, not cards.** Six trips as full-width rows: 300px poster, then year + status, serif title,
  route, blurb, tabular facts, two links. Hairlines separate entries; nothing is boxed.
- **Shelf, not grid.** The six drafted routes sit below at a smaller scale, muted, three across.
  Subordination is the point: taken trips lead, drafts follow.
- **No eyebrow above the hero**, no metric row. The headline carries the page; the numbers live inside
  a sentence.

## Motion

One authored moment: entries fade and rise 14px on intersection, staggered 70ms, cubic-bezier(.16,1,.3,1).
Posters scale 1.035 on hover over 700ms. Everything collapses to static under `prefers-reduced-motion`.

## Browser surfaces

`::selection` gold on ink, `caret-color` gold, themed scrollbars, `text-underline-offset: .18em`,
tabular numerals in every fact and tally, 2px gold `:focus-visible` ring at 3px offset.

## Rules that must not regress

1. No kicker/eyebrow above any heading.
2. No hero metric block; numbers go inside prose.
3. No uniform card grid as the page structure.
4. No coloured or zero-offset shadows.
5. Body and placeholder text never below 4.5:1.
6. Emoji never stand in for an icon; the mark is drawn SVG (`assets/favicon.svg`).
7. `index.html` is generated — edit `scripts/index_template.html` and rebuild.

Gate: `npx impeccable@latest detect index.html --no-advisory` must exit 0.
