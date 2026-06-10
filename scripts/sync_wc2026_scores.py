#!/usr/bin/env python3
"""
sync_wc2026_scores.py — Fetch match results from worldcup26.ir and update
the wc2026_matches table so every country page shows current scores.

Run once daily (e.g. via cron at 09:00 UTC) throughout the tournament.

Usage:
    python scripts/sync_wc2026_scores.py            # live update
    python scripts/sync_wc2026_scores.py --dry-run  # preview changes, no writes
"""

import argparse
import logging
import os
import sys
import unicodedata

import requests

# ── path setup ───────────────────────────────────────────────────────────────
# Allow importing database / ORM models from the project root regardless of
# where this script is invoked from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import WC2026Match, SessionLocal  # noqa: E402

# ── logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── constants ────────────────────────────────────────────────────────────────
API_BASE = "https://worldcup26.ir"

# worldcup26.ir name_en values that don't auto-convert to the right slug.
# Everything else is handled by _name_to_slug() below.
_SLUG_OVERRIDES: dict[str, str] = {
    "United States":                    "usa",
    "Democratic Republic of the Congo": "dr-congo",
    "Bosnia and Herzegovina":           "bosnia-and-herzegovina",
    "Curaçao":                          "curacao",
}


# ── helpers ──────────────────────────────────────────────────────────────────

def _name_to_slug(name: str) -> str:
    """Convert a worldcup26.ir team name to a minesweeper.org slug."""
    if name in _SLUG_OVERRIDES:
        return _SLUG_OVERRIDES[name]
    # Strip diacritics (e.g. accented chars), lowercase, spaces → hyphens
    nfd = unicodedata.normalize("NFD", name)
    plain = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return plain.lower().replace(" ", "-").replace("&", "and").replace("'", "")


def _fetch(path: str) -> list:
    url = f"{API_BASE}{path}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


# ── core logic ───────────────────────────────────────────────────────────────

def build_team_map() -> dict[str, str]:
    """Return {worldcup26_team_id: minesweeper_slug} for all 48 teams."""
    teams = _fetch("/get/teams")
    mapping = {str(t["id"]): _name_to_slug(t["name_en"]) for t in teams}
    log.info("Team map built for %d teams", len(mapping))
    return mapping


def sync(dry_run: bool = False) -> None:
    team_map = build_team_map()
    games    = _fetch("/get/games")

    finished = [g for g in games if str(g.get("finished", "")).upper() == "TRUE"]
    log.info("API returned %d total games, %d finished", len(games), len(finished))

    db = SessionLocal()
    try:
        n_updated = n_already_current = n_not_found = 0

        for game in finished:
            home_id  = str(game.get("home_team_id", ""))
            away_id  = str(game.get("away_team_id", ""))
            home_slug = team_map.get(home_id)
            away_slug = team_map.get(away_id)

            if not home_slug or not away_slug:
                log.warning("  Unknown team id(s): home=%s away=%s — skipping", home_id, away_id)
                n_not_found += 1
                continue

            # Parse scores — worldcup26.ir returns them as strings
            try:
                home_score = int(game["home_score"])
                away_score = int(game["away_score"])
            except (KeyError, TypeError, ValueError):
                log.warning("  Unparseable scores for %s vs %s — skipping", home_slug, away_slug)
                n_not_found += 1
                continue

            # Find our DB row; teams may be stored in either order
            row = (
                db.query(WC2026Match)
                .filter(
                    (
                        (WC2026Match.team1_slug == home_slug) &
                        (WC2026Match.team2_slug == away_slug)
                    ) | (
                        (WC2026Match.team1_slug == away_slug) &
                        (WC2026Match.team2_slug == home_slug)
                    )
                )
                .first()
            )

            if not row:
                log.warning("  No DB row found for %s vs %s — skipping", home_slug, away_slug)
                n_not_found += 1
                continue

            # Assign scores in the same team1/team2 order as stored in our DB
            if row.team1_slug == home_slug:
                new_score1, new_score2 = home_score, away_score
            else:
                new_score1, new_score2 = away_score, home_score

            # Skip if already up to date
            if (row.status == "final"
                    and row.score1 == new_score1
                    and row.score2 == new_score2):
                n_already_current += 1
                continue

            log.info(
                "  %s vs %s  [match %d]  %s→%s  %s-%s → final",
                row.team1_slug, row.team2_slug, row.id,
                row.status, "final", new_score1, new_score2,
            )

            if not dry_run:
                row.score1 = new_score1
                row.score2 = new_score2
                row.status = "final"

            n_updated += 1

        if not dry_run:
            db.commit()
            log.info("Changes committed to database.")
        else:
            log.info("Dry run — no changes written.")

        log.info(
            "Summary: %d updated, %d already current, %d not found/skipped",
            n_updated, n_already_current, n_not_found,
        )

    except Exception:
        db.rollback()
        log.exception("Error during sync — rolled back.")
        raise
    finally:
        db.close()


# ── entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sync WC2026 match scores from worldcup26.ir into the wc2026_matches table."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would change without writing anything to the database.",
    )
    args = parser.parse_args()
    sync(dry_run=args.dry_run)
