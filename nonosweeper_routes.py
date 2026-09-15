"""
nonosweeper_routes.py — Score API and page route handlers for Nonosweeper.
Mount this router in main.py with: app.include_router(nonosweeper_router)
"""
import re
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from database import (
    FlaggedScore, GameReplay, UserProfile,
    NonosweeperScore,
    get_db,
)
from auth import get_current_user
from translations import get_lang, get_t, SUPPORTED_LANGS
import settings as site_settings
from quest_catalog import quest_config
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs

nonosweeper_router = APIRouter()
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


# ── Nonosweeper scores ────────────────────────────────────────────────────────
# NOTE: API score routes must be registered before the page catch-all routes.

class NonosweeperScoreSubmit(BaseModel):
    name:        str = Field(..., min_length=1, max_length=32)
    puzzle_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    difficulty:  str = Field(..., pattern=r"^(beginner|intermediate|expert)$")
    time_secs:   int = Field(..., ge=0, le=99999)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable())
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


@nonosweeper_router.post("/api/nonosweeper-scores", status_code=201)
@limiter.limit("10/minute")
def submit_nonosweeper_score(payload: NonosweeperScoreSubmit, request: Request, db: Session = Depends(get_db)):
    from telemetry import record_score_submit, record_game_complete
    user = get_current_user(request)
    guest_token = get_or_create_guest_token(request, user)
    entry = NonosweeperScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        puzzle_date = payload.puzzle_date,
        difficulty  = payload.difficulty,
        time_secs   = payload.time_secs,
        guest_token = guest_token,
        client_type = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    flag_if_profane(db, entry.__tablename__, entry.id, entry.name)
    record_score_submit("nonosweeper", str(payload.puzzle_date))
    record_game_complete("nonosweeper", mode=payload.difficulty,
                         duration_ms=(payload.time_secs or 0) * 1000)
    return {"ok": True, "id": entry.id}


@nonosweeper_router.get("/api/nonosweeper-scores/{puzzle_date}")
def get_nonosweeper_scores(
    puzzle_date: str,
    difficulty: str = Query("beginner"),
    db: Session = Depends(get_db),
):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", puzzle_date):
        raise HTTPException(status_code=400, detail="Invalid date format")
    if difficulty not in ("beginner", "intermediate", "expert"):
        difficulty = "beginner"
    q = db.query(NonosweeperScore).filter(
        NonosweeperScore.puzzle_date == puzzle_date,
        NonosweeperScore.difficulty  == difficulty,
    )
    q = exclude_flagged(q, NonosweeperScore, db)
    top = (
        q
        .order_by(NonosweeperScore.time_secs.asc(), NonosweeperScore.created_at.asc())
        .limit(20)
        .all()
    )
    return _enrich_with_profiles(top, db)


# ── Nonosweeper ───────────────────────────────────────────────────────────────

@nonosweeper_router.get("/nonosweeper", response_class=HTMLResponse)
async def nonosweeper_page(request: Request, date_param: str = Query(None, alias="date")):
    print(f"[DEBUG] nonosweeper_page hit: {request.url}", flush=True)
    real_today = date.today().isoformat()
    puzzle_date = real_today
    if date_param and re.match(r"^\d{4}-\d{2}-\d{2}$", date_param):
        puzzle_date = date_param
    print(f"[DEBUG] nonosweeper_page puzzle_date={puzzle_date}", flush=True)
    try:
        response = templates.TemplateResponse(request, "nonosweeper.html", {
            "mode": "nonosweeper",
            "user": get_current_user(request),
            "lang": get_lang(request), "t": get_t(request),
            "today": puzzle_date,
            "real_today": real_today,
            "default_no_guess": True,
        })
        print(f"[DEBUG] nonosweeper_page rendered successfully", flush=True)
        return response
    except Exception as e:
        print(f"[DEBUG] nonosweeper_page ERROR: {type(e).__name__}: {e}", flush=True)
        raise


@nonosweeper_router.get("/nonosweeper/{date_str}", response_class=HTMLResponse)
async def nonosweeper_permalink(request: Request, date_str: str):
    print(f"[DEBUG] nonosweeper_permalink hit: {request.url}, date_str={date_str}", flush=True)
    real_today = date.today().isoformat()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        print(f"[DEBUG] nonosweeper_permalink invalid date_str, redirecting", flush=True)
        return RedirectResponse("/nonosweeper", status_code=302)
    try:
        response = templates.TemplateResponse(request, "nonosweeper.html", {
            "mode": "nonosweeper",
            "user": get_current_user(request),
            "lang": get_lang(request), "t": get_t(request),
            "today": date_str,
            "real_today": real_today,
            "noindex": True,
            "default_no_guess": True,
        })
        print(f"[DEBUG] nonosweeper_permalink rendered successfully", flush=True)
        return response
    except Exception as e:
        print(f"[DEBUG] nonosweeper_permalink ERROR: {type(e).__name__}: {e}", flush=True)
        raise
