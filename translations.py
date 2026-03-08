"""UI string translations for EN (English) and EO (Esperanto)."""

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
        # Language switcher
        "lang_other": "en",
        "lang_label": "EN \u2014 English",
    },
}


def get_lang(request) -> str:
    lang = request.cookies.get("lang", "en")
    return lang if lang in TRANSLATIONS else "en"


def get_t(request) -> dict:
    return TRANSLATIONS[get_lang(request)]
