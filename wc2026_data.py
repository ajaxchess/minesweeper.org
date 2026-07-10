"""
wc2026_data.py — Static data for the 2026 FIFA World Cup celebration feature (F97).

All times stored as CDT strings (UTC-5) as published in the official schedule.
"""

# ── Countries ─────────────────────────────────────────────────────────────────
# Each entry: slug, display name, flag CDN code, primary hex, secondary hex,
#             group letter, ottawa treaty signatory status

WC2026_COUNTRIES = [
    # Group A
    {"slug": "mexico",               "name": "Mexico",              "flag": "mx", "primary": "#006847", "secondary": "#FFFFFF", "group": "A", "ottawa": True},
    {"slug": "south-africa",         "name": "South Africa",        "flag": "za", "primary": "#FFCD00", "secondary": "#007A33", "group": "A", "ottawa": True},
    {"slug": "south-korea",          "name": "South Korea",         "flag": "kr", "primary": "#ED1C24", "secondary": "#000000", "group": "A", "ottawa": False},
    {"slug": "czech-republic",       "name": "Czech Republic",      "flag": "cz", "primary": "#ED1B24", "secondary": "#11457E", "group": "A", "ottawa": True},
    # Group B
    {"slug": "canada",               "name": "Canada",              "flag": "ca", "primary": "#FF0000", "secondary": "#FFFFFF", "group": "B", "ottawa": True},
    {"slug": "bosnia-and-herzegovina","name": "Bosnia & Herz.",     "flag": "ba", "primary": "#002395", "secondary": "#FECB00", "group": "B", "ottawa": True},
    {"slug": "qatar",                "name": "Qatar",               "flag": "qa", "primary": "#8A1538", "secondary": "#FFFFFF", "group": "B", "ottawa": False},
    {"slug": "switzerland",          "name": "Switzerland",         "flag": "ch", "primary": "#D52B1E", "secondary": "#FFFFFF", "group": "B", "ottawa": True},
    # Group C
    {"slug": "brazil",               "name": "Brazil",              "flag": "br", "primary": "#FFDF00", "secondary": "#009B3A", "group": "C", "ottawa": True},
    {"slug": "morocco",              "name": "Morocco",             "flag": "ma", "primary": "#C1272D", "secondary": "#006233", "group": "C", "ottawa": True},
    {"slug": "haiti",                "name": "Haiti",               "flag": "ht", "primary": "#00209F", "secondary": "#D21034", "group": "C", "ottawa": True},
    {"slug": "scotland",             "name": "Scotland",            "flag": "gb-sct", "primary": "#002D56", "secondary": "#FFFFFF", "group": "C", "ottawa": True},
    # Group D
    {"slug": "usa",                  "name": "USA",                 "flag": "us", "primary": "#FFFFFF", "secondary": "#002868", "group": "D", "ottawa": False},
    {"slug": "paraguay",             "name": "Paraguay",            "flag": "py", "primary": "#D52B1E", "secondary": "#FFFFFF", "group": "D", "ottawa": True},
    {"slug": "australia",            "name": "Australia",           "flag": "au", "primary": "#FFCD00", "secondary": "#005031", "group": "D", "ottawa": True},
    {"slug": "turkey",               "name": "Türkiye",             "flag": "tr", "primary": "#E30A17", "secondary": "#FFFFFF", "group": "D", "ottawa": True},
    # Group E
    {"slug": "germany",              "name": "Germany",             "flag": "de", "primary": "#FFFFFF", "secondary": "#000000", "group": "E", "ottawa": True},
    {"slug": "curacao",              "name": "Curaçao",             "flag": "cw", "primary": "#002B7F", "secondary": "#F9D616", "group": "E", "ottawa": False},
    {"slug": "ivory-coast",          "name": "Ivory Coast",         "flag": "ci", "primary": "#FF8200", "secondary": "#009E60", "group": "E", "ottawa": True},
    {"slug": "ecuador",              "name": "Ecuador",             "flag": "ec", "primary": "#FFDD00", "secondary": "#034EA2", "group": "E", "ottawa": True},
    # Group F
    {"slug": "netherlands",          "name": "Netherlands",         "flag": "nl", "primary": "#FF4F00", "secondary": "#FFFFFF", "group": "F", "ottawa": True},
    {"slug": "japan",                "name": "Japan",               "flag": "jp", "primary": "#000555", "secondary": "#FFFFFF", "group": "F", "ottawa": True},
    {"slug": "sweden",               "name": "Sweden",              "flag": "se", "primary": "#FECC00", "secondary": "#006AA7", "group": "F", "ottawa": True},
    {"slug": "tunisia",              "name": "Tunisia",             "flag": "tn", "primary": "#FFFFFF", "secondary": "#E70013", "group": "F", "ottawa": True},
    # Group G
    {"slug": "belgium",              "name": "Belgium",             "flag": "be", "primary": "#BA0C2F", "secondary": "#FFCD00", "group": "G", "ottawa": True},
    {"slug": "egypt",                "name": "Egypt",               "flag": "eg", "primary": "#E20111", "secondary": "#000000", "group": "G", "ottawa": False},
    {"slug": "iran",                 "name": "Iran",                "flag": "ir", "primary": "#FFFFFF", "secondary": "#DA291C", "group": "G", "ottawa": False},
    {"slug": "new-zealand",          "name": "New Zealand",         "flag": "nz", "primary": "#FFFFFF", "secondary": "#000000", "group": "G", "ottawa": True},
    # Group H
    {"slug": "spain",                "name": "Spain",               "flag": "es", "primary": "#C60B1E", "secondary": "#FFC400", "group": "H", "ottawa": True},
    {"slug": "cape-verde",           "name": "Cape Verde",          "flag": "cv", "primary": "#003893", "secondary": "#F7D117", "group": "H", "ottawa": True},
    {"slug": "saudi-arabia",         "name": "Saudi Arabia",        "flag": "sa", "primary": "#006C35", "secondary": "#FFFFFF", "group": "H", "ottawa": False},
    {"slug": "uruguay",              "name": "Uruguay",             "flag": "uy", "primary": "#75AADB", "secondary": "#000000", "group": "H", "ottawa": True},
    # Group I
    {"slug": "france",               "name": "France",              "flag": "fr", "primary": "#21304D", "secondary": "#ED2939", "group": "I", "ottawa": True},
    {"slug": "senegal",              "name": "Senegal",             "flag": "sn", "primary": "#FFFFFF", "secondary": "#11A335", "group": "I", "ottawa": True},
    {"slug": "iraq",                 "name": "Iraq",                "flag": "iq", "primary": "#007A33", "secondary": "#FFFFFF", "group": "I", "ottawa": True},
    {"slug": "norway",               "name": "Norway",              "flag": "no", "primary": "#EF2B2D", "secondary": "#002868", "group": "I", "ottawa": True},
    # Group J
    {"slug": "argentina",            "name": "Argentina",           "flag": "ar", "primary": "#75AADB", "secondary": "#FFFFFF", "group": "J", "ottawa": True},
    {"slug": "algeria",              "name": "Algeria",             "flag": "dz", "primary": "#FFFFFF", "secondary": "#006233", "group": "J", "ottawa": True},
    {"slug": "austria",              "name": "Austria",             "flag": "at", "primary": "#ED2939", "secondary": "#FFFFFF", "group": "J", "ottawa": True},
    {"slug": "jordan",               "name": "Jordan",              "flag": "jo", "primary": "#FFFFFF", "secondary": "#CE1126", "group": "J", "ottawa": True},
    # Group K
    {"slug": "portugal",             "name": "Portugal",            "flag": "pt", "primary": "#E42518", "secondary": "#046A38", "group": "K", "ottawa": True},
    {"slug": "dr-congo",             "name": "DR Congo",            "flag": "cd", "primary": "#007FFF", "secondary": "#F7D117", "group": "K", "ottawa": True},
    {"slug": "uzbekistan",           "name": "Uzbekistan",          "flag": "uz", "primary": "#FFFFFF", "secondary": "#0099B5", "group": "K", "ottawa": False},
    {"slug": "colombia",             "name": "Colombia",            "flag": "co", "primary": "#FCD116", "secondary": "#003893", "group": "K", "ottawa": True},
    # Group L
    {"slug": "england",              "name": "England",             "flag": "gb-eng", "primary": "#FFFFFF", "secondary": "#000040", "group": "L", "ottawa": True},
    {"slug": "croatia",              "name": "Croatia",             "flag": "hr", "primary": "#FF0000", "secondary": "#FFFFFF", "group": "L", "ottawa": True},
    {"slug": "ghana",                "name": "Ghana",               "flag": "gh", "primary": "#FFFFFF", "secondary": "#000000", "group": "L", "ottawa": True},
    {"slug": "panama",               "name": "Panama",              "flag": "pa", "primary": "#DA121A", "secondary": "#072357", "group": "L", "ottawa": True},
]

