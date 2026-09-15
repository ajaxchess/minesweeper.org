"""
globesweeper_routes.py — Page and API route handlers for Worldsweeper, CubeSweeper, and MobiusSweeper.
Mount this router in main.py with: app.include_router(globesweeper_router)
"""
import uuid
from datetime import date, timedelta
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from database import (
    FlaggedScore, UserProfile, GameReplay,
    GlobesweeperScore, CubesweeperScore, MobiussweeperScore,
    get_db,
)
from auth import get_current_user
from translations import get_lang, get_t, SUPPORTED_LANGS
import settings as site_settings
from quest_catalog import quest_config
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs

globesweeper_router = APIRouter()
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


# ── Worldsweeper (F55) ───────────────────────────────────────────────────────
# Legacy /globesweeper/* redirects — 301 to canonical /worldsweeper/* URLs

@globesweeper_router.get("/globesweeper")
async def redirect_globesweeper_beginner():
    return RedirectResponse(url="/worldsweeper", status_code=301)

@globesweeper_router.get("/globesweeper/intermediate")
async def redirect_globesweeper_intermediate():
    return RedirectResponse(url="/worldsweeper/intermediate", status_code=301)

@globesweeper_router.get("/globesweeper/expert")
async def redirect_globesweeper_expert():
    return RedirectResponse(url="/worldsweeper/expert", status_code=301)

@globesweeper_router.get("/globesweeper/custom")
async def redirect_globesweeper_custom():
    return RedirectResponse(url="/worldsweeper/custom", status_code=301)

@globesweeper_router.get("/globesweeper/leaderboard")
async def redirect_globesweeper_leaderboard():
    return RedirectResponse(url="/worldsweeper/leaderboard", status_code=301)

GLOBESWEEPER_MODES = {
    "dodecahedron": {"a": 1, "b": 0, "t_param": 1,  "face_count": 12,  "mines": 2},
    "beginner":     {"a": 1, "b": 1, "t_param": 3,  "face_count": 32,  "mines": 4},
    "intermediate": {"a": 2, "b": 1, "t_param": 7,  "face_count": 72,  "mines": 8},
    "expert":       {"a": 5, "b": 0, "t_param": 25, "face_count": 252, "mines": 50},
}
GLOBE_MODES_VALID = {"dodecahedron", "beginner", "intermediate", "expert", "custom"}

# Valid Goldberg T values for the custom board and their GP(a,b) parameters.
CUSTOM_T_AB: dict[int, tuple[int, int]] = {
    1:  (1, 0),  3:  (1, 1),  4:  (2, 0),  7:  (2, 1),  9:  (3, 0),
    12: (2, 2),  13: (3, 1),  16: (4, 0),  19: (3, 2),  21: (4, 1),
    25: (5, 0),  27: (3, 3),  28: (4, 2),  31: (5, 1),  36: (6, 0),
    37: (4, 3),  39: (5, 2),  43: (6, 1),  48: (4, 4),  49: (7, 0),
    57: (7, 1),  61: (5, 4),  75: (5, 5),
}


