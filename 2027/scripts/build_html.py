#!/usr/bin/env python3
"""Build 2027/2027-bier-reisen.html from authoritative 2027/data/route-2027.json."""
from __future__ import annotations

import html
import json
import math
import pathlib
from typing import Any, Dict, List, Tuple

HERE = pathlib.Path(__file__).resolve().parent
DIR_2027 = HERE.parent
DATA_PATH = DIR_2027 / "data" / "route-2027.json"
OUT_HTML = DIR_2027 / "2027-bier-reisen.html"


def esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


def fmt_km_round(km: float) -> str:
    return f"{int(math.floor(km + 0.5)):,}"


def fmt_km_exact(km: float) -> str:
    if abs(km - round(km)) < 1e-6:
        return f"{int(round(km)):,}"
    return f"{km:,.1f}"


def fmt_duration_human(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    if h == 0:
        return f"{m} min"
    return f"{h} h {m:02d}"


def fmt_hmm(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    return f"{h}:{m:02d}"


# City signature beers explicitly specified in the brief
CITY_FAMOUS_BEER: Dict[str, str] = {
    "Bruges": "Flemish red",
    "Ghent": "gruut",
    "Bamberg": "Rauchbier",
    "Sokolov": "Permon IPA 15°",
    "Plzeň": "tank Pilsner",
    "Kout na Šumavě": "Kout 12°",
    "Maxlrain": "Maxlrainer Helles",
    "Andechs": "Doppelbock",
    "Munich": "Helles",
    "Nuremberg": "Rotbier",
}

# Venue-specific house pours grounded strictly in venues[city][i]["note"] + the city's famous style
VENUE_ORDER_LINE: Dict[Tuple[str, str], str] = {
    ("Bruges", "De Halve Maan"): "Brugse Zot blond or Straffe Hendrik quadrupel (city signature: Flemish red)",
    ("Bruges", "De Garre"): "House Tripel 11% — max three per person (city signature: Flemish red)",
    ("Bruges", "'t Brugs Beertje"): "Vintage Belgian bottle or aged Flemish red from the 300+ bottle list",
    ("Bruges", "Café Vlissinghe"): "Classic Belgian abbey pour or Flemish red in the 1515 garden",
    ("Bruges", "Le Trappiste"): "Trappist draught/bottle flight alongside a Bruges Flemish red",
    ("Bruges", "Bourgogne des Flandres"): "Flemish red house beer overlooking the canal",
    ("Ghent", "Gruut Stadsbrouwerij"): "Gruut (Blond, Amber, Brown, White, or Inferno — hop-free herb beer)",
    ("Ghent", "Dok Brewing Company"): "Pils 13 flagship from the 30-tap board (city signature: gruut)",
    ("Ghent", "Stroom Brouwers"): "Belgian-US craft taproom pour (city signature: gruut)",
    ("Ghent", "De Dulle Griet"): "House Max in the yard-glass shoe-basket ritual, or a Ghent gruut",
    ("Ghent", "Het Waterhuis aan de Bierkant"): "Gandavum or Klokke Roeland on the canal terrace (city signature: gruut)",
    ("Ghent", "De Hopduvel"): "Take-home Belgian bottles & local Ghent gruut selection",
    ("Bamberg", "Schlenkerla"): "Rauchbier — beechwood-smoked malt poured straight from oak barrels",
    ("Bamberg", "Spezial"): "Rauchbier — the locals' subtler beechwood smoke",
    ("Bamberg", "Mahr's Bräu"): "'aU' Ungespundetes unfiltered cellar lager (city signature: Rauchbier)",
    ("Bamberg", "Fässla"): "Zwergla dark lager at the brewery tap (city signature: Rauchbier)",
    ("Bamberg", "Greifenklau"): "Fresh Bamberg cellar lager in the hilltop garden (city signature: Rauchbier)",
    ("Bamberg", "Klosterbräu"): "Schwärzla dark lager at Bamberg's 1533 brewery (city signature: Rauchbier)",
    ("Bamberg", "Keesmann"): "Herren Pils — crisp counterpoint to Bamberg's Rauchbier",
    ("Sokolov", "Pivovar Permon"): "Permon IPA 15° and house dark specials on tap",
    ("Plzeň", "Pilsner Urquell"): "Unfiltered, unpasteurised tank Pilsner straight from the cellars",
    ("Plzeň", "U Salzmannů"): "Tank Pilsner (Pilsner Urquell) poured at 1637 pub Pražská 8",
    ("Plzeň", "Na Parkánu"): "Brewery-fresh unpasteurised tank Pilsner next door to Urquell",
    ("Plzeň", "Purkmistr"): "House dark lager at the brewery spa hotel (city signature: tank Pilsner)",
    ("Plzeň", "Pivovar Raven"): "Czech craft IPA, stout, or sour (city signature: tank Pilsner)",
    ("Kout na Šumavě", "Pivovar Kout na Šumavě"): "Kout 12° pale lager — the revived Bohemian Forest cult beer",
    ("Maxlrain", "Schlossbrauerei Maxlrain"): "Maxlrainer Helles (plus Dunkel & Weißbier) in the Bierstube",
    ("Andechs", "Kloster Andechs"): "Doppelbock Dunkel (7.1%) above the Ammersee",
    ("Andechs", "Andechser Hof, Herrsching"): "Andechs Doppelbock Dunkel and full monastery range by the lake",
    ("Munich", "Augustiner-Keller"): "Holzfass Edelstoff & Munich Helles under the chestnut trees",
    ("Munich", "Schneider Bräuhaus"): "Aventinus Weizenbock (city signature: Munich Helles)",
    ("Munich", "Hofbräuhaus"): "Munich Helles in the historic 1589 beer hall",
    ("Munich", "Giesinger Bräu"): "Erhellung unfiltered Helles",
    ("Munich", "ORCA Brau"): "Juicy nano-batch NEIPA (city signature: Munich Helles)",
    ("Munich", "Tilmans Biere"): "Refined small-batch Munich Helles or Pils",
    ("Munich", "Paulaner Nockherberg"): "Munich Helles (and Starkbier tradition above the Isar)",
    ("Nuremberg", "Hausbrauerei Altstadthof"): "Organic Nuremberg Rotbier (plus beer schnapps below the castle)",
    ("Nuremberg", "Schanzenbräu"): "Schanzenbräu Rotbier at the Gostenhof pub",
    ("Nuremberg", "Tucher Mautkeller"): "Tucher Rotbier in the medieval vaulted brewhouse",
    ("Nuremberg", "Zeltner Bierhaus"): "Deepest Nuremberg Rotbier list in the city",
    ("Nuremberg", "Bierwerk Wirtshaus"): "Franconian draughts & Nuremberg Rotbier with Nürnberger sausages",
}

CITY_TO_STOP_ID: Dict[str, str] = {
    "Bruges": "bruges",
    "Ghent": "ghent",
    "Bamberg": "bamberg",
    "Sokolov": "sokolov",
    "Plzeň": "plzen",
    "Kout na Šumavě": "kout",
    "Maxlrain": "maxlrain",
    "Andechs": "andechs",
    "Munich": "munich",
    "Nuremberg": "nuremberg",
}

SHORT_STOP_LABEL: Dict[str, str] = {
    "fra": "FRA",
    "bruges": "Bruges",
    "ghent": "Ghent",
    "bamberg": "Bamberg",
    "sokolov": "Permon (Sokolov)",
    "plzen": "Plzeň",
    "kout": "Kout na Šumavě",
    "maxlrain": "Maxlrain",
    "andechs": "Andechs",
    "munich": "Munich",
    "nuremberg": "Nuremberg",
}

COUNTRY_FLAG: Dict[str, str] = {
    "Germany": "🇩🇪",
    "Belgium": "🇧🇪",
    "Czechia": "🇨🇿",
}

# Style reference metadata keyed to exact (region, style) pairs from route-2027.json
STYLE_DETAILS: Dict[Tuple[str, str], Tuple[str, str, str, str]] = {
    # (color_hex, what_to_expect, abv_band, serving_note)
    ("Belgium", "Flemish red"): (
        "#7c1d24",
        "Oak-foeder aged red-brown ale; tart red-currant, cherry, balsamic tang balanced by soft caramel malt.",
        "5.0 – 6.5%",
        "Stemmed tulip or goblet at 8–10 °C; blend of young and oak-aged stock (Bourgogne des Flandres, Rodenbach).",
    ),
    ("Belgium", "lambic / gueuze"): (
        "#d99b26",
        "Spontaneously fermented wild wheat-barley beer; bone-dry barnyard funk, lemon zest, lively champagne fizz in gueuze blends.",
        "5.0 – 7.0%",
        "Uncarbonated straight lambic in a tumbler or sparkling Oude Gueuze from corked bottles in a fluted glass.",
    ),
    ("Belgium", "saison"): (
        "#eab308",
        "Dry, peppery Wallonian farmhouse ale; expressive yeast phenols, citrus peel, earthy noble hop snap.",
        "5.5 – 7.0%",
        "Wide tulip glass at 8–10 °C with a rocky, persistent white foam cap.",
    ),
    ("Belgium", "tripel"): (
        "#f5c451",
        "Deceptively strong pale abbey-style ale; spicy yeast esters, honeyed pilsner malt, dry warming finish.",
        "8.0 – 11.0%",
        "Wide chalice or house goblet at 8–10 °C (De Garre's 11% house tripel comes with cheese cubes; max 3).",
    ),
    ("Belgium", "dubbel"): (
        "#5b2c1d",
        "Rich mahogany abbey ale brewed with dark candi sugar; dried plum, raisin, toasted bread crust, gentle spice.",
        "6.5 – 8.0%",
        "Wide-mouthed Trappist chalice at cellar temperature (10–12 °C) to open dark-fruit aromatics.",
    ),
    ("Belgium", "witbier"): (
        "#f6e599",
        "Unfiltered spiced wheat beer with coriander seed and bitter Curaçao orange peel; silky, zesty, refreshing.",
        "4.5 – 5.5%",
        "Hexagonal tumbler chilled (5–7 °C), swirled gently to suspend the yeast cloud.",
    ),
    ("Belgium", "gruut (herb beer)"): (
        "#b76e22",
        "Medieval Ghent style brewed with a botanical gruit spice-and-herb blend instead of hops; herbal, earthy, lightly floral.",
        "5.0 – 9.0%",
        "Poured across Blond, Amber, Brown, White, and Inferno strengths at Gruut Stadsbrouwerij in Ghent.",
    ),
    ("Franconia", "Rauchbier"): (
        "#6e3419",
        "Bottom-fermented lager kilned over open beechwood logs; savoury campfire smoke over clean Franconian malt.",
        "4.8 – 6.5%",
        "Gravity-dispensed straight from pitched oak barrels (vom Holzfass) in ceramic or dimpled 0.5 L Seidla.",
    ),
    ("Franconia", "Ungespundetes / Kellerbier"): (
        "#c97a2b",
        "Unfiltered, unbunged cellar lager with soft natural carbonation, bready Munich/Vienna malt, and herbal hops.",
        "4.8 – 5.5%",
        "Served cool from cellar lagering tanks with a low, creamy head; order 'ein U' (e.g. Mahr's Bräu aU).",
    ),
    ("Franconia", "Helles"): (
        "#f1c232",
        "Drier and slightly hoppier than Southern Bavarian Helles; crisp pilsner malt graininess with clean floral balance.",
        "4.7 – 5.3%",
        "0.5 L Seidla mug in brewery taverns or shaded hillside Bierkeller.",
    ),
    ("Franconia", "Pils"): (
        "#f7df74",
        "Assertively bitter, bone-dry Franconian Pilsner showcasing aromatic Hallertau and Spalt noble hops.",
        "4.8 – 5.2%",
        "Tall slender Pilsner glass or tulip with a tight 3-minute foam crown (Keesmann Herren Pils benchmark).",
    ),
    ("Franconia", "Bock"): (
        "#78350f",
        "Seasonal strong lager (autumn/winter Urbock & Maibock); deep melanoidin malt richness, warming, smoked or unsmoked.",
        "6.5 – 7.5%",
        "0.5 L glass or stoneware mug in late autumn/spring; pace carefully alongside hearty Franconian roast pork.",
    ),
    ("Bohemia", "světlý ležák 12°"): (
        "#eab308",
        "The classic 12° Plato Czech pale lager: triple-decoction mash, Moravian malt depth, spicy Žatec (Saaz) hop bitterness.",
        "4.4 – 5.2%",
        "Heavy dimpled 0.5 L Tübinger mug poured 'na hladinku' under a dense, wet, creamy foam cap.",
    ),
    ("Bohemia", "tmavé (dark lager)"): (
        "#2e1912",
        "Bohemian dark lager balancing roasted chocolate and caramel malt sweetness with clean lager crispness — never burnt.",
        "4.4 – 5.8%",
        "0.5 L handled mug; also ordered 'řezané' (half-and-half cut with pale lager) in traditional hospody.",
    ),
    ("Bohemia", "tank beer"): (
        "#f4c430",
        "Unpasteurised (and in Urquell's cellars, unfiltered) světlý ležák delivered straight from brewery to pub steel/copper bladders.",
        "4.4 – 5.0%",
        "Tankové pivo kept at 6–8 °C without CO₂ contact; fresher, rounder malt and livelier Saaz hop oils than kegged pours.",
    ),
    ("Bohemia", "Czech IPA"): (
        "#e07a1f",
        "Modern Bohemian craft wave (typically 14°–16° Plato) pairing New World citrus/pine hops with structured Czech malt.",
        "5.8 – 6.8%",
        "0.4 L or 0.5 L craft tulip/shaker at brewpubs like Pivovar Permon (Permon IPA 15°) and Pivovar Raven.",
    ),
    ("Bavaria", "Helles"): (
        "#f6d358",
        "Soft-water Munich golden lager; gentle bready-sweet pilsner malt, whisper-light Hallertau floral hops, effortless drinkability.",
        "4.8 – 5.6%",
        "0.5 L Willibecher or 1 L Maßkrug; supreme when tapped from wooden barrels (Holzfass Augustiner Edelstoff).",
    ),
    ("Bavaria", "Weißbier"): (
        "#df8b28",
        "Top-fermented Bavarian wheat beer (50%+ malted wheat); signature banana and clove yeast esters, lush effervescence.",
        "5.0 – 5.6% (Weizenbock 8.2%)",
        "Tall curved 0.5 L Weizenglas; swirl the last centimetre of bottle yeast before topping the foam dome.",
    ),
    ("Bavaria", "Doppelbock"): (
        "#3d1f16",
        "Monastic 'liquid bread' brewed originally for Lenten fasting; dark dried fig, toasted bread crust, velvety malt body.",
        "7.0 – 8.5%",
        "0.5 L mug or stemmed Pokal; Kloster Andechs Doppelbock Dunkel (7.1%) on the Holy Mountain is the archetype.",
    ),
    ("Bavaria", "Festbier"): (
        "#e5a922",
        "Deep-golden seasonal festival lager; slightly richer and stronger than everyday Helles with a clean, crisp finish.",
        "5.6 – 6.3%",
        "1 L Maßkrug in beer gardens and festival halls during late summer and autumn.",
    ),
    ("Nuremberg", "Rotbier"): (
        "#9a2c1d",
        "Historic Nuremberg copper-red bottom-fermented lager; kilned specialty malts deliver nutty caramel, bread crust, and clean finish.",
        "4.8 – 5.5%",
        "Served unfiltered from cool rock-cut vaults and brewpubs in 0.5 L mugs (Altstadthof, Schanzenbräu, Tucher Mautkeller).",
    ),
}

# One-line reasons for each of the 14 side_legs in route-2027.json
SIDE_TRIP_NOTES: Dict[Tuple[str, str], str] = {
    ("bruges", "Westvleteren (In de Vrede)"): "Abbey café opposite Sint-Sixtus pouring Trappist Westvleteren 12, 8, and Blond on the terrace without needing a crate reservation.",
    ("bruges", "Roeselare (Rodenbach)"): "Cathedral-like foeder halls where Flemish red-brown ales age for years in towering oak vats.",
    ("ghent", "Antwerp"): "Flemish beer port home to De Koninck city brewery, historic brown bars, and legendary vintage-bottle café Kulminator.",
    ("bamberg", "Aufseß (four-brewery loop)"): "Walkable Franconian Switzerland trail linking four village family breweries (Reichold, Rothenbach, Stadter, Kathi-Bräu).",
    ("bamberg", "Forchheim"): "Forested Kellerwald hillside lined with traditional rock-cut Franconian beer cellars under chestnut trees.",
    ("sokolov", "Loket"): "Dramatic medieval castle town wrapped inside a tight horseshoe bend of the Ohře River — effortless stop en route to Plzeň.",
    ("sokolov", "Karlovy Vary"): "Grand Bohemian spa town of riverside colonnades and steaming mineral springs just east of Sokolov.",
    ("plzen", "Žatec (hop capital)"): "Historic Saaz hop capital with the Hop Museum, Temple of Hops, and local brews yards from the bines.",
    ("plzen", "Chodová Planá (Chodovar beer spa)"): "Centuries-old granite beer caves with an underground restaurant and traditional warm beer-bath spa.",
    ("kout", "Regensburg"): "UNESCO medieval Danube city with time-capsule Kneitinger beer hall and Spitalbrauerei by the Stone Bridge (natural Day 10 break).",
    ("maxlrain", "Wendelstein"): "Bavarian pre-Alps peak reached by historic cog railway or cable car for clear-day Alpine panoramas.",
    ("andechs", "Herrsching (Ammersee)"): "Lakeside overnight base below Kloster Andechs — walk or ride the local bus up the Holy Mountain so the car stays parked.",
    ("munich", "Freising (Weihenstephan)"): "Hilltop Bavarian State Brewery Weihenstephan north of Munich, revered for benchmark Hefeweizen, Vitus, and Korbinian.",
    ("nuremberg", "Bamberg"): "Quick run north up the Regnitz valley if you want one more oak-barrel Rauchbier or cellar Ungespundetes.",
}

LEG_NOTES: Dict[int, Tuple[str, str]] = {
    1: ("hard", "Arrival motorway push west across Germany & Belgium (E40) — swap drivers if jet-lagged."),
    3: ("easy", "Short Flemish hop on the E40; arrives in Ghent well before lunch."),
    4: ("long", "Longest day of the trip (6 h 51) — leave Ghent early, break at Würzburg or Fulda."),
    6: ("easy", "Scenic cross-border run via Bayreuth & Cheb; activate Czech e-vignette before crossing."),
    7: ("easy", "Relaxed Bohemian drive along the Ohře valley; easy detour to Loket or Karlovy Vary."),
    9: ("easy", "Short drive south-west into the Šumava (Bohemian Forest) foothills."),
    10: ("long", "Second-longest drive (3 h 11) — crosses back into Bavaria past Regensburg."),
    11: ("easy", "Pre-Alpine country roads west across Upper Bavaria to Ammersee."),
    12: ("easy", "Shortest leg of the trip (45 min) straight into Munich."),
    14: ("easy", "North on the A9 from Upper Bavaria into Franconian Rotbier country."),
    15: ("hard", "Final A3 motorway return to Frankfurt Airport — leave buffer for traffic, fuel & car drop-off."),
}


def day_region_group(day_num: int) -> str:
    if day_num in (1, 2, 3):
        return "belgium"
    if day_num in (4, 5, 14):
        return "franconia"
    if day_num in (6, 7, 8, 9):
        return "bohemia"
    if day_num in (10, 11, 12, 13):
        return "bavaria"
    return "germany"


def build() -> pathlib.Path:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    stops: List[Dict[str, Any]] = sorted(data["stops"], key=lambda s: int(s["order"]))
    stop_by_id: Dict[str, Dict[str, Any]] = {s["id"]: s for s in stops}
    legs: List[Dict[str, Any]] = data["legs"]
    leg_by_day: Dict[int, Dict[str, Any]] = {int(l["day"]): l for l in legs}
    leg_by_from: Dict[str, Dict[str, Any]] = {l["from"]: l for l in legs}
    days_list: List[Dict[str, Any]] = data["days"]
    venues_dict: Dict[str, List[Dict[str, str]]] = data["venues"]
    styles_list: List[Dict[str, Any]] = data["styles"]
    side_legs: List[Dict[str, Any]] = data["side_legs"]
    matrix_nodes: List[str] = data["matrix"]["nodes"]
    matrix_pairs: Dict[str, List[float]] = data["matrix"]["pairs"]

    # Track night counter per base across days
    base_visit_counter: Dict[str, int] = {}

    # ------------------------------------------------------------------ 1. Build Itinerary HTML
    day_cards_html: List[str] = []
    for idx_d, d in enumerate(days_list):
        dnum = int(d["day"])
        base_id = d["base"]
        bstop = stop_by_id[base_id]
        country = bstop["country"]
        country_cls = country.lower()
        rgroup = day_region_group(dnum)
        has_drive = d["drive"] is not None
        is_long = dnum in (4, 10)

        nights_total = int(bstop["nights"])
        if nights_total > 0:
            base_visit_counter[base_id] = base_visit_counter.get(base_id, 0) + 1
            cur_night = base_visit_counter[base_id]
            if nights_total > 1:
                nights_label = f"{nights_total} nights at base · Night {cur_night} of {nights_total}"
            else:
                nights_label = "1 night at base"
        else:
            nights_label = "0 nights · Car return & departure"

        long_badge = ""
        if dnum == 4:
            long_badge = '<span class="long-badge">⚠️ LONG DRIVE · 6 h 51 (Longest Day)</span>'
        elif dnum == 10:
            long_badge = '<span class="long-badge">⚠️ LONG DRIVE · 3 h 11 (Cross-Border)</span>'

        if has_drive:
            lg = leg_by_day[dnum]
            from_lbl = "FRA" if lg["from"] == "fra" else stop_by_id[lg["from"]]["name"]
            to_lbl = "FRA" if lg["to"] == "fra" else stop_by_id[lg["to"]]["name"]
            drive_html = (
                f'<div class="drive-pill">'
                f'🚗 <strong>{esc(from_lbl)} → {esc(to_lbl)}</strong>'
                f' &nbsp;·&nbsp; <span class="num">{fmt_km_round(float(lg["km"]))} km</span>'
                f' <span class="muted-inline">({fmt_km_exact(float(lg["km"]))} km)</span>'
                f' &nbsp;·&nbsp; <span class="num">{fmt_duration_human(int(lg["minutes"]))}</span>'
                f'</div>'
            )
        else:
            drive_html = '<div class="drive-pill inplace">🚶 <strong>In place</strong> &nbsp;·&nbsp; Car-free brewery day</div>'

        items_li = "\n".join(f"          <li>{esc(it)}</li>" for it in d["items"])
        visit_num = int(bstop["order"]) + 1
        card_classes = ["day-node", country_cls]
        if is_long:
            card_classes.append("long-day")

        day_cards_html.append(f"""      <div class="{' '.join(card_classes)}" data-region="{rgroup}" data-drive="{'yes' if has_drive else 'no'}" data-long="{'yes' if is_long else 'no'}">
        <div class="day-top-row">
          <span class="day-number">DAY {dnum}</span>
          <div class="day-badges">
            <span class="base-chip">{COUNTRY_FLAG[country]} Base: <strong>{esc(bstop['name'])}</strong> · {esc(nights_label)}</span>
            {long_badge}
          </div>
        </div>
        <div class="day-heading-row">
          <h3>{esc(d['title'])}</h3>
          <button type="button" class="jump-map-btn" onclick="focusStopOnMap('{esc(base_id)}')">📍 Stop #{visit_num} on Map</button>
        </div>
        {drive_html}
        <ul class="day-items">
{items_li}
        </ul>
      </div>""")
        if idx_d < len(days_list) - 1:
            day_cards_html.append('      <div class="connector" aria-hidden="true"></div>')

    itinerary_nodes_str = "\n".join(day_cards_html)

    # ------------------------------------------------------------------ 2. Build Map Stop Buttons HTML
    stop_pills_html: List[str] = []
    for s in stops:
        vnum = int(s["order"]) + 1
        n_str = f"{s['nights']}N" if int(s["nights"]) > 0 else "S/E"
        stop_pills_html.append(
            f'<button type="button" class="stop-jump-pill" onclick="focusStopOnMap(\'{esc(s["id"])}\')">'
            f'<span class="pill-num">{vnum}</span> {esc(SHORT_STOP_LABEL[s["id"]])} <span class="pill-nights">{n_str}</span></button>'
        )
    stop_pills_str = "\n        ".join(stop_pills_html)

    # ------------------------------------------------------------------ 3. Build Rankings HTML
    total_venues = sum(len(v) for v in venues_dict.values())
    city_filter_btns = [
        f'<button type="button" class="filter-btn active" onclick="filterRankings(\'all\', this)">All Cities ({total_venues})</button>'
    ]
    city_sections_html: List[str] = []

    for city_name, vlist in venues_dict.items():
        stop_id = CITY_TO_STOP_ID[city_name]
        s_obj = stop_by_id[stop_id]
        c_slug = stop_id
        famous = CITY_FAMOUS_BEER[city_name]
        flag = COUNTRY_FLAG[s_obj["country"]]
        nights_n = int(s_obj["nights"])
        n_txt = f"{nights_n} night{'s' if nights_n != 1 else ''}"

        city_filter_btns.append(
            f'<button type="button" class="filter-btn" onclick="filterRankings(\'{c_slug}\', this)">'
            f'{flag} {esc(city_name)} ({len(vlist)})</button>'
        )

        cards_html: List[str] = []
        for idx_v, v in enumerate(vlist, start=1):
            vname = v["name"]
            vnote = v["note"]
            order_this = VENUE_ORDER_LINE.get((city_name, vname), famous)
            search_blob = f"{city_name} {vname} {vnote} {order_this} {famous}".lower()
            cards_html.append(f"""          <div class="brewery-card" data-city="{c_slug}" data-search="{esc(search_blob)}">
            <span class="rank" title="Rank #{idx_v} in {esc(city_name)}">{idx_v}</span>
            <div class="card-city-tag">{flag} {esc(city_name)} · #{idx_v} of {len(vlist)}</div>
            <h4>{esc(vname)}</h4>
            <p class="desc">{esc(vnote)}</p>
            <div class="order-this">🍺 <strong>Order this:</strong> {esc(order_this)}</div>
          </div>""")

        city_sections_html.append(f"""      <section class="city-ranking-section" data-city-section="{c_slug}">
        <div class="city-section-header">
          <div>
            <h3>{flag} {esc(city_name)} <span class="city-meta-pill">{esc(n_txt)} · Stop #{int(s_obj['order']) + 1}</span></h3>
            <p class="city-subnote">{esc(s_obj['note'])}</p>
          </div>
          <div class="city-famous-pill">🍻 Famous for: <strong>{esc(famous)}</strong></div>
        </div>
        <div class="brewery-grid">
{chr(10).join(cards_html)}
        </div>
      </section>""")

    city_filters_str = "\n      ".join(city_filter_btns)
    city_sections_str = "\n".join(city_sections_html)

    # ------------------------------------------------------------------ 4. Build Beer Guide HTML
    region_tables_html: List[str] = []
    region_filter_btns = [
        '<button type="button" class="filter-btn active" onclick="filterBeerRegions(\'all\', this)">All Regions (5)</button>'
    ]
    for reg_entry in styles_list:
        rname = reg_entry["region"]
        rslug = rname.lower()
        rstyles: List[str] = reg_entry["styles"]
        region_filter_btns.append(
            f'<button type="button" class="filter-btn" onclick="filterBeerRegions(\'{esc(rslug)}\', this)">'
            f'{esc(rname)} ({len(rstyles)})</button>'
        )
        rows_html: List[str] = []
        for st_name in rstyles:
            swatch, expect, abv, serving = STYLE_DETAILS[(rname, st_name)]
            rows_html.append(f"""            <tr>
              <td><span class="color-swatch" style="background:{swatch}"></span><strong>{esc(st_name)}</strong></td>
              <td>{esc(expect)}</td>
              <td class="num"><strong>{esc(abv)}</strong></td>
              <td>{esc(serving)}</td>
            </tr>""")
        region_tables_html.append(f"""      <section class="beer-region-block" data-beer-region="{esc(rslug)}">
        <h3 class="region-table-heading">{esc(rname)} <span class="count-pill">{len(rstyles)} style{'s' if len(rstyles) != 1 else ''}</span></h3>
        <div class="beer-table-wrap">
          <table class="beer-table">
            <thead>
              <tr>
                <th style="width:20%">Style</th>
                <th style="width:38%">What to Expect</th>
                <th style="width:14%">Typical ABV</th>
                <th style="width:28%">Serving Note</th>
              </tr>
            </thead>
            <tbody>
{chr(10).join(rows_html)}
            </tbody>
          </table>
        </div>
      </section>""")

    # "What to Order Where" keyed to the 10 bases
    WHAT_TO_ORDER_BASES: List[Tuple[str, str, str]] = [
        ("bruges", "Flemish red", "Bourgogne des Flandres on the canal; pair with Brugse Zot / Straffe Hendrik at De Halve Maan and the 11% house tripel at De Garre."),
        ("ghent", "gruut (herb beer)", "Blond, Amber, Brown, White, and Inferno at Gruut Stadsbrouwerij; follow with Pils 13 at Dok Brewing and house Max at De Dulle Griet."),
        ("bamberg", "Rauchbier", "Oak-barrel Märzen Rauchbier at Schlenkerla, subtler Rauchbier at Spezial, 'aU' Ungespundetes at Mahr's Bräu, Zwergla at Fässla, and Herren Pils at Keesmann."),
        ("sokolov", "Permon IPA 15°", "Permon IPA 15° and dark specials straight from the taps in Pivovar Permon's Komenského 77 restaurant."),
        ("plzen", "tank Pilsner", "Unfiltered Urquell in the historic cellars, copper-tank Pilsner at U Salzmannů and Na Parkánu, dark lager at Purkmistr, and craft pours at Raven."),
        ("kout", "Kout 12°", "Unpasteurised Kout 12° pale lager at the revived 19th-century brewery in the Šumava foothills."),
        ("maxlrain", "Maxlrainer Helles", "Schlossbrauerei Maxlrain Helles, Dunkel, and Weißbier at the castle Bierstube next door."),
        ("andechs", "Doppelbock", "Monastery Doppelbock Dunkel (7.1%) overlooking the Ammersee at Kloster Andechs, and the full range down at Andechser Hof in Herrsching."),
        ("munich", "Helles", "Wooden-barrel Edelstoff at Augustiner-Keller, Erhellung unfiltered Helles at Giesinger Bräu, Aventinus at Schneider Bräuhaus, and NEIPAs at ORCA Brau."),
        ("nuremberg", "Rotbier", "Organic Rotbier at Hausbrauerei Altstadthof under the castle, Schanzenbräu in Gostenhof, Tucher Mautkeller vaults, and Zeltner Bierhaus."),
    ]
    base_order_cards: List[str] = []
    for idx_b, (bid, sig_beer, detail_txt) in enumerate(WHAT_TO_ORDER_BASES, start=1):
        st = stop_by_id[bid]
        flag = COUNTRY_FLAG[st["country"]]
        base_order_cards.append(f"""        <div class="base-order-card">
          <div class="base-order-top">
            <span class="base-seq">Base {idx_b} · {st['nights']}N</span>
            <span class="base-sig-pill">🍺 {esc(sig_beer)}</span>
          </div>
          <h4>{flag} {esc(st['name'])}</h4>
          <p>{esc(detail_txt)}</p>
        </div>""")

    # ------------------------------------------------------------------ 5. Build Drive Times HTML
    leg_rows_html: List[str] = []
    for idx_l, lg in enumerate(legs, start=1):
        dnum = int(lg["day"])
        s_from = stop_by_id[lg["from"]]
        s_to = stop_by_id[lg["to"]]
        km_v = float(lg["km"])
        min_v = int(lg["minutes"])
        severity, note_txt = LEG_NOTES[dnum]
        row_cls = "leg-row-long" if severity == "long" else ("leg-row-hard" if severity == "hard" else "")
        badge_html = ""
        if dnum == 4:
            badge_html = '<span class="table-alert-pill">LONGEST · 6 h 51</span> '
        elif dnum == 10:
            badge_html = '<span class="table-warn-pill">LONG · 3 h 11</span> '
        leg_rows_html.append(f"""            <tr class="{row_cls}">
              <td class="num"><strong>Day {dnum}</strong></td>
              <td>{COUNTRY_FLAG[s_from['country']]} <strong>{esc(s_from['name'])}</strong> → {COUNTRY_FLAG[s_to['country']]} <strong>{esc(s_to['name'])}</strong></td>
              <td class="num">{fmt_km_exact(km_v)} km <span class="muted-inline">({fmt_km_round(km_v)})</span></td>
              <td class="num"><strong>{fmt_hmm(min_v)}</strong> <span class="muted-inline">({fmt_duration_human(min_v)})</span></td>
              <td>{badge_html}{esc(note_txt)}</td>
            </tr>""")

    # 11 x 11 Symmetric Car Matrix
    itinerary_edges = {(l["from"], l["to"]) for l in legs} | {(l["to"], l["from"]) for l in legs}
    matrix_th = ['<th class="matrix-corner">From \\ To</th>'] + [
        f'<th title="{esc(stop_by_id[nid]["name"])}">{esc(SHORT_STOP_LABEL[nid])}</th>'
        for nid in matrix_nodes
    ]
    matrix_trs: List[str] = []
    for r_idx, a in enumerate(matrix_nodes):
        tds = [f'<th scope="row" class="matrix-row-head" title="{esc(stop_by_id[a]["name"])}">{esc(SHORT_STOP_LABEL[a])}</th>']
        for c_idx, b in enumerate(matrix_nodes):
            if a == b:
                tds.append('<td class="matrix-diag">—</td>')
            else:
                pair_val = matrix_pairs.get(f"{a}|{b}") or matrix_pairs.get(f"{b}|{a}")
                assert pair_val is not None, f"Missing matrix pair {a}|{b}"
                p_km, p_min = float(pair_val[0]), int(pair_val[1])
                is_route_leg = (a, b) in itinerary_edges
                cls_list = ["matrix-cell", "num"]
                if is_route_leg:
                    cls_list.append("matrix-route-cell")
                if c_idx > r_idx:
                    cls_list.append("matrix-upper")
                else:
                    cls_list.append("matrix-lower")
                title_tip = f"{stop_by_id[a]['name']} ↔ {stop_by_id[b]['name']}: {fmt_km_exact(p_km)} km · {fmt_hmm(p_min)}"
                tds.append(
                    f'<td class="{" ".join(cls_list)}" title="{esc(title_tip)}">'
                    f'<span class="m-km">{fmt_km_round(p_km)} km</span>'
                    f'<span class="m-time">{fmt_hmm(p_min)}</span>'
                    f'</td>'
                )
        matrix_trs.append("            <tr>" + "".join(tds) + "</tr>")

    # ------------------------------------------------------------------ 6. Build Suggestions HTML
    side_by_base: Dict[str, List[Dict[str, Any]]] = {}
    for sl in side_legs:
        side_by_base.setdefault(sl["from"], []).append(sl)

    side_groups_html: List[str] = []
    for s in stops:
        sid = s["id"]
        if sid not in side_by_base:
            continue
        s_items = side_by_base[sid]
        flag = COUNTRY_FLAG[s["country"]]
        c_lower = s["country"].lower()
        cards: List[str] = []
        for sl in s_items:
            why = SIDE_TRIP_NOTES[(sid, sl["to"])]
            km_i = int(sl["km"])
            min_i = int(sl["minutes"])
            cards.append(f"""          <div class="detour-card">
            <div class="detour-top">
              <h4>{esc(sl['to'])}</h4>
              <span class="detour-metrics num">{km_i} km · {fmt_duration_human(min_i)} ({fmt_hmm(min_i)})</span>
            </div>
            <p>{esc(why)}</p>
          </div>""")
        side_groups_html.append(f"""      <section class="detour-base-group" data-detour-country="{c_lower}">
        <div class="detour-group-header">
          <h3>{flag} From {esc(s['name'])} <span class="count-pill">{len(s_items)} side trip{'s' if len(s_items) != 1 else ''}</span></h3>
          <span class="muted-inline">Stop #{int(s['order']) + 1} · {s['nights']} night{'s' if int(s['nights']) != 1 else ''}</span>
        </div>
        <div class="detour-grid">
{chr(10).join(cards)}
        </div>
      </section>""")

    # Embed verbatim JSON safely inside script
    embedded_json = json.dumps(data, ensure_ascii=False)

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bier Reisen 2027 — 15-Day European Beer Planner</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
:root {{
  --bg: #141627;
  --surface: #181f38;
  --surface-alt: #1f2847;
  --card: #112a4e;
  --card-hover: #163663;
  --accent: #e94560;
  --gold: #f5a623;
  --beer-light: #f5d76e;
  --beer-dark: #6b3a2a;
  --beer-amber: #c87533;
  --text: #eef1f6;
  --text-muted: #b0b9ce;
  --border: #2b3658;
  --success: #4ecdc4;
  --germany: #ffcc00;
  --belgium: #ff9f43;
  --czech: #38bdf8;
}}

* {{ box-sizing: border-box; margin: 0; padding: 0; }}

::selection {{
  background: rgba(245, 166, 35, 0.32);
  color: #ffffff;
}}

html {{
  color-scheme: dark;
  scroll-behavior: smooth;
}}

body {{
  font-family: 'Avenir Next', 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  line-height: 1.55;
  overflow-x: hidden;
}}

::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: var(--bg); }}
::-webkit-scrollbar-thumb {{ background: #2f3b5e; border-radius: 5px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--gold); }}

button:focus-visible, a:focus-visible, input:focus-visible {{
  outline: 2px solid var(--gold);
  outline-offset: 2px;
}}

.num {{
  font-variant-numeric: tabular-nums;
}}

/* Header */
.header {{
  background: linear-gradient(135deg, var(--surface) 0%, #1a1836 60%, #24192c 100%);
  padding: 2.1rem 1.5rem 1.75rem;
  text-align: center;
  border-bottom: 3px solid var(--accent);
  position: relative;
  overflow: hidden;
}}
.header::before {{
  content: '🍺';
  position: absolute;
  font-size: 7.5rem;
  opacity: 0.05;
  top: -0.8rem;
  left: 2rem;
  pointer-events: none;
}}
.header::after {{
  content: '🏰';
  position: absolute;
  font-size: 7.5rem;
  opacity: 0.05;
  top: -0.8rem;
  right: 2rem;
  pointer-events: none;
}}
.header h1 {{
  font-size: clamp(1.9rem, 3.4vw, 2.6rem);
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--gold);
  margin-bottom: 0.65rem;
}}
.header .route-string {{
  color: var(--text);
  font-size: 0.98rem;
  max-width: 1120px;
  margin: 0 auto 0.7rem;
  line-height: 1.5;
}}
.header .headline-stats {{
  display: inline-block;
  max-width: 100%;
  font-variant-numeric: tabular-nums;
  font-size: 0.96rem;
  font-weight: 700;
  color: var(--beer-light);
  background: rgba(15, 52, 96, 0.65);
  border: 1px solid rgba(245, 166, 35, 0.4);
  padding: 0.42rem 1.1rem;
  border-radius: 24px;
}}
.header-links {{
  margin-top: 0.75rem;
  display: flex;
  justify-content: center;
  gap: 1rem;
  flex-wrap: wrap;
  font-size: 0.83rem;
}}
.header-links a {{
  color: var(--success);
  text-decoration: underline;
  text-underline-offset: 3px;
}}
.header-links a:hover {{
  color: var(--beer-light);
}}

/* Sticky Tab Bar */
.tabs {{
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0;
  background: var(--surface);
  border-bottom: 2px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 1000;
  box-shadow: 0 6px 20px rgba(7, 9, 19, 0.55);
}}
.tab-btn {{
  padding: 0.95rem 1.45rem;
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  color: var(--text-muted);
  font-family: inherit;
  font-size: 0.96rem;
  font-weight: 600;
  cursor: pointer;
  transition: color 0.2s, background 0.2s, border-color 0.2s;
}}
.tab-btn:hover {{
  color: var(--text);
  background: rgba(233, 69, 96, 0.1);
}}
.tab-btn.active {{
  color: var(--gold);
  border-bottom-color: var(--gold);
  background: rgba(245, 166, 35, 0.09);
}}

.tab-content {{
  display: none;
  padding: 2rem 1.5rem 3.5rem;
  max-width: 1380px;
  margin: 0 auto;
}}
.tab-content.active {{
  display: block;
}}

.section-intro {{
  margin-bottom: 1.5rem;
}}
.section-intro h2 {{
  color: var(--gold);
  font-size: 1.55rem;
  margin-bottom: 0.35rem;
}}
.section-intro p {{
  color: var(--text-muted);
  max-width: 75ch;
}}

/* Filter bar */
.region-filter {{
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  align-items: center;
}}
.filter-btn {{
  padding: 0.45rem 0.95rem;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  border-radius: 999px;
  font-family: inherit;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.18s, color 0.18s, border-color 0.18s;
}}
.filter-btn:hover, .filter-btn.active {{
  background: var(--gold);
  color: #111322;
  border-color: var(--gold);
}}
.search-input {{
  padding: 0.48rem 0.9rem;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
  font-size: 0.88rem;
  min-width: 240px;
}}
.search-input::placeholder {{
  color: var(--text-muted);
}}

/* Tab 1: Flowchart Itinerary */
.flowchart {{
  display: flex;
  flex-direction: column;
  align-items: center;
}}
.day-node {{
  background: var(--card);
  border: 1px solid rgba(245, 166, 35, 0.55);
  border-radius: 12px;
  padding: 1.35rem 1.55rem;
  width: 100%;
  max-width: 880px;
  position: relative;
  box-shadow: 0 8px 22px rgba(5, 8, 20, 0.38);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}}
.day-node:hover {{
  transform: translateY(-2px);
  border-color: var(--gold);
  box-shadow: 0 12px 28px rgba(5, 8, 20, 0.52);
}}
.day-node.germany {{ border-left: 5px solid var(--germany); }}
.day-node.belgium {{ border-left: 5px solid var(--belgium); }}
.day-node.czechia {{ border-left: 5px solid var(--czech); }}
.day-node.long-day {{
  background: linear-gradient(135deg, #162b50 0%, #2a1829 100%);
  border-color: var(--accent);
}}

.day-top-row {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin-bottom: 0.65rem;
}}
.day-number {{
  background: var(--accent);
  color: #ffffff;
  padding: 0.22rem 0.78rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  font-variant-numeric: tabular-nums;
}}
.day-badges {{
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}}
.base-chip {{
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.14);
  color: var(--text);
  padding: 0.2rem 0.7rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
}}
.long-badge {{
  background: rgba(233, 69, 96, 0.22);
  border: 1px solid var(--accent);
  color: #ffd0d8;
  padding: 0.2rem 0.72rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}}
.day-heading-row {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.8rem;
  flex-wrap: wrap;
  margin-bottom: 0.6rem;
}}
.day-node h3 {{
  color: var(--gold);
  font-size: 1.2rem;
}}
.jump-map-btn {{
  background: transparent;
  border: 1px solid rgba(78, 205, 196, 0.45);
  color: var(--success);
  padding: 0.2rem 0.62rem;
  border-radius: 6px;
  font-family: inherit;
  font-size: 0.78rem;
  cursor: pointer;
  transition: background 0.18s, color 0.18s;
}}
.jump-map-btn:hover {{
  background: var(--success);
  color: #0e1726;
}}
.drive-pill {{
  display: inline-block;
  background: rgba(245, 166, 35, 0.12);
  border: 1px solid rgba(245, 166, 35, 0.35);
  color: var(--beer-light);
  padding: 0.36rem 0.8rem;
  border-radius: 8px;
  font-size: 0.88rem;
  margin-bottom: 0.75rem;
}}
.drive-pill.inplace {{
  background: rgba(78, 205, 196, 0.12);
  border-color: rgba(78, 205, 196, 0.35);
  color: var(--success);
}}
.muted-inline {{
  color: var(--text-muted);
  font-weight: 400;
  font-size: 0.84em;
}}
.day-items {{
  padding-left: 1.25rem;
  color: var(--text);
  font-size: 0.94rem;
}}
.day-items li {{
  margin-bottom: 0.28rem;
}}
.connector {{
  width: 3px;
  height: 28px;
  background: linear-gradient(to bottom, var(--gold), var(--accent));
  position: relative;
}}
.connector::after {{
  content: '▼';
  position: absolute;
  bottom: -7px;
  left: 50%;
  transform: translateX(-50%);
  color: var(--accent);
  font-size: 0.65rem;
}}

