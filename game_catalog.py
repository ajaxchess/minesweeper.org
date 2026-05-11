"""Shared game, route, language, and SEO catalog data.

This file is the source of truth for puzzle navigation, clean URLs, redirect
targets, and structured data. Game names intentionally stay in English for the
"fun" languages so Pig Latin / Esperanto style UI does not mangle brands.
"""

from __future__ import annotations

from urllib.parse import urlencode


FUN_LANGS: frozenset[str] = frozenset({"eo", "pgl", "tlh"})


LANGUAGE_OPTIONS: list[dict[str, str]] = [
    {"code": "en", "label": "EN", "name": "English", "flag": "en"},
    {"code": "de", "label": "DE", "name": "Deutsch", "flag": "de"},
    {"code": "fr", "label": "FR", "name": "Francais", "flag": "fr"},
    {"code": "es", "label": "ES", "name": "Espanol", "flag": "es"},
    {"code": "pt", "label": "PT", "name": "Portugues", "flag": "pt"},
    {"code": "it", "label": "IT", "name": "Italiano", "flag": "it"},
    {"code": "pl", "label": "PL", "name": "Polski", "flag": "pl"},
    {"code": "ru", "label": "RU", "name": "Russkiy", "flag": "ru"},
    {"code": "uk", "label": "UK", "name": "Ukrainska", "flag": "uk"},
    {"code": "zh", "label": "ZH", "name": "Chinese Simplified", "flag": "zh"},
    {"code": "zh-hant", "label": "ZH", "name": "Chinese Traditional", "flag": "zh-hant"},
    {"code": "ja", "label": "JA", "name": "Japanese", "flag": "ja"},
    {"code": "ko", "label": "KO", "name": "Korean", "flag": "ko"},
    {"code": "th", "label": "TH", "name": "Thai", "flag": "th"},
    {"code": "tl", "label": "TL", "name": "Filipino", "flag": "tl"},
    {"code": "pgl", "label": "PGL", "name": "Pig Latin", "flag": "pgl"},
    {"code": "eo", "label": "EO", "name": "Esperanto", "flag": "eo"},
    {"code": "tlh", "label": "TLH", "name": "Klingon", "flag": "tlh"},
]


def _actions(base: str, *, leaderboard: bool = True, howto: bool = True, generator: bool = False, gallery: bool = False):
    actions: list[dict[str, object]] = [{"href": base, "label": "Play", "primary": True}]
    if leaderboard:
        actions.append({"href": f"{base}/leaderboard", "label_key": "nav_leaderboard"})
    if gallery:
        actions.append({"href": f"{base}/gallery", "label": "Gallery"})
    if generator:
        actions.append({"href": f"{base}/generator", "label_key": "other_generator"})
    if howto:
        actions.append({"href": f"{base}/how-to-play", "label_key": "nav_how_to_play"})
    return actions


