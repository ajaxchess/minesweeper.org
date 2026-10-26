# Sudoku — Difficulty by Solving Technique

**Status:** ready
**Feature ID:** F-SUDOKU-GRADING
**Author:** Gisela Velazco
**Date:** 2026-10-12

---

## Problem / Motivation

Sudoku difficulty is currently set only by the number of givens (F-SUDOKU-HARDER
lowered them to easy 32, medium 28, hard 25, expert 22, daily 28). Givens are a
weak proxy: a 25-given puzzle can fall to singles alone while a 30-given one may
need an X-Wing. Players still find every level easy. Newspaper Sudokus grade
puzzles by the hardest technique a human needs to solve them.

---

## Success Criteria

- [ ] Each difficulty requires a defined set of techniques and no technique
      beyond it (e.g. easy: singles only; expert: needs at least one advanced technique).
- [ ] Players report a clear step in difficulty between levels.
- [ ] The daily puzzle is the same for every player and stays reproducible from its seed.
- [ ] Generation stays fast enough for server-side batch pre-generation.

---

## Scope

**In this feature:**
- A Python logical solver (`sudoku_grader.py`) that applies techniques in order
  of difficulty and reports the hardest one used.
- Technique hierarchy (easiest → hardest):
  1. Naked singles
  2. Hidden singles
  3. Naked pairs
  4. Hidden pairs
  5. Naked triples
  6. Pointing pairs / box-line reduction
  7. X-Wing
  8. Swordfish
  9. XY-Wing
- Difficulty mapping:
  - **Easy**: naked singles + hidden singles only
  - **Medium**: up to naked/hidden pairs
  - **Hard**: up to X-Wing (triples, pointing pairs, X-Wing)
  - **Expert**: requires Swordfish or XY-Wing
  - **Daily**: medium-level (same as medium)
- A Python puzzle generator (`sudoku_generator.py`) that creates a valid solved
  board, removes clues, and verifies the puzzle grades into the requested level.
- A `sudoku_puzzles` database table to store a pool of pre-generated puzzles.
- A management script (`scripts/generate_sudoku_pool.py`) to generate puzzle
  pools — run daily by cron or on demand.
- Updated routes to serve pre-generated puzzles from the database instead of
  sending a seed for client-side generation.
- Updated JS to receive the givens string from the server and skip client-side
  generation.

**Out of scope (future):**
- Showing the technique needed as a hint to the player.

---

## Key Design Decisions

1. **Server-side pre-generation** chosen over client-side grading because
   advanced technique detection (X-Wing, Swordfish, XY-Wing) is too slow for
   phone browsers during puzzle generation. Pre-generated puzzles also guarantee
   reproducibility.

2. **Given-count bounds per level** are kept as a secondary constraint alongside
   technique grading to ensure visual distinctiveness:
   - Easy: 30–36 givens
   - Medium: 26–32 givens
   - Hard: 23–28 givens
   - Expert: 20–26 givens

3. **Daily puzzle**: one medium-difficulty puzzle per day, selected from the pool
   by puzzle_date. Deterministic for all players (same puzzle_date → same puzzle).

4. **Non-daily puzzles**: served randomly from the pool for that difficulty.
   Each play gets a puzzle the player hasn't seen (tracked by board_hash in
   existing SudokuScore table).

5. **Leaderboard continuity**: existing scores keep their difficulty label.
   New puzzles are harder at each level, so old times are not directly comparable,
   but no migration or reset is needed — the leaderboard naturally transitions
   as new scores accumulate.

6. **Pool size target**: generate 50 puzzles per difficulty level, replenished
   as they're consumed. The daily puzzle is generated fresh each day.

---

## Implementation Notes

*Filled in when work completes.*

---

## Review Notes (2026-10-26, @gisela — for @richard)

Reviewed the shipped implementation (157823f, f115f60). It is live: all five
play pages serve pool puzzles in production.

- **Fixed in this review:** the in-page "next game" started after a win
  (F-GAME-END) still generated puzzles in the browser, bypassing grading. It now
  calls `GET /api/sudoku-puzzle?difficulty=…`, which uses the same
  `_fetch_puzzle()` pool selection; the browser generator is only a fallback
  when the pool is empty.
- **Repeats:** non-daily puzzles are the globally least-served one in a pool of
  50, so frequent players see the same puzzles again. Design decision 4 says
  "a puzzle the player hasn't seen" — not implemented yet (could exclude
  `board_hash`es the player already has in `sudoku_scores`).
- **Difficulty ceiling:** puzzles that need techniques beyond XY-Wing are
  discarded as unsolved, so Expert never reaches the hardest puzzles. Consider
  adding chains / forcing techniques, or accepting "needs more than XY-Wing" as Expert.
- **Cron:** `scripts/generate_sudoku_pool.py --daily-range 3` must run daily on
  the server; if a day's daily is missing the page silently falls back to
  ungraded browser generation. Please confirm the cron is installed.
- **Status:** the feature is live, so this file should get Implementation Notes,
  Status `done`, and move to `docs/features/`.

