"""
breadcrumbs.py — Site-wide BreadcrumbList helpers.

Imported by main.py and duel_routes.py (which has its own Jinja2Templates
instance) so that get_breadcrumbs is registered in every template environment.
"""

_BASE_URL = "https://minesweeper.org"

_BREADCRUMB_MAP: dict[str, list[tuple[str, str]]] = {
    # ── Core game ────────────────────────────────────────────────────────────
    "/intermediate":              [("Intermediate", "/intermediate")],
    "/expert":                    [("Expert", "/expert")],
    "/custom":                    [("Custom", "/custom")],
    "/leaderboard":               [("Leaderboard", "/leaderboard")],
    # ── Info / static ────────────────────────────────────────────────────────
    "/how-to-play":               [("How to Play", "/how-to-play")],
    "/strategy":                  [("Strategy", "/strategy")],
    "/history":                   [("History", "/history")],
    "/about":                     [("About", "/about")],
    "/contact":                   [("Contact", "/contact")],
    "/privacy":                   [("Privacy Policy", "/privacy")],
    "/terms":                     [("Terms of Service", "/terms")],
    "/quests":                    [("Quests", "/quests")],
    "/info/3bv":                  [("How to Play", "/how-to-play"), ("3BV", "/info/3bv")],
    # ── Blog ─────────────────────────────────────────────────────────────────
    "/blog":                      [("Blog", "/blog")],
    # ── Rush ─────────────────────────────────────────────────────────────────
    "/rush":                      [("Rush", "/rush")],
    "/rush/how-to-play":          [("Rush", "/rush"), ("How to Play", "/rush/how-to-play")],
    "/rush/leaderboard":          [("Rush", "/rush"), ("Leaderboard", "/rush/leaderboard")],
    # ── Tentaizu ─────────────────────────────────────────────────────────────
    "/tentaizu":                  [("Tentaizu", "/tentaizu")],
    "/tentaizu/how-to-play":      [("Tentaizu", "/tentaizu"), ("How to Play", "/tentaizu/how-to-play")],
    "/tentaizu/strategy":         [("Tentaizu", "/tentaizu"), ("Strategy", "/tentaizu/strategy")],
    "/tentaizu/easy":             [("Tentaizu", "/tentaizu"), ("Easy", "/tentaizu/easy")],
    "/tentaizu/archive":          [("Tentaizu", "/tentaizu"), ("Archive", "/tentaizu/archive")],
    # ── Mosaic ───────────────────────────────────────────────────────────────
    "/mosaic":                    [("Mosaic", "/mosaic")],
    "/mosaic/how-to-play":        [("Mosaic", "/mosaic"), ("How to Play", "/mosaic/how-to-play")],
    "/mosaic/easy":               [("Mosaic", "/mosaic"), ("Easy", "/mosaic/easy")],
    # ── Nonosweeper ──────────────────────────────────────────────────────────
    "/nonosweeper":               [("Nonosweeper", "/nonosweeper")],
    # ── Variants hub ─────────────────────────────────────────────────────────
    "/variants":                  [("Variants", "/variants")],
    "/variants/replay/":          [("Variants", "/variants"), ("Replay", "/variants/replay/")],
    "/variants/board-generator":  [("Variants", "/variants"), ("Board Generator", "/variants/board-generator")],
    # ── Cylinder ─────────────────────────────────────────────────────────────
    "/cylinder":                  [("Variants", "/variants"), ("Cylinder", "/cylinder")],
    "/cylinder/intermediate":     [("Variants", "/variants"), ("Cylinder", "/cylinder"), ("Intermediate", "/cylinder/intermediate")],
    "/cylinder/expert":           [("Variants", "/variants"), ("Cylinder", "/cylinder"), ("Expert", "/cylinder/expert")],
    "/cylinder/custom":           [("Variants", "/variants"), ("Cylinder", "/cylinder"), ("Custom", "/cylinder/custom")],
    "/cylinder/leaderboard":      [("Variants", "/variants"), ("Cylinder", "/cylinder"), ("Leaderboard", "/cylinder/leaderboard")],
    # ── Toroid ───────────────────────────────────────────────────────────────
    "/toroid":                    [("Variants", "/variants"), ("Toroid", "/toroid")],
    "/toroid/intermediate":       [("Variants", "/variants"), ("Toroid", "/toroid"), ("Intermediate", "/toroid/intermediate")],
    "/toroid/expert":             [("Variants", "/variants"), ("Toroid", "/toroid"), ("Expert", "/toroid/expert")],
    "/toroid/custom":             [("Variants", "/variants"), ("Toroid", "/toroid"), ("Custom", "/toroid/custom")],
    # ── Hexsweeper ───────────────────────────────────────────────────────────
    "/hexsweeper":                [("Variants", "/variants"), ("Hexsweeper", "/hexsweeper")],
    "/hexsweeper/intermediate":   [("Variants", "/variants"), ("Hexsweeper", "/hexsweeper"), ("Intermediate", "/hexsweeper/intermediate")],
    "/hexsweeper/expert":         [("Variants", "/variants"), ("Hexsweeper", "/hexsweeper"), ("Expert", "/hexsweeper/expert")],
    "/hexsweeper/custom":         [("Variants", "/variants"), ("Hexsweeper", "/hexsweeper"), ("Custom", "/hexsweeper/custom")],
    "/hexsweeper/leaderboard":    [("Variants", "/variants"), ("Hexsweeper", "/hexsweeper"), ("Leaderboard", "/hexsweeper/leaderboard")],
    # ── WorldSweeper ─────────────────────────────────────────────────────────
    "/worldsweeper":              [("Variants", "/variants"), ("WorldSweeper", "/worldsweeper")],
    "/worldsweeper/intermediate": [("Variants", "/variants"), ("WorldSweeper", "/worldsweeper"), ("Intermediate", "/worldsweeper/intermediate")],
    "/worldsweeper/expert":       [("Variants", "/variants"), ("WorldSweeper", "/worldsweeper"), ("Expert", "/worldsweeper/expert")],
    "/worldsweeper/dodecahedron": [("Variants", "/variants"), ("WorldSweeper", "/worldsweeper"), ("Dodecahedron", "/worldsweeper/dodecahedron")],
    "/worldsweeper/leaderboard":  [("Variants", "/variants"), ("WorldSweeper", "/worldsweeper"), ("Leaderboard", "/worldsweeper/leaderboard")],
    # ── CubeSweeper ──────────────────────────────────────────────────────────
    "/cubesweeper":               [("Variants", "/variants"), ("CubeSweeper", "/cubesweeper")],
    "/cubesweeper/intermediate":  [("Variants", "/variants"), ("CubeSweeper", "/cubesweeper"), ("Intermediate", "/cubesweeper/intermediate")],
    "/cubesweeper/expert":        [("Variants", "/variants"), ("CubeSweeper", "/cubesweeper"), ("Expert", "/cubesweeper/expert")],
    "/cubesweeper/custom":        [("Variants", "/variants"), ("CubeSweeper", "/cubesweeper"), ("Custom", "/cubesweeper/custom")],
    "/cubesweeper/leaderboard":   [("Variants", "/variants"), ("CubeSweeper", "/cubesweeper"), ("Leaderboard", "/cubesweeper/leaderboard")],
    # ── PvP ──────────────────────────────────────────────────────────────────
    "/pvp":                       [("PvP", "/pvp")],
    "/duel":                      [("PvP", "/pvp"), ("Duel", "/duel")],
    "/pvp/leaderboard":           [("PvP", "/pvp"), ("Leaderboard", "/pvp/leaderboard")],
    "/pvp/rankings":              [("PvP", "/pvp"), ("Rankings", "/pvp/rankings")],
    # ── Other hub ────────────────────────────────────────────────────────────
    "/other":                     [("Other Games", "/other")],
    # ── 15 Puzzle ────────────────────────────────────────────────────────────
    "/other/15puzzle":            [("Other Games", "/other"), ("15 Puzzle", "/other/15puzzle/daily")],
    "/other/15puzzle/daily":      [("Other Games", "/other"), ("15 Puzzle", "/other/15puzzle/daily")],
    "/other/15puzzle/leaderboard":[("Other Games", "/other"), ("15 Puzzle", "/other/15puzzle/daily"), ("Leaderboard", "/other/15puzzle/leaderboard")],
    "/other/15puzzle/how-to-play":[("Other Games", "/other"), ("15 Puzzle", "/other/15puzzle/daily"), ("How to Play", "/other/15puzzle/how-to-play")],
    "/other/15puzzle/generator":  [("Other Games", "/other"), ("15 Puzzle", "/other/15puzzle/daily"), ("Generator", "/other/15puzzle/generator")],
    # ── 2048 ─────────────────────────────────────────────────────────────────
    "/other/2048":                [("Other Games", "/other"), ("2048", "/other/2048")],
    "/other/2048/daily":          [("Other Games", "/other"), ("2048", "/other/2048"), ("Daily", "/other/2048/daily")],
    "/other/2048/leaderboard":    [("Other Games", "/other"), ("2048", "/other/2048"), ("Leaderboard", "/other/2048/leaderboard")],
    "/other/2048/how-to-play":    [("Other Games", "/other"), ("2048", "/other/2048"), ("How to Play", "/other/2048/how-to-play")],
    # ── 2048 Hex ─────────────────────────────────────────────────────────────
    "/other/2048hex":             [("Other Games", "/other"), ("2048 Hex", "/other/2048hex")],
    "/other/2048hex/play":        [("Other Games", "/other"), ("2048 Hex", "/other/2048hex"), ("Play", "/other/2048hex/play")],
    "/other/2048hex/how-to-play": [("Other Games", "/other"), ("2048 Hex", "/other/2048hex"), ("How to Play", "/other/2048hex/how-to-play")],
    # ── Jigsaw ───────────────────────────────────────────────────────────────
    "/other/jigsaw":              [("Other Games", "/other"), ("Jigsaw", "/other/jigsaw/daily")],
    "/other/jigsaw/daily":        [("Other Games", "/other"), ("Jigsaw", "/other/jigsaw/daily")],
    "/other/jigsaw/leaderboard":  [("Other Games", "/other"), ("Jigsaw", "/other/jigsaw/daily"), ("Leaderboard", "/other/jigsaw/leaderboard")],
    "/other/jigsaw/how-to-play":  [("Other Games", "/other"), ("Jigsaw", "/other/jigsaw/daily"), ("How to Play", "/other/jigsaw/how-to-play")],
    "/other/jigsaw/gallery":      [("Other Games", "/other"), ("Jigsaw", "/other/jigsaw/daily"), ("Gallery", "/other/jigsaw/gallery")],
    "/other/jigsaw/generator":    [("Other Games", "/other"), ("Jigsaw", "/other/jigsaw/daily"), ("Generator", "/other/jigsaw/generator")],
    # ── Mahjong ──────────────────────────────────────────────────────────────
    "/other/mahjong":             [("Other Games", "/other"), ("Mahjong Solitaire", "/other/mahjong/daily")],
    "/other/mahjong/daily":       [("Other Games", "/other"), ("Mahjong Solitaire", "/other/mahjong/daily")],
    "/other/mahjong/leaderboard": [("Other Games", "/other"), ("Mahjong Solitaire", "/other/mahjong/daily"), ("Leaderboard", "/other/mahjong/leaderboard")],
    "/other/mahjong/how-to-play": [("Other Games", "/other"), ("Mahjong Solitaire", "/other/mahjong/daily"), ("How to Play", "/other/mahjong/how-to-play")],
    # ── Schulte Grid ─────────────────────────────────────────────────────────
    "/other/schulte":             [("Other Games", "/other"), ("Schulte Grid", "/other/schulte/play")],
    "/other/schulte/play":        [("Other Games", "/other"), ("Schulte Grid", "/other/schulte/play")],
    "/other/schulte/leaderboard": [("Other Games", "/other"), ("Schulte Grid", "/other/schulte/play"), ("Leaderboard", "/other/schulte/leaderboard")],
    "/other/schulte/how-to-play": [("Other Games", "/other"), ("Schulte Grid", "/other/schulte/play"), ("How to Play", "/other/schulte/how-to-play")],
}


def get_breadcrumbs(path: str) -> list[dict]:
    """Return full BreadcrumbList items for a URL path, including Home at position 1.
    Returns [] for the home page, unrecognised paths, and blog post detail pages
    (those provide a richer 3-level crumb via their own template block).
    """
    trail = _BREADCRUMB_MAP.get(path)
    if trail is None:
        return []
    result = [{"name": "Home", "url": _BASE_URL + "/"}]
    for name, rel in trail:
        result.append({"name": name, "url": _BASE_URL + rel})
    return result