PUZZLE_GAMES: list[dict[str, object]] = [
    {
        "slug": "tentaizu",
        "category": "puzzles",
        "section": "Daily Logic Puzzles",
        "title": "Tentaizu",
        "short_title": "Tentaizu",
        "description": "A daily Japanese star-chart logic puzzle with number clues and ten hidden stars.",
        "title_key": "nav_tentaizu_daily",
        "desc_key": "nav_sub_tentaizu_daily",
        "canonical_path": "/puzzles/tentaizu",
        "play_path": "/puzzles/tentaizu",
        "how_to_play_path": "/puzzles/tentaizu/how-to-play",
        "leaderboard_path": "",
        "legacy_paths": ["/tentaizu"],
        "translated_slugs": {"en": "tentaizu", "es": "tentaizu", "fr": "tentaizu", "de": "tentaizu"},
        "image": "/static/img/og-tentaizu.png",
        "og_image": "https://minesweeper.org/static/img/og-tentaizu.png",
        "schema_type": "VideoGame",
        "genre": ["Puzzle", "Logic", "Daily Puzzle"],
        "keywords": ["tentaizu", "logic puzzle", "daily puzzle"],
        "is_daily": True,
        "is_multiplayer": False,
        "is_indexable": True,
        "mode": "tentaizu",
        "primary_href": "/puzzles/tentaizu",
        "actions": [
            {"href": "/puzzles/tentaizu", "label_key": "other_daily_puzzle", "primary": True},
            {"href": "/puzzles/tentaizu/easy-5x5-6", "label_key": "nav_tentaizu_easy"},
            {"href": "/puzzles/tentaizu/how-to-play", "label_key": "nav_how_to_play"},
        ],
        "faq_items": [
            {"question": "What is Tentaizu?", "answer": "Tentaizu is a logic puzzle where number clues tell you how many stars are hidden in neighboring cells."},
            {"question": "Does the Tentaizu puzzle change daily?", "answer": "Yes. The daily Tentaizu puzzle gives everyone the same challenge each day."},
        ],
        "how_to_steps": [
            "Read each number clue.",
            "Mark cells that must contain stars.",
            "Mark cells that must be empty.",
            "Finish when all hidden stars are correctly identified.",
        ],
    },
    {
        "slug": "mosaic",
        "category": "puzzles",
        "section": "Daily Logic Puzzles",
        "title": "Mosaic",
        "short_title": "Mosaic",
        "description": "A minesweeper-like mosaic logic puzzle where each clue counts a 3 by 3 area.",
        "title_key": "nav_mosaic_daily",
        "desc_key": "nav_sub_mosaic_daily",
        "canonical_path": "/puzzles/mosaic",
        "play_path": "/puzzles/mosaic",
        "how_to_play_path": "/puzzles/mosaic/how-to-play",
        "leaderboard_path": "",
        "legacy_paths": ["/mosaic", "/mosaic/standard"],
        "translated_slugs": {"en": "mosaic", "es": "mosaico", "fr": "mosaique", "de": "mosaik"},
        "image": "/static/img/og-mosaic.png",
        "og_image": "https://minesweeper.org/static/img/og-mosaic.png",
        "schema_type": "VideoGame",
        "genre": ["Puzzle", "Logic", "Daily Puzzle"],
        "keywords": ["mosaic puzzle", "logic puzzle", "minesweeper puzzle"],
        "is_daily": True,
        "is_multiplayer": False,
        "is_indexable": True,
        "mode": "mosaic",
        "primary_href": "/puzzles/mosaic",
        "actions": [
            {"href": "/puzzles/mosaic", "label_key": "other_daily_puzzle", "primary": True},
            {"href": "/puzzles/mosaic/easy", "label_key": "nav_mosaic_easy"},
            {"href": "/puzzles/mosaic/how-to-play", "label_key": "nav_how_to_play"},
        ],
        "faq_items": [
            {"question": "How is Mosaic different from Minesweeper?", "answer": "Mosaic clues count filled cells in a 3 by 3 area instead of mines around a single square."},
        ],
        "how_to_steps": ["Use number clues to identify filled cells.", "Mark known empty cells.", "Resolve every clue without guessing."],
    },
    {
        "slug": "tametsi",
        "category": "puzzles",
        "section": "Daily Logic Puzzles",
        "title": "Tametsi",
        "short_title": "Tametsi",
        "description": "A line-clue logic puzzle inspired by Minesweeper and nonograms.",
        "title_key": "nav_tametsi_daily",
        "desc_key": "nav_sub_tametsi_daily",
        "canonical_path": "/puzzles/tametsi",
        "play_path": "/puzzles/tametsi",
        "how_to_play_path": "",
        "leaderboard_path": "",
        "legacy_paths": ["/tametsi"],
        "translated_slugs": {"en": "tametsi", "es": "tametsi", "fr": "tametsi", "de": "tametsi"},
        "image": "/static/img/og-default.png",
        "og_image": "https://minesweeper.org/static/img/og-default.png",
        "schema_type": "VideoGame",
        "genre": ["Puzzle", "Logic"],
        "keywords": ["tametsi", "logic puzzle"],
        "is_daily": True,
        "is_multiplayer": False,
        "is_indexable": True,
        "mode": "tametsi",
        "primary_href": "/puzzles/tametsi",
        "actions": [{"href": "/puzzles/tametsi", "label_key": "other_daily_puzzle", "primary": True}],
        "faq_items": [{"question": "What kind of puzzle is Tametsi?", "answer": "Tametsi uses row and column totals to create a deduction puzzle with minesweeper-style marking."}],
        "how_to_steps": ["Read row and column totals.", "Flag cells that must be mines.", "Mark cells that must be safe."],
    },
    {
        "slug": "numbers-match",
        "category": "puzzles",
        "section": "Daily Logic Puzzles",
        "title": "Numbers Match",
        "short_title": "Numbers Match",
        "description": "A daily number-matching puzzle where you clear pairs and manage added rows.",
        "title_key": "nav_numbers_match",
        "desc_key": "nav_sub_numbers_match",
        "canonical_path": "/puzzles/numbers-match",
        "play_path": "/puzzles/numbers-match",
        "how_to_play_path": "",
        "leaderboard_path": "",
        "legacy_paths": ["/numbers-match"],
        "translated_slugs": {"en": "numbers-match", "es": "numbers-match", "fr": "numbers-match", "de": "numbers-match"},
        "image": "/static/img/og-default.png",
        "og_image": "https://minesweeper.org/static/img/og-default.png",
        "schema_type": "VideoGame",
        "genre": ["Puzzle", "Numbers", "Daily Puzzle"],
        "keywords": ["numbers match", "number puzzle", "daily puzzle"],
        "is_daily": True,
        "is_multiplayer": False,
        "is_indexable": True,
        "mode": "numbers-match",
        "primary_href": "/puzzles/numbers-match",
        "actions": [{"href": "/puzzles/numbers-match", "label_key": "other_daily_puzzle", "primary": True}],
        "faq_items": [{"question": "Is Numbers Match a daily puzzle?", "answer": "Yes. The daily Numbers Match board is shared by all players each day."}],
        "how_to_steps": ["Find matching number pairs.", "Clear legal pairs.", "Add rows only when needed.", "Clear the board for the best score."],
    },
    {
        "slug": "15-puzzle",
        "category": "puzzles",
        "section": "More Games",
        "title": "15-Puzzle",
        "short_title": "15-Puzzle",
        "description": "The classic sliding tile puzzle, also known as the Game of Fifteen.",
        "desc_key": "other_15puzzle_desc",
        "canonical_path": "/puzzles/15-puzzle",
        "play_path": "/puzzles/15-puzzle",
        "how_to_play_path": "/puzzles/15-puzzle/how-to-play",
        "leaderboard_path": "/puzzles/15-puzzle/leaderboard",
        "legacy_paths": ["/other/15puzzle", "/other/15puzzle/daily"],
        "translated_slugs": {"en": "15-puzzle", "es": "15-puzzle", "fr": "15-puzzle", "de": "15-puzzle"},
        "image": "/static/img/Diana15Puzzle.png",
        "og_image": "https://minesweeper.org/static/img/Diana15Puzzle.png",
        "schema_type": "VideoGame",
        "genre": ["Puzzle", "Sliding Puzzle"],
        "keywords": ["15 puzzle", "sliding puzzle", "daily puzzle"],
        "is_daily": True,
        "is_multiplayer": False,
        "is_indexable": True,
        "mode": "other",
        "primary_href": "/puzzles/15-puzzle",
        "actions": _actions("/puzzles/15-puzzle", generator=True),
        "faq_items": [{"question": "What is the 15-Puzzle?", "answer": "The 15-Puzzle is a sliding tile game where you arrange numbered tiles in order using one empty space."}],
        "how_to_steps": ["Slide a tile into the empty space.", "Arrange rows in order.", "Finish with all numbered tiles sorted."],
    },
    {
        "slug": "2048",
        "category": "puzzles",
        "section": "More Games",
        "title": "2048",
        "short_title": "2048",
        "description": "The classic number-merging puzzle played on a 4 by 4 grid.",
        "desc_key": "other_2048_desc",
        "canonical_path": "/puzzles/2048",
        "play_path": "/puzzles/2048",
        "how_to_play_path": "/puzzles/2048/how-to-play",
        "leaderboard_path": "/puzzles/2048/leaderboard",
        "legacy_paths": ["/other/2048", "/other/2048/daily"],
        "translated_slugs": {"en": "2048", "es": "2048", "fr": "2048", "de": "2048"},
        "image": "/static/img/og-default.png",
        "og_image": "https://minesweeper.org/static/img/og-default.png",
        "schema_type": "VideoGame",
        "genre": ["Puzzle", "Number Puzzle"],
        "keywords": ["2048", "number puzzle", "daily 2048"],
        "is_daily": True,
        "is_multiplayer": False,
        "is_indexable": True,
        "mode": "other",
        "primary_href": "/puzzles/2048",
        "actions": _actions("/puzzles/2048"),
        "faq_items": [{"question": "How do you win 2048?", "answer": "Merge matching tiles until you create a 2048 tile. You can continue playing after that for a higher score."}],
        "how_to_steps": ["Slide tiles in one direction.", "Merge equal numbers.", "Keep space open.", "Build toward 2048."],
    },
    {
        "slug": "2048-hexagon",
        "category": "puzzles",
        "section": "More Games",
        "title": "2048 Hexagon",
        "short_title": "2048 Hexagon",
        "description": "2048 on a hexagonal grid with six slide directions.",
        "canonical_path": "/puzzles/2048-hexagon",
        "play_path": "/puzzles/2048-hexagon",
        "how_to_play_path": "/puzzles/2048-hexagon/how-to-play",
        "leaderboard_path": "/puzzles/2048-hexagon/leaderboard",
        "legacy_paths": ["/other/2048hex", "/other/2048hex/play"],
        "translated_slugs": {"en": "2048-hexagon", "es": "2048-hexagono", "fr": "2048-hexagone", "de": "2048-hexagon"},
        "image": "/static/img/og-default.png",
        "og_image": "https://minesweeper.org/static/img/og-default.png",
        "schema_type": "VideoGame",
        "genre": ["Puzzle", "Number Puzzle"],
        "keywords": ["2048 hexagon", "hexagon 2048", "number puzzle"],
        "is_daily": True,
        "is_multiplayer": False,
        "is_indexable": True,
        "mode": "other",
        "primary_href": "/puzzles/2048-hexagon",
        "actions": _actions("/puzzles/2048-hexagon"),
        "faq_items": [{"question": "What changes in 2048 Hexagon?", "answer": "2048 Hexagon uses a hex grid with six movement directions instead of the four directions in classic 2048."}],
        "how_to_steps": ["Choose one of six directions.", "Merge matching tiles.", "Plan around the center cell.", "Build the highest tile you can."],
    },
    {
        "slug": "mahjong-solitaire",
        "category": "puzzles",
        "section": "More Games",
        "title": "Mahjong Solitaire",
        "short_title": "Mahjong",
        "description": "A classic tile-matching solitaire puzzle with a daily Turtle layout.",
        "desc_key": "other_mahjong_desc",
        "canonical_path": "/puzzles/mahjong-solitaire",
        "play_path": "/puzzles/mahjong-solitaire",
        "how_to_play_path": "/puzzles/mahjong-solitaire/how-to-play",
        "leaderboard_path": "/puzzles/mahjong-solitaire/leaderboard",
        "legacy_paths": ["/other/mahjong", "/other/mahjong/daily", "/other/mahjong/"],
        "translated_slugs": {"en": "mahjong-solitaire", "es": "mahjong-solitaire", "fr": "mahjong-solitaire", "de": "mahjong-solitaire"},
        "image": "/static/img/og-default.png",
        "og_image": "https://minesweeper.org/static/img/og-default.png",
        "schema_type": "VideoGame",
        "genre": ["Puzzle", "Tile Matching"],
        "keywords": ["mahjong solitaire", "tile matching", "daily mahjong"],
        "is_daily": True,
        "is_multiplayer": False,
        "is_indexable": True,
        "mode": "other",
        "primary_href": "/puzzles/mahjong-solitaire",
        "actions": _actions("/puzzles/mahjong-solitaire"),
        "faq_items": [{"question": "What is Mahjong Solitaire?", "answer": "Mahjong Solitaire is a single-player matching game where you remove pairs of free tiles."}],
        "how_to_steps": ["Find two matching free tiles.", "Remove the pair.", "Open blocked tiles.", "Clear the board."],
    },
    {
        "slug": "jigsaw",
        "category": "puzzles",
        "section": "More Games",
        "title": "Jigsaw Puzzle",
        "short_title": "Jigsaw",
        "description": "A daily browser jigsaw puzzle with multiple difficulty levels.",
        "desc_key": "other_jigsaw_desc",
        "canonical_path": "/puzzles/jigsaw",
        "play_path": "/puzzles/jigsaw",
        "how_to_play_path": "/puzzles/jigsaw/how-to-play",
        "leaderboard_path": "/puzzles/jigsaw/leaderboard",
        "legacy_paths": ["/other/jigsaw", "/other/jigsaw/daily"],
        "translated_slugs": {"en": "jigsaw", "es": "rompecabezas", "fr": "puzzle", "de": "puzzle"},
        "image": "/static/img/og-default.png",
        "og_image": "https://minesweeper.org/static/img/og-default.png",
        "schema_type": "VideoGame",
        "genre": ["Puzzle", "Jigsaw"],
        "keywords": ["jigsaw puzzle", "daily jigsaw", "browser puzzle"],
        "is_daily": True,
        "is_multiplayer": False,
        "is_indexable": True,
        "mode": "other",
        "primary_href": "/puzzles/jigsaw",
        "actions": _actions("/puzzles/jigsaw", generator=True, gallery=True),
        "faq_items": [{"question": "Can I choose a jigsaw difficulty?", "answer": "Yes. Jigsaw supports multiple difficulty levels and daily images."}],
        "how_to_steps": ["Choose a difficulty.", "Move pieces into place.", "Snap matching edges together.", "Complete the image."],
    },
    {
        "slug": "schulte-grid",
        "category": "puzzles",
        "section": "More Games",
        "title": "Schulte Grid",
        "short_title": "Schulte",
        "description": "A visual attention puzzle where you tap numbers in order as fast as possible.",
        "desc_key": "other_schulte_desc",
        "canonical_path": "/puzzles/schulte-grid",
        "play_path": "/puzzles/schulte-grid",
        "how_to_play_path": "/puzzles/schulte-grid/how-to-play",
        "leaderboard_path": "/puzzles/schulte-grid/leaderboard",
        "legacy_paths": ["/other/schulte", "/other/schulte/play"],
        "translated_slugs": {"en": "schulte-grid", "es": "tabla-schulte", "fr": "grille-schulte", "de": "schulte-tabelle"},
        "image": "/static/img/og-default.png",
        "og_image": "https://minesweeper.org/static/img/og-default.png",
        "schema_type": "VideoGame",
        "genre": ["Puzzle", "Cognitive Training"],
        "keywords": ["schulte grid", "attention puzzle", "brain training"],
        "is_daily": False,
        "is_multiplayer": False,
        "is_indexable": True,
        "mode": "other",
        "primary_href": "/puzzles/schulte-grid",
        "actions": _actions("/puzzles/schulte-grid"),
        "faq_items": [{"question": "What does Schulte Grid train?", "answer": "Schulte Grid is commonly used to train visual attention, scanning, and speed."}],
        "how_to_steps": ["Find number 1.", "Tap each number in order.", "Keep your eyes centered.", "Finish as quickly as possible."],
    },
    {
        "slug": "sudoku",
        "category": "puzzles",
        "section": "More Games",
        "title": "Sudoku",
        "short_title": "Sudoku",
        "description": "Classic 9 by 9 Sudoku with daily and random difficulty boards.",
        "desc_key": "other_sudoku_desc",
        "canonical_path": "/puzzles/sudoku",
        "play_path": "/puzzles/sudoku",
        "how_to_play_path": "",
        "leaderboard_path": "/puzzles/sudoku/leaderboard",
        "legacy_paths": ["/other/sudoku", "/other/sudoku/daily"],
        "translated_slugs": {"en": "sudoku", "es": "sudoku", "fr": "sudoku", "de": "sudoku"},
        "image": "/static/img/og-default.png",
        "og_image": "https://minesweeper.org/static/img/og-default.png",
        "schema_type": "VideoGame",
        "genre": ["Puzzle", "Number Puzzle", "Logic"],
        "keywords": ["sudoku", "daily sudoku", "logic puzzle"],
        "is_daily": True,
        "is_multiplayer": False,
        "is_indexable": True,
        "mode": "other",
        "primary_href": "/puzzles/sudoku",
        "actions": [
            {"href": "/puzzles/sudoku", "label": "Play Daily", "primary": True},
            {"href": "/puzzles/sudoku/leaderboard", "label_key": "nav_leaderboard"},
        ],
        "faq_items": [{"question": "What are the rules of Sudoku?", "answer": "Fill each row, column, and 3 by 3 box with digits 1 through 9 without repeating a digit."}],
        "how_to_steps": ["Scan rows and columns.", "Fill certain numbers first.", "Use box constraints.", "Complete the grid without duplicates."],
    },
]


