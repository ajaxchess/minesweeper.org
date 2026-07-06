"""
phase2_analyzer/migrate_difficulty.py — add the `difficulty` column to
game_analyses and backfill it from game_replays.mode.

Why: the bootcamp diagnosis takes a `difficulty` query param but game_analyses
had no difficulty column, so "expert" diagnoses silently blended beginner/
intermediate/custom games. New analyses get the column from the pipeline
(persist_analysis); this migration covers the existing rows.

Idempotent — safe to re-run. Run as a file path, NOT `python3 -m …` (the -m
form triggers phase2_analyzer/__init__.py which imports the whole pipeline):

    # Show the SQL without executing:
    python3 phase2_analyzer/migrate_difficulty.py

    # Execute against the configured database:
    python3 phase2_analyzer/migrate_difficulty.py --apply

Deploy order (cron auto-deploys code every 5 min):
    1. Run this with --apply FIRST — adding the column is harmless while the
       old code is still live.
    2. Let the code deploy pick up the pipeline + query changes.
    Until backfill completes, queries treat NULL difficulty as "any", so
    nothing breaks in between.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

STATEMENTS = [
    # MySQL 8 supports IF NOT EXISTS on ADD COLUMN via a plain try; older
    # versions don't, so we feature-detect in code instead of DDL.
    ("add column",
     "ALTER TABLE game_analyses ADD COLUMN difficulty VARCHAR(16) NULL"),
    ("add index",
     "CREATE INDEX ix_game_analyses_player_diff_created "
     "ON game_analyses (player_id, difficulty, created_at)"),
    ("backfill from game_replays.mode",
     "UPDATE game_analyses ga "
     "JOIN game_replays gr ON gr.id = ga.game_replay_id "
     "SET ga.difficulty = CASE "
     "  WHEN gr.mode IN ('beginner','intermediate','expert') THEN gr.mode "
     "  ELSE 'custom' END "
     "WHERE ga.difficulty IS NULL"),
]


def main() -> int:
    apply = "--apply" in sys.argv

    if not apply:
        print("-- DRY RUN (pass --apply to execute)\n")
        for label, sql in STATEMENTS:
            print(f"-- {label}\n{sql};\n")
        return 0

    from sqlalchemy import inspect, text
    from database import engine  # noqa: deferred so dry-run needs no DB

    insp = inspect(engine)
    columns = {c["name"] for c in insp.get_columns("game_analyses")}
    indexes = {i["name"] for i in insp.get_indexes("game_analyses")}

    with engine.begin() as conn:
        if "difficulty" in columns:
            print("column difficulty already exists — skipping ADD COLUMN")
        else:
            conn.execute(text(STATEMENTS[0][1]))
            print("added column game_analyses.difficulty")

        if "ix_game_analyses_player_diff_created" in indexes:
            print("index already exists — skipping CREATE INDEX")
        else:
            conn.execute(text(STATEMENTS[1][1]))
            print("created index ix_game_analyses_player_diff_created")

        result = conn.execute(text(STATEMENTS[2][1]))
        print(f"backfilled {result.rowcount} rows from game_replays.mode")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
