"""
sudoku_routes.py — Page and API route handlers for Sudoku.
Mount this router in main.py with: app.include_router(sudoku_router)
"""
import uuid
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Request, Depends, HTTPException, Query, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from database import (
    FlaggedScore, UserProfile, GameReplay,
    SudokuScore, SudokuPuzzle,
    get_db,
)
from auth import get_current_user
from translations import get_lang, get_t, SUPPORTED_LANGS
import settings as site_settings
from quest_catalog import quest_config
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs
# The Sudoku day (daily puzzle, score date, "today" leaderboard) follows the same
# America/New_York puzzle day as Numbers Match, not the server's UTC date (B55).
from numbers_match_generator import numbers_match_today_str as sudoku_today_str

sudoku_router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

templates = Jinja2Templates(directory="templates")
templates.env.globals["quest_config"]          = quest_config
templates.env.globals["DEFAULT_SKIN"]          = site_settings.DEFAULT_SKIN
templates.env.globals["active_skin"]           = site_settings.active_skin
templates.env.globals["solstice_banner"]       = site_settings.solstice_banner
templates.env.globals["equinox_banner"]        = site_settings.equinox_banner
templates.env.globals["diana_birthday_banner"] = site_settings.diana_birthday_banner
templates.env.globals["mexico_banner"]         = site_settings.mexico_banner
templates.env.globals["is_mexico_cinco"]       = site_settings.is_mexico_cinco
templates.env.globals["is_mexico_independence"] = site_settings.is_mexico_independence
templates.env.globals["ga_tag"]               = ""
templates.env.globals["get_breadcrumbs"]      = _get_breadcrumbs


# ── Shared utilities (mirrors of main.py helpers; no circular-import solution) ──

_LANG_PREFIX_MAP: dict[str, str] = {
    lang: f"/{lang}" for lang in SUPPORTED_LANGS if lang != "en"
}


def _safe_lang_prefix(lang: str) -> str:
    """Return /{lang} for supported non-English languages, '' otherwise."""
    return _LANG_PREFIX_MAP.get(lang, "")


def _safe_relative_url(url: str, fallback: str = "/") -> str:
    """Reject URLs that carry a scheme or netloc (open-redirect guard)."""
    if "\\" in url:
        return fallback
    if url.startswith("//"):
        return fallback
    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc:
        return fallback
    return url


def get_or_create_guest_token(request: Request, user: dict | None) -> str | None:
    """Return the session guest token for unauthenticated requests, None for signed-in users."""
    if user:
        return None
    if "guest_token" not in request.session:
        request.session["guest_token"] = str(uuid.uuid4())
    return request.session["guest_token"]


def get_client_type(request: Request) -> str:
    """Derive client type from request headers."""
    explicit = request.headers.get("X-Client-Type", "").lower().strip()
    if explicit in ("ios_app", "android_app"):
        return explicit
    ua = request.headers.get("User-Agent", "").lower()
    if not ua:
        return "na"
    if any(kw in ua for kw in ("mobi", "android", "iphone", "ipad", "ipod")):
        return "mobile_browser"
    if "edg/" in ua or "edghtml" in ua:
        return "edge"
    if "opr/" in ua or "opera" in ua:
        return "opera"
    if "chrome" in ua or "chromium" in ua:
        return "chrome"
    if "firefox" in ua:
        return "firefox"
    if "safari" in ua:
        return "safari"
    return "browser"


def flag_if_profane(db, table_name: str, score_id: int, name: str) -> bool:
    """Flag a score for admin review if the name contains profanity. Returns True if flagged."""
    from better_profanity import profanity as _profanity_checker
    if not _profanity_checker.contains_profanity(name):
        return False
    existing = db.query(FlaggedScore).filter_by(table_name=table_name, score_id=score_id).first()
    if not existing:
        db.add(FlaggedScore(table_name=table_name, score_id=score_id, name=name, reason="profanity"))
        db.commit()
    return True


def exclude_flagged(q, model, db):
    """Filter a score query to exclude any scores currently flagged for review."""
    flagged_ids = (
        db.query(FlaggedScore.score_id)
        .filter(FlaggedScore.table_name == model.__tablename__)
        .scalar_subquery()
    )
    return q.filter(~model.id.in_(flagged_ids))


def _enrich_with_profiles(scores: list, db) -> list:
    """Add profile_url, country, and game_id to score dicts."""
    emails = [s.user_email for s in scores if s.user_email]
    profiles = (
        db.query(UserProfile.email, UserProfile.vanity_slug, UserProfile.public_id,
                 UserProfile.is_public, UserProfile.country)
        .filter(UserProfile.email.in_(emails))
        .all()
    ) if emails else []
    url_map:     dict = {}
    country_map: dict = {}
    for p in profiles:
        if p.country:
            country_map[p.email] = p.country
        if not p.is_public:
            continue
        if p.vanity_slug:
            url_map[p.email] = f"/u/{p.vanity_slug}"
        elif p.public_id:
            url_map[p.email] = f"/u/{p.public_id}"
    score_ids = [s.id for s in scores]
    replay_map = {
        r.score_id: r.id
        for r in db.query(GameReplay.id, GameReplay.score_id)
                   .filter(GameReplay.score_id.in_(score_ids))
                   .all()
    }
    result = []
    for s in scores:
        d = s.to_dict()
        d["profile_url"] = url_map.get(s.user_email) if s.user_email else None
        d["country"]     = country_map.get(s.user_email) if s.user_email else None
        d["game_id"]     = replay_map.get(s.id)
        result.append(d)
    return result


