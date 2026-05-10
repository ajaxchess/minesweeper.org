import pytest

from game_catalog import (
    FUN_LANGS,
    PUZZLE_GAMES,
    build_redirect_map,
    game_title,
    localized_action_path,
    localized_game_path,
)


pytestmark = pytest.mark.usefixtures("client")


REQUIRED_FIELDS = {
    "slug",
    "category",
    "section",
    "title",
    "description",
    "canonical_path",
    "play_path",
    "legacy_paths",
    "translated_slugs",
    "schema_type",
    "genre",
    "keywords",
    "is_daily",
    "is_multiplayer",
    "is_indexable",
    "mode",
    "primary_href",
    "actions",
    "faq_items",
    "how_to_steps",
}


def test_every_puzzle_has_required_metadata():
    slugs = set()
    canonical_paths = set()
    for game in PUZZLE_GAMES:
        missing = REQUIRED_FIELDS - set(game)
        assert not missing, f"{game.get('slug', '<unknown>')} missing {sorted(missing)}"
        assert game["slug"] not in slugs
        assert game["canonical_path"] not in canonical_paths
        assert str(game["canonical_path"]).startswith("/puzzles/")
        assert game["translated_slugs"].get("en") == game["slug"]
        assert game["actions"], f"{game['slug']} needs at least one action"
        slugs.add(game["slug"])
        canonical_paths.add(game["canonical_path"])


def test_fun_languages_keep_game_titles_in_english():
    for lang in FUN_LANGS:
        for game in PUZZLE_GAMES:
            assert game_title(game, lang) == game["title"]


def test_localized_game_paths_use_translated_slugs_when_available():
    jigsaw = next(game for game in PUZZLE_GAMES if game["slug"] == "jigsaw")
    assert localized_game_path(jigsaw, "en") == "/puzzles/jigsaw"
    assert localized_game_path(jigsaw, "es") == "/es/puzzles/rompecabezas"
    assert localized_game_path(jigsaw, "eo") == "/eo/puzzles/jigsaw"
    assert localized_action_path(jigsaw, "/puzzles/jigsaw/how-to-play", "es") == (
        "/es/puzzles/rompecabezas/how-to-play"
    )


def test_redirect_map_covers_legacy_puzzle_urls():
    redirects = build_redirect_map()
    assert redirects["/other"] == "/puzzles"
    assert redirects["/tentaizu"] == "/puzzles/tentaizu"
    assert redirects["/mosaic"] == "/puzzles/mosaic"
    assert redirects["/other/2048/daily"] == "/puzzles/2048"
    assert redirects["/other/jigsaw/daily"] == "/puzzles/jigsaw"