/* Tab 2: Map */
.map-toolbar {{
  display: flex;
  gap: 0.42rem;
  flex-wrap: wrap;
  margin-bottom: 0.9rem;
  align-items: center;
}}
.stop-jump-pill {{
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 0.32rem 0.65rem;
  border-radius: 999px;
  font-family: inherit;
  font-size: 0.8rem;
  cursor: pointer;
  transition: border-color 0.18s, background 0.18s;
}}
.stop-jump-pill:hover {{
  border-color: var(--gold);
  background: var(--surface-alt);
}}
.pill-num {{
  background: var(--gold);
  color: #111322;
  font-weight: 800;
  width: 19px;
  height: 19px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
  font-variant-numeric: tabular-nums;
}}
.pill-nights {{
  color: var(--beer-light);
  font-size: 0.74rem;
  font-weight: 700;
}}
#map-container {{
  height: 660px;
  width: 100%;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border);
  background: #0b0c15;
  box-shadow: 0 12px 32px rgba(5, 8, 20, 0.5);
}}
.poster-card {{
  margin-top: 1.5rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.2rem;
}}
.poster-card-head {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}}
.poster-card-head h3 {{
  color: var(--gold);
  font-size: 1.05rem;
}}
.poster-card img {{
  width: 100%;
  height: auto;
  border-radius: 8px;
  border: 1px solid var(--border);
  display: block;
}}

