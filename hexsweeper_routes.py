"""
hexsweeper_routes.py — Page and API route handlers for Hexsweeper.
Mount this router in main.py with: app.include_router(hexsweeper_router)
"""
import uuid
from datetime import date, timedelta
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import case
from sqlalchemy.orm import Session
from better_profanity import profanity as _profanity_checker

from database import (
    FlaggedScore, UserProfile, GameReplay,
    HexsweeperScore,
    get_db,
)
from auth import get_current_user
from translations import get_lang, get_t, SUPPORTED_LANGS
import settings as site_settings
from quest_catalog import quest_config
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs

hexsweeper_router = APIRouter()
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


# ── Period-range helpers (mirrors of main.py) ─────────────────────────────────

SEASON_ORIGIN_YEAR  = 2026
SEASON_ORIGIN_MONTH = 3  # March


def get_season_range(season_num: int):
    """Return (start_date, end_date) for the given 1-based season number."""
    total = SEASON_ORIGIN_MONTH - 1 + (season_num - 1)
    year  = SEASON_ORIGIN_YEAR + total // 12
    month = total % 12 + 1
    start = date(year, month, 1)
    end   = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def current_season_num() -> int:
    today = date.today()
    return (today.year - SEASON_ORIGIN_YEAR) * 12 + (today.month - SEASON_ORIGIN_MONTH) + 1


def get_period_range(period: str, target: Optional[date] = None, season_num: Optional[int] = None):
    """Return date bounds for finite leaderboard periods."""
    target = target or date.today()
    if period == "daily":
        return target, target + timedelta(days=1)
    if period == "weekly":
        start = target - timedelta(days=target.weekday())
        return start, start + timedelta(days=7)
    if period == "monthly":
        start = target.replace(day=1)
        end = date(start.year + 1, 1, 1) if start.month == 12 else date(start.year, start.month + 1, 1)
        return start, end
    if period == "yearly":
        start = date(target.year, 1, 1)
        return start, date(target.year + 1, 1, 1)
    if period == "season":
        return get_season_range(season_num) if season_num and season_num >= 1 else get_season_range(current_season_num())
    return None, None


# ── Hexsweeper Routes ─────────────────────────────────────────────────────────

# Hex board cell count for radius R = 3R²−3R+1
# R=5 → 61 cells, R=7 → 127 cells, R=10 → 271 cells
HEXSWEEPER_MODES = {
    "hex-beginner":     {"radius": 5, "mines": 8},
    "hex-intermediate": {"radius": 7, "mines": 20},
    "hex-expert":       {"radius": 10, "mines": 57},
}


@hexsweeper_router.get("/hexsweeper", response_class=HTMLResponse)
async def hexsweeper_beginner(request: Request):
    return templates.TemplateResponse(request, "hexsweeper.html", {
        "mode": "hex-beginner",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **HEXSWEEPER_MODES["hex-beginner"]
    })


@hexsweeper_router.get("/hexsweeper/intermediate", response_class=HTMLResponse)
async def hexsweeper_intermediate(request: Request):
    return templates.TemplateResponse(request, "hexsweeper.html", {
        "mode": "hex-intermediate",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **HEXSWEEPER_MODES["hex-intermediate"]
    })


@hexsweeper_router.get("/hexsweeper/expert", response_class=HTMLResponse)
async def hexsweeper_expert(request: Request):
    return templates.TemplateResponse(request, "hexsweeper.html", {
        "mode": "hex-expert",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **HEXSWEEPER_MODES["hex-expert"]
    })


@hexsweeper_router.get("/hexsweeper/custom", response_class=HTMLResponse)
async def hexsweeper_custom(request: Request):
    return templates.TemplateResponse(request, "hexsweeper.html", {
        "mode": "hex-custom",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "radius": 5, "mines": 8,
    })


# ── Hexsweeper Leaderboard API ────────────────────────────────────────────────

