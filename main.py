import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"authlib\.integrations\.httpx_client")

from datetime import date, timedelta, datetime, timezone
from zoneinfo import ZoneInfo
from urllib.parse import quote, urlparse
import json
import uuid
import re
import subprocess
import os
import hashlib
import fcntl
from typing import Optional
from fastapi import FastAPI, Request, Depends, HTTPException, Query, Response, Form, File, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.gzip import GZipMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, case, text, cast, Date as SQLDate
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field, field_validator
from countries import COUNTRIES as ALL_COUNTRIES, VALID_COUNTRY_CODES
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from database import Score, GameHistory, GameMode, RushScore, TentaizuScore, TentaizuEasyScore, MosaicScore, MosaicEasyScore, MosaicCustomScore, CylinderScore, ToroidScore, HexsweeperScore, GlobesweeperScore, CubesweeperScore, MobiussweeperScore, ReplayScore, UserProfile, PvpResult, ServerStats, WebTrafficStats, GuestScoreArchive, BlogComment, NonosweeperScore, ContactMessage, FifteenPuzzleScore, FifteenPuzzlePhoto, MemberPuzzle, Game2048Score, Game2048HexScore, MahjongScore, MahjongSavedGame, JigsawScore, JigsawSavedGame, JigsawPhoto, SchulteGridScore, SudokuScore, GameReplay, FlaggedScore, TametsiBoard, TametsiDaily, TametsiScore, NumbersMatchDaily, NumbersMatchScore, EvilGameSession, Pattern, PatternRevision, UserRole, TametsiHexCompletion, TametsiHexTime, TametsiHexUserBoard, SeoRanking, MeowdokuScore, MeowdokuSavedPuzzle, WC2026Score, get_db, init_db, SessionLocal
import seo_checker
from phase2_analyzer import analyze_replay_async
# Near the top of main.py with the other model imports
from phase2_analyzer import GameAnalysis
from tametsi_generator import (
    generate_daily as _tametsi_generate_daily,
    generate_board as _tametsi_generate_board,
    daily_rng as _tametsi_daily_rng,
    LEVELS as _TAMETSI_LEVELS,
)
from numbers_match_generator import generate_daily as _nm_generate_daily
import database as _db_module
from duel_routes import duel_router
from duelold_routes import duelold_router
from admin_routes import admin_router, require_user, user_has_role, require_admin, ADMIN_EMAILS, _PATTERN_SECTIONS
from tametsi_routes import tametsi_router
from blog_routes import blog_router, BLOG_POSTS
from mahjong_routes import mahjong_router
from jigsaw_routes import jigsaw_router
from mosaic_routes import mosaic_router
from cylinder_routes import cylinder_router
from hexsweeper_routes import hexsweeper_router
from globesweeper_routes import globesweeper_router
from numbers_match_routes import numbers_match_router
from sudoku_routes import sudoku_router
from schulte_routes import schulte_router
from meowdoku_routes import meowdoku_router
from game2048_routes import game2048_router
from fifteen_puzzle_routes import fifteen_puzzle_router
from tentaizu_leaderboard_routes import tentaizu_leaderboard_router
from nonosweeper_routes import nonosweeper_router
from pvp_leaderboard_routes import pvp_leaderboard_router
from wc2026_routes import wc2026_router, WC2026_TEAMS
from speff_routes import speff_router
from wc2026_data import WC2026_COUNTRIES, VALID_WC2026_SLUGS
from duel import cleanup_old_games
from auth import oauth, get_current_user, set_session_user, clear_session, SECRET_KEY
from starlette.config import Config
from translations import get_lang, get_t, SUPPORTED_LANGS, REAL_LANGS, FUN_LANGS, TRANSLATIONS
from game_catalog import LEADERBOARD_GROUPS, PUZZLE_GAMES
from leaderboard_platform import leaderboard_cards, leaderboard_catalog, leaderboard_rows
from quest_catalog import quest_config
import settings as site_settings
import logging
import psutil
import threading
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from better_profanity import profanity as _profanity_checker

logger = logging.getLogger(__name__)

# ── Profanity helpers ─────────────────────────────────────────────────────────
# Maps every score table name → its SQLAlchemy model, used to resolve the
# actual score row when deleting a flagged entry.
_SCORE_TABLE_MAP: dict = {}  # populated after all models are imported (below)

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


def _build_score_table_map():
    """Build the table-name → model mapping once all models are imported."""
    global _SCORE_TABLE_MAP
    _SCORE_TABLE_MAP = {
        m.__tablename__: m for m in [
            Score, RushScore, TentaizuScore, TentaizuEasyScore,
            MosaicScore, MosaicEasyScore, MosaicCustomScore,
            CylinderScore, ToroidScore, HexsweeperScore, GlobesweeperScore,
            CubesweeperScore, MobiussweeperScore, ReplayScore,
            NonosweeperScore, FifteenPuzzleScore, Game2048Score,
            Game2048HexScore, SchulteGridScore, SudokuScore,
            MahjongScore, JigsawScore, NumbersMatchScore,
        ]
    }

_build_score_table_map()


# ── Season constants (Season 1 = March 2026, increments monthly) ──────────────
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

# ── Request counter (for hourly stats) ───────────────────────────────────────
_req_lock  = threading.Lock()
_req_count = 0

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Minesweeper")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── OpenTelemetry — AWS Bedrock observability ─────────────────────────────────
from telemetry import (
    setup_telemetry,
    record_score_submit,
    record_game_complete,
    record_duel_delta,
    record_scheduler_run,
    record_db_error,
)
setup_telemetry(app, db_engine=_db_module.engine)

# F96 — Analytics API (Phase 4)
import os
if os.environ.get("ENABLE_ANALYTICS_API", "true").lower() == "true":
    from phase4_routes import router as analytics_router
    from phase7_drills import api_router as drills_api_router, page_router as drills_page_router
    app.include_router(analytics_router)
    app.include_router(drills_api_router)
    app.include_router(drills_page_router)

@app.middleware("http")
async def count_requests(request: Request, call_next):
    global _req_count
    with _req_lock:
        _req_count += 1
    return await call_next(request)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # ── Content-Security-Policy ────────────────────────────────────────────────
    # Note: 'unsafe-inline' is required for script-src and style-src because the
    # codebase uses many inline <script> blocks (gtag, translations, nav handlers,
    # per-page init calls) and dynamic style injection (ad-disable feature).
    # Inline scripts mean injected <script>…</script> tags cannot be blocked by CSP
    # alone; however, restricting script-src to known domains still blocks loading
    # scripts from arbitrary external origins.  The correct long-term fix is to
    # add per-request nonces to every inline <script> and remove 'unsafe-inline'.
    csp = "; ".join([
        "default-src 'self'",
        (
            "script-src 'self' 'unsafe-inline'"
            " https://pagead2.googlesyndication.com"
            " https://www.googletagmanager.com"
            " https://cdn.jsdelivr.net"
            " https://fundingchoicesmessages.google.com"
            " https://*.adtrafficquality.google"
        ),
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        (
            "img-src 'self' data: blob:"
            " https://lh3.googleusercontent.com"
            " https://*.googlesyndication.com"
            " https://*.doubleclick.net"
            " https://www.googletagmanager.com"
            " https://www.google-analytics.com"
            " https://*.adtrafficquality.google"
            " https://flagcdn.com"
        ),
        # 'self' covers same-origin WebSockets (wss://minesweeper.org/ws/…)
        # Broad Google/AdSense domains — bidding partners use many subdomains
        # adtrafficquality.google is Google's SODAR viewability/fraud system (not a *.google.com subdomain)
        (
            "connect-src 'self'"
            " https://www.google-analytics.com"
            " https://region1.google-analytics.com"
            " https://*.googlesyndication.com"
            " https://*.doubleclick.net"
            " https://*.google.com"
            " https://*.googleadservices.com"
            " https://*.googlevideo.com"
            " https://*.adtrafficquality.google"
            " https://csi.gstatic.com"
        ),
        # AdSense renders ad creatives inside iframes from these domains
        # ep2.adtrafficquality.google = Google's ad fraud/viewability system (SODAR)
        # www.google.com = required by some AdSense creatives
        (
            "frame-src"
            " https://googleads.g.doubleclick.net"
            " https://tpc.googlesyndication.com"
            " https://ep2.adtrafficquality.google"
            " https://www.google.com"
        ),
        # Block all plugin-based content (Flash, Java applets, etc.)
        "object-src 'none'",
        # Prevent <base> tag injection from redirecting relative URLs
        "base-uri 'self'",
        # Prevent forms from submitting to external sites
        "form-action 'self'",
        # Prevent this page from being embedded in external frames (clickjacking)
        "frame-ancestors 'self'",
    ])
    response.headers["Content-Security-Policy"] = csp
    # Prevent MIME-type sniffing (e.g. serving a JS file as text/html)
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Legacy clickjacking protection for older browsers that ignore frame-ancestors
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    # Limit referrer information sent on cross-origin navigation
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Disable browser features this site doesn't use
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=(), "
        "accelerometer=*, gyroscope=*"
    )
    return response


@app.middleware("http")
async def csrf_xhr_check(request: Request, call_next):
    """Require X-Requested-With: XMLHttpRequest OR Content-Type: application/json
    on all /api/ POST requests.  Cross-origin fetch() cannot set custom headers
    without a CORS preflight, and application/json also triggers a preflight,
    so both forms are unforgeable by third-party pages.
    """
    if request.method == "POST" and request.url.path.startswith("/api/"):
        is_xhr  = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        is_json = request.headers.get("Content-Type", "").startswith("application/json")
        if not (is_xhr or is_json):
            return JSONResponse({"detail": "CSRF check failed"}, status_code=403)
    return await call_next(request)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="127.0.0.1")
app.include_router(duel_router)
app.include_router(duelold_router)
app.include_router(admin_router)
app.include_router(tametsi_router)
app.include_router(blog_router)
app.include_router(mahjong_router)
app.include_router(jigsaw_router)
app.include_router(mosaic_router)
app.include_router(cylinder_router)
app.include_router(hexsweeper_router)
app.include_router(globesweeper_router)
app.include_router(numbers_match_router)
app.include_router(sudoku_router)
app.include_router(schulte_router)
app.include_router(meowdoku_router)
app.include_router(game2048_router)
app.include_router(fifteen_puzzle_router)
app.include_router(tentaizu_leaderboard_router)
app.include_router(nonosweeper_router)
app.include_router(pvp_leaderboard_router)
app.include_router(wc2026_router)
app.include_router(speff_router)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, https_only=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.globals["ga_tag"]          = Config(".env")("GA_TAG", default="")
templates.env.globals["twitter_handle"]  = Config(".env")("TWITTER_HANDLE", default="")
templates.env.globals["DEFAULT_SKIN"]   = site_settings.DEFAULT_SKIN
templates.env.globals["active_skin"]     = site_settings.active_skin
templates.env.globals["solstice_banner"]       = site_settings.solstice_banner
templates.env.globals["equinox_banner"]        = site_settings.equinox_banner
templates.env.globals["diana_birthday_banner"] = site_settings.diana_birthday_banner
templates.env.globals["mexico_banner"]         = site_settings.mexico_banner
templates.env.globals["is_mexico_cinco"]       = site_settings.is_mexico_cinco
templates.env.globals["is_mexico_independence"] = site_settings.is_mexico_independence
templates.env.globals["page_localized"]        = True  # default; English-only routes override to False
templates.env.globals["FUN_LANGS"]            = FUN_LANGS

def _autolink(text):
    """Jinja2 filter: HTML-escape text then wrap bare URLs in <a> tags."""
    import re
    from markupsafe import Markup, escape
    if not text:
        return Markup('')
    safe = str(escape(text))
    def _replace(m):
        url = m.group(0)
        # Strip trailing punctuation that's unlikely to be part of the URL
        while url and url[-1] in '.,;:!?)]\'\"':
            url = url[:-1]
        return '<a href="{u}" target="_blank" rel="noopener noreferrer">{u}</a>'.format(u=url)
    return Markup(re.sub(r'https?://[^\s<>"\'\x00-\x1f]+', _replace, safe))  # nosec B704 — input already HTML-escaped via markupsafe.escape above

templates.env.filters['autolink'] = _autolink

# ── BreadcrumbList structured data ───────────────────────────────────────────
# Maps URL path → list of (name, relative-path) pairs for crumb levels 2+.
# Home is always level 1 and is prepended automatically.
# Blog post detail pages (/blog/<slug>) are intentionally absent — blog_post.html
# provides its own 3-level override that includes the post title.
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs

templates.env.globals["get_breadcrumbs"] = _get_breadcrumbs
templates.env.globals["quest_config"] = quest_config
templates.env.globals["puzzle_games"] = PUZZLE_GAMES

# ── A/B default: no-guess mode split by IP ────────────────────────────────────
def _ng_default_from_ip(request: Request) -> bool:
    """Return True (no-guess) for ~half of first-time visitors via last bit of IP.
    Deterministic per IP so the same user consistently gets the same default.
    NOTE: if a CDN or shared-cache layer is ever added in front of these routes,
    per-IP HTML content will conflict with shared caching — revisit at that time."""
    ip = (request.client.host if request.client else "") or ""
    try:
        if ":" in ip:
            # IPv6 — last segment may be an IPv4 quad (e.g. ::ffff:192.168.1.1)
            last = ip.rstrip(":").rsplit(":", 1)[-1]
            if "." in last:
                return bool(int(last.rsplit(".", 1)[1]) & 1)
            return bool(int(last or "0", 16) & 1)
        return bool(int(ip.rsplit(".", 1)[1]) & 1)
    except (ValueError, IndexError):
        return False


# ── Redirect safety helpers ──────────────────────────────────────────────────
_LANG_CODE_RE = re.compile(r'^[a-z]{2,10}(?:-[a-z]{2,10})?$')

_LANG_PREFIX_MAP: dict[str, str] = {lang: f"/{lang}" for lang in SUPPORTED_LANGS if lang != "en"}

def _safe_lang_prefix(lang: str) -> str:
    """Return /{lang} for supported non-English languages, "" otherwise.
    Dict lookup from pre-built constants breaks CodeQL's taint trace."""
    return _LANG_PREFIX_MAP.get(lang, "")