# Fast lookups
WC2026_BY_SLUG  = {c["slug"]: c for c in WC2026_COUNTRIES}
WC2026_BY_GROUP = {}
for _c in WC2026_COUNTRIES:
    WC2026_BY_GROUP.setdefault(_c["group"], []).append(_c)

VALID_WC2026_SLUGS = frozenset(WC2026_BY_SLUG)

# Ordered group list
WC2026_GROUPS = ["A","B","C","D","E","F","G","H","I","J","K","L"]


# ── Matches ───────────────────────────────────────────────────────────────────
# status: "scheduled" | "in_progress" | "final"
# score1/score2: None until final

WC2026_MATCHES_SEED = [
    # Group A
    {"group": "A", "date": "2026-06-11", "team1": "mexico",       "team2": "south-africa",  "time_cdt": "14:00", "city": "Mexico City"},
    {"group": "A", "date": "2026-06-11", "team1": "south-korea",  "team2": "czech-republic","time_cdt": "21:00", "city": "Guadalajara"},
    {"group": "A", "date": "2026-06-16", "team1": "mexico",       "team2": "south-korea",   "time_cdt": "17:00", "city": "Monterrey"},
    {"group": "A", "date": "2026-06-16", "team1": "czech-republic","team2": "south-africa", "time_cdt": "20:00", "city": "Seattle"},
    {"group": "A", "date": "2026-06-24", "team1": "czech-republic","team2": "mexico",       "time_cdt": "20:00", "city": "Mexico City"},
    {"group": "A", "date": "2026-06-24", "team1": "south-africa", "team2": "south-korea",   "time_cdt": "20:00", "city": "Monterrey"},
    # Group B
    {"group": "B", "date": "2026-06-12", "team1": "canada",       "team2": "bosnia-and-herzegovina","time_cdt": "14:00", "city": "Toronto"},
    {"group": "B", "date": "2026-06-13", "team1": "qatar",        "team2": "switzerland",   "time_cdt": "14:00", "city": "Vancouver"},
    {"group": "B", "date": "2026-06-17", "team1": "canada",       "team2": "qatar",         "time_cdt": "12:00", "city": "Toronto"},
    {"group": "B", "date": "2026-06-17", "team1": "switzerland",  "team2": "bosnia-and-herzegovina","time_cdt": "20:00", "city": "Vancouver"},
    {"group": "B", "date": "2026-06-24", "team1": "switzerland",  "team2": "canada",        "time_cdt": "14:00", "city": "Vancouver"},
    {"group": "B", "date": "2026-06-24", "team1": "bosnia-and-herzegovina","team2": "qatar","time_cdt": "14:00", "city": "Toronto"},
    # Group C
    {"group": "C", "date": "2026-06-13", "team1": "brazil",       "team2": "morocco",       "time_cdt": "17:00", "city": "Miami"},
    {"group": "C", "date": "2026-06-13", "team1": "haiti",        "team2": "scotland",      "time_cdt": "20:00", "city": "New York/New Jersey"},
    {"group": "C", "date": "2026-06-18", "team1": "brazil",       "team2": "haiti",         "time_cdt": "14:00", "city": "Atlanta"},
    {"group": "C", "date": "2026-06-18", "team1": "scotland",     "team2": "morocco",       "time_cdt": "17:00", "city": "Miami"},
    {"group": "C", "date": "2026-06-24", "team1": "scotland",     "team2": "brazil",        "time_cdt": "11:00", "city": "Miami"},
    {"group": "C", "date": "2026-06-24", "team1": "morocco",      "team2": "haiti",         "time_cdt": "11:00", "city": "Atlanta"},
    # Group D
    {"group": "D", "date": "2026-06-12", "team1": "usa",          "team2": "paraguay",      "time_cdt": "20:00", "city": "Los Angeles"},
    {"group": "D", "date": "2026-06-13", "team1": "australia",    "team2": "turkey",        "time_cdt": "23:00", "city": "Seattle"},
    {"group": "D", "date": "2026-06-19", "team1": "usa",          "team2": "australia",     "time_cdt": "20:00", "city": "Seattle"},
    {"group": "D", "date": "2026-06-19", "team1": "turkey",       "team2": "paraguay",      "time_cdt": "17:00", "city": "San Francisco"},
    {"group": "D", "date": "2026-06-25", "team1": "turkey",       "team2": "usa",           "time_cdt": "20:00", "city": "Los Angeles"},
    {"group": "D", "date": "2026-06-25", "team1": "paraguay",     "team2": "australia",     "time_cdt": "20:00", "city": "San Francisco"},
    # Group E
    {"group": "E", "date": "2026-06-14", "team1": "germany",      "team2": "curacao",       "time_cdt": "12:00", "city": "Kansas City"},
    {"group": "E", "date": "2026-06-14", "team1": "ivory-coast",  "team2": "ecuador",       "time_cdt": "18:00", "city": "Dallas"},
    {"group": "E", "date": "2026-06-20", "team1": "germany",      "team2": "ivory-coast",   "time_cdt": "14:00", "city": "Kansas City"},
    {"group": "E", "date": "2026-06-20", "team1": "ecuador",      "team2": "curacao",       "time_cdt": "11:00", "city": "Dallas"},
    {"group": "E", "date": "2026-06-25", "team1": "ecuador",      "team2": "germany",       "time_cdt": "14:00", "city": "Dallas"},
    {"group": "E", "date": "2026-06-25", "team1": "curacao",      "team2": "ivory-coast",   "time_cdt": "14:00", "city": "Kansas City"},
    # Group F
    {"group": "F", "date": "2026-06-14", "team1": "netherlands",  "team2": "japan",         "time_cdt": "15:00", "city": "Houston"},
    {"group": "F", "date": "2026-06-14", "team1": "sweden",       "team2": "tunisia",       "time_cdt": "21:00", "city": "Monterrey"},
    {"group": "F", "date": "2026-06-20", "team1": "netherlands",  "team2": "sweden",        "time_cdt": "20:00", "city": "Houston"},
    {"group": "F", "date": "2026-06-20", "team1": "tunisia",      "team2": "japan",         "time_cdt": "17:00", "city": "Guadalajara"},
    {"group": "F", "date": "2026-06-25", "team1": "tunisia",      "team2": "netherlands",   "time_cdt": "11:00", "city": "Houston"},
    {"group": "F", "date": "2026-06-25", "team1": "japan",        "team2": "sweden",        "time_cdt": "11:00", "city": "Monterrey"},
    # Group G
    {"group": "G", "date": "2026-06-15", "team1": "belgium",      "team2": "egypt",         "time_cdt": "14:00", "city": "Boston"},
    {"group": "G", "date": "2026-06-15", "team1": "iran",         "team2": "new-zealand",   "time_cdt": "20:00", "city": "Philadelphia"},
    {"group": "G", "date": "2026-06-21", "team1": "belgium",      "team2": "iran",          "time_cdt": "11:00", "city": "Philadelphia"},
    {"group": "G", "date": "2026-06-21", "team1": "new-zealand",  "team2": "egypt",         "time_cdt": "14:00", "city": "Boston"},
    {"group": "G", "date": "2026-06-26", "team1": "new-zealand",  "team2": "belgium",       "time_cdt": "20:00", "city": "Boston"},
    {"group": "G", "date": "2026-06-26", "team1": "egypt",        "team2": "iran",          "time_cdt": "20:00", "city": "Philadelphia"},
    # Group H
    {"group": "H", "date": "2026-06-15", "team1": "spain",        "team2": "cape-verde",    "time_cdt": "11:00", "city": "Los Angeles"},
    {"group": "H", "date": "2026-06-15", "team1": "saudi-arabia", "team2": "uruguay",       "time_cdt": "17:00", "city": "San Francisco"},
    {"group": "H", "date": "2026-06-21", "team1": "spain",        "team2": "saudi-arabia",  "time_cdt": "20:00", "city": "Los Angeles"},
    {"group": "H", "date": "2026-06-21", "team1": "uruguay",      "team2": "cape-verde",    "time_cdt": "17:00", "city": "San Francisco"},
    {"group": "H", "date": "2026-06-26", "team1": "uruguay",      "team2": "spain",         "time_cdt": "14:00", "city": "San Francisco"},
    {"group": "H", "date": "2026-06-26", "team1": "cape-verde",   "team2": "saudi-arabia",  "time_cdt": "14:00", "city": "Los Angeles"},
    # Group I
    {"group": "I", "date": "2026-06-16", "team1": "france",       "team2": "senegal",       "time_cdt": "14:00", "city": "New York/New Jersey"},
    {"group": "I", "date": "2026-06-16", "team1": "iraq",         "team2": "norway",        "time_cdt": "17:00", "city": "Boston"},
    {"group": "I", "date": "2026-06-22", "team1": "france",       "team2": "iraq",          "time_cdt": "12:00", "city": "New York/New Jersey"},
    {"group": "I", "date": "2026-06-22", "team1": "norway",       "team2": "senegal",       "time_cdt": "15:00", "city": "Boston"},
    {"group": "I", "date": "2026-06-26", "team1": "norway",       "team2": "france",        "time_cdt": "11:00", "city": "Boston"},
    {"group": "I", "date": "2026-06-26", "team1": "senegal",      "team2": "iraq",          "time_cdt": "11:00", "city": "New York/New Jersey"},
    # Group J
    {"group": "J", "date": "2026-06-16", "team1": "argentina",    "team2": "algeria",       "time_cdt": "20:00", "city": "Dallas"},
    {"group": "J", "date": "2026-06-16", "team1": "austria",      "team2": "jordan",        "time_cdt": "23:00", "city": "Houston"},
    {"group": "J", "date": "2026-06-22", "team1": "argentina",    "team2": "austria",       "time_cdt": "20:00", "city": "Dallas"},
    {"group": "J", "date": "2026-06-22", "team1": "jordan",       "team2": "algeria",       "time_cdt": "17:00", "city": "Houston"},
    {"group": "J", "date": "2026-06-27", "team1": "jordan",       "team2": "argentina",     "time_cdt": "20:00", "city": "Dallas"},
    {"group": "J", "date": "2026-06-27", "team1": "algeria",      "team2": "austria",       "time_cdt": "20:00", "city": "Houston"},
    # Group K
    {"group": "K", "date": "2026-06-17", "team1": "portugal",     "team2": "dr-congo",      "time_cdt": "12:00", "city": "Miami"},
    {"group": "K", "date": "2026-06-17", "team1": "uzbekistan",   "team2": "colombia",      "time_cdt": "21:00", "city": "Atlanta"},
    {"group": "K", "date": "2026-06-23", "team1": "portugal",     "team2": "uzbekistan",    "time_cdt": "14:00", "city": "Atlanta"},
    {"group": "K", "date": "2026-06-23", "team1": "colombia",     "team2": "dr-congo",      "time_cdt": "11:00", "city": "Miami"},
    {"group": "K", "date": "2026-06-27", "team1": "colombia",     "team2": "portugal",      "time_cdt": "14:00", "city": "Miami"},
    {"group": "K", "date": "2026-06-27", "team1": "dr-congo",     "team2": "uzbekistan",    "time_cdt": "14:00", "city": "Atlanta"},
    # Group L
    {"group": "L", "date": "2026-06-17", "team1": "england",      "team2": "croatia",       "time_cdt": "15:00", "city": "Toronto"},
    {"group": "L", "date": "2026-06-17", "team1": "ghana",        "team2": "panama",        "time_cdt": "18:00", "city": "Vancouver"},
    {"group": "L", "date": "2026-06-23", "team1": "england",      "team2": "ghana",         "time_cdt": "20:00", "city": "Toronto"},
    {"group": "L", "date": "2026-06-23", "team1": "panama",       "team2": "croatia",       "time_cdt": "17:00", "city": "Vancouver"},
    {"group": "L", "date": "2026-06-27", "team1": "panama",       "team2": "england",       "time_cdt": "11:00", "city": "Vancouver"},
    {"group": "L", "date": "2026-06-27", "team1": "croatia",      "team2": "ghana",         "time_cdt": "11:00", "city": "Toronto"},
]

