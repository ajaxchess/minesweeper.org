#!/usr/bin/env python3
"""Generate a pool of technique-graded Sudoku puzzles and store them in the database.

Usage:
    cd /home/ubuntu/minesweeper
    source venv/bin/activate
    python scripts/generate_sudoku_pool.py                       # replenish all levels to 50
    python scripts/generate_sudoku_pool.py --difficulty expert    # only expert
    python scripts/generate_sudoku_pool.py --daily 2026-10-20    # generate a specific daily
    python scripts/generate_sudoku_pool.py --daily-range 7        # next 7 days of dailies

Set up as a daily cron to keep the pool full:
    0 3 * * * cd /home/ubuntu/minesweeper && source venv/bin/activate && python scripts/generate_sudoku_pool.py --daily-range 3 >> /var/log/sudoku_pool.log 2>&1
"""

import argparse
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, SudokuPuzzle
from sudoku_generator import generate_puzzle, generate_daily_puzzle
from sudoku_grader import TECHNIQUE_NAMES

POOL_TARGET = 50


def replenish_difficulty(db, difficulty: str, target: int = POOL_TARGET) -> int:
    """Generate puzzles until the pool has `target` unseen puzzles for this difficulty."""
    current = db.query(SudokuPuzzle).filter(
        SudokuPuzzle.difficulty == difficulty,
        SudokuPuzzle.puzzle_date.is_(None),
    ).count()
    needed = max(0, target - current)
    if needed == 0:
        print(f"  {difficulty}: pool full ({current}/{target})")
        return 0

    print(f"  {difficulty}: {current}/{target} in pool, generating {needed} more...")
    created = 0
    for i in range(needed):
        result = generate_puzzle(difficulty)
        if result is None:
            print(f"    WARNING: failed to generate {difficulty} puzzle after max attempts")
            continue
        existing = db.query(SudokuPuzzle).filter(
            SudokuPuzzle.board_hash == result.board_hash
        ).first()
        if existing:
            continue
        puzzle = SudokuPuzzle(
            difficulty=difficulty,
            givens=result.givens,
            solution=result.solution,
            board_hash=result.board_hash,
            givens_count=sum(1 for c in result.givens if c != "0"),
            hardest_technique=TECHNIQUE_NAMES[result.grade_result.hardest_technique],
        )
        db.add(puzzle)
        db.flush()
        created += 1
        if (i + 1) % 10 == 0:
            print(f"    ... {i + 1}/{needed}")
            db.commit()

    db.commit()
    print(f"  {difficulty}: created {created} new puzzles")
    return created


def generate_daily(db, date_str: str) -> bool:
    """Generate the daily puzzle for a specific date if not already present."""
    existing = db.query(SudokuPuzzle).filter(
        SudokuPuzzle.difficulty == "daily",
        SudokuPuzzle.puzzle_date == date_str,
    ).first()
    if existing:
        print(f"  daily {date_str}: already exists (hash={existing.board_hash[:8]})")
        return False

    result = generate_daily_puzzle(date_str)
    if result is None:
        print(f"  daily {date_str}: FAILED to generate")
        return False

    puzzle = SudokuPuzzle(
        difficulty="daily",
        givens=result.givens,
        solution=result.solution,
        board_hash=result.board_hash,
        givens_count=sum(1 for c in result.givens if c != "0"),
        hardest_technique=TECHNIQUE_NAMES[result.grade_result.hardest_technique],
        puzzle_date=date_str,
    )
    db.add(puzzle)
    db.commit()
    print(f"  daily {date_str}: created (hash={result.board_hash[:8]}, "
          f"givens={puzzle.givens_count}, technique={puzzle.hardest_technique})")
    return True


def main():
    parser = argparse.ArgumentParser(description="Generate technique-graded Sudoku puzzles")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard", "expert"],
                        help="Replenish only this difficulty level")
    parser.add_argument("--daily", metavar="YYYY-MM-DD",
                        help="Generate the daily puzzle for this date")
    parser.add_argument("--daily-range", type=int, metavar="N",
                        help="Generate daily puzzles for the next N days (starting today)")
    parser.add_argument("--target", type=int, default=POOL_TARGET,
                        help=f"Pool target per difficulty (default {POOL_TARGET})")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        print("=" * 60)
        print("Sudoku Pool Generator (F-SUDOKU-GRADING)")
        print("=" * 60)

        total = 0

        if args.daily:
            generate_daily(db, args.daily)
        elif args.daily_range:
            today = date.today()
            for i in range(args.daily_range):
                d = today + timedelta(days=i)
                generate_daily(db, d.isoformat())

        if args.difficulty:
            total += replenish_difficulty(db, args.difficulty, args.target)
        elif not args.daily:
            for diff in ["easy", "medium", "hard", "expert"]:
                total += replenish_difficulty(db, diff, args.target)

        # Always replenish dailies for next 3 days if doing a full run
        if not args.daily and not args.daily_range and not args.difficulty:
            print("\n--- Daily puzzles ---")
            today = date.today()
            for i in range(3):
                d = today + timedelta(days=i)
                generate_daily(db, d.isoformat())

        print("\n" + "=" * 60)
        print(f"Done. {total} new pool puzzles created.")
        print("=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    main()