def _safe_relative_url(url: str, fallback: str = "/") -> str:
    """Reject URLs that carry a scheme or netloc (open-redirect guard).
    urlparse is recognised by CodeQL as a URL sanitizer.

    Also rejects any backslash: per the WHATWG URL spec, browsers treat \\
    as equivalent to / for special schemes (http/https/ws/wss/ftp/file), so
    "/\\evil.com" parses via urlparse as a harmless relative path (empty
    netloc) but browsers resolve it as //evil.com — a protocol-relative
    redirect to another origin. urlparse doesn't know about this browser
    quirk, so it can't be caught by the scheme/netloc check above."""
    if "\\" in url:
        return fallback
    if url.startswith("//"):
        # "///evil.com" fools urlparse (empty netloc) but still resolves as
        # protocol-relative in browsers — reject any double-leading-slash.
        return fallback
    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc:
        return fallback
    return url

# Pre-computed map of language code → URL path prefix.
# Values are derived from SUPPORTED_LANGS at import time, never from user input,
# so dict lookups below cannot produce attacker-controlled redirect targets.
_LANG_URL_PREFIX: dict[str, str] = {
    lang: (f"/{lang}" if lang != "en" else "") for lang in SUPPORTED_LANGS
}

# ── Language-prefix middleware ────────────────────────────────────────────────
# Registered last → runs outermost (first) for every request.
# Responsibilities:
#   1. Record the original path in request.state.original_path (used by the
#      auth ?next= link in base.html so post-login returns to the lang URL).
#   2. Redirect legacy ?lang=XX query-param URLs to path-based equivalents
#      with 301 so search engines update their index entries.
#   3. Strip the /{lang}/ prefix from the scope path so all existing route
#      handlers see bare paths unchanged, then store the lang code in
#      request.state.lang where get_lang() picks it up.
@app.middleware("http")
async def lang_prefix_middleware(request: Request, call_next):
    path = request.scope["path"]  # read from scope to avoid caching request.url

    _SKIP = ("/api/", "/static/", "/auth/", "/ws/", "/admin/",
             "/health", "/set-lang", "/sitemap", "/robots",
             "/favicon", "/ads.txt", "/app-ads.txt", "/.well-known/")
    if any(path.startswith(p) for p in _SKIP):
        return await call_next(request)

    # ── Redirect lang subdomains (e.g. de.minesweeper.org) → /{lang} path (301) ──
    # These subdomains proxy into this same app (see get_lang()'s subdomain
    # fallback below) and were serving live duplicate content with nothing but
    # a canonical tag pointing elsewhere — GSC flagged this as weaker than a
    # real redirect. Absolute URL is built with a hardcoded https://minesweeper.org
    # origin, so this can't be turned into an open redirect by request data.
    host = request.headers.get("host", "").split(":")[0]
    host_parts = host.split(".")
    if len(host_parts) >= 3 and host_parts[0] in SUPPORTED_LANGS and host_parts[0] != "en":
        subdomain_lang = host_parts[0]
        qs = request.url.query
        redirect_path = f"/{subdomain_lang}" + ("" if path == "/" else path)
        redirect_url = f"https://minesweeper.org{redirect_path}" + (f"?{qs}" if qs else "")
        return RedirectResponse(url=redirect_url, status_code=301)

    request.state.original_path = path  # pre-rewrite; used by auth ?next= link

    # ── Redirect ?lang=XX → /{lang}/path (301) ────────────────────────────────
    lang_param = request.query_params.get("lang")
    if lang_param:
        other_qs = "&".join(
            f"{k}={v}" for k, v in request.query_params.items() if k != "lang"
        )
        if lang_param in SUPPORTED_LANGS and lang_param != "en":
            new_path = f"/{lang_param}" + ("" if path == "/" else path)
            redirect_url = new_path + (f"?{other_qs}" if other_qs else "")
            return RedirectResponse(url=_safe_relative_url(redirect_url), status_code=301)
        elif lang_param == "en":
            # path is the raw request path (request.scope["path"]) — fully
            # attacker-controlled, unlike the branch above which always has
            # a fixed "/{lang_param}" prefix. Must go through the
            # open-redirect guard before being used as a redirect target.
            redirect_url = path + (f"?{other_qs}" if other_qs else "")
            return RedirectResponse(url=_safe_relative_url(redirect_url), status_code=301)

    # ── Strip /{lang}/ prefix and rewrite scope path ──────────────────────────
    parts = path.lstrip("/").split("/", 1)
    if parts and parts[0] in SUPPORTED_LANGS and parts[0] != "en":
        lang_code = parts[0]
        bare_path = "/" + (parts[1] if len(parts) > 1 else "")
        if bare_path == "//":
            bare_path = "/"
        # Redirect /{lang}/ → /{lang} to avoid trailing-slash duplicate content
        if bare_path == "/" and path.endswith("/"):
            return RedirectResponse(url=f"/{lang_code}", status_code=301)
        request.state.lang = lang_code
        request.scope["path"] = bare_path
        request.scope["raw_path"] = bare_path.encode("utf-8")

    return await call_next(request)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse(
        request,
        "404.html",
        {"mode": "404",
         "user": get_current_user(request),
         "lang": get_lang(request), "t": get_t(request)},
        status_code=404,
    )

@app.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    return templates.TemplateResponse(
        request,
        "403.html",
        {"mode": "403",
         "user": get_current_user(request),
         "lang": get_lang(request), "t": get_t(request)},
        status_code=403,
    )

# ── SEO: robots.txt and sitemap ───────────────────────────────────────────────
@app.get("/.well-known/apple-app-site-association", include_in_schema=False)
async def apple_app_site_association():
    from fastapi.responses import JSONResponse
    return JSONResponse(content={
        "applinks": {
            "details": [{
                "appIDs": ["JGY24WS6U2.karching.Driver-Education"],
                "components": [{
                    "/": "/cpartners/*",
                    "comment": "Matches any URL whose path starts with /stock/"
                }]
            }]
        }
    })


@app.get("/a5d8abb456594f019c6c89a7d9420d5c.txt", include_in_schema=False)
async def domain_verification():
    return PlainTextResponse("a5d8abb456594f019c6c89a7d9420d5c")

@app.get("/d6f2e20789ed4fd28401bd6975a9fb56.txt", include_in_schema=False)
async def domain_verification_2():
    return PlainTextResponse("d6f2e20789ed4fd28401bd6975a9fb56")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import FileResponse
    return FileResponse("static/favicon.svg", media_type="image/svg+xml")


@app.get("/apple-touch-icon.png", include_in_schema=False)
@app.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
async def apple_touch_icon():
    from fastapi.responses import FileResponse
    return FileResponse("static/img/minesweeper-org-logo.png", media_type="image/png")


@app.get("/robots.txt", include_in_schema=False)
async def robots():
    content = (
        "User-agent: *\n"
        "Allow: /\n\n"
        "Disallow: /game/\n"
        "Disallow: /duel/room/\n"
        "Disallow: /api/\n"
        "Disallow: /ws/\n"
        "Disallow: /auth/\n"
        "Disallow: /login\n"
        "Disallow: /logout\n"
        "Disallow: /register\n"
        "Disallow: /account/\n"
        "Disallow: /static/\n"
        "Disallow: /health\n\n"
        "Sitemap: https://minesweeper.org/sitemap.xml\n"
    )
    return PlainTextResponse(content)

_ENVIRONMENT = Config(".env")("ENVIRONMENT", default="unknown")

@app.get("/health", include_in_schema=False)
async def health(request: Request):
    if request.client.host not in ("127.0.0.1", "::1"):
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            text=True,
            timeout=3,
        ).strip()
    except Exception:
        commit = "unknown"
    return JSONResponse({"status": "ok", "commit": commit, "environment": _ENVIRONMENT})

@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap(request: Request, db: Session = Depends(get_db)):
    published_patterns = (
        db.query(Pattern)
        .filter(Pattern.status == "published")
        .order_by(Pattern.slug)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "sitemap.xml",
        {"today": date.today().isoformat(),
         "blog_posts": BLOG_POSTS, "sitemap_langs": sorted(REAL_LANGS),
         "wc2026_countries": WC2026_COUNTRIES,
         "published_patterns": published_patterns},
        media_type="application/xml",
    )

@app.get("/ads.txt", include_in_schema=False)
async def ads_txt():
    return FileResponse("ads.txt", media_type="text/plain")

@app.get("/app-ads.txt", include_in_schema=False)
async def app_ads_txt():
    return FileResponse("app-ads.txt", media_type="text/plain")

@app.get("/iamatestfile.txt", include_in_schema=False)
async def iamatestfile_txt():
    return PlainTextResponse("healthy")

@app.get("/business/Richard_Cross_Resume.docx", include_in_schema=False)
async def richard_cross_resume():
    return FileResponse(
        "business/Richard_Cross_Resume.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="Richard_Cross_Resume.docx",
    )

GAME_MODES = {
    "beginner":     {"rows": 9, "cols": 9, "mines": 10},
    "intermediate": {"rows": 16, "cols": 16, "mines": 40},
    "expert":       {"rows": 30, "cols": 16, "mines": 99},
}

EVIL_NG_MODE = {"rows": 20, "cols": 30, "mines": 130}

_ANALYSIS_DIR      = os.path.realpath(os.path.join(os.path.dirname(__file__), "analysis"))
_ANALYSIS_EXTS     = {".ts", ".py", ".js", ".pptx", ".docx", ".doc"}

ARCHIVE_MODES = {"beginner", "intermediate", "expert"}

def _round_or_none(value, decimals: int):
    """Round a Decimal/float to N places, or return None if input is None/NaN."""
    if value is None:
        return None
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return None


def _mask_email(player_id: str | None) -> str:
    """Mask an email or guest-token for admin display.
       'richard.cross@enlyt.io' → 'r******s@enlyt.io'
       'abc-uuid-token-...'     → 'abc-...token'"""
    if not player_id:
        return "anonymous"
    if "@" in player_id:
        local, _, domain = player_id.partition("@")
        if len(local) <= 2:
            masked_local = local[0] + "*"
        else:
            masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
        return f"{masked_local}@{domain}"
    if len(player_id) > 12:
        return f"{player_id[:8]}…{player_id[-4:]}"
    return player_id

def get_or_create_guest_token(request: Request, user: dict | None) -> str | None:
    """Return the session guest token for unauthenticated requests, None for signed-in users."""
    if user:
        return None
    if "guest_token" not in request.session:
        request.session["guest_token"] = str(uuid.uuid4())
    return request.session["guest_token"]


# ── Client type detection ─────────────────────────────────────────────────────
def get_client_type(request: Request) -> str:
    """
    Derive client type from request headers.
    Apps identify themselves via X-Client-Type: ios_app | android_app.
    Browsers are classified by User-Agent; mobile browsers get 'mobile_browser'.
    Historical / unrecognised clients return 'na'.
    """
    explicit = request.headers.get("X-Client-Type", "").lower().strip()
    if explicit in ("ios_app", "android_app"):
        return explicit

    ua = request.headers.get("User-Agent", "").lower()
    if not ua:
        return "na"

    # Mobile UA check must come before browser-name checks (Chrome/Safari appear in mobile UAs too)
    if any(kw in ua for kw in ("mobi", "android", "iphone", "ipad", "ipod")):
        return "mobile_browser"

    # Desktop browser detection — order matters (Edge and Opera include "chrome" in their UA)
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