/* Leaflet Dark Popup Theme */
.leaflet-popup-content-wrapper, .leaflet-popup-tip {{
  background: #151c35;
  color: var(--text);
  border: 1px solid var(--gold);
  box-shadow: 0 10px 26px rgba(0, 0, 0, 0.65);
}}
.leaflet-popup-content {{
  margin: 12px 15px;
  line-height: 1.48;
  font-family: 'Avenir Next', 'Segoe UI', system-ui, sans-serif;
}}
.popup-title {{
  color: var(--gold);
  font-size: 1.05rem;
  font-weight: 800;
  margin-bottom: 0.25rem;
}}
.popup-meta {{
  color: var(--success);
  font-size: 0.82rem;
  font-weight: 700;
  margin-bottom: 0.4rem;
}}
.popup-addr {{
  color: var(--text-muted);
  font-size: 0.8rem;
  margin-bottom: 0.4rem;
}}
.popup-note {{
  font-size: 0.86rem;
  margin-bottom: 0.5rem;
}}
.popup-next {{
  background: rgba(245, 166, 35, 0.14);
  border: 1px solid rgba(245, 166, 35, 0.35);
  border-radius: 6px;
  padding: 0.35rem 0.55rem;
  font-size: 0.8rem;
  color: var(--beer-light);
  font-variant-numeric: tabular-nums;
}}