@globesweeper_router.get("/worldsweeper", response_class=HTMLResponse)
async def worldsweeper_beginner(request: Request):
    m = GLOBESWEEPER_MODES["beginner"]
    return templates.TemplateResponse(request, "worldsweeper.html", {
        "mode": "beginner",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@globesweeper_router.get("/worldsweeper/dodecahedron", response_class=HTMLResponse)
async def worldsweeper_dodecahedron(request: Request):
    m = GLOBESWEEPER_MODES["dodecahedron"]
    return templates.TemplateResponse(request, "worldsweeper.html", {
        "mode": "dodecahedron",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@globesweeper_router.get("/worldsweeper/intermediate", response_class=HTMLResponse)
async def worldsweeper_intermediate(request: Request):
    m = GLOBESWEEPER_MODES["intermediate"]
    return templates.TemplateResponse(request, "worldsweeper.html", {
        "mode": "intermediate",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@globesweeper_router.get("/worldsweeper/expert", response_class=HTMLResponse)
async def worldsweeper_expert(request: Request):
    m = GLOBESWEEPER_MODES["expert"]
    return templates.TemplateResponse(request, "worldsweeper.html", {
        "mode": "expert",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@globesweeper_router.get("/worldsweeper/custom", response_class=HTMLResponse)
async def worldsweeper_custom(request: Request, t: int = 3, mines: int = 4):
    if t not in CUSTOM_T_AB:
        t = 3
    a, b = CUSTOM_T_AB[t]
    face_count = 10 * t + 2
    mines = max(1, min(mines, face_count - 1))
    return templates.TemplateResponse(request, "worldsweeper.html", {
        "mode": "custom",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "a": a, "b": b, "t_param": t, "face_count": face_count, "mines": mines,
    })


@globesweeper_router.get("/worldsweeper/leaderboard", response_class=HTMLResponse)
async def worldsweeper_leaderboard(request: Request):
    return templates.TemplateResponse(request, "worldsweeper_leaderboard.html", {
        "user":    get_current_user(request),
        "lang":    get_lang(request), "t": get_t(request),
        "noindex": get_lang(request) != "en",
    })


class WorldsweeperScoreSubmit(BaseModel):
    name:        str           = Field(..., min_length=1, max_length=32)
    glob_mode:   str           = Field(..., pattern="^(dodecahedron|beginner|intermediate|expert|custom)$")
    time_ms:     int           = Field(..., ge=1, le=3_600_000)
    t_param:     int           = Field(..., ge=1, le=75)
    face_count:  int           = Field(..., ge=12, le=752)
    mines:       int           = Field(..., ge=1, le=750)
    bbbv:         Optional[int] = Field(None, ge=1, le=9999)
    left_clicks:  Optional[int] = Field(None, ge=1, le=99999)
    chord_clicks: Optional[int] = Field(None, ge=0, le=99999)
    board_hash:   Optional[str] = Field(None, max_length=128)

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
        face_count = info.data.get("face_count")
        if face_count and v >= face_count:
            raise ValueError("Too many mines for this board size")
        return v


@globesweeper_router.post("/api/worldsweeper-scores", status_code=201)
@limiter.limit("10/minute")
def submit_world_score(payload: WorldsweeperScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    guest_token = get_or_create_guest_token(request, user)
    entry = GlobesweeperScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        glob_mode   = payload.glob_mode,
        time_ms     = payload.time_ms,
        t_param     = payload.t_param,
        face_count  = payload.face_count,
        mines       = payload.mines,
        bbbv         = payload.bbbv,
        left_clicks  = payload.left_clicks,
        chord_clicks = payload.chord_clicks,
        board_hash   = payload.board_hash,
        guest_token  = guest_token,
        client_type  = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    flag_if_profane(db, entry.__tablename__, entry.id, entry.name)
    return {"ok": True, "id": entry.id}


@globesweeper_router.get("/api/worldsweeper-scores/{glob_mode}")
def get_world_scores(glob_mode: str, period: str = "alltime",
                     score_date: Optional[str] = Query(None, alias="date"),
                     db: Session = Depends(get_db)):
    if glob_mode not in GLOBE_MODES_VALID:
        raise HTTPException(status_code=400, detail="Invalid mode")
    if period not in ("daily", "alltime"):
        period = "alltime"

    q = db.query(GlobesweeperScore).filter(GlobesweeperScore.glob_mode == glob_mode)
    q = exclude_flagged(q, GlobesweeperScore, db)

    if period == "daily":
        try:
            target = date.fromisoformat(score_date) if score_date else date.today()
        except ValueError:
            target = date.today()
        q = q.filter(GlobesweeperScore.created_at >= target,
                     GlobesweeperScore.created_at < target + timedelta(days=1))
        top = q.order_by(GlobesweeperScore.time_ms.asc(),
                         GlobesweeperScore.created_at.asc()).limit(20).all()
        return [s.to_dict() for s in top]

    raw = q.order_by(GlobesweeperScore.time_ms.asc(),
                     GlobesweeperScore.created_at.asc()).limit(500).all()
    seen: set = set()
    top: list = []
    for s in raw:
        key = s.user_email or s.name
        if key not in seen:
            seen.add(key)
            top.append(s.to_dict())
            if len(top) >= 20:
                break
    return top


# ── CubeSweeper ──────────────────────────────────────────────────────────────

CUBESWEEPER_MODES = {
    "beginner":     {"grid_size":  9, "mines":   60},
    "intermediate": {"grid_size": 16, "mines":  240},
    "expert":       {"grid_size": 30, "mines": 1050},
}
CUBE_MODES_VALID = {"beginner", "intermediate", "expert", "custom"}


@globesweeper_router.get("/cubesweeper", response_class=HTMLResponse)
async def cubesweeper_beginner(request: Request):
    m = CUBESWEEPER_MODES["beginner"]
    return templates.TemplateResponse(request, "cubesweeper.html", {
        "mode": "beginner",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@globesweeper_router.get("/cubesweeper/intermediate", response_class=HTMLResponse)
async def cubesweeper_intermediate(request: Request):
    m = CUBESWEEPER_MODES["intermediate"]
    return templates.TemplateResponse(request, "cubesweeper.html", {
        "mode": "intermediate",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@globesweeper_router.get("/cubesweeper/expert", response_class=HTMLResponse)
async def cubesweeper_expert(request: Request):
    m = CUBESWEEPER_MODES["expert"]
    return templates.TemplateResponse(request, "cubesweeper.html", {
        "mode": "expert",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@globesweeper_router.get("/cubesweeper/custom", response_class=HTMLResponse)
async def cubesweeper_custom(request: Request):
    return templates.TemplateResponse(request, "cubesweeper.html", {
        "mode": "custom",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "grid_size": 9, "mines": 10,
    })


@globesweeper_router.get("/cubesweeper/leaderboard", response_class=HTMLResponse)
async def cubesweeper_leaderboard(request: Request):
    return templates.TemplateResponse(request, "cubesweeper_leaderboard.html", {
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


class CubesweeperScoreSubmit(BaseModel):
    name:        str           = Field(..., min_length=1, max_length=32)
    cube_mode:   str           = Field(..., pattern="^(beginner|intermediate|expert|custom)$")
    grid_size:   int           = Field(..., ge=1, le=100)
    time_ms:     int           = Field(..., ge=1, le=7_200_000)
    mines:       int           = Field(..., ge=1)
    no_guess:    bool          = False
    bbbv:         Optional[int] = Field(None, ge=1, le=999999)
    left_clicks:  Optional[int] = Field(None, ge=0, le=9999999)
    chord_clicks: Optional[int] = Field(None, ge=0, le=99999)
    board_hash:   Optional[str] = Field(None, max_length=512)

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
        grid_size = info.data.get("grid_size")
        if grid_size and v >= grid_size * grid_size * 6:
            raise ValueError("Too many mines for this board size")
        return v


@globesweeper_router.post("/api/cubesweeper-scores", status_code=201)
@limiter.limit("10/minute")
def submit_cube_score(payload: CubesweeperScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    guest_token = get_or_create_guest_token(request, user)
    entry = CubesweeperScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        cube_mode   = payload.cube_mode,
        grid_size   = payload.grid_size,
        time_ms     = payload.time_ms,
        mines       = payload.mines,
        no_guess    = payload.no_guess,
        bbbv         = payload.bbbv,
        left_clicks  = payload.left_clicks,
        chord_clicks = payload.chord_clicks,
        board_hash   = payload.board_hash,
        guest_token  = guest_token,
        client_type  = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    flag_if_profane(db, entry.__tablename__, entry.id, entry.name)
    return {"ok": True, "id": entry.id}


@globesweeper_router.get("/api/cubesweeper-scores/{cube_mode}")
def get_cube_scores(cube_mode: str, period: str = "alltime",
                    no_guess: bool = False,
                    score_date: Optional[str] = Query(None, alias="date"),
                    db: Session = Depends(get_db)):
    if cube_mode not in CUBE_MODES_VALID:
        raise HTTPException(status_code=400, detail="Invalid mode")
    if period not in ("daily", "alltime"):
        period = "alltime"

    q = db.query(CubesweeperScore).filter(
        CubesweeperScore.cube_mode == cube_mode,
        CubesweeperScore.no_guess  == no_guess,
    )
    q = exclude_flagged(q, CubesweeperScore, db)

    if period == "daily":
        try:
            target = date.fromisoformat(score_date) if score_date else date.today()
        except ValueError:
            target = date.today()
        q = q.filter(CubesweeperScore.created_at >= target,
                     CubesweeperScore.created_at < target + timedelta(days=1))
        top = q.order_by(CubesweeperScore.time_ms.asc(),
                         CubesweeperScore.created_at.asc()).limit(20).all()
        return [s.to_dict() for s in top]

    raw = q.order_by(CubesweeperScore.time_ms.asc(),
                     CubesweeperScore.created_at.asc()).limit(500).all()
    seen: set = set()
    top:  list = []
    for s in raw:
        key = s.user_email or s.name
        if key not in seen:
            seen.add(key)
            top.append(s.to_dict())
            if len(top) >= 20:
                break
    return top


# ── MobiusSweeper ─────────────────────────────────────────────────────────────

MOBIUSSWEEPER_MODES = {
    "beginner":     {"width":  4, "length":  40, "mines":  16},
    "intermediate": {"width":  8, "length":  80, "mines":  64},
    "expert":       {"width": 16, "length": 160, "mines": 256},
}
MOBIUS_MODES_VALID = {"beginner", "intermediate", "expert"}


@globesweeper_router.get("/minesweeperchess", response_class=HTMLResponse)
async def minesweeperchess(request: Request):
    return templates.TemplateResponse(request, "minesweeperchess.html", {
        "mode": "minesweeperchess",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "page_localized": False,
    })


@globesweeper_router.get("/mobiussweeper", response_class=HTMLResponse)
async def mobiussweeper_beginner(request: Request):
    m = MOBIUSSWEEPER_MODES["beginner"]
    return templates.TemplateResponse(request, "mobiussweeper.html", {
        "mode": "beginner",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@globesweeper_router.get("/mobiussweeper/intermediate", response_class=HTMLResponse)
async def mobiussweeper_intermediate(request: Request):
    m = MOBIUSSWEEPER_MODES["intermediate"]
    return templates.TemplateResponse(request, "mobiussweeper.html", {
        "mode": "intermediate",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@globesweeper_router.get("/mobiussweeper/expert", response_class=HTMLResponse)
async def mobiussweeper_expert(request: Request):
    m = MOBIUSSWEEPER_MODES["expert"]
    return templates.TemplateResponse(request, "mobiussweeper.html", {
        "mode": "expert",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@globesweeper_router.get("/mobiussweeper/leaderboard", response_class=HTMLResponse)
async def mobiussweeper_leaderboard(request: Request):
    return templates.TemplateResponse(request, "mobiussweeper_leaderboard.html", {
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


class MobiussweeperScoreSubmit(BaseModel):
    name:        str           = Field(..., min_length=1, max_length=32)
    mobius_mode: str           = Field(..., pattern="^(beginner|intermediate|expert)$")
    width:       int           = Field(..., ge=1, le=64)
    length:      int           = Field(..., ge=4, le=512)
    time_ms:     int           = Field(..., ge=1, le=7_200_000)
    mines:       int           = Field(..., ge=1)
    no_guess:    bool          = False
    bbbv:         Optional[int] = Field(None, ge=1, le=999999)
    left_clicks:  Optional[int] = Field(None, ge=0, le=9999999)
    chord_clicks: Optional[int] = Field(None, ge=0, le=99999)
    board_hash:   Optional[str] = Field(None, max_length=512)

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
        width  = info.data.get("width")
        length = info.data.get("length")
        if width and length and v >= width * length:
            raise ValueError("Too many mines for this board size")
        return v


@globesweeper_router.post("/api/mobiussweeper-scores", status_code=201)
@limiter.limit("10/minute")
def submit_mobius_score(payload: MobiussweeperScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    guest_token = get_or_create_guest_token(request, user)
    entry = MobiussweeperScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        mobius_mode = payload.mobius_mode,
        width       = payload.width,
        length      = payload.length,
        time_ms     = payload.time_ms,
        mines       = payload.mines,
        no_guess    = payload.no_guess,
        bbbv         = payload.bbbv,
        left_clicks  = payload.left_clicks,
        chord_clicks = payload.chord_clicks,
        board_hash   = payload.board_hash,
        guest_token  = guest_token,
        client_type  = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    flag_if_profane(db, entry.__tablename__, entry.id, entry.name)
    return {"ok": True, "id": entry.id}


@globesweeper_router.get("/api/mobiussweeper-scores/{mobius_mode}")
def get_mobius_scores(mobius_mode: str, period: str = "alltime",
                      no_guess: bool = False,
                      score_date: Optional[str] = Query(None, alias="date"),
                      db: Session = Depends(get_db)):
    if mobius_mode not in MOBIUS_MODES_VALID:
        raise HTTPException(status_code=400, detail="Invalid mode")
    if period not in ("daily", "alltime"):
        period = "alltime"

    q = db.query(MobiussweeperScore).filter(
        MobiussweeperScore.mobius_mode == mobius_mode,
        MobiussweeperScore.no_guess    == no_guess,
    )
    q = exclude_flagged(q, MobiussweeperScore, db)

    if period == "daily":
        try:
            target = date.fromisoformat(score_date) if score_date else date.today()
        except ValueError:
            target = date.today()
        q = q.filter(MobiussweeperScore.created_at >= target,
                     MobiussweeperScore.created_at < target + timedelta(days=1))
        top = q.order_by(MobiussweeperScore.time_ms.asc(),
                         MobiussweeperScore.created_at.asc()).limit(20).all()
        return [s.to_dict() for s in top]

    raw = q.order_by(MobiussweeperScore.time_ms.asc(),
                     MobiussweeperScore.created_at.asc()).limit(500).all()
    seen: set = set()
    top:  list = []
    for s in raw:
        key = s.user_email or s.name
        if key not in seen:
            seen.add(key)
            top.append(s.to_dict())
            if len(top) >= 20:
                break
    return top