# ── Daily score reset ─────────────────────────────────────────────────────────
def reset_scores():
    db = SessionLocal()
    try:
        # Exempt from daily reset: app scores (ios_app/android_app) and
        # registered users (user_email is set) — their scores persist for
        # season and all-time leaderboards. Only anonymous guest web scores
        # are cleared each night.
        deleted = (
            db.query(Score)
            .filter(
                ~Score.client_type.in_(["ios_app", "android_app"]),
                Score.user_email.is_(None),
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info(f"Daily score reset complete — {deleted} rows removed.")
        record_scheduler_run("reset_scores", success=True)
    except Exception as e:
        db.rollback()
        logger.error(f"Score reset failed: {e}")
        record_scheduler_run("reset_scores", success=False)
    finally:
        db.close()


NUMBERS_MATCH_TZ = ZoneInfo("America/New_York")
NUMBERS_MATCH_BOARD_REVISION = "v2"


def numbers_match_today_str() -> str:
    return datetime.now(NUMBERS_MATCH_TZ).strftime("%Y-%m-%d")


_prev_net_sent: int | None = None
_prev_net_recv: int | None = None


def collect_server_stats():
    """Snapshot server/app/network metrics and store in the server_stats table."""
    global _req_count, _prev_net_sent, _prev_net_recv

    db = SessionLocal()
    try:
        cpu    = psutil.cpu_percent(interval=1)
        mem    = psutil.virtual_memory()
        disk   = psutil.disk_usage("/")
        net    = psutil.net_io_counters()

        db_size_bytes = db.execute(
            text("SELECT SUM(data_length + index_length) "
                 "FROM information_schema.tables WHERE table_schema = DATABASE()")
        ).scalar() or 0

        delta_sent = (net.bytes_sent - _prev_net_sent) if _prev_net_sent is not None else None
        delta_recv = (net.bytes_recv - _prev_net_recv) if _prev_net_recv is not None else None
        _prev_net_sent = net.bytes_sent
        _prev_net_recv = net.bytes_recv

        with _req_lock:
            reqs       = _req_count
            _req_count = 0

        db.add(ServerStats(
            recorded_at    = datetime.now(timezone.utc),
            cpu_percent    = cpu,
            mem_used_mb    = mem.used    / (1024 ** 2),
            mem_total_mb   = mem.total   / (1024 ** 2),
            mem_percent    = mem.percent,
            disk_used_gb   = disk.used   / (1024 ** 3),
            disk_total_gb  = disk.total  / (1024 ** 3),
            disk_percent   = disk.percent,
            db_size_mb     = db_size_bytes / (1024 ** 2),
            net_bytes_sent = net.bytes_sent,
            net_bytes_recv = net.bytes_recv,
            net_delta_sent = delta_sent,
            net_delta_recv = delta_recv,
            http_requests  = reqs,
        ))
        db.commit()
        logger.info("Server stats snapshot saved.")
        record_scheduler_run("collect_server_stats", success=True)
    except Exception as e:
        db.rollback()
        logger.error(f"collect_server_stats failed: {e}")
        record_scheduler_run("collect_server_stats", success=False)
        record_db_error("collect_server_stats")
    finally:
        db.close()


_APACHE_LOG_GLOB   = "/var/log/apache2/minesweeper.org-ssl-access.log*"
_TRAFFIC_ARCHIVE_START = date(2026, 3, 25)
_LOG_RE = __import__("re").compile(
    r'^(\S+)\s+\S+\s+\S+\s+\[(\d{2}/\w{3}/\d{4}):[^\]]+\]\s+"[^"]*"\s+(\d{3})'
)
_LOG_RE_URL = __import__("re").compile(
    r'^\S+\s+\S+\s+\S+\s+\[(\d{2}/\w{3}/\d{4}):[^\]]+\]\s+"\S+\s+([^?\s#"]+)'
)
_TRACKED_CODES = {"200","201","206","101","302","304","307","403","404","405","422","500","503"}


def collect_web_traffic_stats(target_date: date = None):
    """Parse Apache access logs for target_date and upsert daily traffic stats."""
    import glob as _glob
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    target_str = target_date.strftime("%d/%b/%Y")   # e.g. "25/Mar/2026"
    status_counts: dict = {}
    unique_ips: set = set()

    for log_path in sorted(_glob.glob(_APACHE_LOG_GLOB)):
        try:
            with open(log_path, "r", errors="replace") as fh:
                for line in fh:
                    m = _LOG_RE.match(line)
                    if not m:
                        continue
                    ip, log_date, code = m.group(1), m.group(2), m.group(3)
                    if log_date != target_str:
                        continue
                    unique_ips.add(ip)
                    if code in _TRACKED_CODES:
                        status_counts[code] = status_counts.get(code, 0) + 1
                    else:
                        status_counts["other"] = status_counts.get("other", 0) + 1
        except OSError as exc:
            logger.warning(f"collect_web_traffic_stats: cannot read {log_path}: {exc}")

    total = sum(status_counts.values())

    db = SessionLocal()
    try:
        row = db.query(WebTrafficStats).filter(WebTrafficStats.stat_date == target_date).first()
        if row is None:
            row = WebTrafficStats(stat_date=target_date)
            db.add(row)
        row.total_requests = total
        row.unique_ips     = len(unique_ips)
        row.http_200  = status_counts.get("200", 0)
        row.http_201  = status_counts.get("201", 0)
        row.http_206  = status_counts.get("206", 0)
        row.http_101  = status_counts.get("101", 0)
        row.http_302  = status_counts.get("302", 0)
        row.http_304  = status_counts.get("304", 0)
        row.http_307  = status_counts.get("307", 0)
        row.http_403  = status_counts.get("403", 0)
        row.http_404  = status_counts.get("404", 0)
        row.http_405  = status_counts.get("405", 0)
        row.http_422  = status_counts.get("422", 0)
        row.http_500  = status_counts.get("500", 0)
        row.http_503  = status_counts.get("503", 0)
        row.recorded_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"Web traffic stats saved for {target_date}: {total} requests, {len(unique_ips)} unique IPs")
        record_scheduler_run("collect_web_traffic_stats", success=True)
    except Exception as exc:
        db.rollback()
        logger.error(f"collect_web_traffic_stats DB write failed: {exc}")
        record_scheduler_run("collect_web_traffic_stats", success=False)
        record_db_error("collect_web_traffic_stats")
    finally:
        db.close()


def get_url_traffic_stats(target_date: date = None):
    """Parse Apache logs for target_date and return URL hit counts sorted by count desc."""
    import glob as _glob
    if target_date is None:
        target_date = date.today() - timedelta(days=1)
    target_str = target_date.strftime("%d/%b/%Y")
    url_counts: dict = {}
    for log_path in sorted(_glob.glob(_APACHE_LOG_GLOB)):
        try:
            with open(log_path, "r", errors="replace") as fh:
                for line in fh:
                    m = _LOG_RE_URL.match(line)
                    if not m or m.group(1) != target_str:
                        continue
                    url_counts[m.group(2)] = url_counts.get(m.group(2), 0) + 1
        except OSError:
            pass
    return sorted(url_counts.items(), key=lambda x: x[1], reverse=True)


def _backfill_web_traffic():
    """On startup: process any days from ARCHIVE_START to yesterday missing from DB."""
    yesterday = date.today() - timedelta(days=1)
    d = _TRAFFIC_ARCHIVE_START
    while d <= yesterday:
        db = SessionLocal()
        try:
            exists = db.query(WebTrafficStats).filter(WebTrafficStats.stat_date == d).first() is not None
        finally:
            db.close()
        if not exists:
            collect_web_traffic_stats(target_date=d)
        d += timedelta(days=1)


def archive_guest_scores():
    """Archive (move) all guest scores to guest_score_archive at midnight UTC."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        # Columns: table, mode_expr, time_ms_expr, rows_expr, cols_expr,
        #          mines_expr, bbbv_expr, board_hash_expr, token_expr
        # All exprs are raw SQL — table/column names are hardcoded, not user input.
        specs = [
            ("scores",                "mode",        "IFNULL(time_ms, time_secs * 1000)", "rows", "cols", "mines", "bbbv", "board_hash", "guest_token"),
            ("rush_scores",           "rush_mode",   "time_secs * 1000",                  "NULL", "cols", "NULL",  "NULL", "NULL",       "guest_token"),
            ("cylinder_scores",       "cyl_mode",    "IFNULL(time_ms, time_secs * 1000)", "rows", "cols", "mines", "bbbv", "board_hash", "guest_token"),
            ("toroid_scores",         "tor_mode",    "IFNULL(time_ms, time_secs * 1000)", "rows", "cols", "mines", "bbbv", "board_hash", "guest_token"),
            ("tentaizu_scores",       "puzzle_date", "time_secs * 1000",                  "NULL", "NULL", "NULL",  "NULL", "NULL",       "guest_token"),
            ("replay_scores",         "variant",     "IFNULL(time_ms, time_secs * 1000)", "rows", "cols", "mines", "bbbv", "board_hash", "guest_token"),
            ("nonosweeper_scores",    "puzzle_date", "time_secs * 1000",                  "NULL", "NULL", "NULL",  "NULL", "NULL",       "guest_token"),
            ("fifteen_puzzle_scores", "puzzle_date", "time_ms",                           "NULL", "NULL", "NULL",  "NULL", "NULL",       "guest_token"),
            ("game_2048_scores",      "puzzle_date", "time_ms",                           "NULL", "NULL", "NULL",  "NULL", "NULL",       "guest_token"),
            ("mahjong_scores",        "puzzle_date", "time_ms",                           "NULL", "NULL", "NULL",  "NULL", "board_hash", "guest_token"),
            ("numbers_match_scores",  "puzzle_date", "time_secs * 1000",                  "NULL", "NULL", "NULL",  "NULL", "NULL",       "guest_token"),
            ("meowdoku_scores",       "puzzle_date", "time_secs * 1000",                  "NULL", "NULL", "NULL",  "NULL", "board_hash",  "guest_token"),
        ]
        total = 0
        for tbl, mode_e, time_e, rows_e, cols_e, mines_e, bbbv_e, hash_e, token_e in specs:
            result = db.execute(text(f"""
                INSERT INTO guest_score_archive
                    (source_table, original_id, guest_token, name, game_mode,
                     time_ms, rows, cols, mines, bbbv, board_hash,
                     original_created_at, archived_at)
                SELECT :src, id, {token_e}, name, CAST({mode_e} AS CHAR(32)),
                       {time_e}, {rows_e}, {cols_e}, {mines_e}, {bbbv_e}, {hash_e},
                       created_at, :archived_at
                FROM {tbl}
                WHERE user_email IS NULL
            """), {"src": tbl, "archived_at": now})
            total += result.rowcount
            db.execute(text(f"DELETE FROM {tbl} WHERE user_email IS NULL"))
        db.commit()
        logger.info(f"archive_guest_scores: archived {total} guest score(s).")
        record_scheduler_run("archive_guest_scores", success=True)
    except Exception as e:
        db.rollback()
        logger.error(f"archive_guest_scores failed: {e}")
        record_scheduler_run("archive_guest_scores", success=False)
    finally:
        db.close()


def generate_tametsi_dailies(date_str: str = None):
    """Pre-generate (or verify) daily Tametsi puzzles for all three levels."""
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    all_ok = True
    for level in _TAMETSI_LEVELS:
        db = SessionLocal()
        try:
            existing = (
                db.query(TametsiDaily)
                .filter(TametsiDaily.puzzle_date == date_str, TametsiDaily.level == level)
                .first()
            )
            if existing:
                logger.info(f"generate_tametsi_dailies: {level} {date_str} already exists.")
                continue

            rows, cols, num_mines = _TAMETSI_LEVELS[level]
            board = _tametsi_generate_board(
                rows, cols, num_mines,
                rng=_tametsi_daily_rng(level, date_str),
                max_attempts=50_000,
            )

            if not db.get(TametsiBoard, board.board_hash):
                db.add(TametsiBoard(
                    board_hash = board.board_hash,
                    rows       = board.rows,
                    cols       = board.cols,
                    mines      = len(board.mines),
                    bbbv       = board.bbbv,
                    board_data = board.board_data,
                ))

            db.add(TametsiDaily(
                puzzle_date = date_str,
                level       = level,
                board_hash  = board.board_hash,
            ))
            db.commit()
            logger.info(f"generate_tametsi_dailies: {level} {date_str} stored.")
        except IntegrityError:
            db.rollback()
            logger.info(f"generate_tametsi_dailies: {level} {date_str} already stored by concurrent request.")
        except Exception as e:
            db.rollback()
            logger.error(f"generate_tametsi_dailies {level} failed: {e}")
            all_ok = False
        finally:
            db.close()
    record_scheduler_run("generate_tametsi_dailies", success=all_ok)


def generate_numbers_match_daily(date_str: str = None):
    """Pre-generate (or verify) the Numbers Match daily board for date_str."""
    if date_str is None:
        date_str = numbers_match_today_str()
    db = SessionLocal()
    try:
        existing = db.query(NumbersMatchDaily).filter_by(puzzle_date=date_str).first()
        if existing:
            logger.info(f"generate_numbers_match_daily: {date_str} already exists.")
            record_scheduler_run("generate_numbers_match_daily", success=True)
            return
        result = _nm_generate_daily(date_str)
        db.add(NumbersMatchDaily(
            puzzle_date = date_str,
            board_num   = result["board_num"],
            rows        = result["rows"],
            board_data  = result["board_data"],
        ))
        db.commit()
        logger.info(f"generate_numbers_match_daily: {date_str} stored (board_num={result['board_num']}, rows={result['rows']}).")
    except IntegrityError:
        db.rollback()
        logger.info(f"generate_numbers_match_daily: {date_str} already stored by concurrent request.")
    except Exception as e:
        db.rollback()
        logger.error(f"generate_numbers_match_daily {date_str} failed: {e}")
        record_scheduler_run("generate_numbers_match_daily", success=False)
        return
    finally:
        db.close()
    record_scheduler_run("generate_numbers_match_daily", success=True)


scheduler = BackgroundScheduler(timezone="UTC")
scheduler.add_job(archive_guest_scores,              CronTrigger(hour=23, minute=59)) # 23:59 UTC — archive guests before reset
scheduler.add_job(reset_scores,                      CronTrigger(hour=0,  minute=0))  # midnight UTC — clear all scores
scheduler.add_job(generate_tametsi_dailies,          CronTrigger(hour=0,  minute=1))  # 00:01 UTC — pre-generate daily Tametsi puzzles
scheduler.add_job(generate_numbers_match_daily,      CronTrigger(hour=0,  minute=1, timezone=NUMBERS_MATCH_TZ))  # 00:01 America/New_York — pre-generate daily Numbers Match board
scheduler.add_job(cleanup_old_games,          CronTrigger(hour="*"))             # hourly
scheduler.add_job(collect_server_stats,       CronTrigger(minute=0))             # top of every hour
scheduler.add_job(collect_web_traffic_stats,  CronTrigger(hour=1,  minute=0))   # 1 AM UTC — parse yesterday's logs


def _run_seo_rankings():
    db = SessionLocal()
    try:
        n = seo_checker.update_all_rankings(db)
        logger.info("SEO ranking refresh complete (%d languages)", n)
    except Exception as exc:
        logger.error("SEO ranking refresh failed: %s", exc)
    finally:
        db.close()


scheduler.add_job(_run_seo_rankings, CronTrigger(day_of_week="sun", hour=1, minute=0))  # Sun 1 AM UTC

def _migrate_numbers_match_puzzle_date():
    """Widen numbers_match_scores.puzzle_date from VARCHAR(10) to VARCHAR(32)
    to support difficulty-mode IDs like '2026-05-08-easy'."""
    db = SessionLocal()
    try:
        db.execute(text(
            "ALTER TABLE numbers_match_scores "
            "MODIFY COLUMN puzzle_date VARCHAR(32) NOT NULL"
        ))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


# The app runs as several OS processes (gunicorn's web worker pool plus the
# single-worker pvp instance — see scripts/minesweeper-web.service and
# scripts/minesweeper-pvp.service). Each process runs this startup() hook
# independently, so without a guard every process would start its own
# BackgroundScheduler and each cron job (score reset at midnight, daily puzzle
# generation, hourly stats, weekly SEO rankings, etc.) would fire once per
# process. flock is per-process and non-blocking: only the first process to
# open+lock this file gets True and runs the scheduler; the rest skip it. The
# fd is kept open for the process's lifetime — closing it (or process exit)
# releases the lock so a replacement process can win it next time.
_SCHEDULER_LOCK_PATH = "/tmp/minesweeper_scheduler.lock"  # nosec B108 — lock file, no sensitive data written here
_scheduler_lock_file = None


def _acquire_scheduler_lock() -> bool:
    """Return True if this process won the exclusive lock to run the scheduler."""
    global _scheduler_lock_file
    lock_file = open(_SCHEDULER_LOCK_PATH, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_file.close()
        return False
    _scheduler_lock_file = lock_file  # keep open — closing releases the lock
    return True


# Create DB tables and start scheduler on startup
@app.on_event("startup")
def startup():
    init_db()
    _migrate_numbers_match_puzzle_date()
    if _acquire_scheduler_lock():
        scheduler.start()
        logger.info("Scheduler started — scores reset daily at midnight UTC (this process holds the scheduler lock).")
        threading.Thread(target=_backfill_web_traffic,         daemon=True).start()
        threading.Thread(target=generate_tametsi_dailies,      daemon=True).start()
        threading.Thread(target=generate_numbers_match_daily,  daemon=True).start()
    else:
        logger.info("Scheduler skipped — another process holds the scheduler lock.")

@app.on_event("shutdown")
def shutdown():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down.")

# ── Page Routes ───────────────────────────────────────────────────────────────

@app.get("/set-lang")
async def set_lang(request: Request, lang: str = "en", next: Optional[str] = None):
    # Dict lookup ensures safe_lang is a pre-built constant, never user input directly.
    _lang_self_map = {l: l for l in SUPPORTED_LANGS}
    safe_lang = _lang_self_map.get(lang, "en")
    # Sanitise the return URL: use urlparse to strip scheme/netloc, then allow only the path+query.
    raw = next or request.headers.get("referer", "/")
    _parsed = urlparse(raw)
    redirect_to = (_parsed.path or "/") if (not _parsed.scheme and not _parsed.netloc) else "/"
    if _parsed.query and not _parsed.scheme and not _parsed.netloc:
        redirect_to += "?" + _parsed.query
    # Strip any existing lang prefix so we never stack prefixes (e.g. /de/fr/about)
    parts = redirect_to.lstrip("/").split("/", 1)
    if parts and parts[0] in SUPPORTED_LANGS:
        redirect_to = "/" + (parts[1] if len(parts) > 1 else "")
        if not redirect_to:
            redirect_to = "/"
    # Normalize: single leading slash, no protocol-relative // or backslash prefix
    redirect_to = "/" + redirect_to.lstrip("/\\")
    # Apply the new lang prefix for non-English using pre-built map (untainted value)
    prefix = _LANG_PREFIX_MAP.get(safe_lang, "")
    redirect_to = prefix + ("" if redirect_to == "/" else redirect_to) if prefix else redirect_to
    response = RedirectResponse(url=redirect_to)
    response.set_cookie("lang", safe_lang, max_age=365 * 24 * 3600, samesite="lax")
    return response


@app.get("/beginner", response_class=HTMLResponse)
async def beginner_redirect():
    return RedirectResponse(url="/", status_code=301)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "mode": "beginner",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "default_no_guess": _ng_default_from_ip(request),
        **GAME_MODES["beginner"]
    })

@app.get("/intermediate", response_class=HTMLResponse)
async def intermediate(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "mode": "intermediate",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "default_no_guess": _ng_default_from_ip(request),
        **GAME_MODES["intermediate"]
    })

@app.get("/expert", response_class=HTMLResponse)
async def expert(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "mode": "expert",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "default_no_guess": _ng_default_from_ip(request),
        **GAME_MODES["expert"]
    })

@app.get("/evil", response_class=HTMLResponse)
async def evil_ng(request: Request, db: Session = Depends(get_db)):
    db.add(EvilGameSession())
    db.commit()
    return templates.TemplateResponse(request, "evil.html", {
        "mode": "evil",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **EVIL_NG_MODE
    })


@app.get("/analysis", response_class=HTMLResponse)
def analysis_index():
    rows = []
    for dirpath, _, filenames in os.walk(_ANALYSIS_DIR):
        for fn in sorted(filenames):
            if os.path.splitext(fn)[1].lower() not in _ANALYSIS_EXTS:
                continue
            full = os.path.join(dirpath, fn)
            rel  = os.path.relpath(full, _ANALYSIS_DIR).replace(os.sep, "/")
            rows.append(f'<li><a href="/analysis/{rel}">{rel}</a></li>')
    listing = "\n".join(rows) or "<li>No files found.</li>"
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Analysis Source Files</title>
<style>body{{font-family:monospace;padding:2rem}}a{{color:#4a9eff}}</style>
</head><body>
<h1>Analysis Source Files</h1>
<ul>{listing}</ul>
</body></html>""")


