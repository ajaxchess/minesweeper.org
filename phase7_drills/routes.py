"""
phase7_drills.routes — FastAPI routes for the drill feature.

Mount in main.py:

    from phase7_drills.routes import api_router as drills_api_router
    from phase7_drills.routes import page_router as drills_page_router
    app.include_router(drills_api_router)
    app.include_router(drills_page_router)

Endpoints:

  API (JSON):
    POST /api/drills/start              start a new drill session
    GET  /api/drills/{drill_id}         current state (for resume)
    POST /api/drills/{drill_id}/submit  submit one board's chosen cell

  Pages (HTML):
    GET  /drill/{drill_id}              renders templates/drill.html
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

# ── Project-specific imports (each fenced individually so one missing piece
#    doesn't fall everything back to stubs) ───────────────────────────────────
try:
    from database import get_db                            # type: ignore
except ImportError:
    def get_db():
        yield None

try:
    from auth import get_current_user                      # type: ignore
except ImportError:
    def get_current_user(_request):
        return None

try:
    from main import limiter                               # type: ignore
except ImportError:
    class _StubLimiter:
        @staticmethod
        def limit(_):
            def deco(fn):
                return fn
            return deco
    limiter = _StubLimiter()

# NOTE: `templates` is imported lazily inside the page handler. At the moment
# main.py executes `app.include_router(drills_page_router)` (early in
# startup, around line 163), `templates` is not yet defined on the main
# module (it's created later, around line 278). Pulling it in at import time
# raises ImportError and used to fall every helper back to its stub — which
# is why `get_current_user` was returning None even for authenticated users.
def _get_templates():
    from main import templates                             # type: ignore
    return templates


# i18n helpers — base.html accesses `t.*` and `lang`, so any page handler
# that extends base.html must pass them. Imported lazily for the same reason
# as templates above. Falls back to empty defaults if i18n isn't wired in
# the runtime (keeps standalone tests happy).
def _get_i18n(request):
    try:
        from translations import get_lang, get_t           # type: ignore
        return get_lang(request), get_t(request)
    except Exception:
        return "en", {}

from . import generator, mastery
from .models import DrillSession
from .response_models import (
    DrillAttempt,
    DrillBoardResult,
    DrillBoardVisible,
    DrillStartRequest,
    DrillStartResponse,
    DrillStateResponse,
    DrillSubmitRequest,
    DrillSubmitResponse,
    DrillSummary,
)


api_router = APIRouter(prefix="/api/drills", tags=["drills"])
page_router = APIRouter(tags=["drills"])


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════

def _player_id(request: Request) -> str:
    """Same pattern as phase4_routes — email or guest_token."""
    user = get_current_user(request)
    if user:
        return user["email"]
    token = (
        request.session.get("guest_token")
        if hasattr(request, "session") else None
    )
    if not token:
        raise HTTPException(status_code=401, detail="No player identity")
    return token


def _load_drill(db: Session, drill_id: int, expected_player_id: str) -> DrillSession:
    drill = db.query(DrillSession).filter_by(id=drill_id).one_or_none()
    if drill is None:
        raise HTTPException(status_code=404, detail="Drill not found")
    if drill.player_id != expected_player_id:
        # Don't leak whether the drill exists — return the same 404.
        raise HTTPException(status_code=404, detail="Drill not found")
    return drill


def _visible_from_solution(sol: dict) -> DrillBoardVisible:
    """Build the client-facing visible payload from a stored solution dict."""
    board = generator.deserialize_solution(sol)
    vis = generator.serialize_visible(board)
    return DrillBoardVisible(
        drill_type=vis["drill_type"],
        prompt=vis["prompt"],
        width=vis["width"],
        height=vis["height"],
        num_mines=vis["num_mines"],
        revealed=vis["revealed"],
        flags=vis["flags"],
        numbers=vis["numbers"],
    )


# ═════════════════════════════════════════════════════════════════════════════
# Start
# ═════════════════════════════════════════════════════════════════════════════

@api_router.post("/start", response_model=DrillStartResponse)
@limiter.limit("20/minute")
def start_drill(
    request: Request,
    body: DrillStartRequest,
    db: Session = Depends(get_db),
):
    """Create a fresh drill session for the current player."""
    player_id = _player_id(request)

    # Seed off the wall-clock + player_id so distinct sessions get distinct
    # boards without exposing predictable seeds.
    base_seed = abs(hash((player_id, datetime.now(timezone.utc).timestamp()))) % 1_000_000_000

    boards = generator.generate_drill_set(
        base_seed, n=body.num_boards, drill_type=body.drill_type
    )
    solutions = [generator.serialize_solution(b) for b in boards]
    visible = [_visible_from_solution(s) for s in solutions]

    drill = DrillSession(
        player_id=player_id,
        drill_type=body.drill_type,
        level=body.level,
        difficulty=body.difficulty,
        mode=body.mode,
        num_boards=body.num_boards,
        boards_json=json.dumps(solutions, separators=(",", ":")),
        attempts_json="[]",
        drill_version=mastery.DRILL_VERSION,
    )
    db.add(drill)
    db.commit()
    db.refresh(drill)

    return DrillStartResponse(
        drill_id=drill.id,
        drill_type=drill.drill_type,
        level=drill.level,
        mode=drill.mode,
        difficulty=drill.difficulty,
        num_boards=drill.num_boards,
        boards=visible,
        drill_version=drill.drill_version,
        started_at=drill.started_at.isoformat(),
    )


# ═════════════════════════════════════════════════════════════════════════════
# Submit one board
# ═════════════════════════════════════════════════════════════════════════════

@api_router.post("/{drill_id}/submit", response_model=DrillSubmitResponse)
@limiter.limit("60/minute")
def submit_board(
    drill_id: int,
    request: Request,
    body: DrillSubmitRequest,
    db: Session = Depends(get_db),
):
    """Evaluate the player's pick for one board. Finalises the session if
    this was the last board."""
    player_id = _player_id(request)
    drill = _load_drill(db, drill_id, player_id)

    if drill.completed_at is not None:
        raise HTTPException(status_code=409, detail="Drill already completed")

    if body.board_index >= drill.num_boards:
        raise HTTPException(status_code=400, detail="board_index out of range")

    solutions = json.loads(drill.boards_json)
    attempts: list[dict] = json.loads(drill.attempts_json or "[]")

    # Idempotency: re-submitting the same board returns the prior verdict.
    existing = next(
        (a for a in attempts if a["board_index"] == body.board_index),
        None,
    )
    if existing is not None:
        result = DrillBoardResult(**existing["result"])
    else:
        sol = solutions[body.board_index]
        board = generator.deserialize_solution(sol)
        verdict = generator.evaluate_click(board, body.chosen_row, body.chosen_col)
        result = DrillBoardResult(
            is_correct=verdict.is_correct,
            is_mine=verdict.is_mine,
            opening_size=verdict.opening_size,
            relative_quality=verdict.relative_quality,
            optimal_row=verdict.optimal_cell[0],
            optimal_col=verdict.optimal_cell[1],
            optimal_opening_size=verdict.optimal_opening_size,
        )
        attempts.append({
            "board_index": body.board_index,
            "chosen_row": body.chosen_row,
            "chosen_col": body.chosen_col,
            "decision_ms": body.decision_ms,
            "result": result.model_dump(),
        })
        drill.attempts_json = json.dumps(attempts, separators=(",", ":"))

    # Finalise if every board has been submitted.
    completed = False
    summary: Optional[DrillSummary] = None
    if len(attempts) >= drill.num_boards and drill.completed_at is None:
        _finalise(drill, attempts)
        completed = True
        summary = DrillSummary(
            num_correct=drill.num_correct or 0,
            num_total=drill.num_boards,
            accuracy_pct=round(
                100.0 * (drill.num_correct or 0) / drill.num_boards, 1
            ),
            avg_decision_ms=drill.avg_decision_ms or 0,
            mastery_contribution=drill.mastery_contribution or 0.0,
            counted_toward_mastery=bool(drill.counted_toward_mastery),
        )

    db.commit()

    return DrillSubmitResponse(
        drill_id=drill.id,
        board_index=body.board_index,
        result=result,
        completed=completed or drill.completed_at is not None,
        summary=summary,
    )


def _finalise(drill: DrillSession, attempts: list[dict]) -> None:
    """Populate the summary columns on the session row."""
    num_correct = sum(1 for a in attempts if a["result"]["is_correct"])
    decisions = [a["decision_ms"] for a in attempts if a.get("decision_ms")]
    avg_ms = int(sum(decisions) / len(decisions)) if decisions else 0
    score = mastery.compute_drill_mastery(num_correct, drill.num_boards, avg_ms)

    drill.num_correct = num_correct
    drill.avg_decision_ms = avg_ms
    drill.mastery_contribution = score
    drill.counted_toward_mastery = True
    drill.completed_at = datetime.now(timezone.utc)


# ═════════════════════════════════════════════════════════════════════════════
# Get drill state (for resume / refresh)
# ═════════════════════════════════════════════════════════════════════════════

@api_router.get("/{drill_id}", response_model=DrillStateResponse)
@limiter.limit("60/minute")
def get_drill(
    drill_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    player_id = _player_id(request)
    drill = _load_drill(db, drill_id, player_id)

    solutions = json.loads(drill.boards_json)
    visible = [_visible_from_solution(s) for s in solutions]
    raw_attempts = json.loads(drill.attempts_json or "[]")

    attempts = [
        DrillAttempt(
            board_index=a["board_index"],
            chosen_row=a["chosen_row"],
            chosen_col=a["chosen_col"],
            decision_ms=a["decision_ms"],
            result=DrillBoardResult(**a["result"]),
        )
        for a in raw_attempts
    ]

    summary: Optional[DrillSummary] = None
    if drill.completed_at is not None:
        summary = DrillSummary(
            num_correct=drill.num_correct or 0,
            num_total=drill.num_boards,
            accuracy_pct=round(
                100.0 * (drill.num_correct or 0) / drill.num_boards, 1
            ),
            avg_decision_ms=drill.avg_decision_ms or 0,
            mastery_contribution=drill.mastery_contribution or 0.0,
            counted_toward_mastery=bool(drill.counted_toward_mastery),
        )

    return DrillStateResponse(
        drill_id=drill.id,
        player_id=drill.player_id,
        drill_type=drill.drill_type,
        level=drill.level,
        mode=drill.mode,
        difficulty=drill.difficulty,
        num_boards=drill.num_boards,
        started_at=drill.started_at.isoformat(),
        completed_at=drill.completed_at.isoformat() if drill.completed_at else None,
        boards=visible,
        attempts=attempts,
        summary=summary,
        drill_version=drill.drill_version,
    )


# ═════════════════════════════════════════════════════════════════════════════
# HTML page
# ═════════════════════════════════════════════════════════════════════════════

@page_router.get("/drill/{drill_id}", response_class=HTMLResponse)
async def drill_page(drill_id: int, request: Request):
    """
    Render the drill runner page. All state is fetched client-side from
    /api/drills/{id} on load; this handler only provides the skeleton +
    translation strings.
    """
    templates = _get_templates()
    lang, t = _get_i18n(request)
    return templates.TemplateResponse(request, "drill.html", {
        "mode": "drill",
        "user": get_current_user(request),
        "lang": lang,
        "t": t,
        "drill_id": drill_id,
    })
