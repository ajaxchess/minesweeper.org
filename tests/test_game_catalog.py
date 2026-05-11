import pytest
from html import escape

from game_catalog import (
    FUN_LANGS,
    LEADERBOARD_GROUPS,
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


def test_leaderboard_catalog_has_required_fields():
    titles = set()
    for group in LEADERBOARD_GROUPS:
        assert group["section"]
        assert group["items"]
        for item in group["items"]:
            missing = {"title", "description", "href", "play_href", "badge"} - set(item)
            assert not missing, f"{item.get('title', '<unknown>')} missing {sorted(missing)}"
            assert item["title"] not in titles
            assert str(item["href"]).startswith("/")
            assert str(item["play_href"]).startswith("/")
            titles.add(item["title"])


def test_leaderboard_page_lists_all_catalog_entries(client):
    r = client.get("/leaderboard")
    assert r.status_code == 200
    assert "Your Leaderboard Snapshot" in r.text or "Save your personal leaderboard story" in r.text
    assert "Top 3 From Around The Site" in r.text
    assert "CHAMPION_BOARDS" in r.text
    assert "Hexsweeper" in r.text
    assert "All Leaderboards" in r.text
    for group in LEADERBOARD_GROUPS:
        assert group["section"] in r.text
        for item in group["items"]:
            assert item["title"] in r.text
            assert escape(item["href"], quote=True) in r.text