@app.get("/analysis/{path:path}")
def analysis_file(path: str):
    resolved = os.path.realpath(os.path.join(_ANALYSIS_DIR, path))
    if not resolved.startswith(_ANALYSIS_DIR + os.sep):
        raise HTTPException(status_code=404)
    if os.path.splitext(resolved)[1].lower() not in _ANALYSIS_EXTS:
        raise HTTPException(status_code=404)
    if not os.path.isfile(resolved):
        raise HTTPException(status_code=404)
    return FileResponse(resolved)


@app.get("/custom", response_class=HTMLResponse)
async def custom(request: Request):
    return templates.TemplateResponse(request, "custom.html", {
        "mode": "custom",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })

@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(request: Request):
    return templates.TemplateResponse(request, "leaderboard.html", {
        "mode": "leaderboard",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "leaderboard_groups": LEADERBOARD_GROUPS,
    })


@app.get("/api/leaderboards/catalog")
def api_leaderboards_catalog(response: Response = None):
    if response:
        response.headers["Cache-Control"] = "public, max-age=300"
    return leaderboard_catalog()


@app.get("/api/leaderboards/cards")
def api_leaderboards_cards(
    period: str = "daily",
    category: str = "all",
    score_date: Optional[str] = Query(None, alias="date"),
    season_num: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    response: Response = None,
):
    if response:
        response.headers["Cache-Control"] = "public, max-age=60"
    try:
        target = date.fromisoformat(score_date) if score_date else date.today()
    except ValueError:
        target = date.today()
    return leaderboard_cards(db, period=period, category=category, target=target, season_num=season_num, limit=3)


@app.get("/api/leaderboards/{leaderboard_id}")
def api_leaderboard_rows(
    leaderboard_id: str,
    period: str = "daily",
    score_date: Optional[str] = Query(None, alias="date"),
    season_num: Optional[int] = Query(None),
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
    response: Response = None,
):
    if response:
        response.headers["Cache-Control"] = "public, max-age=60"
    try:
        target = date.fromisoformat(score_date) if score_date else date.today()
    except ValueError:
        target = date.today()
    try:
        return leaderboard_rows(db, leaderboard_id, period=period, target=target, season_num=season_num, limit=limit)
    except KeyError:
        raise HTTPException(status_code=404, detail="Leaderboard not found")

@app.get("/archive", response_class=HTMLResponse)
async def archive_index(request: Request, db: Session = Depends(get_db)):
    raw_dates = (
        db.query(cast(Score.created_at, SQLDate).label("d"))
        .filter(Score.user_email.isnot(None), Score.mode.in_(list(ARCHIVE_MODES)))
        .distinct()
        .order_by(cast(Score.created_at, SQLDate).desc())
        .limit(90)
        .all()
    )
    recent_days: list = [str(r.d) for r in raw_dates[:30]]
    seen_months: dict = {}
    for r in raw_dates:
        m = str(r.d)[:7]
        if m not in seen_months:
            seen_months[m] = True
    recent_months: list = list(seen_months.keys())[:24]
    return templates.TemplateResponse(request, "archive_index.html", {
        "mode":          "archive",
        "user":          get_current_user(request),
        "lang":          get_lang(request),
        "t":             get_t(request),
        "recent_days":   recent_days,
        "recent_months": recent_months,
        "today":         str(date.today()),
    })

# ── Auth routes ───────────────────────────────────────────────────────────────

@app.get("/login")
def legacy_login_redirect(request: Request):
    next_url = _safe_relative_url(request.query_params.get("next", "/"))
    return RedirectResponse(f"/auth/login?next={quote(next_url, safe='/')}", status_code=302)

@app.get("/auth/login")
async def login(request: Request):
    # Reject absolute/protocol-relative URLs to prevent open-redirect phishing via OAuth flow
    next_url = _safe_relative_url(request.query_params.get("next", "/"))
    request.session["next"] = next_url
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        # Stale OAuth state (service restart, crawler, or double-callback).
        # Redirect to login so the user can try again cleanly.
        return RedirectResponse(url="/auth/login?error=session_expired")
    user  = token.get("userinfo")
    if user:
        email = user.get("email", "")
        profile = db.query(UserProfile).filter(UserProfile.email == email).first()
        if not profile:
            profile = UserProfile(email=email, display_name=user.get("name", "")[:32],
                                  public_id=str(uuid.uuid4()), is_public=False)
            db.add(profile)
            db.commit()
        elif not profile.public_id:
            profile.public_id = str(uuid.uuid4())
            db.commit()
        set_session_user(request, user, display_name=profile.display_name)

        # Claim any guest scores submitted before this login
        guest_token = request.session.pop("guest_token", None)
        if guest_token:
            for model in [Score, RushScore, CylinderScore, ToroidScore, TentaizuScore, ReplayScore]:
                db.query(model).filter(
                    model.guest_token == guest_token,
                    model.user_email.is_(None),
                ).update({"user_email": email}, synchronize_session=False)

            # WC2026 score rows — same idea, different column name (email).
            db.query(WC2026Score).filter(
                WC2026Score.guest_token == guest_token,
                WC2026Score.email.is_(None),
            ).update(
                {"email": email, "guest_token": None, "display_name": profile.display_name},
                synchronize_session=False,
            )

            # WC2026 board states — conflict-aware merge. The unique key is
            # (email, country_slug, difficulty); if the user already has a
            # board for the same country+difficulty, prefer it and delete the
            # guest's. Bounded at 48 countries × 2 difficulties = 96 rows.
            guest_boards = db.query(WC2026BoardState).filter(
                WC2026BoardState.guest_token == guest_token,
                WC2026BoardState.email.is_(None),
            ).all()
            for gb in guest_boards:
                existing = db.query(WC2026BoardState).filter_by(
                    email=email,
                    country_slug=gb.country_slug,
                    difficulty=gb.difficulty,
                ).first()
                if existing:
                    db.delete(gb)
                else:
                    gb.email = email
                    gb.guest_token = None

            # If the guest had a fan flag in the cookie but the new profile
            # doesn't have one yet, carry it over.
            guest_fan = request.session.pop("wc2026_fan", None)
            if guest_fan and not profile.wc2026_fan and guest_fan in VALID_WC2026_SLUGS:
                profile.wc2026_fan = guest_fan

            db.commit()
        else:
            # Even with no guest_token, a guest may have set a fan flag in the
            # session before logging in — preserve it.
            guest_fan = request.session.pop("wc2026_fan", None)
            if guest_fan and not profile.wc2026_fan and guest_fan in VALID_WC2026_SLUGS:
                profile.wc2026_fan = guest_fan
                db.commit()

    next_url = request.session.pop("next", "/")
    if not isinstance(next_url, str):
        next_url = "/"
    return RedirectResponse(url=_safe_relative_url(next_url))

@app.get("/auth/logout")
async def logout(request: Request):
    clear_session(request)
    return RedirectResponse(url="/")

# ── Leaderboard API ───────────────────────────────────────────────────────────

class ScoreSubmit(BaseModel):
    name:         str = Field(..., min_length=1, max_length=32)
    mode:         GameMode
    time_secs:    int = Field(..., ge=1, le=99999)
    time_ms:      Optional[int]  = Field(None, ge=1, le=99_999_999)
    rows:         int = Field(..., ge=5,  le=30)
    cols:         int = Field(..., ge=5,  le=50)
    mines:        int = Field(..., ge=1,  le=999)
    no_guess:     bool           = False
    board_hash:   Optional[str]  = Field(None, max_length=128)
    bbbv:         Optional[int]  = Field(None, ge=1, le=9999)
    left_clicks:  Optional[int]  = Field(None, ge=0, le=99999)
    right_clicks: Optional[int]  = Field(None, ge=0, le=99999)
    chord_clicks: Optional[int]  = Field(None, ge=0, le=99999)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        # Strip whitespace, allow only printable ASCII
        v = v.strip()
        v = "".join(c for c in v if c.isprintable())
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]

    @field_validator("mines")
    @classmethod
    def mines_not_exceeding_board(cls, v, info):
        rows = info.data.get("rows")
        cols = info.data.get("cols")
        if rows and cols:
            max_mines = int(rows * cols * 0.85)
            if v > max_mines:
                raise ValueError(f"Too many mines for this board size")
        return v