PUZZLE_SECTIONS: list[str] = ["Daily Logic Puzzles", "More Games"]
PUZZLE_BY_SLUG: dict[str, dict[str, object]] = {str(game["slug"]): game for game in PUZZLE_GAMES}
PUZZLE_BY_CANONICAL_PATH: dict[str, dict[str, object]] = {
    str(game["canonical_path"]): game for game in PUZZLE_GAMES
}

LEADERBOARD_GROUPS: list[dict[str, object]] = [
    {
        "section": "Minesweeper",
        "items": [
            {
                "title": "Classic Minesweeper",
                "description": "Beginner, Intermediate, Expert, Custom, and Evil NG boards with daily, season, and all-time views.",
                "href": "/leaderboard?game=classic",
                "play_href": "/",
                "badge": "Full leaderboard",
            },
            {
                "title": "Rush",
                "description": "Timed wave-clearing scores for Easy, Normal, and Hard Rush modes.",
                "href": "/rush/leaderboard",
                "play_href": "/rush",
                "badge": "All-time scores",
            },
            {
                "title": "PvP Best Times",
                "description": "Fastest head-to-head PvP finishes.",
                "href": "/pvp/leaderboard",
                "play_href": "/pvp",
                "badge": "PvP",
            },
            {
                "title": "PvP Ratings",
                "description": "Elo-style rankings for competitive PvP players.",
                "href": "/pvp/rankings",
                "play_href": "/pvp",
                "badge": "Rankings",
            },
            {
                "title": "PvP Bot",
                "description": "Practice head-to-head Minesweeper against the computer before joining live PvP.",
                "href": "/pvp/bot",
                "play_href": "/pvp/bot",
                "badge": "Practice",
            },
            {
                "title": "Private Duel",
                "description": "Create a private head-to-head room and share the link with another player.",
                "href": "/duel",
                "play_href": "/duel",
                "badge": "Private match",
            },
            {
                "title": "World Cup 2026",
                "description": "Country and individual Minesweeper standings for the 2026 World Cup event.",
                "href": "/2026worldcup",
                "play_href": "/2026worldcup",
                "badge": "Event",
            },
        ],
    },
    {
        "section": "Variants",
        "items": [
            {
                "title": "Cylinder",
                "description": "Horizontal-wrap Minesweeper leaderboards by difficulty.",
                "href": "/leaderboard?game=cylinder",
                "play_href": "/cylinder",
                "badge": "Full leaderboard",
            },
            {
                "title": "Toroid",
                "description": "All-edge-wrap Minesweeper leaderboards by difficulty.",
                "href": "/leaderboard?game=toroid",
                "play_href": "/toroid",
                "badge": "Full leaderboard",
            },
            {
                "title": "Hexsweeper",
                "description": "Hex-grid Minesweeper leaderboards by difficulty.",
                "href": "/leaderboard?game=hex",
                "play_href": "/hexsweeper",
                "badge": "Full leaderboard",
            },
            {
                "title": "Worldsweeper",
                "description": "Minesweeper on polyhedral worlds.",
                "href": "/worldsweeper/leaderboard",
                "play_href": "/worldsweeper",
                "badge": "Variant",
            },
            {
                "title": "Globesweeper",
                "description": "The classic globe-style route, preserved as the familiar doorway into Worldsweeper.",
                "href": "/globesweeper/leaderboard",
                "play_href": "/globesweeper",
                "badge": "Classic route",
            },
            {
                "title": "Cubesweeper",
                "description": "Cube-face Minesweeper records.",
                "href": "/cubesweeper/leaderboard",
                "play_href": "/cubesweeper",
                "badge": "Variant",
            },
            {
                "title": "Mobiussweeper",
                "description": "Minesweeper on a twisted Mobius surface.",
                "href": "/mobiussweeper/leaderboard",
                "play_href": "/mobiussweeper",
                "badge": "Variant",
            },
            {
                "title": "Nonosweeper",
                "description": "Daily nonogram-meets-Minesweeper leaderboard on the game page.",
                "href": "/nonosweeper#nn-lb-section",
                "play_href": "/nonosweeper",
                "badge": "Daily board",
            },
            {
                "title": "Board Replay",
                "description": "Board-specific replay scores for exact shared board hashes.",
                "href": "/variants/replay/?rows=9&cols=9&mines=10",
                "play_href": "/variants/replay/?rows=9&cols=9&mines=10",
                "badge": "Board-specific",
            },
            {
                "title": "Minesweeper Chess",
                "description": "Partner chess variant; play links are listed here so the full games catalog is represented.",
                "href": "/minesweeperchess",
                "play_href": "/minesweeperchess",
                "badge": "Partner game",
            },
        ],
    },
    {
        "section": "Puzzles",
        "items": [
            {
                "title": "Tentaizu Daily",
                "description": "Daily star-chart logic puzzle leaderboard.",
                "href": "/tentaizu#tz-lb-section",
                "play_href": "/tentaizu",
                "badge": "Daily puzzle",
            },
            {
                "title": "Tentaizu Easy",
                "description": "Smaller 5x5 Tentaizu daily leaderboard.",
                "href": "/tentaizu/easy-5x5-6#tz-lb-section",
                "play_href": "/tentaizu/easy-5x5-6",
                "badge": "Daily puzzle",
            },
            {
                "title": "Mosaic Daily",
                "description": "Daily Mosaic logic puzzle leaderboard.",
                "href": "/mosaic/standard#ms-lb-section",
                "play_href": "/mosaic/standard",
                "badge": "Daily puzzle",
            },
            {
                "title": "Mosaic Easy",
                "description": "Easy Mosaic daily leaderboard.",
                "href": "/mosaic#ms-lb-section",
                "play_href": "/mosaic",
                "badge": "Daily puzzle",
            },
            {
                "title": "Mosaic Custom Boards",
                "description": "Custom Mosaic boards with board-specific score tracking.",
                "href": "/mosaic/custom/",
                "play_href": "/mosaic/custom/",
                "badge": "Custom boards",
            },
            {
                "title": "Tametsi",
                "description": "Daily row-and-column logic leaderboard on the game page.",
                "href": "/tametsi#tmt-lb-section",
                "play_href": "/tametsi",
                "badge": "Daily puzzle",
            },
            {
                "title": "Numbers Match",
                "description": "Daily number-pair clearing leaderboard.",
                "href": "/numbers-match#nm-lb-section",
                "play_href": "/numbers-match",
                "badge": "Daily puzzle",
            },
            {
                "title": "15-Puzzle",
                "description": "Sliding tile puzzle leaderboards by grid size.",
                "href": "/other/15puzzle/leaderboard",
                "play_href": "/other/15puzzle/daily",
                "badge": "Puzzle",
            },
            {
                "title": "2048",
                "description": "Classic 2048 daily and all-time scoreboards.",
                "href": "/other/2048/leaderboard",
                "play_href": "/other/2048/daily",
                "badge": "Puzzle",
            },
            {
                "title": "2048 Hexagon",
                "description": "Hex-grid 2048 leaderboards.",
                "href": "/other/2048hex/leaderboard",
                "play_href": "/other/2048hex/play",
                "badge": "Puzzle",
            },
            {
                "title": "Mahjong Solitaire",
                "description": "Daily tile-matching leaderboard.",
                "href": "/other/mahjong/leaderboard",
                "play_href": "/other/mahjong/daily",
                "badge": "Puzzle",
            },
            {
                "title": "Jigsaw Puzzle",
                "description": "Daily jigsaw leaderboards across puzzle sizes.",
                "href": "/other/jigsaw/leaderboard",
                "play_href": "/other/jigsaw/daily",
                "badge": "Puzzle",
            },
            {
                "title": "Schulte Grid",
                "description": "Visual scanning speed leaderboards by board size.",
                "href": "/other/schulte/leaderboard",
                "play_href": "/other/schulte/play",
                "badge": "Puzzle",
            },
            {
                "title": "Sudoku",
                "description": "Daily and difficulty-based Sudoku leaderboards.",
                "href": "/other/sudoku/scores",
                "play_href": "/other/sudoku/daily",
                "badge": "Puzzle",
            },
        ],
    },
]


