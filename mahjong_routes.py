"""
mahjong_routes.py — Page and API route handlers for Mahjong Solitaire.
Mount this router in main.py with: app.include_router(mahjong_router)
"""
import os, json, uuid, re as _re
from datetime import date
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from better_profanity import profanity as _profanity_checker

from database import (
    FlaggedScore, UserProfile, GameReplay,
    MahjongScore,
    get_db,
)
from auth import get_current_user
from translations import get_lang, get_t, SUPPORTED_LANGS
import settings as site_settings
from quest_catalog import quest_config
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs

mahjong_router = APIRouter()
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


# ── Mahjong Solitaire ─────────────────────────────────────────────────────────

_MAH_INDEX_PATH     = os.path.join("static", "mah", "index.html")
_MAH_TURTLE_BOARD   = "2175883231"  # Turtle layout — fixed daily board
_MAH_INDEX_CACHE: str | None = None

# Map minesweeper.org lang codes → mah lang codes (only differences listed)
_MAH_LANG_MAP: dict[str, str] = {"zh-hant": "zh", "tl": "fil"}
# mah supports these lang codes (from ffalt/mah languages.ts)
_MAH_VALID_LANGS: frozenset[str] = frozenset({
    "ar","bn","ca","cs","da","de","el","es","eu","fa","fi","fil","fr",
    "hi","hu","id","it","ja","ko","ms","nl","no","pl","pt","ro","ru",
    "sv","sw","ta","te","th","tr","uk","ur","vi","zh",
})
# Pre-built map: site-lang → mahjong-lang, only for langs the mah app actually supports.
# Dict values are compile-time constants; lookup result is untainted by request data.
_MAH_LANG_SAFE: dict[str, str] = {
    sl: ml
    for sl in SUPPORTED_LANGS
    for ml in [_MAH_LANG_MAP.get(sl, sl)]
    if ml in _MAH_VALID_LANGS
}


def _mah_response(lang: str) -> HTMLResponse:
    global _MAH_INDEX_CACHE
    if not os.path.isfile(_MAH_INDEX_PATH):
        raise HTTPException(status_code=503, detail="Game not yet deployed")
    if _MAH_INDEX_CACHE is None:
        with open(_MAH_INDEX_PATH, encoding="utf-8") as f:
            _MAH_INDEX_CACHE = f.read()
    # safe_lang comes from a pre-built dict (untainted). lang_code is derived
    # from safe_lang only, so it carries no taint from the request parameter.
    # mah_lang is then looked up by lang_code (untainted key) — no user data
    # reaches the HTML injection below.
    safe_lang = _LANG_PREFIX_MAP.get(lang, "")  # "" for "en" or unrecognised codes
    lang_code = safe_lang[1:] if safe_lang else ""  # untainted: derived from dict value only
    mah_lang  = _MAH_LANG_SAFE.get(lang_code) if lang_code else None
    content = _MAH_INDEX_CACHE
    if lang_code:
        content = content.replace(
            '<base href="/other/mahjong/">',
            f'<base href="/{lang_code}/other/mahjong/">',
            1,
        )
    # The Angular app reads ?board=... client-side — the server sends identical
    # markup for every board value, so without a canonical tag Google indexes
    # every ?board= permutation as its own "duplicate" page (GSC: "Duplicate
    # without user-selected canonical"). canonical_url is built from lang_code
    # only (untainted, see above) and never includes the query string.
    canonical_url = f"https://minesweeper.org/{lang_code}/other/mahjong/" if lang_code else "https://minesweeper.org/other/mahjong/"
    content = content.replace(
        '<meta property="og:url" content>',
        f'<meta property="og:url" content="{canonical_url}">\n\t<link rel="canonical" href="{canonical_url}">',
        1,
    )
    if mah_lang:
        # Inject before </head> — runs synchronously before Angular's type="module" scripts
        inject = (
            "<script>(function(){try{var s=JSON.parse(localStorage.getItem('mah.settings')||'{}');"
            f"if(!s.lang||s.lang==='auto'){{s.lang={json.dumps(mah_lang)};"
            "localStorage.setItem('mah.settings',JSON.stringify(s))}}"
            "catch(e){}})();</script>"
        )
        content = content.replace("</head>", inject + "\n</head>", 1)
    return HTMLResponse(content=content)


@mahjong_router.get("/other/mahjong", response_class=HTMLResponse)
def mahjong_landing(request: Request):
    return _mah_response(get_lang(request))