@app.post("/api/scores", status_code=201)
@limiter.limit("10/minute")
def submit_score(payload: ScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user  = get_current_user(request)
    guest_token = get_or_create_guest_token(request, user)

    client_type = get_client_type(request)

    # Reject duplicate board submissions.
    # Logged-in users: one score per (user, board_hash).
    # Guests: one score per board_hash globally — guest_token changes across
    # sessions/tabs so per-token checks allow the same board to be resubmitted.
    if payload.board_hash:
        if user:
            existing = db.query(Score.id).filter(
                Score.board_hash == payload.board_hash,
                Score.user_email == user["email"],
            ).first()
        else:
            existing = db.query(Score.id).filter(
                Score.board_hash == payload.board_hash,
            ).first()
        if existing:
            return JSONResponse({"ok": True, "id": existing.id}, status_code=200)

    score = Score(
        name         = payload.name,
        user_email   = user["email"] if user else None,
        mode         = payload.mode,
        time_secs    = payload.time_secs,
        time_ms      = payload.time_ms,
        rows         = payload.rows,
        cols         = payload.cols,
        mines        = payload.mines,
        no_guess     = payload.no_guess,
        board_hash   = payload.board_hash,
        bbbv         = payload.bbbv,
        left_clicks  = payload.left_clicks,
        right_clicks = payload.right_clicks,
        chord_clicks = payload.chord_clicks,
        guest_token  = guest_token,
        client_type  = client_type,
    )
    db.add(score)

    # Persist permanent history for logged-in users
    if user:
        db.add(GameHistory(
            user_email   = user["email"],
            name         = payload.name,
            mode         = payload.mode,
            time_secs    = payload.time_secs,
            time_ms      = payload.time_ms,
            rows         = payload.rows,
            cols         = payload.cols,
            mines        = payload.mines,
            no_guess     = payload.no_guess,
            board_hash   = payload.board_hash,
            bbbv         = payload.bbbv,
            left_clicks  = payload.left_clicks,
            right_clicks = payload.right_clicks,
            chord_clicks = payload.chord_clicks,
            client_type  = client_type,
        ))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(Score).filter(Score.board_hash == payload.board_hash).first()
        if existing:
            return JSONResponse({"ok": True, "id": existing.id}, status_code=200)
        raise
    db.refresh(score)
    flag_if_profane(db, score.__tablename__, score.id, score.name)
    record_score_submit("minesweeper", payload.mode.value)
    record_game_complete("minesweeper", mode=payload.mode.value,
                         duration_ms=payload.time_ms or (payload.time_secs or 0) * 1000)
    return {"ok": True, "id": score.id}


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

    # GameReplay.score_id directly references Score.id — one bulk lookup.
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


def _archive_ng_filter(no_guess: bool):
    if no_guess:
        return Score.no_guess == True
    return (Score.no_guess == False) | Score.no_guess.is_(None)


def _archive_sort_key():
    return case((Score.time_ms.isnot(None), Score.time_ms), else_=Score.time_secs * 1000)


def _dedup_by_user(raw: list, limit: int = 100) -> list:
    seen: set = set()
    result = []
    for s in raw:
        if s.user_email not in seen:
            seen.add(s.user_email)
            result.append(s)
            if len(result) >= limit:
                break
    return result


def _get_archive_scores_day(db: Session, mode: str, target: date, no_guess: bool) -> list:
    raw = (
        db.query(Score)
        .filter(
            Score.mode == mode,
            Score.user_email.isnot(None),
            _archive_ng_filter(no_guess),
            Score.created_at >= target,
            Score.created_at < target + timedelta(days=1),
        )
        .order_by(_archive_sort_key().asc(), Score.created_at.asc())
        .limit(500)
        .all()
    )
    return _dedup_by_user(raw)


def _get_archive_scores_month(db: Session, mode: str, year: int, month: int, no_guess: bool) -> list:
    start = date(year, month, 1)
    end   = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    raw = (
        db.query(Score)
        .filter(
            Score.mode == mode,
            Score.user_email.isnot(None),
            _archive_ng_filter(no_guess),
            Score.created_at >= start,
            Score.created_at < end,
        )
        .order_by(_archive_sort_key().asc(), Score.created_at.asc())
        .limit(500)
        .all()
    )
    return _dedup_by_user(raw)


def _enrich_archive(scores: list) -> list:
    enriched = []
    for i, s in enumerate(scores, start=1):
        ms        = s.time_ms if s.time_ms else s.time_secs * 1000
        t_display = f"{ms / 1000:.3f}s"
        bbbv_s    = f"{s.bbbv / (ms / 1000):.2f}" if s.bbbv else "—"
        clicks    = (s.left_clicks or 0) + (s.chord_clicks or 0)
        eff       = f"{round(s.bbbv / clicks * 100)}%" if (s.bbbv and clicks) else "—"
        board_url = None
        if s.board_hash:
            board_url = f"/variants/replay/?hash={s.board_hash}&rows={s.rows}&cols={s.cols}&mines={s.mines}"
        enriched.append({
            "rank":      i,
            "name":      s.name,
            "time":      t_display,
            "board":     f"{s.rows}×{s.cols}",
            "mines":     s.mines,
            "bbbv":      s.bbbv if s.bbbv else "—",
            "bbbv_s":    bbbv_s,
            "eff":       eff,
            "board_url": board_url,
        })
    return enriched


# ── F74 Rewind — store win replay log server-side ─────────────────────────────

class RewindSubmit(BaseModel):
    rows:       int            = Field(..., ge=5, le=50)
    cols:       int            = Field(..., ge=5, le=50)
    mines:      int            = Field(..., ge=1, le=999)
    board_hash: Optional[str]  = Field(None, max_length=128)
    no_guess:   bool           = False
    mode:       Optional[str]  = Field(None, max_length=32)
    time_ms:    Optional[int]  = Field(None, ge=0, le=3_600_000)
    won:        bool           = False                                # legacy — derived from outcome when absent
    log:        list           = Field(...)                           # [[t_ms, type, r, c], …]

    # Phase 1 additions
    outcome:          Optional[str] = Field(None, pattern=r"^(win|loss|abandon)$")
    bbbv:             Optional[int] = Field(None, ge=0, le=10_000)
    left_clicks:      Optional[int] = Field(None, ge=0, le=10_000)
    right_clicks:     Optional[int] = Field(None, ge=0, le=10_000)
    chord_clicks:     Optional[int] = Field(None, ge=0, le=10_000)
    cells_revealed:   Optional[int] = Field(None, ge=0, le=2_500)
    cells_total_safe: Optional[int] = Field(None, ge=0, le=2_500)
    score_id:         Optional[int] = Field(None, ge=0)

    @field_validator("log")
    @classmethod
    def validate_log(cls, v):
        if len(v) > 10_000:
            raise ValueError("Log too large")
        for entry in v[:50]:
            if not isinstance(entry, list) or len(entry) != 4:
                raise ValueError("Log entry must be [t_ms, type, r, c]")
            if entry[1] not in ("l", "r", "c"):
                raise ValueError(f"Invalid action type: {entry[1]!r}")
        return v


@app.post("/api/rewind", status_code=201)
@limiter.limit("60/minute")
def submit_rewind(payload: RewindSubmit, request: Request, db: Session = Depends(get_db), background_tasks: BackgroundTasks = None):
    import json as _json

    # Canonical outcome: prefer explicit field, fall back to legacy won bool
    outcome = payload.outcome if payload.outcome else ("win" if payload.won else "loss")

    user       = get_current_user(request)
    user_email = user["email"] if user else None

    guest_token = get_or_create_guest_token(request, user)

    client_type = get_client_type(request)

    # Best-effort link to matching Score row for wins
    score_id = payload.score_id
    if score_id is None and outcome == "win" and payload.board_hash:
        match_q = db.query(Score.id).filter(
            Score.board_hash == payload.board_hash,
            Score.time_ms    == payload.time_ms,
        )
        if user_email:
            match_q = match_q.filter(Score.user_email == user_email)
        elif guest_token:
            match_q = match_q.filter(Score.guest_token == guest_token)
        row = match_q.order_by(Score.created_at.desc()).first()
        if row:
            score_id = row[0]

    cells_total_safe = payload.cells_total_safe
    if cells_total_safe is None:
        cells_total_safe = payload.rows * payload.cols - payload.mines

    replay = GameReplay(
        user_email       = user_email,
        mode             = payload.mode,
        rows             = payload.rows,
        cols             = payload.cols,
        mines            = payload.mines,
        no_guess         = payload.no_guess,
        board_hash       = payload.board_hash,
        time_ms          = payload.time_ms,
        log_json         = _json.dumps(payload.log, separators=(',', ':')),
        outcome          = outcome,
        bbbv             = payload.bbbv,
        left_clicks      = payload.left_clicks,
        right_clicks     = payload.right_clicks,
        chord_clicks     = payload.chord_clicks,
        cells_revealed   = payload.cells_revealed,
        cells_total_safe = cells_total_safe,
        client_type      = client_type,
        guest_token      = guest_token,
        score_id         = score_id,
    )
    db.add(replay)
    db.commit()
    db.refresh(replay)

    if background_tasks is not None:
        background_tasks.add_task(analyze_replay_async, replay.id, SessionLocal)

    return {"id": replay.id, "outcome": outcome}


@app.get("/api/scores/{mode}")
def get_scores(mode: GameMode, no_guess: bool = False,
               period: str = "daily",
               score_date: Optional[str] = Query(None, alias="date"),
               season_num: Optional[int] = Query(None),
               db: Session = Depends(get_db),
               response: Response = None):
    if period not in ("daily", "weekly", "monthly", "season", "yearly", "alltime"):
        period = "daily"

    if response:
        response.headers["Cache-Control"] = "public, max-age=60"

    sort_key = case(
        (Score.time_ms.isnot(None), Score.time_ms),
        else_=Score.time_secs * 1000
    )

    if no_guess:
        ng_filter = Score.no_guess == True
    else:
        ng_filter = (Score.no_guess == False) | Score.no_guess.is_(None)
    q = db.query(Score).filter(Score.mode == mode, ng_filter)
    q = exclude_flagged(q, Score, db)

    if period in ("daily", "weekly", "monthly", "season", "yearly"):
        try:
            target = date.fromisoformat(score_date) if score_date else date.today()
        except ValueError:
            target = date.today()
        p_start, p_end = get_period_range(period, target, season_num)
        q = q.filter(Score.created_at >= p_start, Score.created_at < p_end)
        if period == "daily":
            top = q.order_by(sort_key.asc(), Score.created_at.asc()).limit(15).all()
            return _enrich_with_profiles(top, db)

    # season / alltime: fetch generously, then deduplicate to best per player
    raw = q.order_by(sort_key.asc(), Score.created_at.asc()).limit(500).all()
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


@app.get("/rush", response_class=HTMLResponse)
async def rush(request: Request):
    return templates.TemplateResponse(request, "rush.html", {
        "mode": "rush",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/rush/custom", response_class=HTMLResponse)
async def rush_custom(request: Request):
    return templates.TemplateResponse(request, "rush.html", {
        "mode": "rush",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "auto_custom": True,
    })


@app.get("/rush/how-to-play", response_class=HTMLResponse)
async def rush_howto(request: Request):
    return templates.TemplateResponse(request, "rush_howto.html", {
        "mode": "rush-howto",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


# ── Rush Leaderboard API ───────────────────────────────────────────────────────

RUSH_MODES_VALID = {"easy", "normal", "hard", "custom"}

class RushScoreSubmit(BaseModel):
    name:          str = Field(..., min_length=1, max_length=32)
    rush_mode:     str = Field(..., pattern="^(easy|normal|hard|custom)$")
    score:         int = Field(..., ge=0, le=9_999_999)   # elapsed + cleared_mines*5
    cleared_mines: int = Field(..., ge=0, le=99999)
    rows_cleared:  int = Field(0, ge=0, le=99999)
    time_secs:     int = Field(..., ge=1, le=99999)
    cols:          int = Field(..., ge=5, le=30)
    density:       Optional[float] = Field(None, ge=0.0, le=1.0)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable())
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


@app.post("/api/rush-scores", status_code=201)
@limiter.limit("10/minute")
def submit_rush_score(payload: RushScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user  = get_current_user(request)
    guest_token = get_or_create_guest_token(request, user)
    entry = RushScore(
        name          = payload.name,
        user_email    = user["email"] if user else None,
        score         = payload.score,
        cleared_mines = payload.cleared_mines,
        rows_cleared  = payload.rows_cleared,
        time_secs     = payload.time_secs,
        cols          = payload.cols,
        density       = payload.density,
        rush_mode     = payload.rush_mode,
        guest_token   = guest_token,
        client_type   = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    flag_if_profane(db, entry.__tablename__, entry.id, entry.name)
    record_score_submit("rush", payload.rush_mode)
    return {"ok": True, "id": entry.id}


@app.get("/api/rush-scores/{rush_mode}")
def get_rush_scores(rush_mode: str, alltime: bool = False, db: Session = Depends(get_db)):
    if rush_mode not in RUSH_MODES_VALID:
        raise HTTPException(status_code=400, detail="Invalid mode")
    q = db.query(RushScore).filter(RushScore.rush_mode == rush_mode)
    if not alltime:
        q = q.filter(RushScore.created_at >= date.today())
    q = exclude_flagged(q, RushScore, db)
    top = q.order_by(RushScore.score.desc()).limit(15).all()
    return _enrich_with_profiles(top, db)


@app.get("/rush/leaderboard", response_class=HTMLResponse)
async def rush_leaderboard(request: Request):
    return templates.TemplateResponse(request, "rush_leaderboard.html", {
        "mode": "rush",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/help", response_class=HTMLResponse)
async def help_page(request: Request):
    return templates.TemplateResponse(request, "help.html", {
        "mode": "help",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/how-to-play", response_class=HTMLResponse)
async def how_to_play_page(request: Request):
    return templates.TemplateResponse(request, "howtoplay.html", {
        "mode": "how-to-play",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/strategy", response_class=HTMLResponse)
async def strategy_page(request: Request):
    return templates.TemplateResponse(request, "strategy.html", {
        "mode": "strategy",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request, submitted: bool = False):
    return templates.TemplateResponse(request, "contact.html", {
        "mode": "contact",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "submitted": submitted,
    })


@app.post("/contact", response_class=HTMLResponse)
@limiter.limit("5/minute")
async def contact_submit(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...),
):
    name    = name.strip()[:128]
    email   = email.strip()[:256]
    message = message.strip()[:4000]
    if name and email and message:
        db.add(ContactMessage(name=name, email=email, message=message))
        db.commit()
    return RedirectResponse("/contact?submitted=true", status_code=303)


# ── Puzzles hub (All Puzzles) ──────────────────────────────────────────────────

@app.get("/puzzles", response_class=HTMLResponse)
def puzzles_hub(request: Request):
    return templates.TemplateResponse(request, "puzzles.html", {
        "mode": "puzzles",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })

@app.get("/puzzles/tentaizu", response_class=HTMLResponse)
def puzzles_tentaizu_redirect(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/tentaizu"), status_code=301)


@app.get("/puzzles/numbers-match", response_class=HTMLResponse)
def puzzles_numbers_match_redirect(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/numbers-match"), status_code=301)

@app.get("/puzzles/15puzzle", response_class=HTMLResponse)
def puzzles_15puzzle_redirect(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/other/15puzzle"), status_code=301)

@app.get("/puzzles/15-puzzle", response_class=HTMLResponse)
def puzzles_15_puzzle_redirect(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/other/15puzzle"), status_code=301)

@app.get("/puzzles/2048", response_class=HTMLResponse)
def puzzles_2048_redirect(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/other/2048"), status_code=301)

@app.get("/puzzles/2048hex", response_class=HTMLResponse)
def puzzles_2048hex_redirect(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/other/2048hex"), status_code=301)

@app.get("/puzzles/2048-hexagon", response_class=HTMLResponse)
def puzzles_2048_hexagon_redirect(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/other/2048hex"), status_code=301)

@app.get("/puzzles/mahjong", response_class=HTMLResponse)
def puzzles_mahjong_redirect(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/other/mahjong"), status_code=301)

@app.get("/puzzles/mahjong-solitaire", response_class=HTMLResponse)
def puzzles_mahjong_solitaire_redirect(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/other/mahjong"), status_code=301)

@app.get("/puzzles/jigsaw", response_class=HTMLResponse)
def puzzles_jigsaw_redirect(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/other/jigsaw"), status_code=301)

@app.get("/puzzles/schulte", response_class=HTMLResponse)
def puzzles_schulte_redirect(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/other/schulte"), status_code=301)

@app.get("/puzzles/schulte-grid", response_class=HTMLResponse)
def puzzles_schulte_grid_redirect(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/other/schulte"), status_code=301)

@app.get("/puzzles/sudoku", response_class=HTMLResponse)
def puzzles_sudoku_redirect(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/other/sudoku"), status_code=301)

@app.get("/other", response_class=HTMLResponse)
def other_hub_redirect(request: Request):
    return RedirectResponse("/puzzles", status_code=301)


# 15-Puzzle routes are in fifteen_puzzle_routes.py
# Meowdoku routes are in meowdoku_routes.py
# NOTE: meowdoku_router must be included before WC2026/vibecoding routes.

# 15-Puzzle API, generator, photo, member puzzle, and variable grid routes
# are in fifteen_puzzle_routes.py



# 2048 and 2048 Hexagon routes are in game2048_routes.py
# Sudoku routes are in sudoku_routes.py
# Schulte Grid routes are in schulte_routes.py


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    return templates.TemplateResponse(request, "history.html", {
        "mode": "history",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse(request, "about.html", {
        "mode": "about",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


# ── Mobile app landing pages (F83) ────────────────────────────────────────────

@app.get("/mobile", response_class=HTMLResponse)
async def mobile_landing(request: Request):
    return templates.TemplateResponse(request, "mobile.html", {
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })

@app.get("/mobile/ios", response_class=HTMLResponse)
async def mobile_ios_landing(request: Request):
    return templates.TemplateResponse(request, "mobile_ios.html", {
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })

@app.get("/mobile/android", response_class=HTMLResponse)
async def mobile_android_landing(request: Request):
    return templates.TemplateResponse(request, "mobile_android.html", {
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })

@app.get("/mobile/nmmobile", response_class=HTMLResponse)
async def mobile_nmmobile(request: Request):
    real_today = numbers_match_today_str()
    return templates.TemplateResponse(request, "nmmobile.html", {
        "user":       get_current_user(request),
        "today":      real_today,
        "real_today": real_today,
    }, headers={"Cache-Control": "no-store"})


@app.get("/privacy-policy")
async def privacy_policy_redirect():
    return RedirectResponse(url="/privacy", status_code=301)


@app.get("/terms-of-service")
async def terms_of_service_redirect():
    return RedirectResponse(url="/terms", status_code=301)


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    return templates.TemplateResponse(request, "privacy.html", {
        "mode": "privacy",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/piracy", response_class=HTMLResponse)
async def piracy_page(request: Request):
    return templates.TemplateResponse(request, "piracy.html", {
        "mode": "piracy",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    return templates.TemplateResponse(request, "terms.html", {
        "mode": "terms",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth/login")
    profile = db.query(UserProfile).filter(UserProfile.email == user["email"]).first()
    if profile and not profile.public_id:
        profile.public_id = str(uuid.uuid4())
        db.commit()
    return templates.TemplateResponse(request, "profile.html", {
        "mode":          "profile",
        "user":          user,
        "public_id":     profile.public_id if profile else "",
        "is_public":     profile.is_public if profile else False,
        "favorite_game": profile.favorite_game if profile else "",
        "vanity_slug":   profile.vanity_slug if profile else "",
        "pref_sounds":   profile.pref_sounds   if profile else False,
        "pref_chording": profile.pref_chording if profile else True,
        "games_public":  getattr(profile, "games_public", True) if profile else True,
        "pref_skin":     profile.pref_skin     if profile else site_settings.active_skin(),
        "pref_on_win":   profile.pref_on_win   if profile else 'summary',
        "pref_on_lose":  profile.pref_on_lose  if profile else 'summary',
        "about_text":    profile.about_text    if profile else "",
        "country":       profile.country       if profile else "",
        "countries":     ALL_COUNTRIES,
        "wc2026_teams":  WC2026_TEAMS,
        "wc2026_fan":    profile.wc2026_fan    if profile else "",
        "pref_tz":       profile.timezone       if profile else "",
        "fp_photos":      db.query(FifteenPuzzlePhoto).filter_by(user_email=user["email"]).order_by(FifteenPuzzlePhoto.created_at.desc()).all(),
        "fp_limit":       getattr(profile, "puzzle_storage_limit", 32) if profile else 32,
        "jigsaw_saves":   db.query(JigsawSavedGame).filter_by(user_email=user["email"]).order_by(JigsawSavedGame.updated_at.desc()).all(),
        "meowdoku_saves": db.query(MeowdokuSavedPuzzle).filter_by(user_email=user["email"]).order_by(MeowdokuSavedPuzzle.created_at.desc()).all(),
        "today":          datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "lang": get_lang(request), "t": get_t(request),
    })

@app.get("/bootcamp", response_class=HTMLResponse)
async def bootcamp_page(request: Request):
    return templates.TemplateResponse(request, "bootcamp.html", {
        "mode": "bootcamp",
        "user": get_current_user(request),
        "lang": get_lang(request),
        "t": get_t(request),
    })

@app.get("/quests", response_class=HTMLResponse)
async def quests_page(request: Request):
    return templates.TemplateResponse(request, "quests.html", {
        "mode": "quests",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/variants", response_class=HTMLResponse)
async def variants_page(request: Request):
    return templates.TemplateResponse(request, "variants.html", {
        "mode": "variants",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


# ── Replay page ───────────────────────────────────────────────────────────────

@app.get("/variants/replay/", response_class=HTMLResponse)
async def replay_page(request: Request):
    return templates.TemplateResponse(request, "replay.html", {
        "mode": "replay",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


# ── F101 Game View & My Games ─────────────────────────────────────────────────

_MODE_LABELS = {
    "beginner":     "Beginner",
    "intermediate": "Intermediate",
    "expert":       "Expert",
    "evil":         "Evil NG",
    "custom":       "Custom",
    "daily":        "Daily",
    "no-guess":     "No-Guess",
}


@app.get("/game/{game_id}", response_class=HTMLResponse)
async def game_view_page(game_id: int, request: Request, db: Session = Depends(get_db)):
    import json as _json
    replay = db.get(GameReplay, game_id)
    if not replay or not replay.board_hash or not replay.log_json:
        raise HTTPException(status_code=404)

    player_profile = None
    player_name    = "Anonymous"
    player_slug    = None
    player_country = None
    if replay.user_email:
        player_profile = db.query(UserProfile).filter(UserProfile.email == replay.user_email).first()
        if player_profile:
            player_name    = player_profile.display_name
            player_slug    = player_profile.vanity_slug or player_profile.public_id
            player_country = player_profile.country
            if not getattr(player_profile, "games_public", True):
                raise HTTPException(status_code=404)

    try:
        log_data = _json.loads(replay.log_json)
    except Exception:
        raise HTTPException(status_code=404)

    time_secs       = replay.time_ms / 1000 if replay.time_ms else None
    three_bv_per_sec = (
        round(replay.bbbv / time_secs, 3)
        if replay.bbbv and time_secs else None
    )
    total_clicks = (
        (replay.left_clicks or 0)
        + (replay.right_clicks or 0)
        + (replay.chord_clicks or 0)
    )
    efficiency = (
        round(replay.bbbv / total_clicks * 100)
        if replay.bbbv and total_clicks else None
    )

    site_url = str(request.base_url).rstrip("/")
    play_url = None
    if replay.board_hash:
        from urllib.parse import quote as _quote
        play_url = (
            "/variants/replay/?"
            + f"rows={replay.rows}&cols={replay.cols}&mines={replay.mines}"
            + f"&hash={_quote(replay.board_hash, safe='')}"
            + (f"&date={replay.created_at.strftime('%Y-%m-%d')}" if replay.created_at else "")
            + (f"&mode={replay.mode}" if replay.mode else "")
            + "&game=standard"
        )

    return templates.TemplateResponse(request, "game_view.html", {
        "mode":            "game-view",
        "user":            get_current_user(request),
        "lang":            get_lang(request),
        "t":               get_t(request),
        "game_id":         game_id,
        "replay":          replay,
        "log_data":        log_data,
        "player_name":     player_name,
        "player_slug":     player_slug,
        "player_country":  player_country,
        "time_secs":       round(time_secs, 3) if time_secs else None,
        "three_bv_per_sec": three_bv_per_sec,
        "total_clicks":    total_clicks,
        "efficiency":      efficiency,
        "mode_label":      _MODE_LABELS.get(replay.mode or "", replay.mode or "Custom"),
        "site_url":        site_url,
        "play_url":        play_url,
    })


@app.get("/profile/games", response_class=HTMLResponse)
async def my_games_page(request: Request, page: int = Query(1, ge=1),
                         db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login?next=/profile/games", status_code=302)

    PAGE_SIZE = 20
    offset    = (page - 1) * PAGE_SIZE
    q = (
        db.query(GameReplay)
        .filter(
            GameReplay.user_email == user["email"],
            GameReplay.board_hash.isnot(None),
            GameReplay.log_json.isnot(None),
            GameReplay.log_json != "",
        )
    )
    total       = q.count()
    games       = q.order_by(GameReplay.created_at.desc()).offset(offset).limit(PAGE_SIZE).all()
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    return templates.TemplateResponse(request, "my_games.html", {
        "mode":        "my-games",
        "user":        user,
        "lang":        get_lang(request),
        "t":           get_t(request),
        "games":       games,
        "page":        page,
        "total":       total,
        "total_pages": total_pages,
        "page_size":   PAGE_SIZE,
        "mode_labels": _MODE_LABELS,
    })


# ── Links Page ────────────────────────────────────────────────────────────────

@app.get("/links", response_class=HTMLResponse)
async def links_page(request: Request):
    return templates.TemplateResponse(request, "links.html", {
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


# ── 3BV Info ──────────────────────────────────────────────────────────────────

@app.get("/info/3bv", response_class=HTMLResponse)
async def info_3bv_page(request: Request):
    lang = get_lang(request)
    return templates.TemplateResponse(request, "info_3bv.html", {
        "user": get_current_user(request),
        "lang": lang, "t": get_t(request),
        "noindex": lang != "en",
    })


# ── Board Generator ────────────────────────────────────────────────────────────

@app.get("/variants/board-generator", response_class=HTMLResponse)
async def board_generator_page(request: Request):
    return templates.TemplateResponse(request, "board_generator.html", {
        "mode": "board-generator",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "noindex": get_lang(request) != "en",
    })


# ── Replay Score API ──────────────────────────────────────────────────────────

REPLAY_VARIANTS_VALID = {"standard", "no-guess", "cylinder", "toroid"}

class ReplayScoreSubmit(BaseModel):
    board_hash:   str  = Field(..., min_length=1, max_length=128)
    variant:      str  = Field(..., pattern="^(standard|cylinder|toroid)$")
    name:         str  = Field(..., min_length=1, max_length=32)
    time_secs:    int  = Field(..., ge=1, le=999)
    time_ms:      Optional[int]  = Field(None, ge=1, le=3_600_000)
    rows:         int  = Field(..., ge=2,  le=30)
    cols:         int  = Field(..., ge=2,  le=50)
    mines:        int  = Field(..., ge=1,  le=999)
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
        rows = info.data.get("rows")
        cols = info.data.get("cols")
        if rows and cols:
            if v > int(rows * cols * 0.85):
                raise ValueError("Too many mines for this board size")
        return v


@app.post("/api/replay-scores", status_code=201)
@limiter.limit("10/minute")
def submit_replay_score(payload: ReplayScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user  = get_current_user(request)
    guest_token = get_or_create_guest_token(request, user)
    # Reject duplicate: same board + variant + player + time already recorded
    if payload.time_ms:
        dup_q = db.query(ReplayScore.id).filter(
            ReplayScore.board_hash == payload.board_hash,
            ReplayScore.variant    == payload.variant,
            ReplayScore.time_ms    == payload.time_ms,
        )
        if user:
            dup_q = dup_q.filter(ReplayScore.user_email == user["email"])
        else:
            dup_q = dup_q.filter(ReplayScore.guest_token == guest_token)
        existing = dup_q.first()
        if existing:
            return JSONResponse({"ok": True, "id": existing.id}, status_code=200)

    entry = ReplayScore(
        board_hash   = payload.board_hash,
        variant      = payload.variant,
        name         = payload.name,
        user_email   = user["email"] if user else None,
        time_secs    = payload.time_secs,
        time_ms      = payload.time_ms,
        rows         = payload.rows,
        cols         = payload.cols,
        mines        = payload.mines,
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


@app.get("/api/replay-scores")
def get_replay_scores(board_hash: str, variant: str = "standard", db: Session = Depends(get_db)):
    if variant not in REPLAY_VARIANTS_VALID:
        raise HTTPException(status_code=400, detail="Invalid variant")

    # ── Pull from replay_scores ────────────────────────────────────────────────
    sort_key = case(
        (ReplayScore.time_ms.isnot(None), ReplayScore.time_ms),
        else_=ReplayScore.time_secs * 1000
    )
    replay_rows = (
        exclude_flagged(
            db.query(ReplayScore)
            .filter(ReplayScore.board_hash == board_hash, ReplayScore.variant == variant),
            ReplayScore, db)
        .order_by(sort_key.asc(), ReplayScore.created_at.asc())
        .limit(500)
        .all()
    )

    # ── Also pull from the global scores table (standard variant only) ─────────
    global_rows: list = []
    if variant == "standard":
        global_sort = case(
            (Score.time_ms.isnot(None), Score.time_ms),
            else_=Score.time_secs * 1000
        )
        global_rows = (
            db.query(Score)
            .filter(Score.board_hash == board_hash, Score.no_guess == False)
            .order_by(global_sort.asc(), Score.created_at.asc())
            .limit(500)
            .all()
        )
    elif variant == "no-guess":
        global_sort = case(
            (Score.time_ms.isnot(None), Score.time_ms),
            else_=Score.time_secs * 1000
        )
        global_rows = (
            db.query(Score)
            .filter(Score.board_hash == board_hash, Score.no_guess == True)
            .order_by(global_sort.asc(), Score.created_at.asc())
            .limit(500)
            .all()
        )

    # ── Merge: convert all to dicts, sort, deduplicate ─────────────────────────
    def sort_ms(d: dict) -> int:
        return d["time_ms"] if d.get("time_ms") else d["time_secs"] * 1000

    all_dicts = [s.to_dict() for s in replay_rows] + [s.to_dict() for s in global_rows]
    all_dicts.sort(key=sort_ms)

    seen: set = set()
    top: list = []
    for d in all_dicts:
        key = d.get("user_email") or d.get("name")
        if key not in seen:
            seen.add(key)
            top.append(d)
            if len(top) >= 15:
                break

    # ── Enrich with profile URLs ───────────────────────────────────────────────
    emails = [d["user_email"] for d in top if d.get("user_email")]
    url_map: dict = {}
    if emails:
        profiles = (
            db.query(UserProfile.email, UserProfile.vanity_slug, UserProfile.public_id, UserProfile.is_public)
            .filter(UserProfile.email.in_(emails))
            .all()
        )
        for p in profiles:
            if not p.is_public:
                continue
            if p.vanity_slug:
                url_map[p.email] = f"/u/{p.vanity_slug}"
            elif p.public_id:
                url_map[p.email] = f"/u/{p.public_id}"

    for d in top:
        d["profile_url"] = url_map.get(d.get("user_email")) if d.get("user_email") else None

    return top


@app.get("/api/replay-scores/my-first")
def get_my_first_replay_score(board_hash: str, request: Request, variant: str = "standard", db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return None

    email = user["email"]

    if variant not in REPLAY_VARIANTS_VALID:
        raise HTTPException(status_code=400, detail="Invalid variant")

    candidates = []  # list of (orm_row, dict)

    # Pull from replay_scores for this user
    rr = (
        db.query(ReplayScore)
        .filter(ReplayScore.board_hash == board_hash, ReplayScore.variant == variant, ReplayScore.user_email == email)
        .order_by(ReplayScore.created_at.asc())
        .first()
    )
    if rr:
        candidates.append((rr, rr.to_dict()))

    # Pull from global scores table for standard / no-guess
    if variant == "standard":
        gs = (
            db.query(Score)
            .filter(Score.board_hash == board_hash, Score.no_guess == False, Score.user_email == email)
            .order_by(Score.created_at.asc())
            .first()
        )
        if gs:
            candidates.append((gs, gs.to_dict()))
    elif variant == "no-guess":
        gs = (
            db.query(Score)
            .filter(Score.board_hash == board_hash, Score.no_guess == True, Score.user_email == email)
            .order_by(Score.created_at.asc())
            .first()
        )
        if gs:
            candidates.append((gs, gs.to_dict()))

    if not candidates:
        return None

    # Pick the earliest across both sources by raw ORM created_at datetime
    first_row = min(candidates, key=lambda pair: pair[0].created_at)
    return first_row[1]



# PvP leaderboard and rankings API routes are in pvp_leaderboard_routes.py


@app.get("/tentaizu", response_class=HTMLResponse)
async def tentaizu_page(request: Request, date_param: str = Query(None, alias="date")):
    import re
    real_today = date.today().isoformat()
    puzzle_date = real_today
    if date_param and re.match(r"^\d{4}-\d{2}-\d{2}$", date_param):
        puzzle_date = date_param
    return templates.TemplateResponse(request, "tentaizu.html", {
        "mode": "tentaizu",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": puzzle_date,
        "real_today": real_today,
    })


@app.get("/tentaizu/how-to-play", response_class=HTMLResponse)
async def tentaizu_howto(request: Request):
    return templates.TemplateResponse(request, "tentaizu_howto.html", {
        "mode": "tentaizu-howto",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/tentaizu/strategy", response_class=HTMLResponse)
async def tentaizu_strategy(request: Request):
    return templates.TemplateResponse(request, "tentaizu_strategy.html", {
        "mode": "tentaizu-strategy",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/tentaizu/archive", response_class=HTMLResponse)
async def tentaizu_archive(request: Request):
    from datetime import timedelta
    today = date.today()
    past_dates = [(today - timedelta(days=i)).isoformat() for i in range(1, 91)]
    return templates.TemplateResponse(request, "tentaizu_archive.html", {
        "mode": "tentaizu-archive",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today.isoformat(),
        "past_dates": past_dates,
    })


# ── Easy 5×5 mode ─────────────────────────────────────────────────────────────

@app.get("/tentaizu/easy-5x5-6", response_class=HTMLResponse)
async def tentaizu_easy_page(request: Request):
    real_today = date.today().isoformat()
    return templates.TemplateResponse(request, "tentaizu_easy.html", {
        "mode": "tentaizu-easy",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": real_today,
        "real_today": real_today,
    })


@app.get("/tentaizu/easy-5x5-6/{date_str}", response_class=HTMLResponse)
async def tentaizu_easy_permalink(request: Request, date_str: str):
    import re
    real_today = date.today().isoformat()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return RedirectResponse("/tentaizu/easy-5x5-6", status_code=302)
    return templates.TemplateResponse(request, "tentaizu_easy.html", {
        "mode": "tentaizu-easy",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": date_str,
        "real_today": real_today,
        "noindex": True,
    })


# /tentaizu/daily/20260314      →  301 /tentaizu/2026-03-14
# /tentaizu/easy-5x5-6/20260314 →  301 /tentaizu/easy-5x5-6/2026-03-14
@app.get("/tentaizu/{puzzle_type}/{date_str}", response_class=HTMLResponse)
async def tentaizu_type_permalink(request: Request, puzzle_type: str, date_str: str):
    # Allowlist lookup: use the dict value (hardcoded string), not the user input directly
    _valid = {"daily": "daily", "easy-5x5-6": "easy-5x5-6"}
    safe_type = _valid.get(puzzle_type)
    if safe_type is None:
        return RedirectResponse("/tentaizu", status_code=302)
    # YYYYMMDD → convert to YYYY-MM-DD via int() to break taint chain
    m = re.match(r"^(\d{4})(\d{2})(\d{2})$", date_str)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        canonical = f"{y:04d}-{mo:02d}-{d:02d}"
        if safe_type == "daily":
            return RedirectResponse(f"/tentaizu/{canonical}", status_code=301)
        return RedirectResponse(f"/tentaizu/{safe_type}/{canonical}", status_code=301)
    # YYYY-MM-DD for daily → strip type prefix
    m2 = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", date_str)
    if m2:
        y, mo, d = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        safe_date = f"{y:04d}-{mo:02d}-{d:02d}"
        if safe_type == "daily":
            return RedirectResponse(f"/tentaizu/{safe_date}", status_code=301)
    return RedirectResponse("/tentaizu", status_code=302)


# Must be declared AFTER static sub-routes so /tentaizu/how-to-play etc. match first
@app.get("/tentaizu/{date_str}", response_class=HTMLResponse)
async def tentaizu_permalink(request: Request, date_str: str):
    import re
    real_today = date.today().isoformat()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return RedirectResponse("/tentaizu", status_code=302)
    return templates.TemplateResponse(request, "tentaizu.html", {
        "mode": "tentaizu",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": date_str,
        "real_today": real_today,
        "noindex": True,
    })


# Tentaizu leaderboard API routes are in tentaizu_leaderboard_routes.py


def _build_stats(email: str, db: Session) -> dict:
    """Shared stats aggregation used by both private and public profile endpoints."""
    stats = {}

    # Single query for all game history modes, grouped in Python
    all_history = (
        db.query(GameHistory)
        .filter(GameHistory.user_email == email)
        .order_by(GameHistory.created_at.desc())
        .all()
    )
    history_by_mode: dict[str, list] = {}
    for h in all_history:
        history_by_mode.setdefault(h.mode, []).append(h)

    for mode in ["beginner", "intermediate", "expert", "custom"]:
        scores = history_by_mode.get(mode, [])
        if not scores:
            stats[mode] = None
            continue
        times = [s.time_secs for s in scores]
        recent_all = scores[:1000]

        # GameReplay.score_id references Score.id, not GameHistory.id.
        # Join via shared (board_hash, time_ms) fields instead.
        hashes = list({s.board_hash for s in recent_all if s.board_hash})
        replay_map: dict = {}
        if hashes:
            for r in (
                db.query(GameReplay.id, GameReplay.board_hash, GameReplay.time_ms)
                  .filter(
                      GameReplay.user_email == email,
                      GameReplay.board_hash.in_(hashes),
                  )
                  .all()
            ):
                replay_map.setdefault((r.board_hash, r.time_ms), r.id)

        recent_dicts = []
        for s in recent_all:
            d = s.to_dict()
            d["game_id"] = replay_map.get((s.board_hash, s.time_ms)) if s.board_hash and s.time_ms else None
            recent_dicts.append(d)
        stats[mode] = {
            "games_played": len(scores),
            "best_time":    min(times),
            "avg_time":     round(sum(times) / len(times), 1),
            "worst_time":   max(times),
            "recent":       recent_dicts,
        }

    rush_scores = (
        db.query(RushScore)
        .filter(RushScore.user_email == email)
        .order_by(RushScore.created_at.desc())
        .all()
    )
    if rush_scores:
        scores_list = [s.score for s in rush_scores]
        mines_list  = [s.cleared_mines or 0 for s in rush_scores]
        stats["rush"] = {
            "games_played": len(rush_scores),
            "best_score":   max(scores_list),
            "avg_score":    round(sum(scores_list) / len(scores_list), 1),
            "total_mines":  sum(mines_list),
            "recent":       [s.to_dict() for s in rush_scores[:10]],
        }
    else:
        stats["rush"] = None

    tz_scores = (
        db.query(TentaizuScore)
        .filter(TentaizuScore.user_email == email)
        .order_by(TentaizuScore.created_at.desc())
        .all()
    )
    if tz_scores:
        times = [s.time_secs for s in tz_scores]
        stats["tentaizu"] = {
            "games_played": len(tz_scores),
            "best_time":    min(times),
            "avg_time":     round(sum(times) / len(times), 1),
            "recent":       [s.to_dict() for s in tz_scores[:10]],
        }
    else:
        stats["tentaizu"] = None

    # Mosaic stats — standard (9×9) and easy (5×5)
    ms_std  = db.query(MosaicScore).filter(MosaicScore.user_email == email).all()
    ms_easy = db.query(MosaicEasyScore).filter(MosaicEasyScore.user_email == email).all()
    if ms_std or ms_easy:
        stats["mosaic"] = {
            "standard_played": len(ms_std),
            "standard_best":   min(s.time_secs for s in ms_std) if ms_std else None,
            "easy_played":     len(ms_easy),
            "easy_best":       min(s.time_secs for s in ms_easy) if ms_easy else None,
        }
    else:
        stats["mosaic"] = None

    # PvP stats — wins, losses, and Elo rating (single query via UNION COUNT)
    pvp_wins   = db.query(func.count(PvpResult.id)).filter(PvpResult.winner_email == email).scalar() or 0
    pvp_losses = db.query(func.count(PvpResult.id)).filter(PvpResult.loser_email  == email).scalar() or 0
    profile    = db.query(UserProfile).filter(UserProfile.email == email).first()
    pvp_elo    = profile.pvp_elo if profile else 1200
    stats["pvp"] = {
        "wins":   pvp_wins,
        "losses": pvp_losses,
        "elo":    pvp_elo,
    }

    # Hexsweeper stats
    hex_scores = (
        db.query(HexsweeperScore)
        .filter(HexsweeperScore.user_email == email)
        .order_by(HexsweeperScore.created_at.desc())
        .all()
    )
    if hex_scores:
        times = [s.time_ms if s.time_ms else s.time_secs * 1000 for s in hex_scores]
        best  = min(times)
        stats["hexsweeper"] = {
            "games_played": len(hex_scores),
            "best_time_ms": best,
            "best_time":    round(best / 1000, 3),
            "avg_time":     round(sum(times) / len(times) / 1000, 1),
            "recent":       [s.to_dict() for s in hex_scores[:10]],
        }
    else:
        stats["hexsweeper"] = None

    return stats


def _build_bootcamp(email: str, db: Session) -> dict:
    """Last 100 wins per mode/no_guess combo for Bootcamp performance charts."""
    result = {}
    combos = [
        ("beginner",     False),
        ("beginner",     True),
        ("intermediate", False),
        ("intermediate", True),
        ("expert",       False),
        ("expert",       True),
        ("evil",         True),
    ]
    for mode, no_guess in combos:
        key = f"{mode}_ng" if no_guess else mode
        ng_filter = (
            GameHistory.no_guess == True
            if no_guess
            else (GameHistory.no_guess == False) | GameHistory.no_guess.is_(None)
        )
        rows = (
            db.query(GameHistory)
            .filter(
                GameHistory.user_email == email,
                GameHistory.mode == mode,
                ng_filter,
            )
            .order_by(GameHistory.created_at.desc())
            .limit(100)
            .all()
        )
        if not rows:
            result[key] = None
            continue
        rows = list(reversed(rows))  # chronological so chart reads left→right
        result[key] = [
            {
                "ms":   g.time_ms if g.time_ms else g.time_secs * 1000,
                "bbbv": g.bbbv,
                "lc":   g.left_clicks,
                "rc":   g.right_clicks,
                "cc":   g.chord_clicks,
            }
            for g in rows
        ]
    return result


@app.get("/api/profile/bootcamp")
def profile_bootcamp(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    return _build_bootcamp(user["email"], db)


def _build_tametsi_bootcamp(email: str, db: Session) -> dict:
    """Last 100 solved Tametsi games per mode for Bootcamp charts."""
    result = {}
    for level in ("beginner", "intermediate", "expert"):
        rows = (
            db.query(TametsiScore)
            .filter(TametsiScore.user_email == email, TametsiScore.level == level)
            .order_by(TametsiScore.created_at.desc())
            .limit(100)
            .all()
        )
        if not rows:
            result[level] = None
            continue
        rows = list(reversed(rows))
        result[level] = [
            {
                "ms":   r.time_ms,
                "bbbv": r.bbbv,
                "lc":   r.left_clicks,
                "rc":   r.right_clicks,
            }
            for r in rows
        ]
    for key, difficulty in (("wc_easy", "easy"), ("wc_hard", "hard")):
        rows = (
            db.query(WC2026Score)
            .filter(WC2026Score.email == email, WC2026Score.difficulty == difficulty)
            .order_by(WC2026Score.solved_at.desc())
            .limit(100)
            .all()
        )
        if not rows:
            result[key] = None
            continue
        rows = list(reversed(rows))
        result[key] = [
            {
                "ms":   r.solve_time_ms,
                "bbbv": r.bbbv,
                "lc":   r.left_clicks,
                "rc":   r.right_clicks,
            }
            for r in rows
        ]
    return result


@app.get("/api/profile/tametsi-bootcamp")
def profile_tametsi_bootcamp(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    return _build_tametsi_bootcamp(user["email"], db)


@app.get("/api/profile/stats")
def profile_stats(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    return _build_stats(user["email"], db)


@app.get("/api/profile/public-stats/{public_id}")
def public_profile_stats(public_id: str, db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.public_id == public_id).first()
    if not profile or not profile.is_public:
        return JSONResponse({"error": "Profile not found"}, status_code=404)
    return _build_stats(profile.email, db)


class ProfileSettingsUpdate(BaseModel):
    is_public:     bool
    favorite_game: Optional[str] = None
    pref_sounds:   bool = False
    pref_chording: bool = True
    pref_skin:     str  = site_settings.active_skin()
    pref_on_win:   str  = 'summary'
    pref_on_lose:  str  = 'summary'
    games_public:  bool = True


@app.post("/api/profile/settings")
def update_profile_settings(payload: ProfileSettingsUpdate, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    profile = db.query(UserProfile).filter(UserProfile.email == user["email"]).first()
    if not profile:
        return JSONResponse({"error": "Profile not found"}, status_code=404)
    profile.is_public     = payload.is_public
    profile.favorite_game = payload.favorite_game or None
    profile.pref_sounds   = payload.pref_sounds
    profile.pref_chording = payload.pref_chording
    if hasattr(profile, "games_public"):
        profile.games_public = payload.games_public
    _skin = payload.pref_skin if payload.pref_skin in site_settings.ALLOWED_SKINS else site_settings.DEFAULT_SKIN
    profile.pref_skin     = 'classic' if _skin == 'diana' else _skin
    profile.pref_on_win   = payload.pref_on_win  if payload.pref_on_win  in ('summary', 'new_game') else 'summary'
    profile.pref_on_lose  = payload.pref_on_lose if payload.pref_on_lose in ('summary', 'new_game') else 'summary'
    db.commit()
    return {"ok": True, "public_id": profile.public_id}


@app.get("/api/profile/prefs")
def get_profile_prefs(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    profile = db.query(UserProfile).filter(UserProfile.email == user["email"]).first()
    return {
        "on_win":  profile.pref_on_win  if profile else "summary",
        "on_lose": profile.pref_on_lose if profile else "summary",
    }


@app.get("/u/{slug}", response_class=HTMLResponse)
async def public_profile_page(request: Request, slug: str, db: Session = Depends(get_db)):
    # Accept either vanity slug or UUID
    profile = (
        db.query(UserProfile).filter(UserProfile.vanity_slug == slug).first()
        or db.query(UserProfile).filter(UserProfile.public_id == slug).first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not profile.is_public:
        return templates.TemplateResponse(request, "profile_private.html", {
            "display_name": profile.display_name or "This player",
            "lang": get_lang(request), "t": get_t(request),
        }, status_code=200)
    return templates.TemplateResponse(request, "profile_public.html", {
        "mode":          "profile",
        "display_name":  profile.display_name,
        "favorite_game": profile.favorite_game or "",
        "public_id":     profile.public_id,
        "vanity_slug":   profile.vanity_slug or "",
        "about_text":    profile.about_text or "",
        "noindex":       True,
        "lang": get_lang(request), "t": get_t(request),
    })


class VanitySlugUpdate(BaseModel):
    vanity_slug: str = Field("", max_length=32)

    @field_validator("vanity_slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        import re
        v = v.strip().lower()
        if v and not re.match(r'^[a-z0-9_-]+$', v):
            raise ValueError("Slug may only contain letters, numbers, hyphens, and underscores")
        return v


@app.post("/api/profile/vanity-slug")
def update_vanity_slug(payload: VanitySlugUpdate, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    profile = db.query(UserProfile).filter(UserProfile.email == user["email"]).first()
    if not profile:
        return JSONResponse({"error": "Profile not found"}, status_code=404)
    slug = payload.vanity_slug or None
    if slug:
        taken = db.query(UserProfile).filter(
            UserProfile.vanity_slug == slug,
            UserProfile.email != user["email"]
        ).first()
        if taken:
            return JSONResponse({"error": "That vanity URL is already taken"}, status_code=409)
    profile.vanity_slug = slug
    db.commit()
    return {"ok": True, "vanity_slug": slug}


class DisplayNameUpdate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=32)

    @field_validator("display_name")
    @classmethod
    def sanitize(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable())
        if not v:
            raise ValueError("Display name must contain printable characters")
        return v[:32]


@app.get("/api/profile/display-name")
def get_display_name(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    return {"display_name": user.get("display_name", user.get("name", ""))}


@app.post("/api/profile/display-name")
def update_display_name(payload: DisplayNameUpdate, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    email = user["email"]
    profile = db.query(UserProfile).filter(UserProfile.email == email).first()
    if not profile:
        profile = UserProfile(email=email, display_name=payload.display_name)
        db.add(profile)
    else:
        profile.display_name = payload.display_name
    db.commit()
    # Update session so the new name is used immediately
    request.session["user"]["display_name"] = payload.display_name
    return {"ok": True, "display_name": payload.display_name}


class AboutTextUpdate(BaseModel):
    about_text: str = Field("", max_length=5000)


@app.post("/api/profile/about")
def update_about(payload: AboutTextUpdate, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    profile = db.query(UserProfile).filter(UserProfile.email == user["email"]).first()
    if not profile:
        return JSONResponse({"error": "Profile not found"}, status_code=404)
    profile.about_text = payload.about_text.strip() or None
    db.commit()
    return {"ok": True}


VALID_COUNTRIES = VALID_COUNTRY_CODES

class CountryUpdate(BaseModel):
    country: Optional[str] = None

@app.post("/api/profile/country")
def update_country(payload: CountryUpdate, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    profile = db.query(UserProfile).filter(UserProfile.email == user["email"]).first()
    if not profile:
        return JSONResponse({"error": "Profile not found"}, status_code=404)
    code = (payload.country or "").strip().lower() or None
    if code and code not in VALID_COUNTRIES:
        return JSONResponse({"error": "Invalid country code"}, status_code=400)
    profile.country = code
    db.commit()
    return {"ok": True}


# Valid IANA timezone strings accepted from the profile form
_VALID_TIMEZONES: frozenset = frozenset({
    # Americas
    "America/New_York", "America/Chicago", "America/Denver",
    "America/Los_Angeles", "America/Anchorage", "Pacific/Honolulu",
    "America/Phoenix", "America/Toronto", "America/Vancouver",
    "America/Mexico_City", "America/Sao_Paulo",
    "America/Argentina/Buenos_Aires", "America/Bogota", "America/Lima",
    "America/Santiago", "America/Caracas", "America/Halifax",
    # Europe
    "Europe/London", "Europe/Dublin", "Europe/Lisbon",
    "Europe/Paris", "Europe/Berlin", "Europe/Amsterdam",
    "Europe/Madrid", "Europe/Rome", "Europe/Warsaw",
    "Europe/Kyiv", "Europe/Moscow", "Europe/Istanbul",
    "Europe/Athens", "Europe/Stockholm", "Europe/Helsinki",
    "Europe/Bucharest", "Europe/Prague", "Europe/Budapest",
    # Africa / Middle East
    "Africa/Cairo", "Africa/Nairobi", "Africa/Lagos",
    "Africa/Johannesburg", "Asia/Dubai", "Asia/Riyadh", "Asia/Jerusalem",
    # Asia / Pacific
    "Asia/Karachi", "Asia/Kolkata", "Asia/Colombo",
    "Asia/Dhaka", "Asia/Yangon", "Asia/Bangkok",
    "Asia/Singapore", "Asia/Shanghai", "Asia/Hong_Kong",
    "Asia/Taipei", "Asia/Tokyo", "Asia/Seoul",
    "Australia/Perth", "Australia/Darwin", "Australia/Adelaide",
    "Australia/Sydney", "Australia/Brisbane", "Pacific/Auckland",
    "Pacific/Fiji", "Pacific/Guam",
})

class TimezoneUpdate(BaseModel):
    timezone: str = ""

@app.post("/api/profile/timezone")
def update_timezone(payload: TimezoneUpdate, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    tz = (payload.timezone or "").strip() or None
    if tz and tz not in _VALID_TIMEZONES:
        return JSONResponse({"error": "Invalid timezone"}, status_code=400)
    profile = db.query(UserProfile).filter(UserProfile.email == user["email"]).first()
    if not profile:
        return JSONResponse({"error": "Profile not found"}, status_code=404)
    profile.timezone = tz
    db.commit()
    return {"ok": True}





# ── Public Pattern Wiki ──────────────────────────────────────────────────────

@app.get("/patterns", response_class=HTMLResponse)
def patterns_index(request: Request, db: Session = Depends(get_db)):
    rows = (
        db.query(Pattern)
        .filter(Pattern.status == "published")
        .order_by(Pattern.section, Pattern.sort_order, Pattern.name)
        .all()
    )
    by_section: dict[str, list] = {}
    for p in rows:
        by_section.setdefault(p.section, []).append(p)
    return templates.TemplateResponse(request, "patterns_index.html", {
        "user": get_current_user(request),
        "lang": get_lang(request),
        "t":    get_t(request),
        "patterns_by_section": by_section,
        "sections":            _PATTERN_SECTIONS,
        "mode":                "patterns",
    })


@app.get("/patterns/{slug}", response_class=HTMLResponse)
def patterns_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    pattern = db.query(Pattern).filter_by(slug=slug).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    user = get_current_user(request)
    is_editor = user_has_role(db, user, "pattern_editor")

    # Drafts are visible only to editors/admins.
    if pattern.status != "published" and not is_editor:
        raise HTTPException(status_code=404, detail="Pattern not found")

    variants = (
        db.query(Pattern)
        .filter(Pattern.parent_slug == pattern.slug,
                Pattern.status == "published")
        .order_by(Pattern.sort_order, Pattern.name)
        .all()
    )
    parent = None
    if pattern.parent_slug:
        parent = db.query(Pattern).filter_by(slug=pattern.parent_slug).first()

    import markdown as md_lib
    body_html = md_lib.markdown(pattern.body_md or "", extensions=["extra", "sane_lists"])

    return templates.TemplateResponse(request, "pattern_detail.html", {
        "user":      user,
        "lang":      get_lang(request),
        "t":         get_t(request),
        "pattern":   pattern,
        "parent":    parent,
        "variants":  variants,
        "body_html": body_html,
        "is_editor": is_editor,
        "mode":      "patterns",
    })




# Nonosweeper score API routes are in nonosweeper_routes.py
# NOTE: nonosweeper_router is registered before the 3-segment archive catch-all.


# ── Archive routes (must be last — parameterised path catches all 3-segment URLs) ─

_DATE_DAILY_RE   = __import__("re").compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_MONTHLY_RE = __import__("re").compile(r"^\d{4}-\d{2}$")

# All 3-segment routes must be defined before /{mode}/{date_str}/{guess_mode}
# below, which is a wildcard catch-all that would intercept them first.
# Numbers match API routes are in numbers_match_routes.py


@app.get("/{mode}/{date_str}/{guess_mode}", response_class=HTMLResponse)
async def archive_day(
    request: Request,
    mode: str,
    date_str: str,
    guess_mode: str,
    db: Session = Depends(get_db),
):
    if mode not in ARCHIVE_MODES or guess_mode not in ("guess", "no_guess"):
        raise HTTPException(status_code=404)

    is_daily   = bool(_DATE_DAILY_RE.match(date_str))
    is_monthly = bool(_DATE_MONTHLY_RE.match(date_str)) and not is_daily

    if not is_daily and not is_monthly:
        raise HTTPException(status_code=404)

    no_guess = guess_mode == "no_guess"

    try:
        if is_daily:
            target = date.fromisoformat(date_str)
            scores = _get_archive_scores_day(db, mode, target, no_guess)
            # prev / next dates with any auth score for this mode
            prev_row = (
                db.query(func.max(cast(Score.created_at, SQLDate)))
                .filter(Score.mode == mode, Score.user_email.isnot(None),
                        cast(Score.created_at, SQLDate) < target)
                .scalar()
            )
            next_row = (
                db.query(func.min(cast(Score.created_at, SQLDate)))
                .filter(Score.mode == mode, Score.user_email.isnot(None),
                        cast(Score.created_at, SQLDate) > target,
                        Score.created_at <= datetime.now(timezone.utc))
                .scalar()
            )
            prev_date = str(prev_row) if prev_row else None
            next_date = str(next_row) if next_row else None
            period_label = date_str
        else:
            parts = date_str.split("-")
            year, month = int(parts[0]), int(parts[1])
            if not (1 <= month <= 12):
                raise ValueError("bad month")
            scores = _get_archive_scores_month(db, mode, year, month, no_guess)
            prev_date = next_date = None
            period_label = date_str
    except (ValueError, IndexError):
        raise HTTPException(status_code=404)

    enriched = _enrich_archive(scores)
    mode_cap = mode.capitalize()
    ng_label = " No-Guess" if no_guess else ""
    period_word = "Monthly" if is_monthly else "Daily"
    _title = f"{mode_cap}{ng_label} {period_word} Scores — {date_str}"
    _desc  = (f"Top {mode_cap} minesweeper times for {date_str}"
              f"{' (No-Guess)' if no_guess else ''}. "
              "Server-rendered leaderboard of registered players.")
    _canon = f"https://minesweeper.org/{mode}/{date_str}/{guess_mode}"

    return templates.TemplateResponse(request, "archive_day.html", {
        "mode":         mode,
        "date_str":     date_str,
        "guess_mode":   guess_mode,
        "no_guess":     no_guess,
        "is_daily":     is_daily,
        "is_monthly":   is_monthly,
        "scores":       enriched,
        "prev_date":    prev_date,
        "next_date":    next_date,
        "period_label": period_label,
        "user":         get_current_user(request),
        "lang":         get_lang(request),
        "t":            get_t(request),
        "_title":       _title,
        "_desc":        _desc,
        "_canon":       _canon,
        "noindex":      True,
    })

# Nonosweeper page routes are in nonosweeper_routes.py


# ── MVS static pages ──────────────────────────────────────────────────────────

_MVS_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "static", "mvs"))


@app.get("/mvs")
def mvs_root():
    return RedirectResponse("/mvs/index.html", status_code=302)


# Numbers Match page and score routes are in numbers_match_routes.py


@app.get("/mvs/{path:path}")
def mvs_static(path: str):
    resolved = os.path.realpath(os.path.join(_MVS_DIR, path))
    if not resolved.startswith(_MVS_DIR + os.sep):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not os.path.isfile(resolved):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(resolved)





# ── Vibe Coding talk ──────────────────────────────────────────────────────────

@app.get("/vibecoding", response_class=HTMLResponse)
def vibecoding_talk(request: Request):
    return templates.TemplateResponse(request, "vibecoding.html")

@app.get("/vibecoding/booth", response_class=HTMLResponse)
def vibecoding_booth(request: Request):
    return templates.TemplateResponse(request, "vibecoding_booth.html")