# ── Stadiums ──────────────────────────────────────────────────────────────────

WC2026_STADIUMS = {
    "Mexico City":        {"stadium": "Estadio Azteca",         "lat": 19.3029,  "lon": -99.1505},
    "Guadalajara":        {"stadium": "Estadio Akron",          "lat": 20.6811,  "lon": -103.4628},
    "Monterrey":          {"stadium": "Estadio BBVA",           "lat": 25.6700,  "lon": -100.2447},
    "Toronto":            {"stadium": "BMO Field",              "lat": 43.6332,  "lon": -79.4186},
    "Vancouver":          {"stadium": "BC Place",               "lat": 49.2768,  "lon": -123.1120},
    "Los Angeles":        {"stadium": "SoFi Stadium",           "lat": 33.9535,  "lon": -118.3390},
    "New York/New Jersey":{"stadium": "MetLife Stadium",        "lat": 40.8128,  "lon": -74.0742},
    "Miami":              {"stadium": "Hard Rock Stadium",      "lat": 25.9581,  "lon": -80.2389},
    "Atlanta":            {"stadium": "Mercedes-Benz Stadium",  "lat": 33.7553,  "lon": -84.4006},
    "Seattle":            {"stadium": "Lumen Field",            "lat": 47.5952,  "lon": -122.3316},
    "San Francisco":      {"stadium": "Levi's Stadium",         "lat": 37.4033,  "lon": -121.9694},
    "Dallas":             {"stadium": "AT&T Stadium",           "lat": 32.7473,  "lon": -97.0945},
    "Houston":            {"stadium": "NRG Stadium",            "lat": 29.6847,  "lon": -95.4107},
    "Kansas City":        {"stadium": "Arrowhead Stadium",      "lat": 39.0490,  "lon": -94.4839},
    "Philadelphia":       {"stadium": "Lincoln Financial Field","lat": 39.9008,  "lon": -75.1675},
    "Boston":             {"stadium": "Gillette Stadium",       "lat": 42.0909,  "lon": -71.2643},
}

