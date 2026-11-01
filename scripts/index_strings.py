# -*- coding: utf-8 -*-
"""Copy for the catalog page in EN / PT-BR / DE.

Trip entries keep their proper nouns; only the framing language changes.
`route` strings localise city names (Munich / Munique / München, Bruges / Brügge ...).
"""

LANGS = ["en", "pt", "de"]
LANG_ATTR = {"en": "en", "pt": "pt-BR", "de": "de"}
SITE = "https://renreisen.duckdns.org"

UI = {
    "en": {
        "title": "Every trip, every brewery, one archive — Bier Reisen",
        "desc": ("Five beer trips taken and one being planned: itineraries, route maps, brewery rankings "
                 "and every distance measured. Munich by rail, Belgian Trappists, Czech pilsner towns and "
                 "the village breweries of Franconia."),
        "og_title": "Every trip, every brewery, one archive",
        "og_desc": ("Five trips taken, one being planned. Day-by-day dossiers, route posters and brewery "
                    "rankings for beer travel across Europe and the United States."),
        "skip": "Skip to the trips",
        "h1_a": "Every trip, every brewery,",
        "h1_b": "one archive.",
        "standfirst": ("From nine nights in a single Munich hotel to the Belgian Trappists and the pilsner "
                       "towns of Bohemia. Every dossier carries the day-by-day plan, the route poster, the "
                       "brewery rankings and the distances behind them: <b>{km} km</b> across "
                       "<b>{days} days</b> so far."),
        "cta": "Read the archive",
        "search_ph": "Search a year, a city, a brewery",
        "aria_search": "Search trips",
        "aria_filter": "Filter trips",
        "f_all": "All",
        "f_travelled": "Travelled",
        "f_planned": "Planned",
        "f_drafts": "Drafts",
        "f_rail": "By rail",
        "h_trips": "The trips",
        "n_trips": "Six dossiers, newest first.",
        "h_ideas": "Drafted, not yet walked",
        "n_ideas": "Six routes built from research rather than memory.",
        "empty_a": "Nothing matches that. Try a year, a country or a brewery, or",
        "empty_b": "show everything again",
        "status_travelled": "Travelled",
        "status_planned": "Planned",
        "d_days": "days",
        "d_nights": "nights",
        "d_km_drive": "km driving",
        "d_km_rail": "km by rail",
        "d_stops": "stops",
        "open": "Open the dossier",
        "poster": "Route poster",
        "count": "{n} of {total}",
        "lang_label": "Language",
        "foot_a": "A personal archive of beer travel. Every dossier is a single HTML file; every distance "
                  "was measured, not estimated: OSRM for the driving years, great-circle for flights, "
                  "timetables for the years without a car.",
        "foot_how": "How this is built",
        "foot_data": "Route data",
        "foot_posters": "Regional posters",
        "foot_blog": "Notes from the road",
    },
    "pt": {
        "title": "Toda viagem, toda cervejaria, um arquivo — Bier Reisen",
        "desc": ("Cinco viagens cervejeiras realizadas e uma em planejamento: roteiros, mapas de rota, "
                 "rankings de cervejarias e todas as distâncias medidas. Munique de trem, os trapistas "
                 "belgas, as cidades da Pilsen na Boêmia e as cervejarias de aldeia da Francônia."),
        "og_title": "Toda viagem, toda cervejaria, um arquivo",
        "og_desc": ("Cinco viagens feitas, uma em planejamento. Dossiês dia a dia, pôsteres de rota e "
                    "rankings de cervejarias pela Europa e pelos Estados Unidos."),
        "skip": "Ir para as viagens",
        "h1_a": "Toda viagem, toda cervejaria,",
        "h1_b": "um arquivo.",
        "standfirst": ("De nove noites num único hotel em Munique aos trapistas belgas e às cidades da "
                       "Pilsen na Boêmia. Cada dossiê traz o roteiro dia a dia, o pôster da rota, o ranking "
                       "das cervejarias e as distâncias por trás deles: <b>{km} km</b> em "
                       "<b>{days} dias</b> até agora."),
        "cta": "Ler o arquivo",
        "search_ph": "Ano, cidade ou cervejaria",
        "aria_search": "Buscar viagens",
        "aria_filter": "Filtrar viagens",
        "f_all": "Todas",
        "f_travelled": "Realizadas",
        "f_planned": "Planejada",
        "f_drafts": "Rascunhos",
        "f_rail": "De trem",
        "h_trips": "As viagens",
        "n_trips": "Seis dossiês, do mais recente ao mais antigo.",
        "h_ideas": "Rascunhadas, ainda não caminhadas",
        "n_ideas": "Seis rotas feitas de pesquisa, não de memória.",
        "empty_a": "Nada corresponde a isso. Tente um ano, um país ou uma cervejaria, ou",
        "empty_b": "mostre tudo de novo",
        "status_travelled": "Realizada",
        "status_planned": "Planejada",
        "d_days": "dias",
        "d_nights": "noites",
        "d_km_drive": "km de carro",
        "d_km_rail": "km de trem",
        "d_stops": "paradas",
        "open": "Abrir o dossiê",
        "poster": "Pôster da rota",
        "count": "{n} de {total}",
        "lang_label": "Idioma",
        "foot_a": "Um arquivo pessoal de viagens cervejeiras. Cada dossiê é um único arquivo HTML; cada "
                  "distância foi medida, não estimada: OSRM nos anos de carro, distância geodésica nos voos, "
                  "horários oficiais nos anos sem carro.",
        "foot_how": "Como isto é feito",
        "foot_data": "Dados da rota",
        "foot_posters": "Pôsteres regionais",
        "foot_blog": "Notas de estrada",
    },
    "de": {
        "title": "Jede Reise, jede Brauerei, ein Archiv — Bier Reisen",
        "desc": ("Fünf unternommene Bierreisen und eine in Planung: Reiseverläufe, Routenkarten, "
                 "Brauereiranglisen und jede Distanz gemessen. München mit der Bahn, belgische Trappisten, "
                 "die Pilsner Städte Böhmens und die Dorfbrauereien Frankens."),
        "og_title": "Jede Reise, jede Brauerei, ein Archiv",
        "og_desc": ("Fünf Reisen gemacht, eine in Planung. Tagesdossiers, Routenposter und "
                    "Brauereiranglisten für Bierreisen durch Europa und die USA."),
        "skip": "Zu den Reisen springen",
        "h1_a": "Jede Reise, jede Brauerei,",
        "h1_b": "ein Archiv.",
        "standfirst": ("Von neun Nächten in einem Münchner Hotel zu den belgischen Trappisten und den "
                       "Pilsner Städten Böhmens. Jedes Dossier enthält den Tagesplan, das Routenposter, die "
                       "Brauereirangliste und die Distanzen dahinter: bisher <b>{km} km</b> in "
                       "<b>{days} Tagen</b>."),
        "cta": "Das Archiv ansehen",
        "search_ph": "Jahr, Stadt oder Brauerei suchen",
        "aria_search": "Reisen suchen",
        "aria_filter": "Reisen filtern",
        "f_all": "Alle",
        "f_travelled": "Gemacht",
        "f_planned": "Geplant",
        "f_drafts": "Entwürfe",
        "f_rail": "Mit der Bahn",
        "h_trips": "Die Reisen",
        "n_trips": "Sechs Dossiers, das neueste zuerst.",
        "h_ideas": "Entworfen, noch nicht gegangen",
        "n_ideas": "Sechs Routen aus Recherche statt aus Erinnerung.",
        "empty_a": "Dazu passt nichts. Versuch ein Jahr, ein Land oder eine Brauerei, oder",
        "empty_b": "zeig wieder alles",
        "status_travelled": "Gemacht",
        "status_planned": "Geplant",
        "d_days": "Tage",
        "d_nights": "Nächte",
        "d_km_drive": "km Fahrt",
        "d_km_rail": "km mit der Bahn",
        "d_stops": "Stationen",
        "open": "Dossier öffnen",
        "poster": "Routenposter",
        "count": "{n} von {total}",
        "lang_label": "Sprache",
        "foot_a": "Ein persönliches Archiv von Bierreisen. Jedes Dossier ist eine einzelne HTML-Datei; jede "
                  "Distanz wurde gemessen, nicht geschätzt: OSRM in den Autojahren, Großkreis bei Flügen, "
                  "Fahrpläne in den Jahren ohne Auto.",
        "foot_how": "Wie das gebaut ist",
        "foot_data": "Routendaten",
        "foot_posters": "Regionale Poster",
        "foot_blog": "Notizen von unterwegs",
    },
}

