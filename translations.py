"""UI string translations for EN, EO, DE, ES, TH, PGL, UK."""

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

    "th": {
        # Nav
        "nav_beginner":     "\u0e1c\u0e39\u0e49\u0e40\u0e23\u0e34\u0e48\u0e21\u0e15\u0e49\u0e19",
        "nav_intermediate": "\u0e23\u0e30\u0e14\u0e31\u0e1a\u0e01\u0e25\u0e32\u0e07",
        "nav_expert":       "\u0e1c\u0e39\u0e49\u0e40\u0e0a\u0e35\u0e48\u0e22\u0e27\u0e0a\u0e32\u0e0d",
        "nav_custom":       "\u0e01\u0e33\u0e2b\u0e19\u0e14\u0e40\u0e2d\u0e07",
        "nav_leaderboard":  "\u0e15\u0e32\u0e23\u0e32\u0e07\u0e04\u0e30\u0e41\u0e19\u0e19",
        "nav_duel":         "\u0e14\u0e27\u0e25",
        "nav_pvp":          "PvP",
        # Auth
        "auth_sign_out":     "\u0e2d\u0e2d\u0e01\u0e08\u0e32\u0e01\u0e23\u0e30\u0e1a\u0e1a",
        "auth_sign_in":      "\u0e40\u0e02\u0e49\u0e32\u0e2a\u0e39\u0e48\u0e23\u0e30\u0e1a\u0e1a\u0e14\u0e49\u0e27\u0e22 Google",
        "auth_view_profile": "\u0e14\u0e39\u0e42\u0e1b\u0e23\u0e44\u0e1f\u0e25\u0e4c",
        # Game board
        "game_left_click":    "\u0e04\u0e25\u0e34\u0e01\u0e0b\u0e49\u0e32\u0e22",
        "game_to_reveal":     "\u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e40\u0e1b\u0e34\u0e14\u0e40\u0e1c\u0e22",
        "game_right_click":   "\u0e04\u0e25\u0e34\u0e01\u0e02\u0e27\u0e32",
        "game_to_flag":       "\u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e1b\u0e31\u0e01\u0e18\u0e07",
        "game_to_flag_local": "\u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e1b\u0e31\u0e01\u0e18\u0e07 (\u0e40\u0e09\u0e1e\u0e32\u0e30\u0e17\u0e49\u0e2d\u0e07\u0e16\u0e34\u0e48\u0e19)",
        "game_to_reset":      "\u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e23\u0e35\u0e40\u0e0b\u0e47\u0e15",
        "game_new_game":      "\u0e40\u0e01\u0e21\u0e43\u0e2b\u0e21\u0e48",
        # Custom form
        "custom_rows":  "\u0e41\u0e16\u0e27",
        "custom_cols":  "\u0e04\u0e2d\u0e25\u0e31\u0e21\u0e19\u0e4c",
        "custom_mines": "\u0e17\u0e38\u0e48\u0e19\u0e23\u0e30\u0e40\u0e1a\u0e34\u0e14",
        "custom_start": "\u0e40\u0e23\u0e34\u0e48\u0e21",
        # Duel page
        "duel_you":       "\u0e04\u0e38\u0e13",
        "duel_opponent":  "\u0e04\u0e39\u0e48\u0e15\u0e48\u0e2d\u0e2a\u0e39\u0e49",
        "duel_share":     "\u0e41\u0e0a\u0e23\u0e4c\u0e25\u0e34\u0e07\u0e01\u0e4c\u0e19\u0e35\u0e49\u0e01\u0e31\u0e1a\u0e04\u0e39\u0e48\u0e15\u0e48\u0e2d\u0e2a\u0e39\u0e49\u0e02\u0e2d\u0e07\u0e04\u0e38\u0e13:",
        "duel_copy":      "\u0e04\u0e31\u0e14\u0e25\u0e2d\u0e01",
        "duel_start_btn": "\u25b6 \u0e40\u0e23\u0e34\u0e48\u0e21\u0e40\u0e01\u0e21",
        "duel_scoring":   "\u0e27\u0e34\u0e18\u0e35\u0e01\u0e32\u0e23\u0e19\u0e31\u0e1a\u0e04\u0e30\u0e41\u0e19\u0e19:",
        "duel_scoring_body": (
            "\u0e04\u0e30\u0e41\u0e19\u0e19\u0e02\u0e2d\u0e07\u0e04\u0e38\u0e13\u0e04\u0e33\u0e19\u0e27\u0e13\u0e42\u0e14\u0e22\u0e01\u0e32\u0e23\u0e21\u0e2d\u0e1a "
            "<strong>5 \u0e04\u0e30\u0e41\u0e19\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e48\u0e2d\u0e07\u0e17\u0e35\u0e48\u0e40\u0e1b\u0e34\u0e14\u0e40\u0e1c\u0e22</strong> "
            "\u0e1a\u0e27\u0e01\u0e42\u0e1a\u0e19\u0e31\u0e2a\u0e40\u0e27\u0e25\u0e32 "
            "\u0e42\u0e1a\u0e19\u0e31\u0e2a\u0e40\u0e27\u0e25\u0e32\u0e04\u0e33\u0e19\u0e27\u0e13\u0e14\u0e49\u0e27\u0e22\u0e2a\u0e39\u0e15\u0e23 "
            "<code>(300 &minus; \u0e27\u0e34\u0e19\u0e32\u0e17\u0e35\u0e08\u0e32\u0e01\u0e40\u0e23\u0e34\u0e48\u0e21) &times; \u0e40\u0e1b\u0e2d\u0e23\u0e4c\u0e40\u0e0b\u0e47\u0e19\u0e15\u0e4c\u0e17\u0e35\u0e48\u0e40\u0e1b\u0e34\u0e14\u0e40\u0e1c\u0e22</code> "
            "\u0e41\u0e15\u0e48\u0e08\u0e30\u0e44\u0e21\u0e48\u0e15\u0e48\u0e33\u0e01\u0e27\u0e48\u0e32 0 \u0e40\u0e25\u0e22"
        ),
        # Leaderboard
        "lb_title":           "\U0001f3c6 \u0e15\u0e32\u0e23\u0e32\u0e07\u0e04\u0e30\u0e41\u0e19\u0e19",
        "lb_col_rank":        "#",
        "lb_col_name":        "\u0e0a\u0e37\u0e48\u0e2d",
        "lb_col_time":        "\u0e40\u0e27\u0e25\u0e32",
        "lb_col_board":       "\u0e01\u0e23\u0e30\u0e14\u0e32\u0e19",
        "lb_col_mines":       "\u0e17\u0e38\u0e48\u0e19\u0e23\u0e30\u0e40\u0e1a\u0e34\u0e14",
        "lb_col_date":        "\u0e27\u0e31\u0e19\u0e17\u0e35\u0e48",
        "lb_loading":         "\u0e01\u0e33\u0e25\u0e31\u0e07\u0e42\u0e2b\u0e25\u0e14\u2026",
        "lb_no_scores":       "\u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e21\u0e35\u0e04\u0e30\u0e41\u0e19\u0e19 \u2014 \u0e40\u0e1b\u0e47\u0e19\u0e04\u0e19\u0e41\u0e23\u0e01!",
        "lb_error":           "\u26a0\ufe0f \u0e44\u0e21\u0e48\u0e2a\u0e32\u0e21\u0e32\u0e23\u0e16\u0e42\u0e2b\u0e25\u0e14\u0e04\u0e30\u0e41\u0e19\u0e19\u0e44\u0e14\u0e49",
        "lb_top_prefix":      "\u0e2d\u0e31\u0e19\u0e14\u0e31\u0e1a\u0e15\u0e49\u0e19",
        "lb_top_suffix_one":  "\u0e1c\u0e25\u0e25\u0e31\u0e1e\u0e18\u0e4c",
        "lb_top_suffix_many": "\u0e1c\u0e25\u0e25\u0e31\u0e1e\u0e18\u0e4c",
        "lb_play_beginner":     "\u2190 \u0e40\u0e25\u0e48\u0e19\u0e23\u0e30\u0e14\u0e31\u0e1a\u0e1c\u0e39\u0e49\u0e40\u0e23\u0e34\u0e48\u0e21\u0e15\u0e49\u0e19",
        "lb_play_intermediate": "\u0e40\u0e25\u0e48\u0e19\u0e23\u0e30\u0e14\u0e31\u0e1a\u0e01\u0e25\u0e32\u0e07",
        "lb_play_expert":       "\u0e40\u0e25\u0e48\u0e19\u0e23\u0e30\u0e14\u0e31\u0e1a\u0e1c\u0e39\u0e49\u0e40\u0e0a\u0e35\u0e48\u0e22\u0e27\u0e0a\u0e32\u0e0d",
        "lb_play_custom":       "\u0e40\u0e25\u0e48\u0e19\u0e41\u0e1a\u0e1a\u0e01\u0e33\u0e2b\u0e19\u0e14\u0e40\u0e2d\u0e07",
        # Profile
        "profile_recent_games": "\u0e40\u0e01\u0e21\u0e25\u0e48\u0e32\u0e2a\u0e38\u0e14",
        "profile_loading":      "\u0e01\u0e33\u0e25\u0e31\u0e07\u0e42\u0e2b\u0e25\u0e14\u2026",
        "profile_games":        "\u0e40\u0e01\u0e21",
        "profile_best":         "\u0e14\u0e35\u0e17\u0e35\u0e48\u0e2a\u0e38\u0e14",
        "profile_avg":          "\u0e40\u0e09\u0e25\u0e35\u0e48\u0e22",
        "profile_worst":        "\u0e41\u0e22\u0e48\u0e17\u0e35\u0e48\u0e2a\u0e38\u0e14",
        "profile_no_games":     "\u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e21\u0e35\u0e40\u0e01\u0e21",
        "profile_play_now":     "\u0e40\u0e25\u0e48\u0e19\u0e15\u0e2d\u0e19\u0e19\u0e35\u0e49 \u2192",
        "profile_no_recent":    "\u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e21\u0e35\u0e40\u0e01\u0e21\u0e17\u0e35\u0e48\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01\u0e44\u0e27\u0e49",
        # Help
        "help_title": "\u0e27\u0e34\u0e18\u0e35\u0e40\u0e25\u0e48\u0e19 Minesweeper",
        # Footer
        "footer": "\u0e2a\u0e23\u0e49\u0e32\u0e07\u0e42\u0e14\u0e22 Richard Cross \u0e14\u0e49\u0e27\u0e22 Python &amp; FastAPI",
        # Language switcher (unused by template — kept for symmetry)
        "lang_other": "en",
        "lang_label": "EN \u2014 English",
    },

    "pgl": {
        # Nav
        "nav_beginner":     "Eginnerbay",
        "nav_intermediate": "Intermediateway",
        "nav_expert":       "Expertway",
        "nav_custom":       "Ustomcay",
        "nav_leaderboard":  "Eaderboardlay",
        "nav_duel":         "Uelday",
        "nav_pvp":          "PvP",
        # Auth
        "auth_sign_out":     "Ignsay outway",
        "auth_sign_in":      "Ignsay inway ithway Ooglegay",
        "auth_view_profile": "Iewvay ofilepray",
        # Game board
        "game_left_click":    "Eftlay-ickclay",
        "game_to_reveal":     "otay evealray",
        "game_right_click":   "Ightray-ickclay",
        "game_to_flag":       "otay agflay",
        "game_to_flag_local": "otay agflay (ocallay onlyway)",
        "game_to_reset":      "otay esetray",
        "game_new_game":      "Ewnay Amegay",
        # Custom form
        "custom_rows":  "Owsray",
        "custom_cols":  "Olscay",
        "custom_mines": "Inesmay",
        "custom_start": "Artstay",
        # Duel page
        "duel_you":       "Ouyay",
        "duel_opponent":  "Opponentway",
        "duel_share":     "Areshay isthay inklay ithway ouryay opponentway:",
        "duel_copy":      "Opycay",
        "duel_start_btn": "\u25b6 Artstay Amegay",
        "duel_scoring":   "Owhay oringsscay orksway:",
        "duel_scoring_body": (
            "Ouryay oresscay isway alculatedcay ybay awardingway "
            "<strong>5 ointspay erpay iletay evealedray</strong>, "
            "usplay away imetay onusbay. Ethay imetay onusbay isway alculatedcay "
            "ithway ethay ormulafay "
            "<code>(300 &minus; econdssay omfray artstay) &times; ercentpay evealedray</code>, "
            "oweverhay itway illway evernay opday elowbay 0."
        ),
        # Leaderboard
        "lb_title":           "\U0001f3c6 Eaderboardlay",
        "lb_col_rank":        "#",
        "lb_col_name":        "Amenay",
        "lb_col_time":        "Imetay",
        "lb_col_board":       "Oardbay",
        "lb_col_mines":       "Inesmay",
        "lb_col_date":        "Ateday",
        "lb_loading":         "Oadinglay\u2026",
        "lb_no_scores":       "Onay oresscay etyay \u2014 ebay ethay irstfay!",
        "lb_error":           "\u26a0\ufe0f Ouldcay otnay oadlay oresscay.",
        "lb_top_prefix":      "Optay",
        "lb_top_suffix_one":  "imetay",
        "lb_top_suffix_many": "imestay",
        "lb_play_beginner":     "\u2190 Ayplay Eginnerbay",
        "lb_play_intermediate": "Ayplay Intermediateway",
        "lb_play_expert":       "Ayplay Expertway",
        "lb_play_custom":       "Ayplay Ustomcay",
        # Profile
        "profile_recent_games": "Ecentray Amesgay",
        "profile_loading":      "Oadinglay\u2026",
        "profile_games":        "Amesgay",
        "profile_best":         "Estbay",
        "profile_avg":          "Avgway",
        "profile_worst":        "Orstway",
        "profile_no_games":     "Onay amesgay etyay",
        "profile_play_now":     "Ayplay ownay \u2192",
        "profile_no_recent":    "Onay amesgay ecordedray etyay.",
        # Help
        "help_title": "Owhay otay Ayplay Inesweepermay",
        # Footer
        "footer": "Uiltbay ybay Ichardray Osscray ithway Ythonpay &amp; FastAPI",
        # Language switcher (unused by template — kept for symmetry)
        "lang_other": "en",
        "lang_label": "EN \u2014 English",
    },

    "uk": {
        # Nav
        "nav_beginner":     "\u041f\u043e\u0447\u0430\u0442\u043a\u0456\u0432\u0435\u0446\u044c",
        "nav_intermediate": "\u0421\u0435\u0440\u0435\u0434\u043d\u0456\u0439",
        "nav_expert":       "\u0415\u043a\u0441\u043f\u0435\u0440\u0442",
        "nav_custom":       "\u0412\u043b\u0430\u0441\u043d\u0438\u0439",
        "nav_leaderboard":  "\u0420\u0435\u0439\u0442\u0438\u043d\u0433",
        "nav_duel":         "\u0414\u0443\u0435\u043b\u044c",
        "nav_pvp":          "PvP",
        # Auth
        "auth_sign_out":     "\u0412\u0438\u0439\u0442\u0438",
        "auth_sign_in":      "\u0423\u0432\u0456\u0439\u0442\u0438 \u0447\u0435\u0440\u0435\u0437 Google",
        "auth_view_profile": "\u041f\u0435\u0440\u0435\u0433\u043b\u044f\u043d\u0443\u0442\u0438 \u043f\u0440\u043e\u0444\u0456\u043b\u044c",
        # Game board
        "game_left_click":    "\u041b\u0456\u0432\u0438\u0439 \u043a\u043b\u0456\u043a",
        "game_to_reveal":     "\u0449\u043e\u0431 \u0432\u0456\u0434\u043a\u0440\u0438\u0442\u0438",
        "game_right_click":   "\u041f\u0440\u0430\u0432\u0438\u0439 \u043a\u043b\u0456\u043a",
        "game_to_flag":       "\u0449\u043e\u0431 \u043f\u043e\u0437\u043d\u0430\u0447\u0438\u0442\u0438",
        "game_to_flag_local": "\u0449\u043e\u0431 \u043f\u043e\u0437\u043d\u0430\u0447\u0438\u0442\u0438 (\u0442\u0456\u043b\u044c\u043a\u0438 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e)",
        "game_to_reset":      "\u0449\u043e\u0431 \u0441\u043a\u0438\u043d\u0443\u0442\u0438",
        "game_new_game":      "\u041d\u043e\u0432\u0430 \u0433\u0440\u0430",
        # Custom form
        "custom_rows":  "\u0420\u044f\u0434\u043a\u0438",
        "custom_cols":  "\u0421\u0442\u043e\u0432\u043f\u0446\u0456",
        "custom_mines": "\u041c\u0456\u043d\u0438",
        "custom_start": "\u041f\u043e\u0447\u0430\u0442\u0438",
        # Duel page
        "duel_you":       "\u0412\u0438",
        "duel_opponent":  "\u0421\u0443\u043f\u0435\u0440\u043d\u0438\u043a",
        "duel_share":     "\u041f\u043e\u0434\u0456\u043b\u0456\u0442\u044c\u0441\u044f \u0446\u0438\u043c \u043f\u043e\u0441\u0438\u043b\u0430\u043d\u043d\u044f\u043c \u0437 \u0441\u0443\u043f\u0435\u0440\u043d\u0438\u043a\u043e\u043c:",
        "duel_copy":      "\u041a\u043e\u043f\u0456\u044e\u0432\u0430\u0442\u0438",
        "duel_start_btn": "\u25b6 \u041f\u043e\u0447\u0430\u0442\u0438 \u0433\u0440\u0443",
        "duel_scoring":   "\u042f\u043a \u043d\u0430\u0440\u0430\u0445\u043e\u0432\u0443\u044e\u0442\u044c\u0441\u044f \u043e\u0447\u043a\u0438:",
        "duel_scoring_body": (
            "\u0412\u0430\u0448 \u0440\u0430\u0445\u0443\u043d\u043e\u043a \u043e\u0431\u0447\u0438\u0441\u043b\u044e\u0454\u0442\u044c\u0441\u044f \u0448\u043b\u044f\u0445\u043e\u043c \u043d\u0430\u0440\u0430\u0445\u0443\u0432\u0430\u043d\u043d\u044f "
            "<strong>5 \u043e\u0447\u043a\u0456\u0432 \u0437\u0430 \u043a\u043e\u0436\u043d\u0443 \u0432\u0456\u0434\u043a\u0440\u0438\u0442\u0443 \u043a\u043b\u0456\u0442\u0438\u043d\u043a\u0443</strong>, "
            "\u043f\u043b\u044e\u0441 \u0447\u0430\u0441\u043e\u0432\u0438\u0439 \u0431\u043e\u043d\u0443\u0441. "
            "\u0427\u0430\u0441\u043e\u0432\u0438\u0439 \u0431\u043e\u043d\u0443\u0441 \u043e\u0431\u0447\u0438\u0441\u043b\u044e\u0454\u0442\u044c\u0441\u044f \u0437\u0430 \u0444\u043e\u0440\u043c\u0443\u043b\u043e\u044e "
            "<code>(300 &minus; \u0441\u0435\u043a\u0443\u043d\u0434\u0438\u0412\u0456\u0434\u041f\u043e\u0447\u0430\u0442\u043a\u0443) &times; \u0432\u0456\u0434\u0441\u043e\u0442\u043e\u043a\u0412\u0456\u0434\u043a\u0440\u0438\u0442\u043e\u0433\u043e</code>, "
            "\u043e\u0434\u043d\u0430\u043a \u0432\u0456\u043d \u043d\u0456\u043a\u043e\u043b\u0438 \u043d\u0435 \u043e\u043f\u0443\u0441\u0442\u0438\u0442\u044c\u0441\u044f \u043d\u0438\u0436\u0095 0."
        ),
        # Leaderboard
        "lb_title":           "\U0001f3c6 \u0420\u0435\u0439\u0442\u0438\u043d\u0433",
        "lb_col_rank":        "#",
        "lb_col_name":        "\u0406\u043c\u2019\u044f",
        "lb_col_time":        "\u0427\u0430\u0441",
        "lb_col_board":       "\u041f\u043e\u043b\u0435",
        "lb_col_mines":       "\u041c\u0456\u043d\u0438",
        "lb_col_date":        "\u0414\u0430\u0442\u0430",
        "lb_loading":         "\u0417\u0430\u0432\u0430\u043d\u0442\u0430\u0436\u0435\u043d\u043d\u044f\u2026",
        "lb_no_scores":       "\u0429\u0435 \u043d\u0435\u043c\u0430\u0454 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u0456\u0432 \u2014 \u0431\u0443\u0434\u044c\u0442\u0435 \u043f\u0435\u0440\u0448\u0438\u043c!",
        "lb_error":           "\u26a0\ufe0f \u041d\u0435 \u0432\u0434\u0430\u043b\u043e\u0441\u044f \u0437\u0430\u0432\u0430\u043d\u0442\u0430\u0436\u0438\u0442\u0438 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u0438.",
        "lb_top_prefix":      "\u0422\u043e\u043f",
        "lb_top_suffix_one":  "\u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442",
        "lb_top_suffix_many": "\u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u0456\u0432",
        "lb_play_beginner":     "\u2190 \u0413\u0440\u0430\u0442\u0438 (\u041f\u043e\u0447\u0430\u0442\u043a\u0456\u0432\u0435\u0446\u044c)",
        "lb_play_intermediate": "\u0413\u0440\u0430\u0442\u0438 (\u0421\u0435\u0440\u0435\u0434\u043d\u0456\u0439)",
        "lb_play_expert":       "\u0413\u0440\u0430\u0442\u0438 (\u0415\u043a\u0441\u043f\u0435\u0440\u0442)",
        "lb_play_custom":       "\u0413\u0440\u0430\u0442\u0438 (\u0412\u043b\u0430\u0441\u043d\u0438\u0439)",
        # Profile
        "profile_recent_games": "\u041e\u0441\u0442\u0430\u043d\u043d\u0456 \u0456\u0433\u0440\u0438",
        "profile_loading":      "\u0417\u0430\u0432\u0430\u043d\u0442\u0430\u0436\u0435\u043d\u043d\u044f\u2026",
        "profile_games":        "\u0406\u0433\u0440\u0438",
        "profile_best":         "\u041d\u0430\u0439\u043a\u0440\u0430\u0449\u0438\u0439",
        "profile_avg":          "\u0421\u0435\u0440\u0435\u0434\u043d\u0456\u0439",
        "profile_worst":        "\u041d\u0430\u0439\u0433\u0456\u0440\u0448\u0438\u0439",
        "profile_no_games":     "\u0429\u0435 \u043d\u0435\u043c\u0430\u0454 \u0456\u0433\u043e\u0440",
        "profile_play_now":     "\u0413\u0440\u0430\u0442\u0438 \u0437\u0430\u0440\u0430\u0437 \u2192",
        "profile_no_recent":    "\u0429\u0435 \u043d\u0435\u043c\u0430\u0454 \u0437\u0430\u043f\u0438\u0441\u0430\u043d\u0438\u0445 \u0456\u0433\u043e\u0440.",
        # Help
        "help_title": "\u042f\u043a \u0433\u0440\u0430\u0442\u0438 \u0432 \u0421\u0430\u043f\u0435\u0440",
        # Footer
        "footer": "\u0421\u0442\u0432\u043e\u0440\u0435\u043d\u043e \u0420\u0456\u0447\u0430\u0440\u0434\u043e\u043c \u041a\u0440\u043e\u0441\u043e\u043c \u0437\u0430 \u0434\u043e\u043f\u043e\u043c\u043e\u0433\u043e\u044e Python &amp; FastAPI",
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