/* Tab 3: Rankings */
.city-ranking-section {{
  margin-bottom: 2.5rem;
}}
.city-section-header {{
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 0.9rem;
  margin-bottom: 1rem;
  padding-bottom: 0.7rem;
  border-bottom: 1px solid var(--border);
}}
.city-section-header h3 {{
  color: var(--gold);
  font-size: 1.32rem;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
}}
.city-meta-pill {{
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 0.16rem 0.6rem;
  border-radius: 999px;
}}
.city-subnote {{
  color: var(--text-muted);
  font-size: 0.9rem;
  margin-top: 0.2rem;
}}
.city-famous-pill {{
  background: rgba(245, 166, 35, 0.14);
  border: 1px solid rgba(245, 166, 35, 0.45);
  color: var(--beer-light);
  padding: 0.4rem 0.85rem;
  border-radius: 999px;
  font-size: 0.86rem;
}}
.brewery-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
  gap: 1.25rem;
}}
.brewery-card {{
  background: var(--card);
  border-radius: 12px;
  padding: 1.35rem 1.4rem;
  border: 1px solid var(--border);
  position: relative;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 20px rgba(5, 8, 20, 0.35);
  transition: border-color 0.2s, transform 0.2s;
}}
.brewery-card:hover {{
  border-color: var(--gold);
  transform: translateY(-2px);
}}
.brewery-card .rank {{
  position: absolute;
  top: -11px;
  right: 14px;
  background: var(--accent);
  color: #ffffff;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 0.84rem;
  font-variant-numeric: tabular-nums;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4);
}}
.card-city-tag {{
  color: var(--success);
  font-size: 0.76rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.25rem;
}}
.brewery-card h4 {{
  color: var(--gold);
  font-size: 1.12rem;
  margin-bottom: 0.45rem;
}}
.brewery-card .desc {{
  color: var(--text);
  font-size: 0.91rem;
  margin-bottom: 0.9rem;
  flex-grow: 1;
}}
.order-this {{
  background: rgba(12, 22, 42, 0.65);
  border: 1px solid rgba(245, 215, 110, 0.3);
  border-radius: 8px;
  padding: 0.5rem 0.7rem;
  font-size: 0.84rem;
  color: var(--beer-light);
}}

