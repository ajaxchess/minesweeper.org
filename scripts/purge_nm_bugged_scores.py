#!/usr/bin/env python3
"""
purge_nm_bugged_scores.py — one-off cleanup for B52.

From 2026-05-13 (f0d4909 deferred minesweeper.js in base.html) until the B52
fix, the Numbers Match web client called minesweeper.js's startTimer/stopTimer
instead of its own, so every completed game was saved with time_secs = 1.
No real game can be finished in 1 second, so those rows are deleted along with
any flagged_scores entries that point at them. Mobile app scores (ios_app /
android_app) use their own timer and are left alone.

Run on the server AFTER the B52 fix is deployed, otherwise new bugged scores
keep arriving:
  /home/ubuntu/minesweeper/venv/bin/python scripts/purge_nm_bugged_scores.py           # dry run
  /home/ubuntu/minesweeper/venv/bin/python scripts/purge_nm_bugged_scores.py --apply   # delete
"""
import sys
import os

# Allow running from any directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from database import SessionLocal, NumbersMatchScore, FlaggedScore

BUG_START = datetime(2026, 5, 13)


def purge(apply: bool):
    db = SessionLocal()
    try:
        q = db.query(NumbersMatchScore).filter(
            NumbersMatchScore.time_secs <= 1,
            NumbersMatchScore.created_at >= BUG_START,
            NumbersMatchScore.client_type.notin_(["ios_app", "android_app"]),
        )
        rows = q.all()
        ids = [r.id for r in rows]
        print(f"Found {len(ids)} Numbers Match score(s) with time_secs <= 1 since {BUG_START.date()}.")
        for r in rows[:20]:
            print(f"  id={r.id} {r.puzzle_date} name={r.name!r} score={r.score} created_at={r.created_at}")
        if len(rows) > 20:
            print(f"  ... and {len(rows) - 20} more")

        if not apply:
            print("Dry run — nothing deleted. Re-run with --apply to delete.")
            return
        if not ids:
            return

        flagged = (
            db.query(FlaggedScore)
            .filter(FlaggedScore.table_name == NumbersMatchScore.__tablename__,
                    FlaggedScore.score_id.in_(ids))
            .delete(synchronize_session=False)
        )
        deleted = (
            db.query(NumbersMatchScore)
            .filter(NumbersMatchScore.id.in_(ids))
            .delete(synchronize_session=False)
        )
        db.commit()
        print(f"Deleted {deleted} score(s) and {flagged} flagged_scores row(s).")
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    purge(apply="--apply" in sys.argv)