# ── Sudoku ────────────────────────────────────────────────────────────────────

_SUDOKU_DIFFICULTIES = {"daily", "easy", "medium", "hard", "expert"}


def _fetch_puzzle(db: Session, difficulty: str, today: str) -> SudokuPuzzle | None:
    """Fetch a pre-generated puzzle from the pool.

    Daily puzzles are looked up by date. Other difficulties return the
    least-served puzzle (round-robin) and bump its served_count.
    """
    if difficulty == "daily":
        return db.query(SudokuPuzzle).filter(
            SudokuPuzzle.difficulty == "daily",
            SudokuPuzzle.puzzle_date == today,
        ).first()

    puzzle = db.query(SudokuPuzzle).filter(
        SudokuPuzzle.difficulty == difficulty,
        SudokuPuzzle.puzzle_date.is_(None),
    ).order_by(SudokuPuzzle.served_count.asc(), SudokuPuzzle.id.asc()).first()

    if puzzle:
        puzzle.served_count += 1
        db.commit()
    return puzzle


def _sudoku_seed(difficulty: str, today: str) -> int:
    """Fallback seed for client-side generation when no pre-generated puzzle exists."""
    import hashlib as _hl
    if difficulty == "daily":
        return int(_hl.md5(f"sudoku-daily-{today}".encode(), usedforsecurity=False).hexdigest(), 16) & 0xFFFFFFFF
    import random as _rand
    return _rand.randint(0, 0xFFFFFFFF)


def _sudoku_context(request: Request, db: Session, difficulty: str) -> dict:
    """Build template context for a Sudoku play page, using a pre-generated
    puzzle if available and falling back to client-side generation otherwise."""
    today = sudoku_today_str()
    puzzle = _fetch_puzzle(db, difficulty, today)
    if puzzle:
        givens = puzzle.givens
        seed = None
    else:
        givens = None
        seed = _sudoku_seed(difficulty, today)
    return {
        "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today, "difficulty": difficulty,
        "seed": seed, "givens": givens,
    }


@sudoku_router.get("/other/sudoku", response_class=HTMLResponse)
def sudoku_landing(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/other/sudoku/daily"), status_code=302)


@sudoku_router.get("/other/sudoku/daily", response_class=HTMLResponse)
def sudoku_daily(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "sudoku_play.html",
                                      _sudoku_context(request, db, "daily"))


@sudoku_router.get("/other/sudoku/easy", response_class=HTMLResponse)
def sudoku_easy(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "sudoku_play.html",
                                      _sudoku_context(request, db, "easy"))


@sudoku_router.get("/other/sudoku/medium", response_class=HTMLResponse)
def sudoku_medium(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "sudoku_play.html",
                                      _sudoku_context(request, db, "medium"))


@sudoku_router.get("/other/sudoku/hard", response_class=HTMLResponse)
def sudoku_hard(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "sudoku_play.html",
                                      _sudoku_context(request, db, "hard"))


@sudoku_router.get("/other/sudoku/expert", response_class=HTMLResponse)
def sudoku_expert(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "sudoku_play.html",
                                      _sudoku_context(request, db, "expert"))


@sudoku_router.get("/other/sudoku/scores", response_class=HTMLResponse)
def sudoku_scores_page(request: Request):
    return templates.TemplateResponse(request, "sudoku_scores.html", {
        "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": sudoku_today_str(),
    })


@sudoku_router.get("/other/sudoku/board/{board_hash}", response_class=HTMLResponse)
def sudoku_play_by_hash(board_hash: str, request: Request, db: Session = Depends(get_db)):
    row = db.query(SudokuScore).filter(SudokuScore.board_hash == board_hash).first()
    if not row:
        raise HTTPException(status_code=404, detail="Board not found")
    return templates.TemplateResponse(request, "sudoku_play.html", {
        "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": sudoku_today_str(),
        "difficulty": row.difficulty,
        "seed": None, "givens": row.board_givens,
    })


class SudokuScoreSubmit(BaseModel):
    name:         str = Field(..., min_length=1, max_length=32)
    puzzle_date:  str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    difficulty:   str = Field(..., min_length=1, max_length=16)
    board_hash:   str = Field(..., min_length=64, max_length=64)
    board_givens: str = Field(..., min_length=81, max_length=81)
    time_ms:      int = Field(..., ge=1, le=86400000)   # max 24 h
    hints_used:   int = Field(0, ge=0, le=81)
    # Bitmask: 1 = auto candidates, 2 = auto check. Shown on the leaderboard.
    assists:      int = Field(0, ge=0, le=3)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable())
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        if v not in _SUDOKU_DIFFICULTIES:
            raise ValueError(f"Invalid difficulty: {v}")
        return v

    @field_validator("board_givens")
    @classmethod
    def validate_givens(cls, v: str) -> str:
        if not all(c in "0123456789" for c in v):
            raise ValueError("board_givens must be 81 digits 0-9")
        return v