# Board dimensions
WC2026_EASY = {"cols": 15, "rows": 9,  "mines": 20, "top_rows": 5, "solve_bonus": 20}
WC2026_HARD = {"cols": 30, "rows": 18, "mines": 99, "top_rows": 9, "solve_bonus": 50}


# ── Knockout stage ────────────────────────────────────────────────────────────
# Bracket matches after the group stage. Unlike group matches, the two teams
# in a knockout slot aren't known until earlier rounds finish, so team1/team2
# are None (rendered as "TBD") until resolved. source_game_id is the stable id
# from the worldcup26.ir schedule — scripts/sync_wc2026_scores.py uses it to
# find/update the right row (including backfilling team1/team2 once decided)
# instead of matching by team slug, which only works once both teams are set.
#
# round: "r32" | "r16" | "qf" | "sf" | "third" | "final"
# Snapshot: R32/R16/QF1 (France–Morocco) final; remaining QFs scheduled,
# SF/3rd/Final TBD. Run scripts/sync_wc2026_scores.py to pick up later results.

WC2026_ROUND_ORDER  = ["r32", "r16", "qf", "sf", "third", "final"]
WC2026_ROUND_LABELS = {
    "r32":   "Round of 32",
    "r16":   "Round of 16",
    "qf":    "Quarterfinal",
    "sf":    "Semifinal",
    "third": "Third Place Match",
    "final": "Final",
}