def game_title(game: dict[str, object], lang: str = "en") -> str:
    """Return the catalog title. Fun languages intentionally keep English names."""
    return str(game["title"])


def localized_game_path(game: dict[str, object], lang: str = "en", suffix: str = "") -> str:
    """Build a localized path with translated slugs where available."""
    slug_map = game.get("translated_slugs", {})
    slug = str(slug_map.get(lang, slug_map.get("en", game["slug"]))) if isinstance(slug_map, dict) else str(game["slug"])
    path = f"/puzzles/{slug}{suffix}"
    return path if lang == "en" else f"/{lang}{path}"


def localized_action_path(game: dict[str, object], href: str, lang: str = "en") -> str:
    """Localize action URLs that belong to the game's canonical puzzle path."""
    canonical = str(game.get("canonical_path", ""))
    if canonical and (href == canonical or href.startswith(f"{canonical}/")):
        return localized_game_path(game, lang, href[len(canonical):])
    return href


def build_redirect_map() -> dict[str, str]:
    redirects: dict[str, str] = {"/other": "/puzzles"}
    suffix_pairs = {
        "/leaderboard": "/leaderboard",
        "/how-to-play": "/how-to-play",
        "/generator": "/generator",
        "/gallery": "/gallery",
    }
    for game in PUZZLE_GAMES:
        canonical = str(game["canonical_path"])
        for legacy in game.get("legacy_paths", []):
            redirects[str(legacy)] = canonical
        for legacy in game.get("legacy_paths", []):
            for old_suffix, new_suffix in suffix_pairs.items():
                redirects[f"{legacy}{old_suffix}"] = f"{canonical}{new_suffix}"
    redirects.update({
        "/tentaizu/easy-5x5-6": "/puzzles/tentaizu/easy-5x5-6",
        "/mosaic/easy": "/puzzles/mosaic/easy",
        "/other/2048hex/leaderboard": "/puzzles/2048-hexagon/leaderboard",
        "/other/2048hex/how-to-play": "/puzzles/2048-hexagon/how-to-play",
        "/other/mahjong/leaderboard": "/puzzles/mahjong-solitaire/leaderboard",
        "/other/mahjong/how-to-play": "/puzzles/mahjong-solitaire/how-to-play",
        "/other/schulte/leaderboard": "/puzzles/schulte-grid/leaderboard",
        "/other/schulte/how-to-play": "/puzzles/schulte-grid/how-to-play",
        "/other/sudoku/scores": "/puzzles/sudoku/leaderboard",
    })
    return redirects


def with_query(path: str, query_params) -> str:
    query = urlencode(list(query_params.multi_items())) if hasattr(query_params, "multi_items") else ""
    return f"{path}?{query}" if query else path