HEX_MODES_VALID = {"beginner", "intermediate", "expert", "custom"}


class HexscoreSubmit(BaseModel):
    name:         str          = Field(..., min_length=1, max_length=32)
    hex_mode:     str          = Field(..., pattern="^(beginner|intermediate|expert|custom)$")
    time_secs:    int          = Field(..., ge=1, le=999)
    time_ms:      Optional[int]  = Field(None, ge=1, le=3_600_000)
    radius:       int          = Field(..., ge=3, le=20)
    mines:        int          = Field(..., ge=1, le=999)
    board_hash:   Optional[str]  = Field(None, max_length=128)
    bbbv:         Optional[int]  = Field(None, ge=1, le=9999)
    left_clicks:  Optional[int]  = Field(None, ge=0, le=99999)
    right_clicks: Optional[int]  = Field(None, ge=0, le=99999)
    chord_clicks: Optional[int]  = Field(None, ge=0, le=99999)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable())
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]

    @field_validator("mines")
    @classmethod
    def mines_not_exceeding_board(cls, v, info):
        radius = info.data.get("radius")
        if radius:
            cells = 3 * radius * radius - 3 * radius + 1
            if v > int(cells * 0.85):
                raise ValueError("Too many mines for this board size")
        return v


@hexsweeper_router.post("/api/hexsweeper-scores", status_code=201)
@limiter.limit("10/minute")
def submit_hex_score(payload: HexscoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    guest_token = get_or_create_guest_token(request, user)
    entry = HexsweeperScore(
        name         = payload.name,
        user_email   = user["email"] if user else None,
        hex_mode     = payload.hex_mode,
        time_secs    = payload.time_secs,
        time_ms      = payload.time_ms,
        radius       = payload.radius,
        mines        = payload.mines,
        board_hash   = payload.board_hash,
        bbbv         = payload.bbbv,
        left_clicks  = payload.left_clicks,
        right_clicks = payload.right_clicks,
        chord_clicks = payload.chord_clicks,
        guest_token  = guest_token,
        client_type  = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    flag_if_profane(db, entry.__tablename__, entry.id, entry.name)
    return {"ok": True, "id": entry.id}


@hexsweeper_router.get("/api/hexsweeper-scores/{hex_mode}")
def get_hex_scores(hex_mode: str, period: str = "alltime",
                   score_date: Optional[str] = Query(None, alias="date"),
                   season_num: Optional[int] = Query(None),
                   db: Session = Depends(get_db)):
    if hex_mode not in HEX_MODES_VALID:
        raise HTTPException(status_code=400, detail="Invalid mode")
    if period not in ("daily", "weekly", "monthly", "season", "yearly", "alltime"):
        period = "alltime"

    sort_key = case(
        (HexsweeperScore.time_ms.isnot(None), HexsweeperScore.time_ms),
        else_=HexsweeperScore.time_secs * 1000
    )

    q = db.query(HexsweeperScore).filter(HexsweeperScore.hex_mode == hex_mode)
    q = exclude_flagged(q, HexsweeperScore, db)

    if period in ("daily", "weekly", "monthly", "season", "yearly"):
        try:
            target = date.fromisoformat(score_date) if score_date else date.today()
        except ValueError:
            target = date.today()
        p_start, p_end = get_period_range(period, target, season_num)
        q = q.filter(HexsweeperScore.created_at >= p_start,
                     HexsweeperScore.created_at < p_end)
        if period == "daily":
            top = q.order_by(sort_key.asc(), HexsweeperScore.created_at.asc()).limit(15).all()
            return _enrich_with_profiles(top, db)

    raw = q.order_by(sort_key.asc(), HexsweeperScore.created_at.asc()).limit(500).all()
    seen: set = set()
    top: list = []
    for s in raw:
        key = s.user_email or s.name
        if key not in seen:
            seen.add(key)
            top.append(s)
            if len(top) >= 15:
                break
    return _enrich_with_profiles(top, db)
