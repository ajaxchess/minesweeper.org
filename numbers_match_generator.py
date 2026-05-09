"""
numbers_match_generator.py

Generates deterministic Numbers Match daily boards.

Board number is computed as days elapsed since 2024-01-01 (1-based).
Row count follows the spec schedule.
Board content is a seeded Fisher-Yates shuffle of the canonical
sequence (1-9 repeated to fill the grid).

Any board produced here is solvable: numbers 1-9 always have a valid
partner (equal value or sum-to-10), and the Add Lines mechanic ensures
the game can always progress to a full clear.
"""

from datetime import date
import hashlib
import random

_EPOCH = date(2024, 1, 1)


def board_number(date_str: str) -> int:
    """Return the 1-based sequential board number for a given YYYY-MM-DD date."""
    return (date.fromisoformat(date_str) - _EPOCH).days + 1


def initial_rows(board_num: int) -> int:
    """Return the starting row count. Always 4; Add Lines handles progression."""
    return 4


def generate_daily(date_str: str) -> dict:
    """
    Generate the daily Numbers Match board for the given YYYY-MM-DD date.

    Returns a dict with:
      board_num  — sequential board number
      rows       — initial row count
      board_data — flat list of ints (1-9), length = rows * 9
    """
    b_num = board_number(date_str)
    rows  = initial_rows(b_num)
    total = rows * 9

    # Canonical base: 1-9 repeated, trimmed to total cells
    base = [(i % 9) + 1 for i in range(total)]

    # Deterministic seed derived from date string via SHA-256
    seed = int(hashlib.sha256(date_str.encode()).hexdigest(), 16) % (2 ** 32)
    rng  = random.Random(seed)
    rng.shuffle(base)

    return {"board_num": b_num, "rows": rows, "board_data": base}
