"""
mosaic_routes.py — Page and API route handlers for Mosaic Sweeper.
Mount this router in main.py with: app.include_router(mosaic_router)
"""
import hashlib
import re as _re
import uuid
from datetime import date
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from better_profanity import profanity as _profanity_checker

from database import (
    FlaggedScore, UserProfile, GameReplay,
    MosaicScore, MosaicEasyScore, MosaicCustomScore,
    get_db,
)
from auth import get_current_user
from translations import get_lang, get_t, SUPPORTED_LANGS
import settings as site_settings
from quest_catalog import quest_config
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs

mosaic_router = APIRouter()
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


# ── Mosaic puzzle redirect ─────────────────────────────────────────────────────

@mosaic_router.get("/puzzles/mosaic", response_class=HTMLResponse)
@mosaic_router.get("/puzzles/mosaic/easy", response_class=HTMLResponse)
@mosaic_router.get("/puzzles/mosaic/standard", response_class=HTMLResponse)
def puzzles_mosaic_redirect(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/mosaic"), status_code=301)


# ── Mosaic ────────────────────────────────────────────────────────────────────

@mosaic_router.get("/mosaic", response_class=HTMLResponse)
async def mosaic_page(request: Request, seed: str = ""):
    return templates.TemplateResponse(request, "mosaic_easy.html", {
        "mode": "mosaic",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": date.today().isoformat(),
        "seed": seed.replace(".", "-"),
    })

@mosaic_router.get("/mosaic/how-to-play", response_class=HTMLResponse)
async def mosaic_howto(request: Request):
    return templates.TemplateResponse(request, "mosaic_howto.html", {
        "mode": "mosaic-howto",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })

@mosaic_router.get("/mosaic/easy", response_class=HTMLResponse)
async def mosaic_easy_redirect(request: Request):
    return RedirectResponse(url="/mosaic", status_code=301)

@mosaic_router.get("/mosaic/standard", response_class=HTMLResponse)
async def mosaic_standard_page(request: Request, seed: str = ""):
    return templates.TemplateResponse(request, "mosaic.html", {
        "mode": "mosaic",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": date.today().isoformat(),
        "seed": seed.replace(".", "-"),
    })

@mosaic_router.get("/mosaic/replay", response_class=HTMLResponse)
async def mosaic_replay_page(request: Request, seed: str = "", rows: int = 9, cols: int = 9):
    cell_size = 64 if rows <= 5 else 42
    return templates.TemplateResponse(request, "mosaic_replay.html", {
        "mode": "mosaic",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": date.today().isoformat(),
        "seed": seed, "rows": rows, "cols": cols, "cell_size": cell_size,
    })


# ── Mosaic Custom ──────────────────────────────────────────────────────────────

@mosaic_router.get("/mosaic/custom/", response_class=HTMLResponse)
async def mosaic_custom_page(
    request: Request,
    hash: str = "",
    rows: int = 9,
    cols: int = 9,
    density: float = 0.35,
    mask: str = "",
):
    rows      = max(3, min(20, rows))
    cols      = max(3, min(20, cols))
    density   = max(0.1, min(0.6, density))
    cell_size = 64 if (rows <= 5 and cols <= 5) else (46 if rows <= 9 else 34)
    return templates.TemplateResponse(request, "mosaic_custom.html", {
        "mode": "mosaic",
        "user":      get_current_user(request),
        "lang":      get_lang(request), "t": get_t(request),
        "hash":      hash,
        "rows":      rows,
        "cols":      cols,
        "density":   density,
        "cell_size": cell_size,
        "mask":      mask,
    })


# ── Mosaic Leaderboard API ─────────────────────────────────────────────────────

class MosaicScoreSubmit(BaseModel):
    name:        str = Field(..., min_length=1, max_length=32)
    puzzle_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    time_secs:   int = Field(..., ge=0, le=99999)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable())
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


