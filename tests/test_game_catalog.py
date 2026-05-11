import pytest
import re
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from game_catalog import (
    FUN_LANGS,
    LANGUAGE_OPTIONS,
    LEADERBOARD_GROUPS,
    PUZZLE_GAMES,
    build_redirect_map,
    game_title,
    localized_action_path,
    localized_game_path,
)
from leaderboard_platform import LEADERBOARD_SPECS, SPECS_BY_ID
from quest_catalog import DAILY_QUESTS, SEASONAL_QUESTS, quest_config
from translations import SUPPORTED_LANGS


pytestmark = pytest.mark.usefixtures("client")


REQUIRED_FIELDS = {
    "slug",
    "category",
    "section",
    "title",
    "icon",
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


def test_leaderboard_catalog_features_all_playable_game_families():
    expected_titles = {
        "Classic Minesweeper",
        "Rush",
        "PvP Best Times",
        "PvP Ratings",
        "PvP Bot",
        "Private Duel",
        "World Cup 2026",
        "Cylinder",
        "Toroid",
        "Hexsweeper",
        "Worldsweeper",
        "Globesweeper",
        "Cubesweeper",
        "Mobiussweeper",
        "Nonosweeper",
        "Board Replay",
        "Minesweeper Chess",
        "Tentaizu Daily",
        "Tentaizu Easy",
        "Mosaic Daily",
        "Mosaic Easy",
        "Mosaic Custom Boards",
        "Tametsi",
        "Numbers Match",
        "15-Puzzle",
        "2048",
        "2048 Hexagon",
        "Mahjong Solitaire",
        "Jigsaw Puzzle",
        "Schulte Grid",
        "Sudoku",
    }
    titles = {
        item["title"]
        for group in LEADERBOARD_GROUPS
        for item in group["items"]
    }
    assert expected_titles <= titles


def test_leaderboard_page_lists_all_catalog_entries(client):
    r = client.get("/leaderboard")
    assert r.status_code == 200
    assert "Your Leaderboard Snapshot" in r.text or "Save your personal leaderboard story" in r.text
    assert "Top 3 From Around The Site" in r.text
    assert "CHAMPION_BOARDS" in r.text
    assert "Hexsweeper" in r.text
    assert "All Leaderboards" in r.text
    for period in ["daily", "weekly", "monthly", "season", "yearly", "alltime"]:
        assert f'data-period="{period}"' in r.text
        assert f'data-showcase-period="{period}"' in r.text
    for group in LEADERBOARD_GROUPS:
        assert group["section"] in r.text
        for item in group["items"]:
            assert item["title"] in r.text
            assert escape(item["href"], quote=True) in r.text


def test_leaderboard_full_board_links_resolve(client):
    template = Path("templates/leaderboard.html").read_text(encoding="utf-8")
    js_links = re.findall(r"leaderboard: '([^']+)'", template)
    catalog_links = [item["href"] for group in LEADERBOARD_GROUPS for item in group["items"]]
    links = list(dict.fromkeys(catalog_links + js_links))
    assert links

    bad = []
    for href in links:
        parsed = urlsplit(href)
        path = parsed.path or "/"
        target = path + (f"?{parsed.query}" if parsed.query else "")
        response = client.get(target, follow_redirects=True)
        if response.status_code >= 400:
            bad.append((href, response.status_code))

    assert not bad


def test_leaderboard_page_represents_every_puzzle_game(client):
    titles = {
        item["title"]
        for group in LEADERBOARD_GROUPS
        for item in group["items"]
        if group["section"] == "Puzzles"
    }
    joined_titles = " ".join(titles)
    for game in PUZZLE_GAMES:
        assert game["title"] in joined_titles
        assert game["play_path"] or game["primary_href"]

    r = client.get("/leaderboard")
    assert r.status_code == 200
    for title in titles:
        assert title in r.text


def test_normalized_leaderboard_catalog_covers_major_categories(client):
    assert SPECS_BY_ID
    categories = {spec.category for spec in LEADERBOARD_SPECS}
    assert {"minesweeper", "rush", "puzzles", "pvp", "events"} <= categories
    assert any(spec.group == "Cylinder" and spec.category == "minesweeper" for spec in LEADERBOARD_SPECS)
    assert any(spec.group == "Toroid" and spec.category == "minesweeper" for spec in LEADERBOARD_SPECS)
    assert any(spec.category == "rush" for spec in LEADERBOARD_SPECS)
    assert "pvp-wins" in SPECS_BY_ID
    assert "wc2026-individuals" in SPECS_BY_ID

    r = client.get("/api/leaderboards/catalog")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == len(LEADERBOARD_SPECS)
    assert data == sorted(data, key=lambda item: item["popularity"])


def test_normalized_leaderboard_cards_endpoint_returns_every_card(client):
    r = client.get("/api/leaderboards/cards?period=daily")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == len(LEADERBOARD_SPECS)
    first = data[0]
    assert {"id", "title", "category", "group", "level", "period", "metric", "play_href", "full_href", "rows"} <= set(first)
    assert isinstance(first["rows"], list)

    puzzles = client.get("/api/leaderboards/cards?category=puzzles&period=daily").json()
    assert puzzles
    assert {card["category"] for card in puzzles} == {"puzzles"}


def test_puzzles_dropdown_lists_all_puzzle_games(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "All Puzzles" in r.text
    assert 'href="/puzzles"' in r.text
    for game in PUZZLE_GAMES:
        assert "nav_desc_key" in game
        assert f'href="{game["play_path"]}"' in r.text
        assert f"puzzle-nav-logo-{game['slug']}" in r.text
    assert "Slide 15 numbered tiles into order" not in r.text
    assert "A new daily puzzle is generated each day" not in r.text


def test_all_supported_languages_render_core_pages(client):
    assert {option["code"] for option in LANGUAGE_OPTIONS} <= SUPPORTED_LANGS
    for lang in sorted(SUPPORTED_LANGS - {"en"}):
        for path in ["/", "/leaderboard", "/puzzles", "/quests"]:
            r = client.get(f"/{lang}{path}")
            assert r.status_code == 200, f"{lang}{path}"
            assert f'<html lang="{lang}">' in r.text


def test_quest_catalog_has_required_fields():
    for quest in DAILY_QUESTS:
        assert {"id", "label_key", "icon", "link", "target"} <= set(quest)
    for quest in SEASONAL_QUESTS:
        assert {"id", "label_key", "icon", "type", "key"} <= set(quest)
        if quest["type"] == "count":
            assert "target" in quest


def test_quests_page_uses_rendered_config(client):
    r = client.get("/quests")
    assert r.status_code == 200
    assert "window.QUEST_CONFIG" in r.text
    assert "questsGetState" in r.text
    config = quest_config({
        "quest_daily_tentaizu": "Clear the daily Tentaizu puzzle",
        "quest_daily_easy_win": "Win Easy Minesweeper",
        "quest_daily_rush_5": "Clear 5 mines on Rush mode",
        "quest_season_tentaizu_10": "Clear 10 daily Tentaizu puzzles",
        "quest_season_intermediate_win": "Win Intermediate Minesweeper",
        "quest_season_rush_100": "Clear 100 mines on Rush mode",
        "quest_play": "Play",
        "quest_complete": "Complete!",
        "quest_not_complete": "Not yet completed",
        "quest_unlocked": "Unlocked!",
        "quest_days": "days",
        "quest_reward_reason_streak": "20-day daily quest streak",
        "quest_reward_reason_season": "10 daily quests this season",
        "quest_toast_reward_unlocked": "Reward unlocked! Ads disabled — {reason}.",
        "quest_toast_daily_tentaizu": "Daily quest complete! Tentaizu puzzle cleared.",
        "quest_toast_daily_easy": "Daily quest complete! Easy Minesweeper won.",
        "quest_toast_daily_rush": "Daily quest complete! 5 Rush mines cleared.",
        "quest_toast_season_tentaizu": "Seasonal quest complete! 10 Tentaizu puzzles cleared!",
        "quest_toast_season_intermediate": "Seasonal quest complete! Intermediate Minesweeper won!",
        "quest_toast_season_rush": "Seasonal quest complete! 100 Rush mines cleared!",
    })
    for quest in config["daily"] + config["seasonal"]:
        assert quest["id"] in r.text