@sudoku_router.post("/api/sudoku-scores", status_code=201)
@limiter.limit("20/minute")
def submit_sudoku_score(payload: SudokuScoreSubmit, request: Request, db: Session = Depends(get_db)):
    from telemetry import record_score_submit, record_game_complete
    user = get_current_user(request)
    if user:
        guest_token = None
        # First-score-per-hash rule for signed-in users
        exists = db.query(SudokuScore).filter(
            SudokuScore.user_email == user["email"],
            SudokuScore.board_hash == payload.board_hash,
        ).first()
        if exists:
            return {"ok": True, "id": exists.id, "duplicate": True}
    else:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
        exists = db.query(SudokuScore).filter(
            SudokuScore.guest_token == guest_token,
            SudokuScore.board_hash == payload.board_hash,
        ).first()
        if exists:
            return {"ok": True, "id": exists.id, "duplicate": True}

    entry = SudokuScore(
        name         = payload.name,
        user_email   = user["email"] if user else None,
        difficulty   = payload.difficulty,
        board_hash   = payload.board_hash,
        board_givens = payload.board_givens,
        time_ms      = payload.time_ms,
        hints_used   = payload.hints_used,
        assists      = payload.assists,
        puzzle_date  = payload.puzzle_date,
        guest_token  = guest_token,
        client_type  = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    flag_if_profane(db, entry.__tablename__, entry.id, entry.name)
    record_score_submit("sudoku", payload.puzzle_date)
    record_game_complete("sudoku", mode=payload.difficulty, duration_ms=payload.time_ms)
    return {"ok": True, "id": entry.id}


@sudoku_router.get("/api/sudoku-puzzle")
@limiter.limit("30/minute")
def get_sudoku_puzzle(request: Request, response: Response, difficulty: str = "easy",
                      db: Session = Depends(get_db)):
    """Next technique-graded puzzle for the in-page "next game" (F-GAME-END + F-SUDOKU-GRADING).

    Same pool selection as the play pages; returns givens: null when the pool for
    this level is empty, and the client falls back to generating one itself.
    The daily is served by its page only, so it is not available here.
    """
    response.headers["Cache-Control"] = "no-store"
    if difficulty not in _SUDOKU_DIFFICULTIES or difficulty == "daily":
        raise HTTPException(status_code=400, detail="Invalid difficulty")
    puzzle = _fetch_puzzle(db, difficulty, sudoku_today_str())
    return {"difficulty": difficulty, "givens": puzzle.givens if puzzle else None}


@sudoku_router.get("/api/sudoku-scores")
def get_sudoku_scores(
    difficulty:  str = "daily",
    period:      str = "today",
    puzzle_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    import re
    if difficulty not in _SUDOKU_DIFFICULTIES:
        raise HTTPException(status_code=400, detail="Invalid difficulty")
    if period not in ("today", "alltime"):
        raise HTTPException(status_code=400, detail="Invalid period")

    q = db.query(SudokuScore).filter(SudokuScore.difficulty == difficulty)
    q = exclude_flagged(q, SudokuScore, db)

    if period == "today":
        today = puzzle_date or sudoku_today_str()
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", today):
            raise HTTPException(status_code=400, detail="Invalid date format")
        q = q.filter(SudokuScore.puzzle_date == today) \
             .order_by(SudokuScore.time_ms.asc(), SudokuScore.created_at.asc()) \
             .limit(50)
        return _enrich_with_profiles(q.all(), db)

    # all-time: best score per signed-in user
    from sqlalchemy import func
    subq = (
        db.query(
            SudokuScore.user_email,
            func.min(SudokuScore.time_ms).label("best_time"),
        )
        .filter(
            SudokuScore.difficulty == difficulty,
            SudokuScore.user_email.isnot(None),
        )
        .group_by(SudokuScore.user_email)
        .order_by(func.min(SudokuScore.time_ms).asc())
        .limit(50)
        .subquery()
    )
    rows = (
        db.query(SudokuScore)
        .join(subq, (SudokuScore.user_email == subq.c.user_email) &
                    (SudokuScore.time_ms == subq.c.best_time))
        .filter(SudokuScore.difficulty == difficulty)
        .order_by(SudokuScore.time_ms.asc(), SudokuScore.created_at.asc())
        .limit(50)
        .all()
    )
    return _enrich_with_profiles(rows, db)
