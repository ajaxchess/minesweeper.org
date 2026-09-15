"""
game2048_routes.py — Page and API route handlers for 2048 and 2048 Hexagon.
Mount this router in main.py with: app.include_router(game2048_router)
"""
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
    Game2048Score, Game2048HexScore,
    get_db,
)
from auth import get_current_user
from translations import get_lang, get_t, SUPPORTED_LANGS
import settings as site_settings
from quest_catalog import quest_config
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs

game2048_router = APIRouter()
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


# ── 2048 ──────────────────────────────────────────────────────────────────────

@game2048_router.get("/other/2048", response_class=HTMLResponse)
def game_2048_landing(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/other/2048/daily"), status_code=302)


@game2048_router.get("/other/2048/daily", response_class=HTMLResponse)
def game_2048_daily(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse(request, "2048_daily.html", {
        "mode":    "other",
        "user":    get_current_user(request),
        "lang":    get_lang(request), "t": get_t(request),
        "today":   today,
        "noindex": get_lang(request) != "en",
    })


@game2048_router.get("/other/2048/leaderboard", response_class=HTMLResponse)
def game_2048_leaderboard_page(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse(request, "2048_leaderboard.html", {
        "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today,
    })


@game2048_router.get("/other/2048/how-to-play", response_class=HTMLResponse)
def game_2048_howtoplay(request: Request):
    return templates.TemplateResponse(request, "2048_howtoplay.html", {
        "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


class Game2048ScoreSubmit(BaseModel):
    name:          str            = Field(..., min_length=1, max_length=32)
    puzzle_date:   str            = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    score:         int            = Field(..., ge=0, le=9999999)
    time_ms:       int            = Field(..., ge=0, le=9999999)
    moves:         int            = Field(..., ge=1, le=99999)
    fours_spawned: Optional[int]  = Field(None, ge=0, le=99999)
    moves_to_2048: Optional[int]  = Field(None, ge=1, le=99999)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable())
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


@game2048_router.post("/api/2048-scores", status_code=201)
@limiter.limit("10/minute")
def submit_2048_score(payload: Game2048ScoreSubmit, request: Request, db: Session = Depends(get_db)):
    from telemetry import record_score_submit, record_game_complete
    user = get_current_user(request)
    guest_token = get_or_create_guest_token(request, user)
    entry = Game2048Score(
        name          = payload.name,
        user_email    = user["email"] if user else None,
        puzzle_date   = payload.puzzle_date,
        score         = payload.score,
        time_ms       = payload.time_ms,
        moves         = payload.moves,
        fours_spawned = payload.fours_spawned,
        moves_to_2048 = payload.moves_to_2048,
        guest_token   = guest_token,
        client_type   = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    flag_if_profane(db, entry.__tablename__, entry.id, entry.name)
    record_score_submit("2048", payload.puzzle_date)
    record_game_complete("2048", mode="daily", duration_ms=payload.time_ms)
    return {"ok": True, "id": entry.id}


@game2048_router.get("/api/2048-scores/{puzzle_date}")
def get_2048_scores(puzzle_date: str, sort: str = "score", db: Session = Depends(get_db)):
    import re
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", puzzle_date):
        raise HTTPException(status_code=400, detail="Invalid date format")
    q = db.query(Game2048Score).filter(Game2048Score.puzzle_date == puzzle_date)
    q = exclude_flagged(q, Game2048Score, db)
    if sort == "moves":
        q = q.filter(Game2048Score.moves_to_2048.isnot(None)) \
             .order_by(Game2048Score.moves_to_2048.asc(), Game2048Score.time_ms.asc())
    else:
        q = q.order_by(Game2048Score.score.desc(), Game2048Score.time_ms.asc())
    return _enrich_with_profiles(q.limit(20).all(), db)


@game2048_router.get("/api/2048-scores")
def get_2048_scores_all_time(sort: str = "score", db: Session = Depends(get_db)):
    q = db.query(Game2048Score)
    q = exclude_flagged(q, Game2048Score, db)
    if sort == "moves":
        q = q.filter(Game2048Score.moves_to_2048.isnot(None)) \
             .order_by(Game2048Score.moves_to_2048.asc(), Game2048Score.time_ms.asc())
    else:
        q = q.order_by(Game2048Score.score.desc(), Game2048Score.time_ms.asc())
    return _enrich_with_profiles(q.limit(20).all(), db)


@game2048_router.get("/api/2048-histogram")
def get_2048_histogram(puzzle_date: Optional[str] = None, db: Session = Depends(get_db)):
    import re
    # Only count games where player stopped at 2048 (moves == moves_to_2048).
    # Excludes games where the player hit Continue and kept playing.
    q = db.query(Game2048Score.moves_to_2048).filter(
        Game2048Score.moves_to_2048.isnot(None),
        Game2048Score.moves == Game2048Score.moves_to_2048,
    )
    if puzzle_date:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", puzzle_date):
            raise HTTPException(status_code=400, detail="Invalid date format")
        q = q.filter(Game2048Score.puzzle_date == puzzle_date)
    rows = q.all()
    buckets: dict[int, int] = {}
    for (m,) in rows:
        b = (m // 100) * 100
        buckets[b] = buckets.get(b, 0) + 1
    return [{"bucket": k, "count": v} for k, v in sorted(buckets.items())]


# ── 2048 Hexagon ──────────────────────────────────────────────────────────────

@game2048_router.get("/other/2048hex", response_class=HTMLResponse)
def game_2048hex_landing(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/other/2048hex/play"), status_code=302)


@game2048_router.get("/other/2048hex/play", response_class=HTMLResponse)
def game_2048hex_play(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse(request, "2048hex.html", {
        "mode":    "other",
        "user":    get_current_user(request),
        "lang":    get_lang(request), "t": get_t(request),
        "today":   today,
        "noindex": get_lang(request) != "en",
    })


@game2048_router.get("/other/2048hex/leaderboard", response_class=HTMLResponse)
def game_2048hex_leaderboard(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse(request, "2048hex_leaderboard.html", {
        "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today,
    })


@game2048_router.get("/other/2048hex/how-to-play", response_class=HTMLResponse)
def game_2048hex_htp(request: Request):
    return templates.TemplateResponse(request, "2048hex_howtoplay.html", {
        "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


class Game2048HexScoreSubmit(BaseModel):
    name:          str            = Field(..., min_length=1, max_length=32)
    puzzle_date:   str            = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    score:         int            = Field(..., ge=0, le=9999999)
    time_ms:       int            = Field(..., ge=0, le=9999999)
    moves:         int            = Field(..., ge=1, le=99999)
    fours_spawned: Optional[int]  = Field(None, ge=0, le=99999)
    moves_to_2048: Optional[int]  = Field(None, ge=1, le=99999)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable())
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


@game2048_router.post("/api/2048hex-scores", status_code=201)
@limiter.limit("10/minute")
def submit_2048hex_score(payload: Game2048HexScoreSubmit, request: Request, db: Session = Depends(get_db)):
    from telemetry import record_score_submit, record_game_complete
    user = get_current_user(request)
    guest_token = get_or_create_guest_token(request, user)
    entry = Game2048HexScore(
        name          = payload.name,
        user_email    = user["email"] if user else None,
        puzzle_date   = payload.puzzle_date,
        score         = payload.score,
        time_ms       = payload.time_ms,
        moves         = payload.moves,
        fours_spawned = payload.fours_spawned,
        moves_to_2048 = payload.moves_to_2048,
        guest_token   = guest_token,
        client_type   = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    flag_if_profane(db, entry.__tablename__, entry.id, entry.name)
    record_score_submit("2048hex", payload.puzzle_date)
    record_game_complete("2048hex", mode="daily", duration_ms=payload.time_ms)
    return {"ok": True, "id": entry.id}


@game2048_router.get("/api/2048hex-scores/{puzzle_date}")
def get_2048hex_scores(puzzle_date: str, sort: str = "score", db: Session = Depends(get_db)):
    import re
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", puzzle_date):
        raise HTTPException(status_code=400, detail="Invalid date format")
    q = db.query(Game2048HexScore).filter(Game2048HexScore.puzzle_date == puzzle_date)
    q = exclude_flagged(q, Game2048HexScore, db)
    if sort == "moves":
        q = q.filter(Game2048HexScore.moves_to_2048.isnot(None)) \
             .order_by(Game2048HexScore.moves_to_2048.asc(), Game2048HexScore.time_ms.asc())
    else:
        q = q.order_by(Game2048HexScore.score.desc(), Game2048HexScore.time_ms.asc())
    return _enrich_with_profiles(q.limit(20).all(), db)


@game2048_router.get("/api/2048hex-scores")
def get_2048hex_scores_all_time(sort: str = "score", db: Session = Depends(get_db)):
    q = db.query(Game2048HexScore)
    q = exclude_flagged(q, Game2048HexScore, db)
    if sort == "moves":
        q = q.filter(Game2048HexScore.moves_to_2048.isnot(None)) \
             .order_by(Game2048HexScore.moves_to_2048.asc(), Game2048HexScore.time_ms.asc())
    else:
        q = q.order_by(Game2048HexScore.score.desc(), Game2048HexScore.time_ms.asc())
    return _enrich_with_profiles(q.limit(20).all(), db)


@game2048_router.get("/api/2048hex-histogram")
def get_2048hex_histogram(puzzle_date: Optional[str] = None, db: Session = Depends(get_db)):
    import re
    # Only count games where player stopped at 2048 (moves == moves_to_2048).
    # Excludes games where the player hit Continue and kept playing.
    q = db.query(Game2048HexScore.moves_to_2048).filter(
        Game2048HexScore.moves_to_2048.isnot(None),
        Game2048HexScore.moves == Game2048HexScore.moves_to_2048,
    )
    if puzzle_date:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", puzzle_date):
            raise HTTPException(status_code=400, detail="Invalid date format")
        q = q.filter(Game2048HexScore.puzzle_date == puzzle_date)
    rows = q.all()
    buckets: dict[int, int] = {}
    for (m,) in rows:
        b = (m // 100) * 100
        buckets[b] = buckets.get(b, 0) + 1
    return [{"bucket": k, "count": v} for k, v in sorted(buckets.items())]