/* Tab 4: Beer Guide */
.beer-region-block {{
  margin-bottom: 2.1rem;
}}
.region-table-heading {{
  color: var(--gold);
  font-size: 1.24rem;
  margin-bottom: 0.65rem;
  display: flex;
  align-items: center;
  gap: 0.55rem;
}}
.count-pill {{
  font-size: 0.76rem;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 0.14rem 0.55rem;
  border-radius: 999px;
}}
.beer-table-wrap {{
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
}}
.beer-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}}
.beer-table th {{
  background: var(--card);
  color: var(--gold);
  padding: 0.8rem 0.9rem;
  text-align: left;
  border-bottom: 2px solid var(--gold);
  white-space: nowrap;
}}
.beer-table td {{
  padding: 0.72rem 0.9rem;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}}
.beer-table tbody tr:last-child td {{
  border-bottom: none;
}}
.beer-table tbody tr:hover {{
  background: rgba(245, 166, 35, 0.06);
}}
.color-swatch {{
  display: inline-block;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  vertical-align: middle;
  margin-right: 8px;
  border: 1px solid rgba(255, 255, 255, 0.35);
}}
.base-order-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
  gap: 1.1rem;
  margin-top: 1rem;
}}
.base-order-card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.1rem 1.2rem;
}}
.base-order-top {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.45rem;
}}
.base-seq {{
  font-size: 0.76rem;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}}
.base-sig-pill {{
  background: rgba(245, 166, 35, 0.16);
  border: 1px solid rgba(245, 166, 35, 0.45);
  color: var(--beer-light);
  padding: 0.15rem 0.58rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
}}
.base-order-card h4 {{
  color: var(--gold);
  margin-bottom: 0.35rem;
  font-size: 1.05rem;
}}
.base-order-card p {{
  color: var(--text);
  font-size: 0.88rem;
}}