@mosaic_router.post("/api/mosaic-scores", status_code=201)
@limiter.limit("10/minute")
def submit_mosaic_score(payload: MosaicScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    guest_token = get_or_create_guest_token(request, user)
    entry = MosaicScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        puzzle_date = payload.puzzle_date,
        time_secs   = payload.time_secs,
        guest_token = guest_token,
        client_type = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    flag_if_profane(db, entry.__tablename__, entry.id, entry.name)
    return {"ok": True, "id": entry.id}


@mosaic_router.get("/api/mosaic-scores/{puzzle_date}")
def get_mosaic_scores(puzzle_date: str, db: Session = Depends(get_db)):
    if not _re.match(r"^\d{4}-\d{2}-\d{2}$", puzzle_date):
        raise HTTPException(status_code=400, detail="Invalid date format")
    q = db.query(MosaicScore).filter(MosaicScore.puzzle_date == puzzle_date)
    q = exclude_flagged(q, MosaicScore, db)
    top = (
        q
        .order_by(MosaicScore.time_secs.asc(), MosaicScore.created_at.asc())
        .limit(20)
        .all()
    )
    return _enrich_with_profiles(top, db)


# ── Mosaic Easy Leaderboard API ────────────────────────────────────────────────

class MosaicEasyScoreSubmit(BaseModel):
    name:        str = Field(..., min_length=1, max_length=32)
    puzzle_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    time_secs:   int = Field(..., ge=0, le=99999)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable())
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


@mosaic_router.post("/api/mosaic-easy-scores", status_code=201)
@limiter.limit("10/minute")
def submit_mosaic_easy_score(payload: MosaicEasyScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    guest_token = get_or_create_guest_token(request, user)
    entry = MosaicEasyScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        puzzle_date = payload.puzzle_date,
        time_secs   = payload.time_secs,
        guest_token = guest_token,
        client_type = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    flag_if_profane(db, entry.__tablename__, entry.id, entry.name)
    return {"ok": True, "id": entry.id}


@mosaic_router.get("/api/mosaic-easy-scores/{puzzle_date}")
def get_mosaic_easy_scores(puzzle_date: str, db: Session = Depends(get_db)):
    if not _re.match(r"^\d{4}-\d{2}-\d{2}$", puzzle_date):
        raise HTTPException(status_code=400, detail="Invalid date format")
    q = db.query(MosaicEasyScore).filter(MosaicEasyScore.puzzle_date == puzzle_date)
    q = exclude_flagged(q, MosaicEasyScore, db)
    top = (
        q
        .order_by(MosaicEasyScore.time_secs.asc(), MosaicEasyScore.created_at.asc())
        .limit(20)
        .all()
    )
    return _enrich_with_profiles(top, db)


# ── Mosaic Custom Board Leaderboard API (F44) ──────────────────────────────────

class MosaicCustomScoreSubmit(BaseModel):
    board_hash: str = Field(..., min_length=1, max_length=128)
    board_mask: str = Field("", max_length=128)
    rows:       int = Field(..., ge=3, le=20)
    cols:       int = Field(..., ge=3, le=20)
    name:       str = Field(..., min_length=1, max_length=32)
    time_secs:  int = Field(..., ge=0, le=99999)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable())
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


def _mosaic_custom_board_id(rows: int, cols: int, board_hash: str, board_mask: str) -> str:
    raw = f"{rows}x{cols}:{board_hash}:{board_mask}"
    return hashlib.sha256(raw.encode()).hexdigest()


@mosaic_router.post("/api/mosaic-custom-scores", status_code=201)
@limiter.limit("10/minute")
def submit_mosaic_custom_score(payload: MosaicCustomScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    guest_token = get_or_create_guest_token(request, user)
    board_id = _mosaic_custom_board_id(payload.rows, payload.cols, payload.board_hash, payload.board_mask)
    entry = MosaicCustomScore(
        board_id    = board_id,
        name        = payload.name,
        user_email  = user["email"] if user else None,
        time_secs   = payload.time_secs,
        guest_token = guest_token,
        client_type = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    flag_if_profane(db, entry.__tablename__, entry.id, entry.name)
    return {"ok": True, "id": entry.id, "board_id": board_id}


@mosaic_router.get("/api/mosaic-custom-scores/{board_id}")
def get_mosaic_custom_scores(board_id: str, db: Session = Depends(get_db)):
    if not _re.match(r"^[0-9a-f]{64}$", board_id):
        raise HTTPException(status_code=400, detail="Invalid board_id")
    q = db.query(MosaicCustomScore).filter(MosaicCustomScore.board_id == board_id)
    q = exclude_flagged(q, MosaicCustomScore, db)
    top = (
        q
        .order_by(MosaicCustomScore.time_secs.asc(), MosaicCustomScore.created_at.asc())
        .limit(20)
        .all()
    )
    return _enrich_with_profiles(top, db)
