#!/usr/bin/env python3
"""
archive_anon_pvp.py — nightly job that moves anonymous PvP results
(winner_email IS NULL) from previous days into anonymous_pvp_results.

Run via cron at midnight UTC:
  0 0 * * * /home/ubuntu/venv/bin/python /home/ubuntu/git/minesweeper.org/scripts/archive_anon_pvp.py >> /home/ubuntu/logs/archive_anon_pvp.log 2>&1
"""
import sys
import os

# Allow running from any directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from database import SessionLocal, PvpResult, AnonymousPvpResult


def archive_anonymous_pvp():
    db = SessionLocal()
    try:
        today_utc = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        rows = (
            db.query(PvpResult)
            .filter(
                PvpResult.winner_email.is_(None),
                PvpResult.created_at < today_utc,
            )
            .all()
        )
        if not rows:
            print(f"[{datetime.now(timezone.utc).isoformat()}] Nothing to archive.")
            return

        for r in rows:
            db.add(AnonymousPvpResult(
                winner_name  = r.winner_name,
                winner_email = r.winner_email,
                loser_name   = r.loser_name,
                loser_email  = r.loser_email,
                elapsed_ms   = r.elapsed_ms,
                submode      = r.submode,
                rows         = r.rows,
                cols         = r.cols,
                mines        = r.mines,
                board_hash   = r.board_hash,
                created_at   = r.created_at,
            ))
            db.delete(r)

        db.commit()
        print(f"[{datetime.now(timezone.utc).isoformat()}] Archived {len(rows)} anonymous PvP result(s).")
    except Exception as e:
        db.rollback()
        print(f"[{datetime.now(timezone.utc).isoformat()}] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    archive_anonymous_pvp()
