"""
meowdoku_routes.py — Page and API route handlers for Meowdoku.
Mount this router in main.py with: app.include_router(meowdoku_router)

NOTE: This router must be included before WC2026/vibecoding routes in main.py.
Routes with path parameters defined after ~line 9700 return 404 — likely an
OTEL FastAPIInstrumentor interaction with the large route table.
"""
import re
from datetime import date
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from better_profanity import profanity as _profanity_checker

from database import (
    FlaggedScore, UserProfile, GameReplay,
    MeowdokuScore, MeowdokuSavedPuzzle,
    get_db,
)
from auth import get_current_user
from admin_routes import require_user
from translations import get_lang, get_t, SUPPORTED_LANGS
import settings as site_settings
from quest_catalog import quest_config
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs

meowdoku_router = APIRouter()
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
    import uuid
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


# ── Meowdoku ─────────────────────────────────────────────────────────────────

@meowdoku_router.get("/meowdoku", response_class=HTMLResponse)
async def meowdoku_page(
    request: Request,
    date_param: str = Query(None, alias="date"),
    size: int = Query(8, ge=4, le=10),
    board: str = Query(None),   # custom board hash from generator
):
    real_today = date.today().isoformat()
    puzzle_date = real_today
    if date_param and re.match(r"^\d{4}-\d{2}-\d{2}$", date_param):
        puzzle_date = date_param
    return templates.TemplateResponse(request, "meowdoku.html", {
        "mode":       "meowdoku",
        "user":       get_current_user(request),
        "lang":       get_lang(request),
        "t":          get_t(request),
        "today":      puzzle_date,
        "real_today": real_today,
        "grid_size":  size,
        "custom_board": board or "",
    })


@meowdoku_router.get("/puzzles/meowdoku", response_class=HTMLResponse)
async def puzzles_meowdoku_redirect(request: Request):
    prefix = _safe_lang_prefix(get_lang(request))
    return RedirectResponse(f"{prefix}/meowdoku", status_code=301)


@meowdoku_router.get("/meowdoku/generator", response_class=HTMLResponse)
async def meowdoku_generator_page(request: Request):
    return templates.TemplateResponse(request, "meowdoku_generator.html", {
        "mode": "meowdoku",
        "user": get_current_user(request),
        "lang": get_lang(request),
        "t":    get_t(request),
    })


@meowdoku_router.get("/puzzles/meowdoku/generator", response_class=HTMLResponse)
async def puzzles_meowdoku_generator_redirect(request: Request):
    prefix = _safe_lang_prefix(get_lang(request))
    return RedirectResponse(f"{prefix}/meowdoku/generator", status_code=301)


class MeowdokuScoreSubmit(BaseModel):
    name:        str = Field(..., min_length=1, max_length=32)
    puzzle_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    grid_size:   int = Field(..., ge=4, le=10)
    time_secs:   int = Field(..., ge=0, le=99999)
    board_hash:  str = Field("", max_length=128)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable())
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


@meowdoku_router.post("/api/meowdoku-scores", status_code=201)
@limiter.limit("10/minute")
def submit_meowdoku_score(payload: MeowdokuScoreSubmit, request: Request, db: Session = Depends(get_db)):
    from telemetry import record_score_submit, record_game_complete
    user = get_current_user(request)
    guest_token = get_or_create_guest_token(request, user)
    entry = MeowdokuScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        puzzle_date = payload.puzzle_date,
        grid_size   = payload.grid_size,
        time_secs   = payload.time_secs,
        board_hash  = payload.board_hash or None,
        guest_token = guest_token,
        client_type = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    flag_if_profane(db, entry.__tablename__, entry.id, entry.name)
    record_score_submit("meowdoku", str(payload.puzzle_date))
    record_game_complete("meowdoku", mode="daily", duration_ms=(payload.time_secs or 0) * 1000)
    return {"ok": True, "id": entry.id}


@meowdoku_router.get("/api/meowdoku-scores/{puzzle_date}")
def get_meowdoku_scores(puzzle_date: str, size: int = Query(8, ge=4, le=10), db: Session = Depends(get_db)):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", puzzle_date):
        raise HTTPException(status_code=400, detail="Invalid date format")
    q = (
        db.query(MeowdokuScore)
        .filter(MeowdokuScore.puzzle_date == puzzle_date, MeowdokuScore.grid_size == size)
    )
    q = exclude_flagged(q, MeowdokuScore, db)
    top = (
        q.order_by(MeowdokuScore.time_secs.asc(), MeowdokuScore.created_at.asc())
        .limit(20)
        .all()
    )
    return _enrich_with_profiles(top, db)


class MeowdokuSavePuzzlePayload(BaseModel):
    board_hash: str = Field(..., min_length=1, max_length=128)
    grid_size:  int = Field(..., ge=4, le=10)


@meowdoku_router.post("/api/meowdoku/saved-puzzles", status_code=201)
def save_meowdoku_puzzle(payload: MeowdokuSavePuzzlePayload, request: Request, db: Session = Depends(get_db)):
    user = require_user(request)
    count = db.query(MeowdokuSavedPuzzle).filter_by(user_email=user["email"]).count()
    if count >= 50:
        raise HTTPException(status_code=400, detail="Saved puzzle limit reached (50)")
    existing = db.query(MeowdokuSavedPuzzle).filter_by(
        user_email=user["email"], board_hash=payload.board_hash
    ).first()
    if existing:
        return existing.to_dict()
    puzzle = MeowdokuSavedPuzzle(
        user_email=user["email"],
        grid_size=payload.grid_size,
        board_hash=payload.board_hash,
    )
    db.add(puzzle)
    db.commit()
    db.refresh(puzzle)
    return puzzle.to_dict()


@meowdoku_router.delete("/api/meowdoku/saved-puzzles/{puzzle_id}", status_code=204)
def delete_meowdoku_saved_puzzle(puzzle_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_user(request)
    puzzle = db.query(MeowdokuSavedPuzzle).filter_by(id=puzzle_id, user_email=user["email"]).first()
    if not puzzle:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(puzzle)
    db.commit()