@mahjong_router.get("/other/mahjong/daily")
def mahjong_daily_page(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/other/mahjong/?board={_MAH_TURTLE_BOARD}"), status_code=302)


@mahjong_router.get("/other/mahjong/")
def mahjong_game_root(request: Request):
    return _mah_response(get_lang(request))


@mahjong_router.get("/other/mahjong/leaderboard", response_class=HTMLResponse)
def mahjong_leaderboard_page(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse(request, "mj_leaderboard.html", {
        "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today,
    })


@mahjong_router.get("/other/mahjong/how-to-play", response_class=HTMLResponse)
def mahjong_howtoplay_page(request: Request):
    return templates.TemplateResponse(request, "mj_howtoplay.html", {
        "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@mahjong_router.get("/other/mahjong/{path:path}")
def mahjong_game_static(path: str):
    safe_base = os.path.realpath(os.path.join("static", "mah"))
    resolved = os.path.realpath(os.path.join("static", "mah", path))
    if resolved.startswith(safe_base + os.sep) and os.path.isfile(resolved):
        return FileResponse(resolved)
    return FileResponse(_MAH_INDEX_PATH)


_UUID_RE = _re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', _re.IGNORECASE)

class MahjongScoreSubmit(BaseModel):
    name:        str = Field(..., min_length=1, max_length=32)
    puzzle_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    board_hash:  str = Field(..., min_length=4, max_length=200)
    time_ms:     int = Field(..., ge=0, le=99999999)
    guest_token: Optional[str] = Field(None, min_length=36, max_length=36)
    device_type: Optional[str] = Field(None, pattern=r'^(ios|android|web)$')
    device_id:   Optional[str] = Field(None, min_length=36, max_length=36)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable())
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]

    @field_validator("board_hash")
    @classmethod
    def sanitize_hash(cls, v: str) -> str:
        import re
        v = v.strip()
        if not re.match(r'^[A-Za-z0-9_\-=+/]{4,200}$', v):
            raise ValueError("Invalid board hash")
        return v

    @field_validator("guest_token", "device_id")
    @classmethod
    def validate_uuid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _UUID_RE.match(v):
            raise ValueError("Must be a valid UUID v4")
        return v


@mahjong_router.post("/api/mahjong-scores", status_code=201)
@limiter.limit("10/minute")
def submit_mahjong_score(payload: MahjongScoreSubmit, request: Request, db: Session = Depends(get_db)):
    from telemetry import record_score_submit, record_game_complete
    user = get_current_user(request)
    if not user:
        if payload.guest_token:
            guest_token = payload.guest_token
        else:
            if "guest_token" not in request.session:
                request.session["guest_token"] = str(uuid.uuid4())
            guest_token = request.session["guest_token"]
    else:
        guest_token = None
    entry = MahjongScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        puzzle_date = payload.puzzle_date,
        board_hash  = payload.board_hash,
        time_ms     = payload.time_ms,
        guest_token = guest_token,
        client_type = get_client_type(request),
        device_type = payload.device_type,
        device_id   = payload.device_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    flag_if_profane(db, entry.__tablename__, entry.id, entry.name)
    record_score_submit("mahjong", payload.puzzle_date)
    record_game_complete("mahjong", mode="daily", duration_ms=payload.time_ms)
    return {"ok": True, "id": entry.id}


@mahjong_router.get("/api/mahjong-scores")
def get_mahjong_scores(
    request: Request,
    puzzle_date: Optional[str] = Query(None, alias="date", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    season: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    all_time: Optional[bool] = Query(None, alias="all"),
    db: Session = Depends(get_db),
):
    LIMIT = 20
    if puzzle_date:
        q = db.query(MahjongScore).filter(MahjongScore.puzzle_date == puzzle_date)
        q = exclude_flagged(q, MahjongScore, db)
        top = q.order_by(MahjongScore.time_ms.asc(), MahjongScore.created_at.asc()).limit(LIMIT).all()
    elif season:
        year, month = season.split("-")
        prefix = f"{year}-{month}"
        q = db.query(MahjongScore).filter(MahjongScore.puzzle_date.like(f"{prefix}%"))
        q = exclude_flagged(q, MahjongScore, db)
        top = q.order_by(MahjongScore.time_ms.asc(), MahjongScore.created_at.asc()).limit(LIMIT).all()
    else:
        q = db.query(MahjongScore)
        q = exclude_flagged(q, MahjongScore, db)
        top = q.order_by(MahjongScore.time_ms.asc(), MahjongScore.created_at.asc()).limit(LIMIT).all()
    return _enrich_with_profiles(top, db)
