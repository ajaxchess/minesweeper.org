"""
wc2026_board.py — No-guess Tametsi board management for the 2026 World Cup (F97).

Each user gets a deterministic board per country per difficulty, generated once
and persisted to wc2026_board_states.  The mine layout is stored so the same
board is always resumed on return.
"""

import hashlib
import json
import random
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from tametsi_generator import generate_board
from wc2026_data import WC2026_EASY, WC2026_HARD


def _seed_for(email: str, country_slug: str, difficulty: str, play_count: int = 0) -> int:
    """Deterministic seed: same user + country + difficulty + play_count → same board."""
    raw = f"wc2026:{email}:{country_slug}:{difficulty}:{play_count}"
    return int(hashlib.md5(raw.encode()).hexdigest(), 16) & 0xFFFF_FFFF


def _spec(difficulty: str) -> dict:
    return WC2026_EASY if difficulty == "easy" else WC2026_HARD


def _make_board(email: str, country_slug: str, difficulty: str, play_count: int = 0):
    """Generate a no-guess board and return (mine_layout_json, cell_state_json)."""
    spec = _spec(difficulty)
    rng  = random.Random(_seed_for(email, country_slug, difficulty, play_count))
    board = generate_board(spec["rows"], spec["cols"], spec["mines"], rng=rng)
    mines_json = json.dumps(sorted([r, c] for r, c in board.mines))
    total = spec["rows"] * spec["cols"]
    # all cells start hidden; the JS reveals cell 0 on first click (start-gate)
    cells = ["hidden"] * total
    cells_json = json.dumps(cells)
    return mines_json, cells_json


def get_or_create_board(db: Session, email: str, country_slug: str, difficulty: str):
    """Return the WC2026BoardState row, creating it if it doesn't exist."""
    from database import WC2026BoardState  # local import avoids circular deps

    row = (
        db.query(WC2026BoardState)
        .filter_by(email=email, country_slug=country_slug, difficulty=difficulty)
        .first()
    )
    if row:
        return row

    mines_json, cells_json = _make_board(email, country_slug, difficulty)
    row = WC2026BoardState(
        email=email,
        country_slug=country_slug,
        difficulty=difficulty,
        mine_layout=mines_json,
        cell_state=cells_json,
        is_solved=False,
        started_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def board_to_dict(row) -> dict:
    """Serialise a WC2026BoardState for the API response."""
    spec       = _spec(row.difficulty)
    mines      = {tuple(m) for m in json.loads(row.mine_layout)}
    cells      = json.loads(row.cell_state)
    rows, cols = spec["rows"], spec["cols"]

    # Row / col remaining counts (unflagged mines)
    row_counts = [0] * rows
    col_counts = [0] * cols
    for r, c in mines:
        row_counts[r] += 1
        col_counts[c] += 1

    row_remaining = list(row_counts)
    col_remaining = list(col_counts)
    for idx, state in enumerate(cells):
        if state == "flagged":
            r, c = divmod(idx, cols)
            row_remaining[r] -= 1
            col_remaining[c] -= 1

    # Zone remaining (primary vs secondary color zone)
    top_rows = spec["top_rows"]
    primary_remaining   = sum(1 for r, c in mines if r < top_rows
                              and cells[r * cols + c] != "flagged")
    secondary_remaining = sum(1 for r, c in mines if r >= top_rows
                              and cells[r * cols + c] != "flagged")

    return {
        "rows":                rows,
        "cols":                cols,
        "mines":               spec["mines"],
        "top_rows":            top_rows,
        "difficulty":          row.difficulty,
        "is_solved":           row.is_solved,
        "cells":               cells,
        "mine_layout":         json.loads(row.mine_layout),
        "row_counts":          row_counts,
        "col_counts":          col_counts,
        "row_remaining":       row_remaining,
        "col_remaining":       col_remaining,
        "primary_remaining":   primary_remaining,
        "secondary_remaining": secondary_remaining,
        "solve_bonus":         spec["solve_bonus"],
    }
