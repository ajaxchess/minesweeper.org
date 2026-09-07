# F53 Sudoku — /sudoku

## Overview

A timed Sudoku game with daily, easy, medium, hard, and expert tracks, each with
their own leaderboard. Every board has a deterministic hash derived from its givens,
enabling per-board high scores and shareable replay links. Future variants (6×6,
Killer, diagonal, etc.) will be separate features but the data model must accommodate
them cleanly from the start.

---

## URLs

| Path | Description |
|------|-------------|
| `/sudoku` | Landing page — links to Daily, Easy, Medium, Hard, Expert |
| `/sudoku/daily` | Today's daily puzzle (Easy difficulty, seeded from date) |
| `/sudoku/easy` | Random easy puzzle |
| `/sudoku/medium` | Random medium puzzle |
| `/sudoku/hard` | Random hard puzzle |
| `/sudoku/expert` | Random expert puzzle |
| `/sudoku/play/<board_hash>` | Replay a specific board by hash |
| `/sudoku/scores` | Leaderboard — filterable by difficulty and period |

---

## Puzzle Generation

- **Standard 9×9 Proper Sudoku** — exactly one solution (no ambiguous boards).
- **Daily puzzle**: seeded RNG from the ISO date string (e.g. `"2026-04-14"`), same
  algorithm as Jigsaw / Schulte. Every user gets the same board on the same day.
  *(Curated editorial sets are a future enhancement once an editor is appointed.)*
- **Random puzzles**: seeded from a random seed at game start; seed is embedded in
  the board hash so the same hash always reproduces the same board.
- **Difficulty levels**: Easy, Medium, Hard, Expert — determined by number of givens
  and/or solver technique complexity. Daily is always Easy.

---

## Board Hash

- SHA-256 (or MD5, truncated to 16 hex chars) of the canonical givens string:
  an 81-character string where givens are their digit and empty cells are `0`,
  read left-to-right, top-to-bottom.
- Deterministic: same puzzle givens → same hash, always.
- Displayed as first 8 characters on the leaderboard.
- Clicking the hash navigates to `/sudoku/play/<full_hash>` to replay that exact board.

---

## Gameplay

### Input Methods (three, all active simultaneously)
1. **Number pad** — rendered below the board; tap a digit to fill the selected cell.
2. **Keyboard** — type a digit (1–9) or `Delete`/`Backspace` to clear.
3. **Tap-to-cycle** — repeatedly tap the selected cell to cycle through 1→2→…→9→blank.

### Cell Selection
- Tap/click a cell to select it, then use any input method above.
- Tapping an already-selected cell advances the cycle.

### Mistake Highlighting
- Invalid entries (duplicates in row, column, or 3×3 box) are shown in red.
- **Togglable** — on by default; a toggle button in the toolbar turns it off for a
  cleaner solve experience.

### Hints
- A "Hint" button reveals the correct value for the selected empty cell.
- **Hints used** is tracked and displayed as a column on the leaderboard.
- No time penalty; hints are purely informational to the viewer.

### Timer
- Counts up from 0:00 when the first cell is filled.
- No time limit — take as long as needed, but time determines leaderboard rank.
- Timer pauses if the tab/window loses focus (prevents unfair advantage).

### Win Condition
- All 81 cells correctly filled → puzzle complete.
- Show a completion modal with time, hints used, and a submit score form.

---

## Scoring & Leaderboard

### Score Metric
- **Primary**: elapsed time (ascending — lower is better).
- **Secondary**: hints used (ascending — fewer hints is better, used as tiebreaker).

### Submission Rules
- **First score per user per board hash is kept** — replaying the same board does not
  update the existing entry.
- Playing a different board hash (including a new random game) creates a new entry.
- Anonymous (guest) scores are accepted. At end of day, only Google-signed-in scores
  persist (same policy as Schulte Grid and the rest of the site).

### Leaderboard Columns
| # | Name | Time | Hints | Difficulty | Board | Date |
|---|------|------|-------|------------|-------|------|

### Leaderboard Filters
- **Difficulty**: Daily / Easy / Medium / Hard / Expert (+ All)
- **Period**: Daily / Season / All Time

---

## Data Model

```python
class SudokuScore(Base):
    __tablename__ = "sudoku_scores"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(32), nullable=False)
    user_email   = Column(String(256), nullable=True, index=True)
    difficulty   = Column(String(16), nullable=False)   # daily|easy|medium|hard|expert
    variant      = Column(String(32), nullable=False, server_default="standard")  # future: killer|diagonal|6x6
    board_hash   = Column(String(64), nullable=False, index=True)
    time_ms      = Column(Integer, nullable=False)
    hints_used   = Column(Integer, nullable=False, default=0)
    puzzle_date  = Column(String(10), nullable=False)   # YYYY-MM-DD of the daily, or solve date
    guest_token  = Column(String(36), nullable=True, index=True)
    client_type  = Column(String(32), nullable=False, server_default="web")
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_sudoku_scores_hash_email", "board_hash", "user_email"),
        Index("ix_sudoku_scores_diff_date_time", "difficulty", "puzzle_date", "time_ms"),
    )
```

The `variant` column future-proofs for 6×6, Killer, diagonal, etc. without a schema
migration.

---

## UI / UX

- Matches minesweeper.org visual style (dark theme default, light theme support).
- Board rendered as an HTML `<table>` or CSS grid with bold borders separating the
  nine 3×3 boxes.
- Toolbar above the board: **New Game** | **Hint** | **Mistakes toggle** | elapsed timer.
- Number pad below the board: digits 1–9 + Erase button.
- Given (pre-filled) cells are visually distinct (bolder font, slightly different
  background) and are not editable.
- Selected cell highlighted with accent colour; same row/col/box lightly tinted.

---

## SEO / Sitemap

- Add `/sudoku`, `/sudoku/daily`, `/sudoku/easy`, `/sudoku/medium`, `/sudoku/hard`,
  `/sudoku/expert`, `/sudoku/scores` to `sitemap.xml`.
- Add Sudoku card to the variants/other landing page.
- Meta description: "Play free Sudoku online with daily puzzles, multiple difficulty
  levels, and global leaderboards. Easy, Medium, Hard, and Expert — no download needed."

---

## Implementation Notes

- Puzzle generator can be a pure-Python backtracking solver + hole-puncher, or a
  well-tested JS library (`sudoku.js`) run client-side for random games.
- For daily seeded generation: generate on the server at route time, cache in memory
  keyed by date.
- The 81-char givens string is all that needs to be stored to reconstruct any board.
- Consider storing the givens string in the score row so the hash can always be
  verified and the board replayed even if the RNG algorithm changes.
