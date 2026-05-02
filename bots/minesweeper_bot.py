"""
minesweeper_bot.py — Constraint-based Minesweeper AI for bot vs. human PvP.

The bot tracks revealed cell values and uses iterative constraint analysis
to find cells that are definitively safe or mines.  When no deterministic
move exists it falls back to a probability-informed guess.

Difficulty levels
-----------------
easy   — full solver but 40 % chance of random click;  2.0 s between moves
medium — full solver, best-effort guess;                0.7 s between moves
hard   — full solver, better probability guess;         0.2 s between moves
"""

import random

# Sentinel values stored in self.known[r][c]
HIDDEN = -2   # cell not yet seen
MINE   = -1   # confirmed mine (from constraint analysis)

MOVE_DELAY: dict[str, float] = {
    "easy":   2.0,
    "medium": 0.7,
    "hard":   0.2,
}


class MinesweeperBot:
    def __init__(self, rows: int, cols: int, mines: int, difficulty: str = "medium"):
        self.rows        = rows
        self.cols        = cols
        self.total_mines = mines
        self.difficulty  = difficulty if difficulty in MOVE_DELAY else "medium"

        # known[r][c]: HIDDEN = unknown, MINE = confirmed mine, 0-8 = revealed value
        self.known: list[list[int]] = [[HIDDEN] * cols for _ in range(rows)]

    # ── Public API ────────────────────────────────────────────────────────────

    def move_delay(self) -> float:
        """Seconds to wait between moves for this difficulty."""
        return MOVE_DELAY[self.difficulty]

    def apply_reveal(self, r: int, c: int, val: int) -> None:
        """Record that cell (r, c) was revealed with the given value (0-8)."""
        self.known[r][c] = val

    def reset_cell(self, r: int, c: int) -> None:
        """Mark cell (r, c) as unknown again (F71 mine-hit realloc reset)."""
        self.known[r][c] = HIDDEN

    def next_move(self) -> tuple[int, int] | None:
        """
        Return (r, c) — the next cell to reveal.
        Returns None if the board appears fully solved.

        Easy mode: 40 % chance to skip analysis and click randomly.
        """
        if self.difficulty == "easy" and random.random() < 0.40:
            hidden = self._hidden_cells()
            return random.choice(hidden) if hidden else None

        safe = self._run_solver()
        if safe:
            return random.choice(safe)

        return self._guess()

    # ── Constraint solver ─────────────────────────────────────────────────────

    def _neighbors(self, r: int, c: int):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    yield nr, nc

    def _analyze_pass(self) -> tuple[set, set]:
        """
        Single constraint pass over all revealed numbered cells.
        Returns (safe_set, mine_set) for this pass.
        """
        safe:  set[tuple[int, int]] = set()
        mines: set[tuple[int, int]] = set()

        for r in range(self.rows):
            for c in range(self.cols):
                v = self.known[r][c]
                if v < 1:          # not a revealed number — skip
                    continue

                hidden_adj: list[tuple[int, int]] = []
                mine_adj = 0

                for nr, nc in self._neighbors(r, c):
                    k = self.known[nr][nc]
                    if k == MINE:
                        mine_adj += 1
                    elif k == HIDDEN:
                        hidden_adj.append((nr, nc))

                effective = v - mine_adj

                if effective == 0:
                    # All mines around this cell accounted for — hidden neighbours are safe.
                    safe.update(hidden_adj)
                elif effective > 0 and effective == len(hidden_adj):
                    # Every hidden neighbour must be a mine.
                    mines.update(hidden_adj)

        return safe, mines

    def _run_solver(self) -> list[tuple[int, int]]:
        """
        Iteratively apply constraint analysis until stable.
        Marks confirmed mines in self.known and returns confirmed-safe hidden cells.
        """
        safe_cells: set[tuple[int, int]] = set()
        changed = True

        while changed:
            changed = False
            new_safe, new_mines = self._analyze_pass()

            for r, c in new_mines:
                if self.known[r][c] == HIDDEN:
                    self.known[r][c] = MINE
                    changed = True

            for pos in new_safe:
                r, c = pos
                if self.known[r][c] == HIDDEN:
                    safe_cells.add(pos)

        return [pos for pos in safe_cells if self.known[pos[0]][pos[1]] == HIDDEN]

    # ── Guessing ──────────────────────────────────────────────────────────────

    def _hidden_cells(self) -> list[tuple[int, int]]:
        return [
            (r, c) for r in range(self.rows) for c in range(self.cols)
            if self.known[r][c] == HIDDEN
        ]

    def _guess(self) -> tuple[int, int] | None:
        """
        Best-effort guess when no deterministic move exists.

        Prefers interior cells (not adjacent to any revealed number) because
        they carry no local mine-density signal and are statistically safer
        on average than frontier cells when mine density is low.
        """
        hidden = self._hidden_cells()
        if not hidden:
            return None

        interior: list[tuple[int, int]] = []
        border:   list[tuple[int, int]] = []

        for r, c in hidden:
            on_border = any(self.known[nr][nc] >= 1 for nr, nc in self._neighbors(r, c))
            (border if on_border else interior).append((r, c))

        pool = interior if interior else border
        return random.choice(pool)