TRIPS = {
    "2027": {
        "en": {"title": "The 2027 plan · Würzburg route",
               "route": "Frankfurt → Bruges → Ghent → Bamberg → Sokolov → Plzeň → Kout na Šumavě → "
                        "Maxlrain → Andechs → Munich → Nuremberg → Frankfurt",
               "blurb": "Two nights in Bruges, two in Bamberg, both Czech brewing towns and a night in a "
                        "Franconian castle brewery, with the long Ghent → Bamberg day split at Würzburg. "
                        "The route this archive has been building towards."},
        "pt": {"title": "O plano de 2027 · rota por Würzburg",
               "route": "Frankfurt → Bruges → Gante → Bamberg → Sokolov → Plzeň → Kout na Šumavě → "
                        "Maxlrain → Andechs → Munique → Nuremberg → Frankfurt",
               "blurb": "Duas noites em Bruges, duas em Bamberg, as duas cidades cervejeiras tchecas e uma "
                        "noite num castelo-cervejaria da Francônia, com o longo dia Gante → Bamberg "
                        "dividido em Würzburg. A rota para a qual este arquivo foi construído."},
        "de": {"title": "Der Plan für 2027 · Route über Würzburg",
               "route": "Frankfurt → Brügge → Gent → Bamberg → Sokolov → Plzeň → Kout na Šumavě → "
                        "Maxlrain → Andechs → München → Nürnberg → Frankfurt",
               "blurb": "Zwei Nächte in Brügge, zwei in Bamberg, beide tschechischen Braustädte und eine "
                        "Nacht in einer fränkischen Schlossbrauerei, mit dem langen Tag Gent → Bamberg "
                        "geteilt in Würzburg. Die Route, auf die dieses Archiv hinausläuft."},
    },
    "2026": {
        "en": {"title": "Franconia, Bohemia and the Alps",
               "route": "Frankfurt → Merkendorf → Plzeň → České Budějovice → Bad Reichenhall → Munich",
               "blurb": "Three nights in a village brewery, two with Budvar, three under the Watzmann with "
                        "Salzburg across the border, then four in Munich."},
        "pt": {"title": "Francônia, Boêmia e os Alpes",
               "route": "Frankfurt → Merkendorf → Plzeň → České Budějovice → Bad Reichenhall → Munique",
               "blurb": "Três noites numa cervejaria de aldeia, duas com a Budvar, três sob o Watzmann com "
                        "Salzburgo do outro lado da fronteira, e depois quatro em Munique."},
        "de": {"title": "Franken, Böhmen und die Alpen",
               "route": "Frankfurt → Merkendorf → Plzeň → České Budějovice → Bad Reichenhall → München",
               "blurb": "Drei Nächte in einer Dorfbrauerei, zwei bei Budvar, drei unter dem Watzmann mit "
                        "Salzburg gleich hinter der Grenze, dann vier in München."},
    },
    "2024": {
        "en": {"title": "Franconia, Bohemia and Advent",
               "route": "Frankfurt → Memmelsdorf → Plzeň → České Budějovice → Berchtesgaden → Munich",
               "blurb": "Late November: Christmas markets opening, brewery tours half empty, and the other "
                        "Budweiser in its home town."},
        "pt": {"title": "Francônia, Boêmia e o Advento",
               "route": "Frankfurt → Memmelsdorf → Plzeň → České Budějovice → Berchtesgaden → Munique",
               "blurb": "Fim de novembro: mercados de Natal abrindo, visitas a cervejarias pela metade e a "
                        "outra Budweiser na cidade onde nasceu."},
        "de": {"title": "Franken, Böhmen und der Advent",
               "route": "Frankfurt → Memmelsdorf → Plzeň → České Budějovice → Berchtesgaden → München",
               "blurb": "Ende November: Weihnachtsmärkte öffnen, Brauereiführungen sind halb leer, und der "
                        "andere Budweiser in seiner Heimatstadt."},
    },
    "2021": {
        "en": {"title": "Bamberg to the Allgäu",
               "route": "Frankfurt → Bamberg → Nuremberg → Essing → Traunstein → Schönram → Berchtesgaden "
                        "→ Nesselwang → Missen-Wilhams → Munich",
               "blurb": "Village breweries and two nights sleeping above the brewhouse, then a week in "
                        "Munich at the end of October."},
        "pt": {"title": "De Bamberg ao Allgäu",
               "route": "Frankfurt → Bamberg → Nuremberg → Essing → Traunstein → Schönram → Berchtesgaden "
                        "→ Nesselwang → Missen-Wilhams → Munique",
               "blurb": "Cervejarias de aldeia e duas noites dormindo acima da sala de brassagem, depois "
                        "uma semana em Munique no fim de outubro."},
        "de": {"title": "Von Bamberg ins Allgäu",
               "route": "Frankfurt → Bamberg → Nürnberg → Essing → Traunstein → Schönram → Berchtesgaden "
                        "→ Nesselwang → Missen-Wilhams → München",
               "blurb": "Dorfbrauereien und zwei Nächte über dem Sudhaus, dann eine Woche München Ende "
                        "Oktober."},
    },
    "2020": {
        "en": {"title": "The first European loop",
               "route": "Munich → Bamberg → Düsseldorf → La Trappe → Antwerp → Brussels → Bruges → "
                        "Westvleteren → Chimay → Zwiefaltendorf → Munich",
               "blurb": "The trip that started it: Altbier, Trappists, lambic, and a Swabian village "
                        "brewery on the Danube on the way home."},
        "pt": {"title": "O primeiro circuito europeu",
               "route": "Munique → Bamberg → Düsseldorf → La Trappe → Antuérpia → Bruxelas → Bruges → "
                        "Westvleteren → Chimay → Zwiefaltendorf → Munique",
               "blurb": "A viagem que começou tudo: Altbier, trapistas, lambic e uma cervejaria de aldeia da "
                        "Suábia no Danúbio, no caminho de volta."},
        "de": {"title": "Die erste Europaschleife",
               "route": "München → Bamberg → Düsseldorf → La Trappe → Antwerpen → Brüssel → Brügge → "
                        "Westvleteren → Chimay → Zwiefaltendorf → München",
               "blurb": "Die Reise, mit der alles begann: Altbier, Trappisten, Lambic und eine schwäbische "
                        "Dorfbrauerei an der Donau auf dem Rückweg."},
    },
    "2019": {
        "en": {"title": "Munich by rail",
               "route": "Munich · Andechs · Aying · Bamberg",
               "blurb": "The first one, and the only one without a car: nine nights in one hotel, with day "
                        "returns to a monastery, a village brewery and a Rauchbier town."},
        "pt": {"title": "Munique de trem",
               "route": "Munique · Andechs · Aying · Bamberg",
               "blurb": "A primeira, e a única sem carro: nove noites num único hotel, com idas e voltas de "
                        "trem a um mosteiro, uma cervejaria de aldeia e uma cidade da Rauchbier."},
        "de": {"title": "München mit der Bahn",
               "route": "München · Andechs · Aying · Bamberg",
               "blurb": "Die erste und die einzige ohne Auto: neun Nächte in einem Hotel, mit Tagesausflügen "
                        "zu einem Kloster, einer Dorfbrauerei und einer Rauchbierstadt."},
    },
}

IDEAS = {
    "uk": {"en": "UK Beer Pilgrimage", "pt": "Peregrinação Cervejeira pelo Reino Unido",
           "de": "Bierpilgerreise durch Großbritannien"},
    "belgian": {"en": "Belgian Beer Pilgrimage", "pt": "Peregrinação Cervejeira Belga",
                "de": "Belgische Bierpilgerreise"},
    "bavaria-bohemia": {"en": "Bavaria & Bohemia", "pt": "Baviera e Boêmia", "de": "Bayern und Böhmen"},
    "colorado": {"en": "Colorado Craft Beer Odyssey", "pt": "Odisseia da Cerveja Artesanal do Colorado",
                 "de": "Colorado Craft-Bier-Odyssee"},
    "florida": {"en": "Florida Brewery Trail", "pt": "Rota das Cervejarias da Flórida",
                "de": "Florida Brauereiroute"},
    "italy-grand-tour": {"en": "Italy & Switzerland Grand Tour", "pt": "Grand Tour Itália e Suíça",
                         "de": "Grand Tour Italien und Schweiz"},
}
