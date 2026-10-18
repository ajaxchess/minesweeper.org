"""
sudoku_generator.py — Server-side Sudoku puzzle generator with technique-based grading.

Generates puzzles that grade into a specific difficulty level based on the
solving techniques required (see sudoku_grader.py).

Usage:
    from sudoku_generator import generate_puzzle

    givens, solution, grade_result = generate_puzzle("hard")
    # givens:       81-char string (0 = empty)
    # solution:     81-char string (complete board)
    # grade_result: GradeResult from sudoku_grader
"""

from __future__ import annotations

import hashlib
import random
from typing import NamedTuple

from sudoku_grader import grade, GradeResult


class PuzzleResult(NamedTuple):
    givens: str
    solution: str
    grade_result: GradeResult
    board_hash: str


GIVENS_RANGE = {
    "easy":   (30, 36),
    "medium": (26, 32),
    "hard":   (23, 28),
    "expert": (20, 26),
    "daily":  (26, 32),
}

MAX_ATTEMPTS = {
    "easy":   200,
    "medium": 200,
    "hard":   500,
    "expert": 1000,
    "daily":  200,
}


def _generate_solution(rng: random.Random) -> list[int]:
    """Generate a complete valid Sudoku board using backtracking with shuffled candidates."""
    board = [0] * 81

    def _solve(pos: int) -> bool:
        if pos == 81:
            return True
        r, c = divmod(pos, 9)
        br, bc = (r // 3) * 3, (c // 3) * 3
        used = set()
        for i in range(9):
            used.add(board[r * 9 + i])
            used.add(board[i * 9 + c])
        for dr in range(3):
            for dc in range(3):
                used.add(board[(br + dr) * 9 + (bc + dc)])
        digits = [d for d in range(1, 10) if d not in used]
        rng.shuffle(digits)
        for d in digits:
            board[pos] = d
            if _solve(pos + 1):
                return True
        board[pos] = 0
        return False

    _solve(0)
    return board


def _count_solutions(board: list[int], limit: int = 2) -> int:
    """Count solutions up to limit. Returns limit if the budget is exhausted."""
    count = 0
    budget = 50_000

    def _candidates(pos: int) -> set[int]:
        r, c = divmod(pos, 9)
        br, bc = (r // 3) * 3, (c // 3) * 3
        used = set()
        for i in range(9):
            used.add(board[r * 9 + i])
            used.add(board[i * 9 + c])
        for dr in range(3):
            for dc in range(3):
                used.add(board[(br + dr) * 9 + (bc + dc)])
        return set(range(1, 10)) - used

    def _solve() -> bool:
        nonlocal count, budget
        budget -= 1
        if budget <= 0:
            count = limit
            return True
        best, best_cands = -1, None
        for i in range(81):
            if board[i] == 0:
                c = _candidates(i)
                if not c:
                    return False
                if best_cands is None or len(c) < len(best_cands):
                    best, best_cands = i, c
        if best == -1:
            count += 1
            return count >= limit
        for d in best_cands:
            board[best] = d
            if _solve():
                board[best] = 0
                return True
            board[best] = 0
        return False

    _solve()
    return count


def _create_puzzle(solution: list[int], rng: random.Random,
                   min_givens: int, max_givens: int) -> list[int]:
    """Remove cells from a solution while maintaining unique solvability."""
    board = solution[:]
    indices = list(range(81))
    rng.shuffle(indices)
    removed = 0
    target_empties = 81 - min_givens

    for idx in indices:
        if removed >= target_empties:
            break
        val = board[idx]
        board[idx] = 0
        if _count_solutions(board) == 1:
            removed += 1
        else:
            board[idx] = val

    return board


def _board_hash(givens: str) -> str:
    return hashlib.sha256(givens.encode()).hexdigest()


def generate_puzzle(difficulty: str, rng: random.Random | None = None) -> PuzzleResult | None:
    """Generate a single puzzle that grades into the target difficulty.

    Returns PuzzleResult on success, None if MAX_ATTEMPTS exhausted.
    """
    if difficulty not in GIVENS_RANGE:
        raise ValueError(f"Invalid difficulty: {difficulty}")

    min_givens, max_givens = GIVENS_RANGE[difficulty]
    rng = rng or random.Random()

    max_attempts = MAX_ATTEMPTS[difficulty]

    actual_target = difficulty if difficulty != "daily" else "medium"

    for _ in range(max_attempts):
        solution = _generate_solution(rng)
        board = _create_puzzle(solution, rng, min_givens, max_givens)
        givens_str = "".join(str(d) for d in board)

        result = grade(givens_str)
        if result.solved and result.difficulty == actual_target:
            solution_str = "".join(str(d) for d in solution)
            return PuzzleResult(
                givens=givens_str,
                solution=solution_str,
                grade_result=result,
                board_hash=_board_hash(givens_str),
            )

    return None


def generate_daily_puzzle(date_str: str) -> PuzzleResult | None:
    """Generate the daily puzzle for a given date string (YYYY-MM-DD).

    Uses a deterministic seed so the same date always produces the same puzzle.
    """
    seed = int(hashlib.md5(
        f"sudoku-graded-daily-{date_str}".encode(), usedforsecurity=False
    ).hexdigest(), 16) & 0xFFFFFFFF
    rng = random.Random(seed)
    return generate_puzzle("daily", rng)
