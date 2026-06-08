"""
backfill_with_progress.py — Backfill historical replays with live progress.

Wrapper around backfill_analyses() that prints per-batch progress, throughput,
and ETA so you can watch a long-running backfill without going blind.

Usage (from ~/git/minesweeper.org/ with the app's venv active):

    python -m phase2_analyzer.backfill_with_progress
    python -m phase2_analyzer.backfill_with_progress --batch-size 200
    python -m phase2_analyzer.backfill_with_progress --limit 5000

Run it under nohup for a fire-and-forget multi-hour backfill:

    nohup python -m phase2_analyzer.backfill_with_progress \\
        > /var/log/uvicorn/backfill.log 2>&1 &
    echo "PID: $!"
    tail -f /var/log/uvicorn/backfill.log

Safe to interrupt (Ctrl-C or kill <pid>) — resumes where it left off because
of the unique constraint on game_analyses.game_replay_id.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from contextlib import contextmanager
from typing import Iterator

# Imports — assume we're running inside ~/git/minesweeper.org/ with venv active
try:
    from database import SessionLocal, GameReplay
    from phase2_analyzer import GameAnalysis, analyze_game, persist_analysis
    from phase2_analyzer.pipeline import _game_from_replay
except ImportError as e:
    print(f"ERROR: must run from minesweeper.org project root with venv active: {e}",
          file=sys.stderr)
    sys.exit(2)


_log = logging.getLogger("backfill")


# ── Signal handling: graceful Ctrl-C ─────────────────────────────────────────
_STOP_REQUESTED = False


def _on_signal(signum, frame):
    global _STOP_REQUESTED
    _STOP_REQUESTED = True
    print("\n⏸  Stop requested — finishing current batch then exiting cleanly.\n",
          file=sys.stderr, flush=True)


signal.signal(signal.SIGINT, _on_signal)
signal.signal(signal.SIGTERM, _on_signal)


# ── Helpers ─────────────────────────────────────────────────────────────────
def _fmt_eta(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.2f}h"


def _count_pending(db) -> tuple[int, int]:
    """Return (total_pending, recoverable_pending).
       Recoverable = has both board_hash and log_json populated."""
    base = (db.query(GameReplay)
              .outerjoin(GameAnalysis, GameAnalysis.game_replay_id == GameReplay.id)
              .filter(GameAnalysis.id.is_(None)))
    total = base.count()
    recoverable = (base
        .filter(GameReplay.board_hash.isnot(None))
        .filter(GameReplay.board_hash != "")
        .filter(GameReplay.log_json.isnot(None))
        .filter(GameReplay.log_json != "")
        .count())
    return total, recoverable


def _fetch_pending_ids(db, limit: int) -> list[int]:
    """Fetch IDs of pending replays that have the required fields populated.

    Pre-Phase-1 captures often have empty board_hash (client/server schema
    mismatch fixed in Phase 1). Those records can't be analyzed without
    reconstructing the mine layout from scratch — skip them here so the
    backfill works on records that have what it needs.
    """
    rows = (db.query(GameReplay.id)
              .outerjoin(GameAnalysis, GameAnalysis.game_replay_id == GameReplay.id)
              .filter(GameAnalysis.id.is_(None))
              .filter(GameReplay.board_hash.isnot(None))
              .filter(GameReplay.board_hash != "")
              .filter(GameReplay.log_json.isnot(None))
              .filter(GameReplay.log_json != "")
              .order_by(GameReplay.id.asc())
              .limit(limit)
              .all())
    return [r[0] for r in rows]


# ── Core loop ───────────────────────────────────────────────────────────────
def backfill(batch_size: int = 200, limit: int | None = None) -> None:
    """
    Process pending replays in batches until done (or limit reached, or
    SIGINT/SIGTERM received).
    """
    db = SessionLocal()
    try:
        total_pending, recoverable_pending = _count_pending(db)
    finally:
        db.close()

    unrecoverable = total_pending - recoverable_pending

    if recoverable_pending == 0:
        print(f"✓ No recoverable pending replays.")
        if unrecoverable:
            print(f"  ({unrecoverable:,} replays lack board_hash or log_json — pre-Phase-1 captures, "
                  "can't be analyzed without rebuilding the mine layout.)")
        return

    target = min(recoverable_pending, limit) if limit else recoverable_pending
    print(f"┌─ Backfill starting")
    print(f"│  Total pending in DB:   {total_pending:,}")
    print(f"│  Recoverable:           {recoverable_pending:,}")
    print(f"│  Unrecoverable (skip):  {unrecoverable:,}  (no board_hash / log_json)")
    if limit:
        print(f"│  Will process at most:  {limit:,}")
    print(f"│  Batch size:            {batch_size}")
    print(f"└─ {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    start = time.time()
    analyzed = 0
    errors = 0
    skipped = 0
    last_log_time = start
    last_log_count = 0

    while not _STOP_REQUESTED:
        if limit and analyzed >= limit:
            break

        db = SessionLocal()
        try:
            remaining = batch_size if not limit else min(batch_size, limit - analyzed)
            pending_ids = _fetch_pending_ids(db, remaining)
            if not pending_ids:
                break

            for rid in pending_ids:
                if _STOP_REQUESTED:
                    break
                replay = db.query(GameReplay).filter_by(id=rid).first()
                if not replay:
                    continue
                game = _game_from_replay(replay)
                if game is None:
                    # Slipped through the fetch filter — log it once for visibility
                    skipped += 1
                    if skipped <= 5:
                        print(f"   ⚠ Replay #{rid} skipped — _game_from_replay returned None",
                              file=sys.stderr)
                    continue
                try:
                    analysis = analyze_game(game)
                    persist_analysis(db, replay.id, game, analysis)
                    analyzed += 1
                except Exception as exc:                       # noqa: BLE001
                    errors += 1
                    db.rollback()
                    if errors <= 10:
                        print(f"   ⚠ Replay #{rid}: {type(exc).__name__}: {exc}",
                              file=sys.stderr)
                    elif errors == 11:
                        print(f"   ⚠ Suppressing further per-replay errors "
                              "(running total in summary line).", file=sys.stderr)
        finally:
            db.close()

        # Throttle progress log to every 5 seconds of wall time, regardless
        # of batch size (avoids flooding stdout on fast hardware)
        now = time.time()
        if now - last_log_time >= 5 or _STOP_REQUESTED:
            elapsed = now - start
            interval = now - last_log_time
            interval_count = analyzed - last_log_count
            rate_recent = interval_count / interval if interval else 0
            rate_avg    = analyzed / elapsed if elapsed else 0
            remaining_n = max(0, target - analyzed)
            eta = remaining_n / rate_recent if rate_recent else float("inf")

            print(
                f"  {analyzed:>6,}/{target:,} "
                f"({100 * analyzed / target:>5.1f}%) │ "
                f"recent {rate_recent:>5.1f}/s │ "
                f"avg {rate_avg:>5.1f}/s │ "
                f"errors {errors:>4} │ "
                f"skipped {skipped:>4} │ "
                f"ETA {_fmt_eta(eta) if eta != float('inf') else '—'} │ "
                f"elapsed {_fmt_eta(elapsed)}",
                flush=True,
            )
            last_log_time = now
            last_log_count = analyzed

    total_elapsed = time.time() - start
    print()
    print(f"┌─ Backfill {'interrupted' if _STOP_REQUESTED else 'complete'}")
    print(f"│  Analyzed:        {analyzed:,}")
    print(f"│  Skipped:         {skipped:,}")
    print(f"│  Errors:          {errors:,}")
    print(f"│  Elapsed:         {_fmt_eta(total_elapsed)}")
    if total_elapsed:
        print(f"│  Avg rate:        {analyzed / total_elapsed:.1f}/sec")
    db = SessionLocal()
    try:
        total_left, recoverable_left = _count_pending(db)
    finally:
        db.close()
    print(f"│  Still pending:   {recoverable_left:,} recoverable, "
          f"{total_left - recoverable_left:,} unrecoverable")
    print(f"└─ {time.strftime('%Y-%m-%d %H:%M:%S')}")


# ── CLI ─────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill the analyzer over historical replays with live progress",
    )
    parser.add_argument(
        "--batch-size", type=int, default=200,
        help="Replays per DB batch (default: 200). Lower if your DB is loaded.",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Maximum replays to analyze this run (default: all). Useful for "
             "testing or doing the backfill in chunks during low-traffic windows.",
    )
    args = parser.parse_args()
    backfill(batch_size=args.batch_size, limit=args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