WC2026_KNOCKOUT_SEED = [
    # Round of 32 — 2026-06-28 to 2026-07-03 (all final)
    {"source_game_id": 73, "round": "r32", "date": "2026-06-28", "time_cdt": "14:00", "city": "Los Angeles",         "team1": "south-africa",  "team2": "canada",                "score1": 0, "score2": 1, "status": "final"},
    {"source_game_id": 74, "round": "r32", "date": "2026-06-29", "time_cdt": "15:30", "city": "Boston",              "team1": "germany",        "team2": "paraguay",              "score1": 1, "score2": 1, "status": "final"},
    {"source_game_id": 75, "round": "r32", "date": "2026-06-29", "time_cdt": "20:00", "city": "Monterrey",           "team1": "netherlands",    "team2": "morocco",               "score1": 1, "score2": 1, "status": "final"},
    {"source_game_id": 76, "round": "r32", "date": "2026-06-29", "time_cdt": "12:00", "city": "Houston",             "team1": "brazil",         "team2": "japan",                 "score1": 2, "score2": 1, "status": "final"},
    {"source_game_id": 77, "round": "r32", "date": "2026-06-30", "time_cdt": "16:00", "city": "New York/New Jersey", "team1": "france",         "team2": "sweden",                "score1": 3, "score2": 0, "status": "final"},
    {"source_game_id": 78, "round": "r32", "date": "2026-06-30", "time_cdt": "12:00", "city": "Dallas",              "team1": "ivory-coast",    "team2": "norway",                "score1": 1, "score2": 2, "status": "final"},
    {"source_game_id": 79, "round": "r32", "date": "2026-06-30", "time_cdt": "20:00", "city": "Mexico City",         "team1": "mexico",         "team2": "ecuador",               "score1": 2, "score2": 0, "status": "final"},
    {"source_game_id": 80, "round": "r32", "date": "2026-07-01", "time_cdt": "11:00", "city": "Atlanta",             "team1": "england",        "team2": "dr-congo",              "score1": 2, "score2": 1, "status": "final"},
    {"source_game_id": 81, "round": "r32", "date": "2026-07-01", "time_cdt": "19:00", "city": "San Francisco",       "team1": "usa",            "team2": "bosnia-and-herzegovina","score1": 2, "score2": 0, "status": "final"},
    {"source_game_id": 82, "round": "r32", "date": "2026-07-01", "time_cdt": "15:00", "city": "Seattle",             "team1": "belgium",        "team2": "senegal",               "score1": 3, "score2": 2, "status": "final"},
    {"source_game_id": 83, "round": "r32", "date": "2026-07-02", "time_cdt": "18:00", "city": "Toronto",             "team1": "portugal",       "team2": "croatia",               "score1": 2, "score2": 1, "status": "final"},
    {"source_game_id": 84, "round": "r32", "date": "2026-07-02", "time_cdt": "14:00", "city": "Los Angeles",         "team1": "spain",          "team2": "austria",               "score1": 3, "score2": 0, "status": "final"},
    {"source_game_id": 85, "round": "r32", "date": "2026-07-02", "time_cdt": "22:00", "city": "Vancouver",           "team1": "switzerland",    "team2": "algeria",               "score1": 2, "score2": 0, "status": "final"},
    {"source_game_id": 86, "round": "r32", "date": "2026-07-03", "time_cdt": "17:00", "city": "Miami",               "team1": "argentina",      "team2": "cape-verde",            "score1": 3, "score2": 2, "status": "final"},
    {"source_game_id": 87, "round": "r32", "date": "2026-07-03", "time_cdt": "20:30", "city": "Kansas City",         "team1": "colombia",       "team2": "ghana",                 "score1": 1, "score2": 0, "status": "final"},
    {"source_game_id": 88, "round": "r32", "date": "2026-07-03", "time_cdt": "13:00", "city": "Dallas",              "team1": "australia",      "team2": "egypt",                 "score1": 1, "score2": 1, "status": "final"},
    # Round of 16 — 2026-07-04 to 2026-07-07 (all final)
    {"source_game_id": 89, "round": "r16", "date": "2026-07-04", "time_cdt": "16:00", "city": "Philadelphia",        "team1": "paraguay",       "team2": "france",                "score1": 0, "score2": 1, "status": "final"},
    {"source_game_id": 90, "round": "r16", "date": "2026-07-04", "time_cdt": "12:00", "city": "Houston",             "team1": "canada",         "team2": "morocco",               "score1": 0, "score2": 3, "status": "final"},
    {"source_game_id": 91, "round": "r16", "date": "2026-07-05", "time_cdt": "15:00", "city": "New York/New Jersey", "team1": "brazil",         "team2": "norway",                "score1": 1, "score2": 2, "status": "final"},
    {"source_game_id": 92, "round": "r16", "date": "2026-07-05", "time_cdt": "19:00", "city": "Mexico City",         "team1": "mexico",         "team2": "england",               "score1": 2, "score2": 3, "status": "final"},
    {"source_game_id": 93, "round": "r16", "date": "2026-07-06", "time_cdt": "14:00", "city": "Dallas",              "team1": "portugal",       "team2": "spain",                 "score1": 0, "score2": 1, "status": "final"},
    {"source_game_id": 94, "round": "r16", "date": "2026-07-06", "time_cdt": "19:00", "city": "Seattle",             "team1": "usa",            "team2": "belgium",               "score1": 1, "score2": 4, "status": "final"},
    {"source_game_id": 95, "round": "r16", "date": "2026-07-07", "time_cdt": "11:00", "city": "Atlanta",             "team1": "argentina",      "team2": "egypt",                 "score1": 3, "score2": 2, "status": "final"},
    {"source_game_id": 96, "round": "r16", "date": "2026-07-07", "time_cdt": "15:00", "city": "Vancouver",           "team1": "switzerland",    "team2": "colombia",              "score1": 0, "score2": 0, "status": "final"},
    # Quarterfinals — 2026-07-09 to 2026-07-11 (scheduled — next round up)
    {"source_game_id": 97,  "round": "qf", "date": "2026-07-09", "time_cdt": "15:00", "city": "Boston",        "team1": "france",    "team2": "morocco",     "score1": 2,    "score2": 0,    "status": "final"},
    {"source_game_id": 98,  "round": "qf", "date": "2026-07-10", "time_cdt": "14:00", "city": "Los Angeles",   "team1": "spain",     "team2": "belgium",     "score1": None, "score2": None, "status": "scheduled"},
    {"source_game_id": 99,  "round": "qf", "date": "2026-07-11", "time_cdt": "16:00", "city": "Miami",         "team1": "norway",    "team2": "england",     "score1": None, "score2": None, "status": "scheduled"},
    {"source_game_id": 100, "round": "qf", "date": "2026-07-11", "time_cdt": "20:00", "city": "Kansas City",   "team1": "argentina", "team2": "switzerland", "score1": None, "score2": None, "status": "scheduled"},
    # Semifinals, Third Place, Final — teams TBD until the rounds above resolve
    {"source_game_id": 101, "round": "sf",    "date": "2026-07-14", "time_cdt": "14:00", "city": "Dallas",              "team1": None, "team2": None, "team1_label": "Winner QF1", "team2_label": "Winner QF2", "score1": None, "score2": None, "status": "scheduled"},
    {"source_game_id": 102, "round": "sf",    "date": "2026-07-15", "time_cdt": "14:00", "city": "Atlanta",             "team1": None, "team2": None, "team1_label": "Winner QF3", "team2_label": "Winner QF4", "score1": None, "score2": None, "status": "scheduled"},
    {"source_game_id": 103, "round": "third", "date": "2026-07-18", "time_cdt": "16:00", "city": "Miami",               "team1": None, "team2": None, "team1_label": "Loser SF1",  "team2_label": "Loser SF2",  "score1": None, "score2": None, "status": "scheduled"},
    {"source_game_id": 104, "round": "final",  "date": "2026-07-19", "time_cdt": "14:00", "city": "New York/New Jersey", "team1": None, "team2": None, "team1_label": "Winner SF1", "team2_label": "Winner SF2", "score1": None, "score2": None, "status": "scheduled"},
]