/* Tab 5: Drive Times & 11x11 Matrix */
.stats-strip {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(185px, 1fr));
  gap: 0.9rem;
  margin-bottom: 1.8rem;
}}
.stat-box {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.95rem 1.1rem;
}}
.stat-box .stat-val {{
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--gold);
  font-variant-numeric: tabular-nums;
}}
.stat-box .stat-lbl {{
  font-size: 0.82rem;
  color: var(--text-muted);
  margin-top: 0.15rem;
}}
.leg-row-long {{
  background: rgba(233, 69, 96, 0.11);
}}
.leg-row-hard {{
  background: rgba(245, 166, 35, 0.06);
}}
.table-alert-pill {{
  display: inline-block;
  background: var(--accent);
  color: #fff;
  font-size: 0.72rem;
  font-weight: 800;
  padding: 0.1rem 0.48rem;
  border-radius: 4px;
  margin-right: 0.3rem;
}}
.table-warn-pill {{
  display: inline-block;
  background: var(--gold);
  color: #111322;
  font-size: 0.72rem;
  font-weight: 800;
  padding: 0.1rem 0.48rem;
  border-radius: 4px;
  margin-right: 0.3rem;
}}
.tfoot-totals td {{
  background: var(--surface-alt);
  color: var(--beer-light);
  font-weight: 700;
  border-top: 2px solid var(--gold);
}}

.matrix-wrap {{
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
  margin-top: 0.75rem;
}}
.matrix-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
}}
.matrix-table th, .matrix-table td {{
  border: 1px solid var(--border);
  padding: 0.45rem 0.42rem;
  text-align: center;
}}
.matrix-table thead th {{
  background: var(--card);
  color: var(--gold);
  font-weight: 700;
  white-space: nowrap;
}}
.matrix-row-head {{
  background: var(--card);
  color: var(--gold);
  text-align: left !important;
  padding-left: 0.65rem !important;
  white-space: nowrap;
  position: sticky;
  left: 0;
}}
.matrix-corner {{
  position: sticky;
  left: 0;
  z-index: 2;
}}
.matrix-diag {{
  background: #101425;
  color: var(--text-muted);
  font-weight: 700;
}}
.matrix-cell .m-km {{
  display: block;
  color: var(--text);
  font-weight: 700;
}}
.matrix-cell .m-time {{
  display: block;
  color: var(--text-muted);
  font-size: 0.73rem;
}}
.matrix-lower {{
  opacity: 0.86;
}}
.matrix-route-cell {{
  background: rgba(245, 166, 35, 0.16);
  box-shadow: inset 0 0 0 1px rgba(245, 166, 35, 0.55);
}}
.matrix-route-cell .m-km {{
  color: var(--beer-light);
}}
.matrix-table[data-mode="km"] .m-time {{ display: none; }}
.matrix-table[data-mode="time"] .m-km {{ display: none; }}
.matrix-table[data-mode="time"] .m-time {{ font-size: 0.8rem; color: var(--text); font-weight: 700; }}

.notes-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
  gap: 1.15rem;
  margin-top: 1rem;
}}
.practical-card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.2rem 1.3rem;
}}
.practical-card h4 {{
  color: var(--gold);
  margin-bottom: 0.45rem;
  font-size: 1.02rem;
}}
.practical-card p {{
  color: var(--text);
  font-size: 0.9rem;
}}

/* Tab 6: Suggestions & Tips */
.detour-base-group {{
  margin-bottom: 1.85rem;
}}
.detour-group-header {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  padding-bottom: 0.45rem;
  border-bottom: 1px solid var(--border);
}}
.detour-group-header h3 {{
  color: var(--gold);
  font-size: 1.15rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}}
.detour-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 1rem;
}}
.detour-card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.1rem 1.25rem;
}}
.detour-top {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.6rem;
  flex-wrap: wrap;
  margin-bottom: 0.4rem;
}}
.detour-top h4 {{
  color: var(--beer-light);
  font-size: 1.02rem;
}}
.detour-metrics {{
  background: rgba(78, 205, 196, 0.14);
  border: 1px solid rgba(78, 205, 196, 0.4);
  color: var(--success);
  padding: 0.16rem 0.58rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  white-space: nowrap;
}}
.detour-card p {{
  color: var(--text);
  font-size: 0.89rem;
}}
.suggestion-box {{
  background: linear-gradient(135deg, rgba(78, 205, 196, 0.1), rgba(245, 166, 35, 0.1));
  border: 1px solid var(--success);
  border-radius: 12px;
  padding: 1.45rem;
  margin-top: 2rem;
}}
.suggestion-box h3 {{
  color: var(--success);
  margin-bottom: 0.9rem;
  font-size: 1.22rem;
}}

