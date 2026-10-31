#!/usr/bin/env python3
"""Inject the EN / PT-BR / DE runtime into the generated 2027 planner pages.

The catalog (2027/i18n/catalog.json) is keyed semantically but every entry carries the exact
English string the template renders, so the page can be translated at runtime by matching the
English text of a node against the catalog. This keeps the generator untouched: build_html.py
emits English exactly as before, and this script appends the switcher + catalog + translator.
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
DIR_2027 = HERE.parent
CATALOG_PATH = DIR_2027 / "i18n" / "catalog.json"

PAGES = {
    "v1": DIR_2027 / "2027-bier-reisen.html",
    "v2": DIR_2027 / "v2" / "2027-bier-reisen-v2.html",
    "v3": DIR_2027 / "v3" / "2027-bier-reisen-v3.html",
}

START = "<!-- i18n:start -->"
END = "<!-- i18n:end -->"

CSS = """<style id="i18n-style">
.lang-switch{display:flex;gap:.35rem;align-items:center;justify-content:center;margin:1rem auto 0;font-size:.85rem}
.lang-switch span{color:#9aa5bc;letter-spacing:.08em;font-size:.72rem;text-transform:uppercase;margin-right:.35rem}
.lang-switch button{background:transparent;border:1px solid #2a3050;color:#9aa5bc;border-radius:999px;
  padding:.32rem .78rem;font:inherit;font-weight:600;letter-spacing:.04em;cursor:pointer;transition:all .18s}
.lang-switch button:hover{border-color:#e6a817;color:#e6a817}
.lang-switch button.active{background:#e6a817;border-color:#e6a817;color:#0b0c15}
</style>"""

CHIPS = """<div class="lang-switch" role="group" aria-label="Language / Idioma / Sprache">
<span>Language</span>
<button type="button" data-lang="en">EN</button>
<button type="button" data-lang="pt-BR">PT</button>
<button type="button" data-lang="de">DE</button>
</div>"""

RUNTIME_JS = (HERE / "i18n_runtime.js").read_text(encoding="utf-8")
RUNTIME = '<script id="i18n-runtime">' + RUNTIME_JS + "</script>"



def escape_json_for_script(obj) -> str:
    payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def norm_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+([,.;:!?)\]])", r"\1", s)
    s = re.sub(r"\(\s+", "(", s)
    return s.strip()


def build_map(catalog: dict) -> dict:
    """English text -> {pt, de}. First key wins on duplicates."""
    out: dict[str, dict] = {}
    dupes = 0
    for _key, row in catalog.items():
        en = row.get("en")
        if not en:
            continue
        en_norm = norm_text(en)
        if not en_norm:
            continue
        if en_norm in out:
            dupes += 1
            continue
        out[en_norm] = {"pt": row.get("pt", ""), "de": row.get("de", "")}
    if dupes:
        print(f"  (skipped {dupes} duplicate English strings)")
    return out


def inject(page: pathlib.Path, mapping: dict) -> None:
    html = page.read_text(encoding="utf-8")
    if START in html and END in html:
        html = re.sub(re.escape(START) + r".*?" + re.escape(END), "", html, flags=re.S)
    html = html.replace(CHIPS, "")
    block = "\n".join([
        START, CSS,
        '<script id="i18n-catalog" type="application/json">' + escape_json_for_script(mapping) + "</script>",
        RUNTIME, END,
    ])
    if "</header>" not in html or "</body>" not in html:
        raise SystemExit(f"{page}: unexpected structure")
    html = html.replace("</header>", CHIPS + "\n</header>", 1)
    html = html.replace("</body>", block + "\n</body>", 1)
    page.write_text(html, encoding="utf-8")


def report(page: pathlib.Path, mapping: dict) -> None:
    """Rough coverage: how many of the page's text runs exist in the catalog."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(page.read_text(encoding="utf-8"), "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    strings = [re.sub(r"\s+", " ", s).strip() for s in soup.stripped_strings]
    strings = [s for s in strings if s]
    hit = [s for s in strings if s in mapping]
    print(f"  {page.name}: {len(hit)}/{len(strings)} text runs covered ({100*len(hit)/max(len(strings),1):.0f}%), "
          f"catalog {len(mapping)} entries")
    missing = [s for s in strings if s not in mapping and len(s) > 3]
    for s in missing[:12]:
        print("    miss:", s[:90])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("pages", nargs="*", default=None)
    args = ap.parse_args()

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    mapping = build_map(catalog)
    print(f"catalog: {len(catalog)} keys -> {len(mapping)} English strings")

    targets = args.pages or list(PAGES)
    for name in targets:
        page = PAGES[name]
        if args.report:
            report(page, mapping)
        else:
            inject(page, mapping)
            print(f"injected {page.relative_to(DIR_2027)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
