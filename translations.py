"""UI string translations for EN (English), EO (Esperanto), and DE (German)."""

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # Nav
        "nav_beginner":     "Beginner",
        "nav_intermediate": "Intermediate",
        "nav_expert":       "Expert",
        "nav_custom":       "Custom",
        "nav_leaderboard":  "Leaderboard",
        "nav_duel":         "Duel",
        "nav_pvp":          "PvP",
        # Auth
        "auth_sign_out":      "Sign out",
        "auth_sign_in":       "Sign in with Google",
        "auth_view_profile":  "View profile",
        # Game board
        "game_left_click":  "Left-click",
        "game_to_reveal":   "to reveal",
        "game_right_click": "Right-click",
        "game_to_flag":     "to flag",
        "game_to_flag_local": "to flag (local only)",
        "game_to_reset":    "to reset",
        "game_new_game":    "New Game",
        # Custom form
        "custom_rows":  "Rows",
        "custom_cols":  "Cols",
        "custom_mines": "Mines",
        "custom_start": "Start",
        # Duel page
        "duel_you":       "You",
        "duel_opponent":  "Opponent",
        "duel_share":     "Share this link with your opponent:",
        "duel_copy":      "Copy",
        "duel_start_btn": "▶ Start Game",
        "duel_scoring":   "How scoring works:",
        "duel_scoring_body": (
            "Your score is calculated by awarding <strong>5 points per tile revealed</strong>, "
            "plus a time bonus. The time bonus is calculated with the formula "
            "<code>(300 &minus; secondsFromStart) &times; percentRevealed</code>, "
            "however it will never drop below 0."
        ),
        # Leaderboard
        "lb_title":           "🏆 Leaderboard",
        "lb_col_rank":        "#",
        "lb_col_name":        "Name",
        "lb_col_time":        "Time",
        "lb_col_board":       "Board",
        "lb_col_mines":       "Mines",
        "lb_col_date":        "Date",
        "lb_loading":         "Loading\u2026",
        "lb_no_scores":       "No scores yet \u2014 be the first!",
        "lb_error":           "\u26a0\ufe0f Could not load scores.",
        "lb_top_prefix":      "Top",
        "lb_top_suffix_one":  "time",
        "lb_top_suffix_many": "times",
        "lb_play_beginner":     "\u2190 Play Beginner",
        "lb_play_intermediate": "Play Intermediate",
        "lb_play_expert":       "Play Expert",
        "lb_play_custom":       "Play Custom",
        # Profile
        "profile_recent_games": "Recent Games",
        "profile_loading":      "Loading\u2026",
        "profile_games":        "Games",
        "profile_best":         "Best",
        "profile_avg":          "Avg",
        "profile_worst":        "Worst",
        "profile_no_games":     "No games yet",
        "profile_play_now":     "Play now \u2192",
        "profile_no_recent":    "No games recorded yet.",
        # Help
        "help_title": "How to Play Minesweeper",
        # Footer
        "footer": "Built by Richard Cross with Python &amp; FastAPI",
        # Language switcher
        "lang_other": "eo",
        "lang_label": "EO \u2014 Esperanto",
    },

    "eo": {
        # Nav
        "nav_beginner":     "Komencanto",
        "nav_intermediate": "Mez-nivela",
        "nav_expert":       "Sperta",
        "nav_custom":       "Propra",
        "nav_leaderboard":  "Rekordtabelo",
        "nav_duel":         "Duelo",
        "nav_pvp":          "PvP",
        # Auth
        "auth_sign_out":     "Elsalutu",
        "auth_sign_in":      "Ensalutu per Google",
        "auth_view_profile": "Vidu profilon",
        # Game board
        "game_left_click":    "Maldekstra klako",
        "game_to_reveal":     "por malka\u015di",
        "game_right_click":   "Dekstra klako",
        "game_to_flag":       "por flagi",
        "game_to_flag_local": "por flagi (loke nur)",
        "game_to_reset":      "por rekomenci",
        "game_new_game":      "Nova Ludo",
        # Custom form
        "custom_rows":  "Vicoj",
        "custom_cols":  "Kolumnoj",
        "custom_mines": "Minoj",
        "custom_start": "Komencu",
        # Duel page
        "duel_you":       "Vi",
        "duel_opponent":  "Kontra\u016dludo",
        "duel_share":     "Kunhavigu \u0109i tiun ligilon kun via kontra\u016dludo:",
        "duel_copy":      "Kopiu",
        "duel_start_btn": "\u25b6 Ekludu",
        "duel_scoring":   "Kiel la poentado funkcias:",
        "duel_scoring_body": (
            "Via poentaro estas kalkulata donante <strong>5 poentojn por malka\u015dita kahelo</strong>, "
            "plus tempa bonuso. La tempa bonuso estas kalkulata per la formulo "
            "<code>(300 &minus; sekundojDeEkludu) &times; procento Malka\u015dita</code>, "
            "tamen \u011di neniam falos sub 0."
        ),
        # Leaderboard
        "lb_title":           "\u2019 Rekordtabelo",
        "lb_col_rank":        "#",
        "lb_col_name":        "Nomo",
        "lb_col_time":        "Tempo",
        "lb_col_board":       "Tabulo",
        "lb_col_mines":       "Minoj",
        "lb_col_date":        "Dato",
        "lb_loading":         "\u015car\u011das\u2026",
        "lb_no_scores":       "Ankoraŭ ne estas poentoj \u2014 estu la unua!",
        "lb_error":           "\u26a0\ufe0f Ne eblis \u015cargi poentojn.",
        "lb_top_prefix":      "Plej bonaj",
        "lb_top_suffix_one":  "tempo",
        "lb_top_suffix_many": "tempoj",
        "lb_play_beginner":     "\u2190 Ludu Komencante",
        "lb_play_intermediate": "Ludu Mez-nivele",
        "lb_play_expert":       "Ludu Sperte",
        "lb_play_custom":       "Ludu Propre",
        # Profile
        "profile_recent_games": "Lastatempaj Ludoj",
        "profile_loading":      "\u015car\u011das\u2026",
        "profile_games":        "Ludoj",
        "profile_best":         "Plej bona",
        "profile_avg":          "Avera\u011da",
        "profile_worst":        "Plej malbona",
        "profile_no_games":     "Ankoraŭ ne estas ludoj",
        "profile_play_now":     "Ludu nun \u2192",
        "profile_no_recent":    "Ankoraŭ ne estas registritaj ludoj.",
        # Help
        "help_title": "Kiel Ludi Minosvepiston",
        # Footer
        "footer": "Konstruita de Richard Cross per Python kaj FastAPI",
        # Language switcher (unused by template — kept for symmetry)
        "lang_other": "en",
        "lang_label": "EN \u2014 English",
    },

    "de": {
        # Nav
        "nav_beginner":     "Anf\u00e4nger",
        "nav_intermediate": "Mittel",
        "nav_expert":       "Experte",
        "nav_custom":       "Eigene",
        "nav_leaderboard":  "Bestenliste",
        "nav_duel":         "Duell",
        "nav_pvp":          "PvP",
        # Auth
        "auth_sign_out":     "Abmelden",
        "auth_sign_in":      "Mit Google anmelden",
        "auth_view_profile": "Profil anzeigen",
        # Game board
        "game_left_click":    "Linksklick",
        "game_to_reveal":     "zum Aufdecken",
        "game_right_click":   "Rechtsklick",
        "game_to_flag":       "zum Markieren",
        "game_to_flag_local": "zum Markieren (nur lokal)",
        "game_to_reset":      "zum Zur\u00fccksetzen",
        "game_new_game":      "Neues Spiel",
        # Custom form
        "custom_rows":  "Zeilen",
        "custom_cols":  "Spalten",
        "custom_mines": "Minen",
        "custom_start": "Start",
        # Duel page
        "duel_you":       "Du",
        "duel_opponent":  "Gegner",
        "duel_share":     "Teile diesen Link mit deinem Gegner:",
        "duel_copy":      "Kopieren",
        "duel_start_btn": "\u25b6 Spiel starten",
        "duel_scoring":   "So funktioniert die Punktewertung:",
        "duel_scoring_body": (
            "Deine Punktzahl wird berechnet, indem <strong>5 Punkte pro aufgedecktem Feld</strong> "
            "vergeben werden, plus ein Zeitbonus. Der Zeitbonus wird mit der Formel "
            "<code>(300 &minus; SekundenSeitStart) &times; aufgedeckterProzentsatz</code> "
            "berechnet, wird jedoch nie unter 0 fallen."
        ),
        # Leaderboard
        "lb_title":           "\U0001f3c6 Bestenliste",
        "lb_col_rank":        "#",
        "lb_col_name":        "Name",
        "lb_col_time":        "Zeit",
        "lb_col_board":       "Feld",
        "lb_col_mines":       "Minen",
        "lb_col_date":        "Datum",
        "lb_loading":         "L\u00e4dt\u2026",
        "lb_no_scores":       "Noch keine Ergebnisse \u2014 sei der Erste!",
        "lb_error":           "\u26a0\ufe0f Ergebnisse konnten nicht geladen werden.",
        "lb_top_prefix":      "Top",
        "lb_top_suffix_one":  "Ergebnis",
        "lb_top_suffix_many": "Ergebnisse",
        "lb_play_beginner":     "\u2190 Anf\u00e4nger spielen",
        "lb_play_intermediate": "Mittel spielen",
        "lb_play_expert":       "Experte spielen",
        "lb_play_custom":       "Eigene spielen",
        # Profile
        "profile_recent_games": "Letzte Spiele",
        "profile_loading":      "L\u00e4dt\u2026",
        "profile_games":        "Spiele",
        "profile_best":         "Beste",
        "profile_avg":          "Durchschnitt",
        "profile_worst":        "Schlechteste",
        "profile_no_games":     "Noch keine Spiele",
        "profile_play_now":     "Jetzt spielen \u2192",
        "profile_no_recent":    "Noch keine Spiele aufgezeichnet.",
        # Help
        "help_title": "Wie man Minesweeper spielt",
        # Footer
        "footer": "Erstellt von Richard Cross mit Python &amp; FastAPI",
        # Language switcher (unused by template — kept for symmetry)
        "lang_other": "en",
        "lang_label": "EN \u2014 English",
    },

    "es": {
        # Nav
        "nav_beginner":     "Principiante",
        "nav_intermediate": "Intermedio",
        "nav_expert":       "Experto",
        "nav_custom":       "Personalizado",
        "nav_leaderboard":  "Clasificaci\u00f3n",
        "nav_duel":         "Duelo",
        "nav_pvp":          "PvP",
        # Auth
        "auth_sign_out":     "Cerrar sesi\u00f3n",
        "auth_sign_in":      "Iniciar sesi\u00f3n con Google",
        "auth_view_profile": "Ver perfil",
        # Game board
        "game_left_click":    "Clic izquierdo",
        "game_to_reveal":     "para revelar",
        "game_right_click":   "Clic derecho",
        "game_to_flag":       "para marcar",
        "game_to_flag_local": "para marcar (solo local)",
        "game_to_reset":      "para reiniciar",
        "game_new_game":      "Nueva Partida",
        # Custom form
        "custom_rows":  "Filas",
        "custom_cols":  "Columnas",
        "custom_mines": "Minas",
        "custom_start": "Comenzar",
        # Duel page
        "duel_you":       "T\u00fa",
        "duel_opponent":  "Oponente",
        "duel_share":     "Comparte este enlace con tu oponente:",
        "duel_copy":      "Copiar",
        "duel_start_btn": "\u25b6 Iniciar Partida",
        "duel_scoring":   "C\u00f3mo funciona la puntuaci\u00f3n:",
        "duel_scoring_body": (
            "Tu puntuaci\u00f3n se calcula otorgando <strong>5 puntos por cada casilla revelada</strong>, "
            "m\u00e1s un bono de tiempo. El bono de tiempo se calcula con la f\u00f3rmula "
            "<code>(300 &minus; segundosDesdeInicio) &times; porcentajeRevelado</code>, "
            "aunque nunca bajar\u00e1 de 0."
        ),
        # Leaderboard
        "lb_title":           "\U0001f3c6 Clasificaci\u00f3n",
        "lb_col_rank":        "#",
        "lb_col_name":        "Nombre",
        "lb_col_time":        "Tiempo",
        "lb_col_board":       "Tablero",
        "lb_col_mines":       "Minas",
        "lb_col_date":        "Fecha",
        "lb_loading":         "Cargando\u2026",
        "lb_no_scores":       "A\u00fan no hay puntuaciones \u2014 \u00a1s\u00e9 el primero!",
        "lb_error":           "\u26a0\ufe0f No se pudieron cargar las puntuaciones.",
        "lb_top_prefix":      "Top",
        "lb_top_suffix_one":  "resultado",
        "lb_top_suffix_many": "resultados",
        "lb_play_beginner":     "\u2190 Jugar Principiante",
        "lb_play_intermediate": "Jugar Intermedio",
        "lb_play_expert":       "Jugar Experto",
        "lb_play_custom":       "Jugar Personalizado",
        # Profile
        "profile_recent_games": "Partidas Recientes",
        "profile_loading":      "Cargando\u2026",
        "profile_games":        "Partidas",
        "profile_best":         "Mejor",
        "profile_avg":          "Promedio",
        "profile_worst":        "Peor",
        "profile_no_games":     "A\u00fan no hay partidas",
        "profile_play_now":     "Jugar ahora \u2192",
        "profile_no_recent":    "A\u00fan no hay partidas registradas.",
        # Help
        "help_title": "C\u00f3mo jugar al Buscaminas",
        # Footer
        "footer": "Creado por Richard Cross con Python &amp; FastAPI",
        # Language switcher (unused by template — kept for symmetry)
        "lang_other": "en",
        "lang_label": "EN \u2014 English",
    },
}


def get_lang(request) -> str:
    lang = request.cookies.get("lang", "en")
    return lang if lang in TRANSLATIONS else "en"


def get_t(request) -> dict:
    return TRANSLATIONS[get_lang(request)]