@media (max-width: 760px) {{
  .tab-btn {{ padding: 0.75rem 0.9rem; font-size: 0.86rem; }}
  .tab-content {{ padding: 1.35rem 1rem 2.5rem; }}
  #map-container {{ height: 480px; }}
  .detour-grid, .brewery-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>

<header class="header">
  <h1>🍺 Bier Reisen 2027 🏰</h1>
  <p class="route-string">Frankfurt Airport → Bruges (2 nights) → Ghent (1) → Bamberg (2) → Pivovar Permon, Sokolov (1) → Plzeň (2) → Kout na Šumavě (1) → Maxlrain Bierstube, Tuntenhausen (1) → Andechs/Herrsching (1) → Munich (2) → Nuremberg (1) → Frankfurt Airport</p>
  <div class="headline-stats">15 days · 14 nights · 10 bases · 2,297 km · 27 h driving · 3 countries</div>
  <div class="header-links">
    <a href="assets/2027-route-map.png" target="_blank" rel="noopener">🗺️ Open 4800×3120 Route Poster (PNG)</a>
    <a href="data/route-2027.json" target="_blank" rel="noopener">📄 Authoritative Route Data (JSON)</a>
  </div>
</header>

<nav class="tabs" role="tablist" aria-label="Bier Reisen 2027 sections">
  <button type="button" class="tab-btn active" role="tab" aria-selected="true" data-tab="itinerary" onclick="switchTab('itinerary', this)">📋 Itinerary</button>
  <button type="button" class="tab-btn" role="tab" aria-selected="false" data-tab="map" onclick="switchTab('map', this)">🗺️ Map</button>
  <button type="button" class="tab-btn" role="tab" aria-selected="false" data-tab="rankings" onclick="switchTab('rankings', this)">🏆 Rankings</button>
  <button type="button" class="tab-btn" role="tab" aria-selected="false" data-tab="beers" onclick="switchTab('beers', this)">🍻 Beer Guide</button>
  <button type="button" class="tab-btn" role="tab" aria-selected="false" data-tab="drives" onclick="switchTab('drives', this)">🚗 Drive Times</button>
  <button type="button" class="tab-btn" role="tab" aria-selected="false" data-tab="suggestions" onclick="switchTab('suggestions', this)">💡 Suggestions</button>
</nav>

<!-- TAB 1: ITINERARY -->
<div id="itinerary" class="tab-content active" role="tabpanel">
  <div class="section-intro">
    <h2>📋 15-Day Day-by-Day Itinerary</h2>
    <p>Closed-loop rental-car pilgrimage starting and ending at Frankfurt Airport (FRA): 14 nights across 10 overnight bases in Belgium, Germany, and Czechia, with 11 driving legs (2,296.5 km / 27 h 01) and 4 car-free brewery crawl days.</p>
  </div>

  <div class="region-filter" id="itinerary-filters">
    <button type="button" class="filter-btn active" onclick="filterDays('all', this)">All 15 Days</button>
    <button type="button" class="filter-btn" onclick="filterDays('belgium', this)">🇧🇪 Belgium (Days 1–3)</button>
    <button type="button" class="filter-btn" onclick="filterDays('franconia', this)">🇩🇪 Franconia &amp; Nuremberg (Days 4–5, 14)</button>
    <button type="button" class="filter-btn" onclick="filterDays('bohemia', this)">🇨🇿 Bohemia (Days 6–9)</button>
    <button type="button" class="filter-btn" onclick="filterDays('bavaria', this)">🇩🇪 Upper Bavaria &amp; Munich (Days 10–13)</button>
    <button type="button" class="filter-btn" onclick="filterDays('inplace', this)">🚶 Car-Free Days (4)</button>
    <button type="button" class="filter-btn" onclick="filterDays('long', this)">⚠️ Long Drives (Days 4 &amp; 10)</button>
  </div>

  <div class="flowchart" id="itinerary-flowchart">
{itinerary_nodes_str}
  </div>
</div>

<!-- TAB 2: MAP -->
<div id="map" class="tab-content" role="tabpanel">
  <div class="section-intro">
    <h2>🗺️ Interactive Route Map — 11 Stops in Visit Order</h2>
    <p>Click any numbered marker (1–11) or route leg to inspect overnight stays, brewery addresses, notes, and the next OSRM driving leg.</p>
  </div>

  <div class="map-toolbar">
    <button type="button" class="filter-btn active" onclick="fitFullRoute()">🔍 Fit Full Loop</button>
    {stop_pills_str}
  </div>

  <div id="map-container"></div>

  <div class="poster-card">
    <div class="poster-card-head">
      <h3>🖼️ High-Resolution Offline Route Poster (4800 × 3120 px)</h3>
      <a href="assets/2027-route-map.png" target="_blank" rel="noopener" style="color:var(--gold);font-size:0.88rem;">Open full-size PNG in new tab →</a>
    </div>
    <img src="assets/2027-route-map.png" alt="Bier Reisen 2027 route map poster showing all 11 stops, night chips, leg drive times, and 15-day ledger" loading="lazy" />
  </div>
</div>

<!-- TAB 3: RANKINGS -->
<div id="rankings" class="tab-content" role="tabpanel">
  <div class="section-intro">
    <h2>🏆 Per-City Brewery &amp; Bar Rankings</h2>
    <p>All {total_venues} vetted breweries, medieval cellars, monastery taps, and brown cafés across the 10 overnight bases, ranked 1..n per city with what to order at each stop.</p>
  </div>

  <div class="region-filter" id="ranking-filters">
    {city_filters_str}
    <input type="search" id="venue-search" class="search-input" placeholder="🔍 Search venues, styles, notes..." oninput="searchRankings()" aria-label="Search venues" />
  </div>

  <div id="rankings-container">
{city_sections_str}
  </div>
</div>

<!-- TAB 4: BEER GUIDE -->
<div id="beers" class="tab-content" role="tabpanel">
  <div class="section-intro">
    <h2>🍻 Regional Beer Style Guide &amp; What to Order Where</h2>
    <p>Five distinct European brewing cultures in one loop: Flanders wild &amp; herb ales, Franconian smoked &amp; unbunged cellar lagers, Bohemian decoction tank pilsners, Upper Bavarian wheat &amp; monastery bocks, and Nuremberg copper-red Rotbier.</p>
  </div>

  <div class="region-filter" id="beer-region-filters">
    {" ".join(region_filter_btns)}
  </div>

  <div id="beer-regions-wrap">
{chr(10).join(region_tables_html)}
  </div>

  <div class="section-intro" style="margin-top:2.6rem;">
    <h2>📍 What to Order Where — Keyed to All 10 Bases</h2>
    <p>Quick ordering cheat sheet in itinerary order from Night 1 in Bruges to Night 14 in Nuremberg.</p>
  </div>
  <div class="base-order-grid">
{chr(10).join(base_order_cards)}
  </div>
</div>

<!-- TAB 5: DRIVE TIMES -->
<div id="drives" class="tab-content" role="tabpanel">
  <div class="section-intro">
    <h2>🚗 Drive Times, Itinerary Legs &amp; 11 × 11 OSRM Car Matrix</h2>
    <p>Every distance and duration below comes directly from OSRM car routing in <code>data/route-2027.json</code> — zero estimates.</p>
  </div>

  <div class="stats-strip">
    <div class="stat-box">
      <div class="stat-val">2,296.5 km</div>
      <div class="stat-lbl">Exact Route Total (2,297 km rounded)</div>
    </div>
    <div class="stat-box">
      <div class="stat-val">27 h 01</div>
      <div class="stat-lbl">1,621 Total Driving Minutes</div>
    </div>
    <div class="stat-box">
      <div class="stat-val">11 legs</div>
      <div class="stat-lbl">11 Drive Days · 4 Car-Free Days</div>
    </div>
    <div class="stat-box">
      <div class="stat-val">6 h 51</div>
      <div class="stat-lbl">Longest Day (Day 4: Ghent → Bamberg, 650.5 km)</div>
    </div>
    <div class="stat-box">
      <div class="stat-val">44 – 45 min</div>
      <div class="stat-lbl">Shortest Hops (Bruges→Ghent &amp; Andechs→Munich)</div>
    </div>
  </div>

  <h3 class="region-table-heading" style="margin-bottom:0.75rem;">(a) The 11 Itinerary Driving Legs</h3>
  <div class="beer-table-wrap" style="margin-bottom:2.4rem;">
    <table class="beer-table">
      <thead>
        <tr>
          <th style="width:10%">Day</th>
          <th style="width:28%">From → To</th>
          <th style="width:15%">Distance (km)</th>
          <th style="width:15%">Time (h:mm)</th>
          <th style="width:32%">Route Note</th>
        </tr>
      </thead>
      <tbody>
{chr(10).join(leg_rows_html)}
      </tbody>
      <tfoot>
        <tr class="tfoot-totals">
          <td>15 Days</td>
          <td>Closed Loop: FRA → 10 Bases → FRA (11 legs)</td>
          <td class="num">2,296.5 km (2,297 km)</td>
          <td class="num">27:01 (1,621 min)</td>
          <td>3 countries · 14 nights · 4 in-place crawl days</td>
        </tr>
      </tfoot>
    </table>
  </div>

  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.75rem;margin-bottom:0.5rem;">
    <h3 class="region-table-heading" style="margin-bottom:0;">(b) Full 11 × 11 Car Distance &amp; Duration Matrix</h3>
    <div class="region-filter" style="margin-bottom:0;" id="matrix-mode-btns">
      <button type="button" class="filter-btn active" onclick="setMatrixMode('both', this)">Both (km + h:mm)</button>
      <button type="button" class="filter-btn" onclick="setMatrixMode('km', this)">Distance (km)</button>
      <button type="button" class="filter-btn" onclick="setMatrixMode('time', this)">Time (h:mm)</button>
    </div>
  </div>
  <p style="color:var(--text-muted);font-size:0.86rem;margin-bottom:0.65rem;">Upper triangle directly from <code>matrix.pairs</code> (55 OSRM pairs), mirrored symmetrically across the <code>—</code> diagonal. Gold-outlined cells mark consecutive stops driven on the itinerary. <em>Note: in symmetric pair lookup <code>fra|nuremberg</code> is 230.7 km / 2:27, whereas the directed Day 15 return leg <code>nuremberg → fra</code> is 231.5 km / 2:25 due to motorway interchange geometry.</em></p>

  <div class="matrix-wrap" style="margin-bottom:2.4rem;">
    <table class="matrix-table" id="car-matrix" data-mode="both">
      <thead>
        <tr>{"".join(matrix_th)}</tr>
      </thead>
      <tbody>
{chr(10).join(matrix_trs)}
      </tbody>
    </table>
  </div>

  <h3 class="region-table-heading">(c) Totals &amp; Practical Road Notes</h3>
  <div class="notes-grid">
    <div class="practical-card">
      <h4>🇨🇿 Czech Motorway Vignette Required</h4>
      <p>Passenger cars on Czech motorways require an official electronic vignette (<em>edalnice.cz</em>) registered to the rental license plate — purchase it before crossing near Cheb on Day 6 to cover the Bohemian stretch (Days 6–10), and confirm cross-border permission for Belgium and Czechia at the FRA rental desk.</p>
    </div>
    <div class="practical-card">
      <h4>🇧🇪 Belgium Has No Motorway Toll</h4>
      <p>Belgian motorways (E40 to Bruges and Ghent) are completely toll-free for passenger cars. Watch out instead for Ghent's inner Low Emission Zone (LEZ): register foreign German rental plates online beforehand or park at edge-of-centre garages.</p>
    </div>
    <div class="practical-card">
      <h4>🇩🇪 German Autobahn &amp; A-Road Alternatives</h4>
      <p>German Autobahns have no passenger-car tolls, though summer <em>Baustellen</em> (roadworks) slow sections of the A3 (Frankfurt–Würzburg–Nuremberg) and A9 (Munich–Nuremberg). On shorter hops (Bamberg–Bayreuth–Cheb, Maxlrain–Andechs), scenic federal B-roads offer relaxed country driving.</p>
    </div>
    <div class="practical-card">
      <h4>⏱️ Tackling the 6 h 51 Day (Ghent → Bamberg)</h4>
      <p>Day 4 (650.5 km / 6 h 51) is by far the longest leg, trading West Flanders for Upper Franconia in one push. Depart Ghent early to clear the Brussels/Cologne rings smoothly, split the drive with lunch in Würzburg or Fulda, then park for two nights and reward yourself with oak-barrel Rauchbier at Schlenkerla.</p>
    </div>
  </div>
</div>

<!-- TAB 6: SUGGESTIONS -->
<div id="suggestions" class="tab-content" role="tabpanel">
  <div class="section-intro">
    <h2>💡 Measured Side-Trip Detours &amp; Practical Trip Tips</h2>
    <p>14 optional side trips measured from their nearest overnight base, followed by six essential planning rules for a smooth pilgrimage.</p>
  </div>

  <div class="region-filter" id="detour-filters">
    <button type="button" class="filter-btn active" onclick="filterDetours('all', this)">All 14 Side Trips</button>
    <button type="button" class="filter-btn" onclick="filterDetours('belgium', this)">🇧🇪 From Belgian Bases (3)</button>
    <button type="button" class="filter-btn" onclick="filterDetours('germany', this)">🇩🇪 From German Bases (6)</button>
    <button type="button" class="filter-btn" onclick="filterDetours('czechia', this)">🇨🇿 From Czech Bases (5)</button>
  </div>

  <div id="detours-container">
{chr(10).join(side_groups_html)}
  </div>

  <div class="suggestion-box">
    <h3>🧭 Six Trip-Level Tips Before You Go</h3>
    <div class="notes-grid">
      <div class="practical-card">
        <h4>1. Book Pilsner Urquell &amp; Purkmistr Ahead</h4>
        <p>Reserve English-language Pilsner Urquell cellar tours (for the unfiltered oak-barrel pour) and Purkmistr beer-spa slots weeks ahead, plus De Halve Maan's XL rooftop/pipeline tour in Bruges.</p>
      </div>
      <div class="practical-card">
        <h4>2. Watch Monday Closures (<em>Ruhetag</em>)</h4>
        <p>Small family breweries in Bamberg, Franconian villages, rural Bohemia, and Upper Bavaria frequently close on Mondays and/or Tuesdays. Verify weekly taproom hours so a key brewery isn't shuttered.</p>
      </div>
      <div class="practical-card">
        <h4>3. Carry Cash in Franconia &amp; Country Inns</h4>
        <p>Traditional Bamberg <em>Schwemme</em> tap windows, hillside beer cellars, and village inns often take cash only. Carry small Euro bills in Germany and Czech koruna (CZK) in Sokolov and Kout na Šumavě.</p>
      </div>
      <div class="practical-card">
        <h4>4. Strict Driving &amp; Drinking Rules (0.0% in Czechia)</h4>
        <p>Czechia enforces <strong>zero tolerance (0.0% BAC)</strong> behind the wheel, and Germany and Belgium enforce strict drink-driving limits as well. Finish each day's drive first, check in, and visit every brewery on foot or local transit (e.g. Herrsching ↔ Kloster Andechs).</p>
      </div>
      <div class="practical-card">
        <h4>5. Best Season: May – September</h4>
        <p>Late spring through early autumn opens Bamberg's Greifenklau terrace, Forchheim's Kellerwald, Munich's chestnut-shaded Augustiner-Keller, Ammersee panoramas at Andechs, and Šumava forest trails.</p>
      </div>
      <div class="practical-card">
        <h4>6. Bottle Crate Space &amp; Airport Return</h4>
        <p>Keep a sturdy crate in the boot for De Hopduvel (Ghent), Kout 12°, and Franconian bottles — pack bubble sleeves for checked luggage before returning the rental car at FRA on Day 15.</p>
      </div>
    </div>
  </div>
</div>

<script>
window.ROUTE_2027 = {embedded_json};

let leafletMap = null;
const markerByStopId = {{}};
let routeBounds = null;

function fmtHmm(mins) {{
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return h === 0 ? (m + ' min') : (h + ' h ' + String(m).padStart(2, '0'));
}}

function switchTab(id, btnEl) {{
  document.querySelectorAll('.tab-content').forEach(pane => pane.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(btn => {{
    btn.classList.remove('active');
    btn.setAttribute('aria-selected', 'false');
  }});
  const targetPane = document.getElementById(id);
  if (targetPane) targetPane.classList.add('active');
  const activeBtn = btnEl || document.querySelector('.tab-btn[data-tab="' + id + '"]');
  if (activeBtn) {{
    activeBtn.classList.add('active');
    activeBtn.setAttribute('aria-selected', 'true');
  }}
  if (id === 'map') {{
    initMap();
    if (leafletMap) setTimeout(() => leafletMap.invalidateSize(), 80);
  }}
}}

// Keyboard arrow support on tablist
document.querySelector('.tabs').addEventListener('keydown', (e) => {{
  if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
  const btns = Array.from(document.querySelectorAll('.tab-btn'));
  const idx = btns.indexOf(document.activeElement);
  if (idx === -1) return;
  e.preventDefault();
  const next = btns[(idx + (e.key === 'ArrowRight' ? 1 : btns.length - 1)) % btns.length];
  next.focus();
  switchTab(next.dataset.tab, next);
}});

function filterDays(mode, btnEl) {{
  document.querySelectorAll('#itinerary-filters .filter-btn').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  const cards = Array.from(document.querySelectorAll('#itinerary-flowchart .day-node'));
  const connectors = Array.from(document.querySelectorAll('#itinerary-flowchart .connector'));

  cards.forEach(card => {{
    let show = true;
    if (mode === 'inplace') show = card.dataset.drive === 'no';
    else if (mode === 'long') show = card.dataset.long === 'yes';
    else if (mode !== 'all') show = card.dataset.region === mode;
    card.style.display = show ? '' : 'none';
  }});

  connectors.forEach((conn, idx) => {{
    const prevVis = cards[idx] && cards[idx].style.display !== 'none';
    const anyAfterVis = cards.slice(idx + 1).some(c => c.style.display !== 'none');
    conn.style.display = (prevVis && anyAfterVis) ? '' : 'none';
  }});
}}

let currentRankingCity = 'all';
function filterRankings(citySlug, btnEl) {{
  currentRankingCity = citySlug;
  document.querySelectorAll('#ranking-filters .filter-btn').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  applyRankingFilter();
}}

function searchRankings() {{
  applyRankingFilter();
}}

function applyRankingFilter() {{
  const q = (document.getElementById('venue-search').value || '').trim().toLowerCase();
  document.querySelectorAll('.city-ranking-section').forEach(sec => {{
    const secCity = sec.dataset.citySection;
    const cityMatch = (currentRankingCity === 'all' || secCity === currentRankingCity);
    let visibleCards = 0;
    sec.querySelectorAll('.brewery-card').forEach(card => {{
      const textMatch = !q || card.dataset.search.includes(q);
      const show = cityMatch && textMatch;
      card.style.display = show ? '' : 'none';
      if (show) visibleCards++;
    }});
    sec.style.display = visibleCards > 0 ? '' : 'none';
  }});
}}

function filterBeerRegions(regionSlug, btnEl) {{
  document.querySelectorAll('#beer-region-filters .filter-btn').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  document.querySelectorAll('.beer-region-block').forEach(sec => {{
    sec.style.display = (regionSlug === 'all' || sec.dataset.beerRegion === regionSlug) ? '' : 'none';
  }});
}}

function setMatrixMode(mode, btnEl) {{
  document.querySelectorAll('#matrix-mode-btns .filter-btn').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  document.getElementById('car-matrix').setAttribute('data-mode', mode);
}}

function filterDetours(countrySlug, btnEl) {{
  document.querySelectorAll('#detour-filters .filter-btn').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  document.querySelectorAll('.detour-base-group').forEach(sec => {{
    sec.style.display = (countrySlug === 'all' || sec.dataset.detourCountry === countrySlug) ? '' : 'none';
  }});
}}

function initMap() {{
  if (leafletMap) return;
  const container = document.getElementById('map-container');
  if (typeof window.L === 'undefined') {{
    container.innerHTML = '<div style="padding:2rem;color:#b0b9ce;text-align:center;">Leaflet library unavailable offline — view the full 4800×3120 route map poster right below.</div>';
    return;
  }}

  leafletMap = L.map('map-container', {{ zoomControl: true }}).setView([49.8, 9.2], 6);

  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
    attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
    maxZoom: 16
  }}).addTo(leafletMap);
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
    maxZoom: 16
  }}).addTo(leafletMap);

  const stops = window.ROUTE_2027.stops.slice().sort((a, b) => a.order - b.order);
  const stopById = {{}};
  stops.forEach(s => {{ stopById[s.id] = s; }});

  const legByFrom = {{}};
  window.ROUTE_2027.legs.forEach(l => {{ legByFrom[l.from] = l; }});
  const returnLeg = window.ROUTE_2027.legs[window.ROUTE_2027.legs.length - 1];

  const countryColors = {{
    Germany: '#f5a623',
    Belgium: '#ff7a59',
    Czechia: '#38bdf8'
  }};

  // Draw each route leg as an interactive polyline
  window.ROUTE_2027.legs.forEach((leg, idx) => {{
    const sA = stopById[leg.from];
    const sB = stopById[leg.to];
    const pts = [[sA.lat, sA.lon], [sB.lat, sB.lon]];
    const isFinal = idx === window.ROUTE_2027.legs.length - 1;
    const isLong = leg.day === 4 || leg.day === 10;
    const lineColor = isLong ? '#e94560' : (isFinal ? '#b283f8' : '#f5a623');

    // Subtle dark casing
    L.polyline(pts, {{ color: '#080a14', weight: 7, opacity: 0.75, interactive: false }}).addTo(leafletMap);

    const seg = L.polyline(pts, {{
      color: lineColor,
      weight: isLong ? 4 : 3.2,
      opacity: 0.9,
      dashArray: isFinal ? '8, 7' : null
    }}).addTo(leafletMap);

    seg.bindPopup(
      '<div class="popup-title">Day ' + leg.day + ' Drive</div>' +
      '<div class="popup-meta">' + sA.name + ' → ' + sB.name + '</div>' +
      '<div class="popup-next">' + leg.km.toFixed(1) + ' km (' + Math.round(leg.km) + ' km) · ' + fmtHmm(leg.minutes) + '</div>'
    );
  }});

  const boundsLatLngs = [];

  stops.forEach((s) => {{
    const visitNum = s.order + 1;
    boundsLatLngs.push([s.lat, s.lon]);
    const bgCol = s.kind === 'airport' ? '#4ecdc4' : (countryColors[s.country] || '#f5a623');

    const icon = L.divIcon({{
      className: '',
      html: '<div style="background:' + bgCol + ';color:#111322;width:28px;height:28px;border-radius:50%;border:2.5px solid #eef1f6;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:12px;box-shadow:0 3px 10px rgba(0,0,0,0.65);font-variant-numeric:tabular-nums;">' + visitNum + '</div>',
      iconSize: [28, 28],
      iconAnchor: [14, 14],
      popupAnchor: [0, -14]
    }});

    const nightsLine = s.nights > 0
      ? (s.nights + (s.nights === 1 ? ' night' : ' nights') + ' · ' + s.city + ', ' + s.country)
      : ('Start (Day 1) & End (Day 15) · ' + s.city + ', ' + s.country + ' · 0 nights');

    const addrLine = s.address
      ? '<div class="popup-addr">📍 ' + s.address + '</div>'
      : '';

    const nextLeg = legByFrom[s.id];
    let nextLine = '';
    if (nextLeg) {{
      const nextStop = stopById[nextLeg.to];
      nextLine = '<div class="popup-next"><strong>Next leg (Day ' + nextLeg.day + '):</strong> → ' +
        nextStop.name + ' · ' + nextLeg.km.toFixed(1) + ' km · ' + fmtHmm(nextLeg.minutes) + '</div>';
    }}
    if (s.id === 'fra' && returnLeg) {{
      const prevStop = stopById[returnLeg.from];
      nextLine += '<div class="popup-next" style="margin-top:5px;"><strong>Return leg (Day ' + returnLeg.day + '):</strong> ' +
        prevStop.name + ' → FRA · ' + returnLeg.km.toFixed(1) + ' km · ' + fmtHmm(returnLeg.minutes) + '</div>';
    }}

    const popupHtml =
      '<div class="popup-title">#' + visitNum + ' · ' + s.name + '</div>' +
      '<div class="popup-meta">' + nightsLine + '</div>' +
      addrLine +
      '<div class="popup-note">' + s.note + '</div>' +
      nextLine;

    const marker = L.marker([s.lat, s.lon], {{ icon: icon }}).bindPopup(popupHtml, {{ maxWidth: 320 }}).addTo(leafletMap);
    markerByStopId[s.id] = marker;
  }});

  routeBounds = L.latLngBounds(boundsLatLngs);
  leafletMap.fitBounds(routeBounds, {{ padding: [42, 42] }});

  const legend = L.control({{ position: 'bottomright' }});
  legend.onAdd = function() {{
    const div = L.DomUtil.create('div', 'legend');
    div.style.cssText = 'background:#151c35;color:#eef1f6;padding:10px 14px;border-radius:8px;border:1px solid #2b3658;box-shadow:0 6px 18px rgba(0,0,0,0.55);font-size:12px;line-height:1.75;';
    div.innerHTML =
      '<strong style="color:#f5a623;font-size:12.5px;">Route Legend (1–11)</strong><br>' +
      '<span style="display:inline-block;width:10px;height:10px;background:#4ecdc4;border-radius:50%;margin-right:6px;"></span>Start &amp; End (FRA)<br>' +
      '<span style="display:inline-block;width:10px;height:10px;background:#ff7a59;border-radius:50%;margin-right:6px;"></span>Belgium Base<br>' +
      '<span style="display:inline-block;width:10px;height:10px;background:#f5a623;border-radius:50%;margin-right:6px;"></span>Germany Base<br>' +
      '<span style="display:inline-block;width:10px;height:10px;background:#38bdf8;border-radius:50%;margin-right:6px;"></span>Czechia Base<br>' +
      '<span style="display:inline-block;width:18px;border-top:3px solid #e94560;vertical-align:middle;margin-right:6px;"></span>Long Drive (Days 4 &amp; 10)<br>' +
      '<span style="display:inline-block;width:18px;border-top:2.5px dashed #b283f8;vertical-align:middle;margin-right:6px;"></span>Day 15 Return to FRA';
    return div;
  }};
  legend.addTo(leafletMap);
}}

function fitFullRoute() {{
  initMap();
  if (leafletMap && routeBounds) {{
    leafletMap.fitBounds(routeBounds, {{ padding: [42, 42] }});
  }}
}}

function focusStopOnMap(stopId) {{
  switchTab('map');
  setTimeout(() => {{
    if (!leafletMap) return;
    const m = markerByStopId[stopId];
    if (m) {{
      leafletMap.setView(m.getLatLng(), 9, {{ animate: true }});
      m.openPopup();
    }}
  }}, 120);
}}
</script>
</body>
</html>
"""
    OUT_HTML.write_text(html_doc, encoding="utf-8")
    return OUT_HTML


if __name__ == "__main__":
    out = build()
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
