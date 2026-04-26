from datetime import date, timedelta, datetime, timezone
import uuid
import re
import subprocess
import os
from typing import Optional
from fastapi import FastAPI, Request, Depends, HTTPException, Query, Response, Form, File, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.gzip import GZipMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, case, text, cast, Date as SQLDate
from pydantic import BaseModel, Field, field_validator
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from database import Score, GameHistory, GameMode, RushScore, TentaizuScore, TentaizuEasyScore, MosaicScore, MosaicEasyScore, MosaicCustomScore, CylinderScore, ToroidScore, HexsweeperScore, GlobesweeperScore, CubesweeperScore, MobiussweeperScore, ReplayScore, UserProfile, PvpResult, ServerStats, WebTrafficStats, GuestScoreArchive, BlogComment, NonosweeperScore, ContactMessage, FifteenPuzzleScore, FifteenPuzzlePhoto, Game2048Score, Game2048HexScore, MahjongScore, MahjongSavedGame, JigsawScore, JigsawSavedGame, JigsawPhoto, SchulteGridScore, SudokuScore, GameReplay, get_db, init_db, SessionLocal
import database as _db_module
from duel_routes import duel_router
from duel import cleanup_old_games
from auth import oauth, get_current_user, set_session_user, clear_session, SECRET_KEY
from starlette.config import Config
from translations import get_lang, get_t
import settings as site_settings
import logging
import psutil
import threading
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

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
        ),
        # 'self' covers same-origin WebSockets (wss://minesweeper.org/ws/…)
        # Broad Google/AdSense domains — bidding partners use many subdomains
        (
            "connect-src 'self'"
            " https://www.google-analytics.com"
            " https://region1.google-analytics.com"
            " https://*.googlesyndication.com"
            " https://*.doubleclick.net"
            " https://*.google.com"
            " https://*.googleadservices.com"
            " https://*.googlevideo.com"
        ),
        # AdSense renders ad creatives inside iframes from these domains
        "frame-src https://googleads.g.doubleclick.net https://tpc.googlesyndication.com",
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
        while url and url[-1] in '.,;:!?)\]\'\"':
            url = url[:-1]
        return '<a href="{u}" target="_blank" rel="noopener noreferrer">{u}</a>'.format(u=url)
    return Markup(re.sub(r'https?://[^\s<>"\'\x00-\x1f]+', _replace, safe))

templates.env.filters['autolink'] = _autolink

# ── BreadcrumbList structured data ───────────────────────────────────────────
# Maps URL path → list of (name, relative-path) pairs for crumb levels 2+.
# Home is always level 1 and is prepended automatically.
# Blog post detail pages (/blog/<slug>) are intentionally absent — blog_post.html
# provides its own 3-level override that includes the post title.
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs

templates.env.globals["get_breadcrumbs"] = _get_breadcrumbs


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse(
        "404.html",
        {"request": request, "mode": "404",
         "user": get_current_user(request),
         "lang": get_lang(request), "t": get_t(request)},
        status_code=404,
    )

@app.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    return templates.TemplateResponse(
        "403.html",
        {"request": request, "mode": "403",
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


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import FileResponse
    return FileResponse("static/favicon.svg", media_type="image/svg+xml")


@app.get("/robots.txt", include_in_schema=False)
async def robots():
    content = (
        "User-agent: *\n"
        "Allow: /\n\n"
        "Disallow: /game/\n"
        "Disallow: /duel/room/\n"
        "Disallow: /api/\n"
        "Disallow: /ws/\n"
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
async def sitemap(request: Request):
    return templates.TemplateResponse(
        "sitemap.xml",
        {"request": request, "today": date.today().isoformat(), "blog_posts": BLOG_POSTS},
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

CYLINDER_MODES = {
    "cylinder-beginner":     {"rows": 9, "cols": 9, "mines": 10},
    "cylinder-intermediate": {"rows": 16, "cols": 16, "mines": 40},
    "cylinder-expert":       {"rows": 16, "cols": 30, "mines": 99},
}

TOROID_MODES = {
    "toroid-beginner":     {"rows": 9, "cols": 9, "mines": 10},
    "toroid-intermediate": {"rows": 16, "cols": 16, "mines": 40},
    "toroid-expert":       {"rows": 16, "cols": 30, "mines": 99},
}

ARCHIVE_MODES = {"beginner", "intermediate", "expert"}

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
    db = SessionLocal()
    try:
        existing = {str(r.stat_date) for r in db.query(WebTrafficStats.stat_date).all()}
    finally:
        db.close()
    d = _TRAFFIC_ARCHIVE_START
    while d <= yesterday:
        if str(d) not in existing:
            collect_web_traffic_stats(target_date=d)
        d += timedelta(days=1)


def archive_guest_scores():
    """Archive (move) all guest scores to guest_score_archive at midnight UTC."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        tables = [
            (Score,             "scores",             "mode"),
            (RushScore,         "rush_scores",         "rush_mode"),
            (CylinderScore,     "cylinder_scores",     "cyl_mode"),
            (ToroidScore,       "toroid_scores",       "tor_mode"),
            (TentaizuScore,     "tentaizu_scores",     "puzzle_date"),
            (ReplayScore,       "replay_scores",       "variant"),
            (NonosweeperScore,    "nonosweeper_scores",    "puzzle_date"),
            (FifteenPuzzleScore,  "fifteen_puzzle_scores", "puzzle_date"),
            (Game2048Score,       "game_2048_scores",      "puzzle_date"),
            (MahjongScore,        "mahjong_scores",        "puzzle_date"),
        ]
        total = 0
        for model, table_name, mode_attr in tables:
            guests = db.query(model).filter(model.user_email.is_(None)).all()
            for row in guests:
                db.add(GuestScoreArchive(
                    source_table        = table_name,
                    original_id         = row.id,
                    guest_token         = getattr(row, "guest_token", None),
                    name                = row.name,
                    game_mode           = str(getattr(row, mode_attr, "")),
                    time_ms             = getattr(row, "time_ms", None) or (getattr(row, "time_secs", 0) * 1000 if hasattr(row, "time_secs") else None),
                    rows                = getattr(row, "rows", None),
                    cols                = getattr(row, "cols", None),
                    mines               = getattr(row, "mines", None),
                    bbbv                = getattr(row, "bbbv", None),
                    board_hash          = getattr(row, "board_hash", None),
                    original_created_at = row.created_at,
                    archived_at         = now,
                ))
                db.delete(row)
                total += 1
        db.commit()
        logger.info(f"archive_guest_scores: archived {total} guest score(s).")
        record_scheduler_run("archive_guest_scores", success=True)
    except Exception as e:
        db.rollback()
        logger.error(f"archive_guest_scores failed: {e}")
        record_scheduler_run("archive_guest_scores", success=False)
    finally:
        db.close()


scheduler = BackgroundScheduler(timezone="UTC")
scheduler.add_job(archive_guest_scores,        CronTrigger(hour=23, minute=59)) # 23:59 UTC — archive guests before reset
scheduler.add_job(reset_scores,               CronTrigger(hour=0,  minute=0))  # midnight UTC — clear all scores
scheduler.add_job(cleanup_old_games,          CronTrigger(hour="*"))             # hourly
scheduler.add_job(collect_server_stats,       CronTrigger(minute=0))             # top of every hour
scheduler.add_job(collect_web_traffic_stats,  CronTrigger(hour=1,  minute=0))   # 1 AM UTC — parse yesterday's logs

# Create DB tables and start scheduler on startup
@app.on_event("startup")
def startup():
    init_db()
    scheduler.start()
    logger.info("Scheduler started — scores reset daily at midnight UTC.")
    threading.Thread(target=_backfill_web_traffic, daemon=True).start()

@app.on_event("shutdown")
def shutdown():
    scheduler.shutdown()
    logger.info("Scheduler shut down.")

# ── Page Routes ───────────────────────────────────────────────────────────────

@app.get("/set-lang")
async def set_lang(request: Request, lang: str = "en", next: Optional[str] = None):
    if lang not in ("en", "eo", "de", "es", "th", "pgl", "uk", "fr", "ko", "ja", "zh", "zh-hant", "pl", "tl", "ru", "pt", "it"):
        lang = "en"
    # Use explicit next param, then referer, then home
    redirect_to = next or request.headers.get("referer", "/")
    # Safety: only allow relative URLs to prevent open redirect
    # Block absolute (http/https) and protocol-relative (//evil.com) URLs
    if not redirect_to.startswith("/") or redirect_to.startswith("//"):
        redirect_to = "/"
    response = RedirectResponse(url=redirect_to)
    response.set_cookie("lang", lang, max_age=365 * 24 * 3600, samesite="lax")
    return response


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, "mode": "beginner",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **GAME_MODES["beginner"]
    })

@app.get("/intermediate", response_class=HTMLResponse)
async def intermediate(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, "mode": "intermediate",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **GAME_MODES["intermediate"]
    })

@app.get("/expert", response_class=HTMLResponse)
async def expert(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, "mode": "expert",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **GAME_MODES["expert"]
    })

@app.get("/custom", response_class=HTMLResponse)
async def custom(request: Request):
    return templates.TemplateResponse("custom.html", {
        "request": request, "mode": "custom",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })

@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(request: Request):
    return templates.TemplateResponse("leaderboard.html", {
        "request": request, "mode": "leaderboard",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })

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
    return templates.TemplateResponse("archive_index.html", {
        "request":       request,
        "mode":          "archive",
        "user":          get_current_user(request),
        "lang":          get_lang(request),
        "t":             get_t(request),
        "recent_days":   recent_days,
        "recent_months": recent_months,
        "today":         str(date.today()),
    })

# ── Auth routes ───────────────────────────────────────────────────────────────

@app.get("/auth/login")
async def login(request: Request):
    next_url = request.query_params.get("next", "/")
    # Reject absolute URLs to prevent open-redirect phishing via OAuth flow
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = "/"
    request.session["next"] = next_url
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
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
            db.commit()

    next_url = request.session.pop("next", "/")
    return RedirectResponse(url=next_url)

@app.get("/auth/logout")
async def logout(request: Request):
    clear_session(request)
    return RedirectResponse(url="/")

# ── Leaderboard API ───────────────────────────────────────────────────────────

class ScoreSubmit(BaseModel):
    name:         str = Field(..., min_length=1, max_length=32)
    mode:         GameMode
    time_secs:    int = Field(..., ge=1, le=999)
    time_ms:      Optional[int]  = Field(None, ge=1, le=3_600_000)
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
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
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
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None

    client_type = get_client_type(request)
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

    db.commit()
    db.refresh(score)
    record_score_submit("minesweeper", payload.mode.value)
    record_game_complete("minesweeper", mode=payload.mode.value,
                         duration_ms=payload.time_ms or (payload.time_secs or 0) * 1000)
    return {"ok": True, "id": score.id}


def _enrich_with_profiles(scores: list, db) -> list:
    """Add profile_url to score dicts for entries with a user_email."""
    emails = [s.user_email for s in scores if s.user_email]
    if not emails:
        return [s.to_dict() for s in scores]

    profiles = (
        db.query(UserProfile.email, UserProfile.vanity_slug, UserProfile.public_id, UserProfile.is_public)
        .filter(UserProfile.email.in_(emails))
        .all()
    )
    url_map: dict = {}
    for p in profiles:
        if not p.is_public:
            continue
        if p.vanity_slug:
            url_map[p.email] = f"/u/{p.vanity_slug}"
        elif p.public_id:
            url_map[p.email] = f"/u/{p.public_id}"

    result = []
    for s in scores:
        d = s.to_dict()
        d["profile_url"] = url_map.get(s.user_email) if s.user_email else None
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
    won:        bool           = False
    log:        list           = Field(...)  # [[t_ms, type, r, c], …]

    @field_validator("log")
    @classmethod
    def validate_log(cls, v):
        if len(v) > 10_000:
            raise ValueError("Log too large")
        return v


@app.post("/api/rewind", status_code=201)
@limiter.limit("30/minute")
def submit_rewind(payload: RewindSubmit, request: Request, db: Session = Depends(get_db)):
    import json as _json
    user = get_current_user(request)
    replay = GameReplay(
        user_email = user["email"] if user else None,
        mode       = payload.mode,
        rows       = payload.rows,
        cols       = payload.cols,
        mines      = payload.mines,
        no_guess   = payload.no_guess,
        board_hash = payload.board_hash,
        time_ms    = payload.time_ms,
        log_json   = _json.dumps(payload.log, separators=(',', ':')),
    )
    db.add(replay)
    db.commit()
    db.refresh(replay)
    return {"id": replay.id}


@app.get("/api/scores/{mode}")
def get_scores(mode: GameMode, no_guess: bool = False,
               period: str = "daily",
               score_date: Optional[str] = Query(None, alias="date"),
               season_num: Optional[int] = Query(None),
               db: Session = Depends(get_db),
               response: Response = None):
    if period not in ("daily", "season", "alltime"):
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

    if period == "daily":
        try:
            target = date.fromisoformat(score_date) if score_date else date.today()
        except ValueError:
            target = date.today()
        q = q.filter(Score.created_at >= target, Score.created_at < target + timedelta(days=1))
        top = q.order_by(sort_key.asc(), Score.created_at.asc()).limit(15).all()
        return _enrich_with_profiles(top, db)

    if period == "season":
        if season_num and season_num >= 1:
            s_start, s_end = get_season_range(season_num)
            q = q.filter(Score.created_at >= s_start, Score.created_at < s_end)
        else:
            today = date.today()
            q = q.filter(Score.created_at >= today.replace(day=1))

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
    return templates.TemplateResponse("rush.html", {
        "request": request, "mode": "rush",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/rush/custom", response_class=HTMLResponse)
async def rush_custom(request: Request):
    return templates.TemplateResponse("rush.html", {
        "request": request, "mode": "rush",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "auto_custom": True,
    })


@app.get("/rush/how-to-play", response_class=HTMLResponse)
async def rush_howto(request: Request):
    return templates.TemplateResponse("rush_howto.html", {
        "request": request, "mode": "rush-howto",
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
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


@app.post("/api/rush-scores", status_code=201)
@limiter.limit("10/minute")
def submit_rush_score(payload: RushScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user  = get_current_user(request)
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None
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
    record_score_submit("rush", payload.rush_mode)
    return {"ok": True, "id": entry.id}


@app.get("/api/rush-scores/{rush_mode}")
def get_rush_scores(rush_mode: str, alltime: bool = False, db: Session = Depends(get_db)):
    if rush_mode not in RUSH_MODES_VALID:
        raise HTTPException(status_code=400, detail="Invalid mode")
    q = db.query(RushScore).filter(RushScore.rush_mode == rush_mode)
    if not alltime:
        q = q.filter(RushScore.created_at >= date.today())
    top = q.order_by(RushScore.score.desc()).limit(15).all()
    return _enrich_with_profiles(top, db)


@app.get("/rush/leaderboard", response_class=HTMLResponse)
async def rush_leaderboard(request: Request):
    return templates.TemplateResponse("rush_leaderboard.html", {
        "request": request, "mode": "rush",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/help", response_class=HTMLResponse)
async def help_page(request: Request):
    return templates.TemplateResponse("help.html", {
        "request": request, "mode": "help",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/how-to-play", response_class=HTMLResponse)
async def how_to_play_page(request: Request):
    return templates.TemplateResponse("howtoplay.html", {
        "request": request, "mode": "how-to-play",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/strategy", response_class=HTMLResponse)
async def strategy_page(request: Request):
    return templates.TemplateResponse("strategy.html", {
        "request": request, "mode": "strategy",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request, submitted: bool = False):
    return templates.TemplateResponse("contact.html", {
        "request": request, "mode": "contact",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "submitted": submitted,
    })


@app.post("/contact", response_class=HTMLResponse)
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


# ── Other Puzzles ──────────────────────────────────────────────────────────────

@app.get("/other", response_class=HTMLResponse)
def other_hub(request: Request):
    return templates.TemplateResponse("other.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/other/15puzzle", response_class=HTMLResponse)
def fifteen_puzzle_landing(request: Request):
    return RedirectResponse("/other/15puzzle/daily", status_code=302)


@app.get("/other/15puzzle/daily", response_class=HTMLResponse)
def fifteen_puzzle_daily(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse("fifteen_puzzle_daily.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today,
    })


@app.get("/other/15puzzle/leaderboard", response_class=HTMLResponse)
def fifteen_puzzle_leaderboard_page(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse("fifteen_puzzle_leaderboard.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today,
    })


@app.get("/other/15puzzle/how-to-play", response_class=HTMLResponse)
def fifteen_puzzle_howtoplay(request: Request):
    return templates.TemplateResponse("fifteen_puzzle_howtoplay.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


# ── 15-Puzzle API ──────────────────────────────────────────────────────────────

class FifteenPuzzleScoreSubmit(BaseModel):
    name:        str = Field(..., min_length=1, max_length=32)
    puzzle_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    time_ms:     int = Field(..., ge=0, le=9999999)
    moves:       int = Field(..., ge=1, le=99999)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


@app.post("/api/fifteen-puzzle-scores", status_code=201)
@limiter.limit("10/minute")
def submit_fifteen_puzzle_score(payload: FifteenPuzzleScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None
    entry = FifteenPuzzleScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        puzzle_date = payload.puzzle_date,
        time_ms     = payload.time_ms,
        moves       = payload.moves,
        guest_token = guest_token,
        client_type = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    record_score_submit("fifteen_puzzle", payload.puzzle_date)
    record_game_complete("fifteen_puzzle", mode="daily", duration_ms=payload.time_ms)
    return {"ok": True, "id": entry.id}


@app.get("/api/fifteen-puzzle-scores/{puzzle_date}")
def get_fifteen_puzzle_scores(puzzle_date: str, db: Session = Depends(get_db)):
    import re
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", puzzle_date):
        raise HTTPException(status_code=400, detail="Invalid date format")
    top = (
        db.query(FifteenPuzzleScore)
        .filter(FifteenPuzzleScore.puzzle_date == puzzle_date)
        .order_by(FifteenPuzzleScore.time_ms.asc(), FifteenPuzzleScore.created_at.asc())
        .limit(20)
        .all()
    )
    return _enrich_with_profiles(top, db)


@app.get("/other/15puzzle/generator", response_class=HTMLResponse)
def fifteen_puzzle_generator_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    photos = []
    limit = 32
    if user:
        photos = (
            db.query(FifteenPuzzlePhoto)
            .filter_by(user_email=user["email"])
            .order_by(FifteenPuzzlePhoto.created_at.desc())
            .all()
        )
        profile = db.query(UserProfile).filter_by(email=user["email"]).first()
        limit = getattr(profile, "puzzle_storage_limit", 32) if profile else 32
    return templates.TemplateResponse("fifteen_puzzle_generator.html", {
        "request": request, "mode": "other",
        "user": user,
        "lang": get_lang(request), "t": get_t(request),
        "photos": photos,
        "limit": limit,
    })


@app.get("/other/15puzzle/photo/{board_hash}", response_class=HTMLResponse)
def fifteen_puzzle_photo_play(request: Request, board_hash: str, mode: str = Query("tiles"), db: Session = Depends(get_db)):
    import re
    if not re.match(r'^[A-Za-z0-9_\-]{10,128}$', board_hash):
        raise HTTPException(status_code=404, detail="Not found")
    photo = db.query(FifteenPuzzlePhoto).filter_by(board_hash=board_hash).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Puzzle not found")
    if mode not in ("tiles", "reveal"):
        mode = photo.photo_mode
    return templates.TemplateResponse("fifteen_puzzle_daily.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": date.today().isoformat(),
        "photo_url": f"/static/uploads/15puzzle/{photo.filename}",
        "photo_mode": mode,
        "board_hash": board_hash,
        "display_name": photo.display_name or "",
        "noindex": True,
    })


@app.post("/api/fifteen-puzzle/upload-photo", status_code=201)
@limiter.limit("20/minute")
async def upload_fifteen_puzzle_photo(
    request: Request,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    display_name: str = Form(""),
    photo_mode: str = Form("tiles"),
    board_hash: str = Form(...),
):
    import re, shutil
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")

    # Validate mode
    if photo_mode not in ("tiles", "reveal"):
        photo_mode = "tiles"

    # Validate board_hash format
    if not re.match(r'^[A-Za-z0-9_\-]{10,128}$', board_hash):
        raise HTTPException(status_code=400, detail="Invalid board hash")

    # Check duplicate hash
    if db.query(FifteenPuzzlePhoto).filter_by(board_hash=board_hash).first():
        raise HTTPException(status_code=409, detail="A puzzle with this board already exists")

    # Check per-user limit
    profile = db.query(UserProfile).filter_by(email=user["email"]).first()
    limit = getattr(profile, "puzzle_storage_limit", 32) if profile else 32
    count = db.query(FifteenPuzzlePhoto).filter_by(user_email=user["email"]).count()
    if count >= limit:
        raise HTTPException(status_code=400, detail=f"Puzzle limit reached ({limit})")

    # Validate file type and size
    content_type = file.content_type or ""
    if content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=400, detail="Only JPG and PNG files are accepted")
    data = await file.read()
    if len(data) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 2MB)")

    # Save file
    upload_dir = os.path.join("static", "uploads", "15puzzle")
    os.makedirs(upload_dir, exist_ok=True)
    ext = ".jpg" if content_type == "image/jpeg" else ".png"
    safe_hash = re.sub(r'[^A-Za-z0-9_\-]', '', board_hash)
    filename = f"{safe_hash}{ext}"
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(data)

    entry = FifteenPuzzlePhoto(
        user_email   = user["email"],
        filename     = filename,
        display_name = display_name.strip()[:128] or None,
        photo_mode   = photo_mode,
        board_hash   = board_hash,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {
        "ok": True,
        "url": f"/other/15puzzle/photo/{board_hash}?mode={photo_mode}",
    }


@app.post("/api/fifteen-puzzle/delete-photo/{board_hash}")
def delete_fifteen_puzzle_photo(board_hash: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    photo = db.query(FifteenPuzzlePhoto).filter_by(board_hash=board_hash).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Not found")
    if photo.user_email != user["email"] and user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")
    # Delete file from disk
    filepath = os.path.join("static", "uploads", "15puzzle", photo.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    db.delete(photo)
    db.commit()
    return {"ok": True}


# ── Admin: 15-Puzzle photo moderation ─────────────────────────────────────────

@app.get("/admin/15puzzle-photos", response_class=HTMLResponse)
def admin_15puzzle_photos(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user or user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")
    photos = (
        db.query(FifteenPuzzlePhoto)
        .order_by(FifteenPuzzlePhoto.created_at.desc())
        .all()
    )
    return templates.TemplateResponse("admin_15puzzle_photos.html", {
        "request": request, "user": user,
        "lang": get_lang(request), "t": get_t(request),
        "photos": photos,
    })


@app.post("/admin/15puzzle-photos/{board_hash}/delete")
def admin_delete_15puzzle_photo(board_hash: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user or user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")
    photo = db.query(FifteenPuzzlePhoto).filter_by(board_hash=board_hash).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Not found")
    filepath = os.path.join("static", "uploads", "15puzzle", photo.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    db.delete(photo)
    db.commit()
    return RedirectResponse("/admin/15puzzle-photos", status_code=303)


# ── 2048 ──────────────────────────────────────────────────────────────────────

@app.get("/other/2048", response_class=HTMLResponse)
def game_2048_landing(request: Request):
    return RedirectResponse("/other/2048/daily", status_code=302)


@app.get("/other/2048/daily", response_class=HTMLResponse)
def game_2048_daily(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse("2048_daily.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today,
    })


@app.get("/other/2048/leaderboard", response_class=HTMLResponse)
def game_2048_leaderboard_page(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse("2048_leaderboard.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today,
    })


@app.get("/other/2048/how-to-play", response_class=HTMLResponse)
def game_2048_howtoplay(request: Request):
    return templates.TemplateResponse("2048_howtoplay.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


# ── 2048 Hexagon ──────────────────────────────────────────────────────────────
@app.get("/other/2048hex", response_class=HTMLResponse)
def game_2048hex_landing(request: Request):
    return RedirectResponse("/other/2048hex/play", status_code=302)

@app.get("/other/2048hex/play", response_class=HTMLResponse)
def game_2048hex_play(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse("2048hex.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today,
    })

@app.get("/other/2048hex/leaderboard", response_class=HTMLResponse)
def game_2048hex_leaderboard(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse("2048hex_leaderboard.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today,
    })

@app.get("/other/2048hex/how-to-play", response_class=HTMLResponse)
def game_2048hex_htp(request: Request):
    return templates.TemplateResponse("2048hex_howtoplay.html", {
        "request": request, "mode": "other",
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
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


@app.post("/api/2048hex-scores", status_code=201)
@limiter.limit("10/minute")
def submit_2048hex_score(payload: Game2048HexScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None
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
    record_score_submit("2048hex", payload.puzzle_date)
    record_game_complete("2048hex", mode="daily", duration_ms=payload.time_ms)
    return {"ok": True, "id": entry.id}


@app.get("/api/2048hex-scores/{puzzle_date}")
def get_2048hex_scores(puzzle_date: str, sort: str = "score", db: Session = Depends(get_db)):
    import re
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", puzzle_date):
        raise HTTPException(status_code=400, detail="Invalid date format")
    q = db.query(Game2048HexScore).filter(Game2048HexScore.puzzle_date == puzzle_date)
    if sort == "moves":
        q = q.filter(Game2048HexScore.moves_to_2048.isnot(None)) \
             .order_by(Game2048HexScore.moves_to_2048.asc(), Game2048HexScore.time_ms.asc())
    else:
        q = q.order_by(Game2048HexScore.score.desc(), Game2048HexScore.time_ms.asc())
    return _enrich_with_profiles(q.limit(20).all(), db)


@app.get("/api/2048hex-scores")
def get_2048hex_scores_all_time(sort: str = "score", db: Session = Depends(get_db)):
    q = db.query(Game2048HexScore)
    if sort == "moves":
        q = q.filter(Game2048HexScore.moves_to_2048.isnot(None)) \
             .order_by(Game2048HexScore.moves_to_2048.asc(), Game2048HexScore.time_ms.asc())
    else:
        q = q.order_by(Game2048HexScore.score.desc(), Game2048HexScore.time_ms.asc())
    return _enrich_with_profiles(q.limit(20).all(), db)


@app.get("/api/2048hex-histogram")
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


# ── Schulte Grid ───────────────────────────────────────────────────────────────

_SCHULTE_MODES = {"normal", "easy", "blind_normal", "blind_easy", "easy_mix", "mix"}
_SCHULTE_SIZES = set(range(3, 11))   # 3–10 inclusive

@app.get("/other/schulte", response_class=HTMLResponse)
def schulte_landing(request: Request):
    return RedirectResponse("/other/schulte/play", status_code=302)

@app.get("/other/schulte/play", response_class=HTMLResponse)
def schulte_play(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse("schulte_play.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today,
    })

@app.get("/other/schulte/leaderboard", response_class=HTMLResponse)
def schulte_leaderboard_page(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse("schulte_leaderboard.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today,
    })

@app.get("/other/schulte/how-to-play", response_class=HTMLResponse)
def schulte_howtoplay(request: Request):
    return templates.TemplateResponse("schulte_howtoplay.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


class SchulteScoreSubmit(BaseModel):
    name:        str = Field(..., min_length=1, max_length=32)
    puzzle_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    mode:        str = Field(..., min_length=1, max_length=16)
    board_size:  int = Field(..., ge=3, le=10)
    time_ms:     int = Field(..., ge=1, le=9999999)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in _SCHULTE_MODES:
            raise ValueError(f"Invalid mode: {v}")
        return v


@app.post("/api/schulte-scores", status_code=201)
@limiter.limit("20/minute")
def submit_schulte_score(payload: SchulteScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None
    entry = SchulteGridScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        mode        = payload.mode,
        board_size  = payload.board_size,
        time_ms     = payload.time_ms,
        puzzle_date = payload.puzzle_date,
        guest_token = guest_token,
        client_type = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    record_score_submit("schulte", payload.puzzle_date)
    record_game_complete("schulte", mode=payload.mode, duration_ms=payload.time_ms)
    return {"ok": True, "id": entry.id}


@app.get("/api/schulte-scores")
def get_schulte_scores(
    mode:        str = "normal",
    size:        int = 5,
    period:      str = "today",
    puzzle_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    import re
    if mode not in _SCHULTE_MODES:
        raise HTTPException(status_code=400, detail="Invalid mode")
    if size not in _SCHULTE_SIZES:
        raise HTTPException(status_code=400, detail="Invalid board size")
    if period not in ("today", "alltime"):
        raise HTTPException(status_code=400, detail="Invalid period")

    q = db.query(SchulteGridScore).filter(
        SchulteGridScore.mode == mode,
        SchulteGridScore.board_size == size,
    )

    if period == "today":
        today = puzzle_date or date.today().isoformat()
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", today):
            raise HTTPException(status_code=400, detail="Invalid date format")
        q = q.filter(SchulteGridScore.puzzle_date == today) \
             .order_by(SchulteGridScore.time_ms.asc(), SchulteGridScore.created_at.asc()) \
             .limit(20)
        return _enrich_with_profiles(q.all(), db)

    # all-time: best score per signed-in user only
    from sqlalchemy import func
    subq = (
        db.query(
            SchulteGridScore.user_email,
            func.min(SchulteGridScore.time_ms).label("best_time"),
        )
        .filter(
            SchulteGridScore.mode == mode,
            SchulteGridScore.board_size == size,
            SchulteGridScore.user_email.isnot(None),
        )
        .group_by(SchulteGridScore.user_email)
        .order_by(func.min(SchulteGridScore.time_ms).asc())
        .limit(20)
        .subquery()
    )
    rows = (
        db.query(SchulteGridScore)
        .join(subq, (SchulteGridScore.user_email == subq.c.user_email) &
                    (SchulteGridScore.time_ms == subq.c.best_time))
        .filter(SchulteGridScore.mode == mode, SchulteGridScore.board_size == size)
        .order_by(SchulteGridScore.time_ms.asc(), SchulteGridScore.created_at.asc())
        .limit(20)
        .all()
    )
    return _enrich_with_profiles(rows, db)


# ── Sudoku ────────────────────────────────────────────────────────────────────

_SUDOKU_DIFFICULTIES = {"daily", "easy", "medium", "hard", "expert"}


@app.get("/other/sudoku", response_class=HTMLResponse)
def sudoku_landing(request: Request):
    return RedirectResponse("/other/sudoku/daily", status_code=302)


def _sudoku_seed(difficulty: str, today: str) -> int:
    import hashlib as _hl
    if difficulty == "daily":
        return int(_hl.md5(f"sudoku-daily-{today}".encode()).hexdigest(), 16) & 0xFFFFFFFF
    import random as _rand
    return _rand.randint(0, 0xFFFFFFFF)


@app.get("/other/sudoku/daily", response_class=HTMLResponse)
def sudoku_daily(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse("sudoku_play.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today, "difficulty": "daily",
        "seed": _sudoku_seed("daily", today), "givens": None,
    })


@app.get("/other/sudoku/easy", response_class=HTMLResponse)
def sudoku_easy(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse("sudoku_play.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today, "difficulty": "easy",
        "seed": _sudoku_seed("easy", today), "givens": None,
    })


@app.get("/other/sudoku/medium", response_class=HTMLResponse)
def sudoku_medium(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse("sudoku_play.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today, "difficulty": "medium",
        "seed": _sudoku_seed("medium", today), "givens": None,
    })


@app.get("/other/sudoku/hard", response_class=HTMLResponse)
def sudoku_hard(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse("sudoku_play.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today, "difficulty": "hard",
        "seed": _sudoku_seed("hard", today), "givens": None,
    })


@app.get("/other/sudoku/expert", response_class=HTMLResponse)
def sudoku_expert(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse("sudoku_play.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today, "difficulty": "expert",
        "seed": _sudoku_seed("expert", today), "givens": None,
    })


@app.get("/other/sudoku/scores", response_class=HTMLResponse)
def sudoku_scores_page(request: Request):
    return templates.TemplateResponse("sudoku_scores.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": date.today().isoformat(),
    })


@app.get("/other/sudoku/board/{board_hash}", response_class=HTMLResponse)
def sudoku_play_by_hash(board_hash: str, request: Request, db: Session = Depends(get_db)):
    row = db.query(SudokuScore).filter(SudokuScore.board_hash == board_hash).first()
    if not row:
        raise HTTPException(status_code=404, detail="Board not found")
    return templates.TemplateResponse("sudoku_play.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": date.today().isoformat(),
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

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
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


@app.post("/api/sudoku-scores", status_code=201)
@limiter.limit("20/minute")
def submit_sudoku_score(payload: SudokuScoreSubmit, request: Request, db: Session = Depends(get_db)):
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
        puzzle_date  = payload.puzzle_date,
        guest_token  = guest_token,
        client_type  = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    record_score_submit("sudoku", payload.puzzle_date)
    record_game_complete("sudoku", mode=payload.difficulty, duration_ms=payload.time_ms)
    return {"ok": True, "id": entry.id}


@app.get("/api/sudoku-scores")
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

    if period == "today":
        today = puzzle_date or date.today().isoformat()
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
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


@app.post("/api/2048-scores", status_code=201)
@limiter.limit("10/minute")
def submit_2048_score(payload: Game2048ScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None
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
    record_score_submit("2048", payload.puzzle_date)
    record_game_complete("2048", mode="daily", duration_ms=payload.time_ms)
    return {"ok": True, "id": entry.id}


@app.get("/api/2048-scores/{puzzle_date}")
def get_2048_scores(puzzle_date: str, sort: str = "score", db: Session = Depends(get_db)):
    import re
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", puzzle_date):
        raise HTTPException(status_code=400, detail="Invalid date format")
    q = db.query(Game2048Score).filter(Game2048Score.puzzle_date == puzzle_date)
    if sort == "moves":
        q = q.filter(Game2048Score.moves_to_2048.isnot(None)) \
             .order_by(Game2048Score.moves_to_2048.asc(), Game2048Score.time_ms.asc())
    else:
        q = q.order_by(Game2048Score.score.desc(), Game2048Score.time_ms.asc())
    return _enrich_with_profiles(q.limit(20).all(), db)


@app.get("/api/2048-scores")
def get_2048_scores_all_time(sort: str = "score", db: Session = Depends(get_db)):
    q = db.query(Game2048Score)
    if sort == "moves":
        q = q.filter(Game2048Score.moves_to_2048.isnot(None)) \
             .order_by(Game2048Score.moves_to_2048.asc(), Game2048Score.time_ms.asc())
    else:
        q = q.order_by(Game2048Score.score.desc(), Game2048Score.time_ms.asc())
    return _enrich_with_profiles(q.limit(20).all(), db)


@app.get("/api/2048-histogram")
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


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    return templates.TemplateResponse("history.html", {
        "request": request, "mode": "history",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse("about.html", {
        "request": request, "mode": "about",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/team", response_class=HTMLResponse)
async def team_page(request: Request):
    return templates.TemplateResponse("team.html", {
        "request": request, "mode": "team",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


# ── Blog ──────────────────────────────────────────────────────────────────────

# Post registry — add a new entry here for each new post.
# date:    ISO 8601 date string (YYYY-MM-DD)
# file:    path relative to the repo root
# excerpt: one-sentence summary shown on the index page
BLOG_POSTS = [
    {
        "slug":          "nononoguess",
        "file":          "blog/nononoguess.md",
        "title":         "Nonosweeper's No Guess Mode: Every Puzzle, Solvable by Logic Alone",
        "date":          "2026-04-11",
        "datePublished": "2026-04-11T00:00:00Z",
        "image":         "/static/img/Nono_Guess_Required.png",
        "excerpt":       "Not every randomly-generated nonogram plays fair — sometimes the clues "
                         "leave a 50/50 guess at the end. No Guess mode runs a constraint-propagation "
                         "solver on every candidate board and only presents puzzles that are fully "
                         "solvable by logic alone.",
    },
    {
        "slug":          "traffic-growth",
        "file":          "blog/traffic-growth.md",
        "title":         "We're Growing — When Will We Hit 100,000 Daily Visitors?",
        "date":          "2026-04-11",
        "datePublished": "2026-04-11T00:00:00Z",
        "image":         "/static/img/minesweeper_org_Linear_Fit.png",
        "excerpt":       "We fitted a linear + weekly-periodic model to 17 days of traffic data "
                         "and asked: when does minesweeper.org reach 100,000 daily unique IPs? "
                         "The answer ranges from October 2026 to November 2040, depending on which "
                         "growth curve we're actually on.",
    },
    {
        "slug":          "rodential-heroics",
        "file":          "blog/magawa-hero-rat-wnm.md",
        "title":         "Rodential Heroics",
        "date":          "2026-04-10",
        "datePublished": "2026-04-10T15:00:00Z",
        "image":         "/static/img/Magawa_in_2020.jpg",
        "excerpt":       "There is a seven-foot stone statue in Siem Reap, Cambodia, depicting a rat "
                         "wearing a gold medal. When you learn what Magawa did to earn it, "
                         "it might be among the most deserved monuments in the world.",
    },
    {
        "slug":          "multicloud",
        "file":          "blog/multicloud.md",
        "title":         "Minesweeper.org Goes Multicloud",
        "date":          "2026-04-05",
        "datePublished": "2026-04-05T00:00:00Z",
        "image":         "/static/img/toby-learned-pig-c6c4ff-small.webp",
        "excerpt":       "The Lady Di's Mines team has spun up a GCP instance at pgl.minesweeper.org "
                         "in support of the native Pig Latin speakers of Iowa.",
    },
    {
        "slug":          "royalty-free",
        "file":          "blog/15puzzle-generator.md",
        "title":         "Nothing About Her Is Royalty-Free",
        "date":          "2026-04-03",
        "datePublished": "2026-04-03T00:00:00Z",
        "image":         "https://minesweeper.org/static/img/Diana_Princess_of_Wales_1997.jpg",
        "excerpt": "Searching for a royalty-free photo of Diana, Princess of Wales, "
                   "to demo our new 15-Puzzle Generator. It turns out that's complicated.",
    },
    {
        "slug":          "fifteen-puzzle",
        "file":          "blog/15puzzle_article.md",
        "title":         "The new 15-puzzle!",
        "date":          "2026-03-31",
        "datePublished": "2026-03-31T00:00:00Z",
        "image":         "https://minesweeper.org/static/img/Diana15Puzzle.png",
        "excerpt": "Minesweeper.org has a new sliding tile puzzle: the 15-Puzzle. "
                   "Play the daily challenge, upload your own photo, and slide whole rows in one move.",
    },
    {
        "slug":          "tentaizu-theme",
        "file":          "blog/tentaizu-theme.md",
        "title":         "The new Tentaizu Theme",
        "date":          "2026-03-20",
        "datePublished": "2026-03-20T00:00:00Z",
        "image":         "https://minesweeper.org/static/img/TentaizuPuzzle20260320Equinox.png",
        "excerpt": "Lady Di's Mines now switches to the Tentaizu theme on solstices and equinoxes. "
                   "Here's what the theme is and a little about the Tentaizu puzzle.",
    },
    {
        "slug":          "no-jira-required",
        "file":          "blog/2_saaspocalypse-kanban.md",
        "title":         "No Jira Required: GitAgile Kanban in Your Repo",
        "date":          "2026-03-19",
        "datePublished": "2026-03-19T12:00:00Z",
        "excerpt": "Instead of subscribing to Jira, Claude Code built a kanban board "
                   "that reads directly from a markdown file in the repo. "
                   "The SaaSpocalypse comes for project management.",
    },
    {
        "slug":          "3bv",
        "file":          "blog/3bv_blog_post.md",
        "title":         "We've added 3BV values to Lady Di's Mines",
        "date":          "2026-03-18",
        "datePublished": "2026-03-18T00:00:00Z",
        "image":         "https://minesweeper.org/static/img/3BV_Example.png",
        "excerpt": "Lady Di's Mines now displays 3BV — Bechtel's Board Benchmark Value — "
                   "the minimum clicks needed to clear a board. Here's what it means and why it matters.",
    },
    {
        "slug":    "lady-di",
        "file":    "blog/lady-di-blog-post.md",
        "title":   "She's Back: The Return of Lady Di's Mines",
        "date":          "2026-03-15",
        "datePublished": "2026-03-15T15:00:00Z",
        "excerpt": "I built the original minesweeper.org in 1999 as a Physics PhD student. "
                   "Here's the story of Lady Di's Mines — and why she's back.",
    },
    {
        "slug":          "saaspocalypse",
        "file":          "blog/1_saaspocalypse-blog-post.md",
        "title":         "SaaSpocalypse.Now!",
        "date":          "2026-03-14",
        "datePublished": "2026-03-14T15:00:00Z",
        "excerpt": "AI coding tools have collapsed the distance between "
                   "'I want a thing' and 'I have the thing.' "
                   "Meet the SaaSpocalypse.",
    },
]

def _blog_post_meta(post: dict) -> dict:
    """Attach display-friendly date; return enriched copy."""
    from datetime import date as _date
    import datetime
    try:
        d = datetime.date.fromisoformat(post["date"])
        display = d.strftime("%B %-d, %Y")
    except Exception:
        display = post["date"]
    return {**post, "date_display": display}

_BLOG_INDEX = [_blog_post_meta(p) for p in BLOG_POSTS]
_BLOG_BY_SLUG = {p["slug"]: p for p in _BLOG_INDEX}


@app.get("/blog", response_class=HTMLResponse)
async def blog_index(request: Request):
    return templates.TemplateResponse("blog_index.html", {
        "request": request, "mode": "blog",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "posts": _BLOG_INDEX,
    })


def _parse_front_matter(raw: str) -> tuple[dict, str]:
    """Extract YAML front matter from markdown. Returns (meta dict, body text)."""
    import re
    meta = {}
    # Strip UTF-8 BOM if present
    raw = raw.lstrip("\ufeff")
    # Normalise line endings
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    m = re.match(r"^---\n(.*?\n)---\n", raw, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                meta[key.strip()] = val.strip().strip('"').strip("'")
        raw = raw[m.end():].lstrip("\n")
    return meta, raw


def _make_absolute_url(request: Request, url: str) -> str:
    """Return an absolute URL, resolving relative paths against the request base URL."""
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    base = str(request.base_url).rstrip("/")
    return base + ("" if url.startswith("/") else "/") + url


def _webp_if_exists(image_url: str) -> str:
    """Return the .webp URL only if the file exists on disk, else empty string."""
    import os
    if not image_url.endswith(".png"):
        return ""
    webp_url = image_url.replace(".png", ".webp")
    local_path = webp_url.replace("https://minesweeper.org/", "")
    return webp_url if os.path.exists(local_path) else ""


@app.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(request: Request, slug: str, db: Session = Depends(get_db)):
    import markdown as md_lib
    post = _BLOG_BY_SLUG.get(slug)
    if not post:
        from fastapi.responses import Response
        return Response(status_code=404)
    raw = open(post["file"], encoding="utf-8").read()
    front_matter, body = _parse_front_matter(raw)
    # Strip the H1 title line — it's rendered by the template
    lines = body.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    html_content = md_lib.markdown(
        "\n".join(lines),
        extensions=["extra", "sane_lists"],
    )
    date_published = (
        front_matter.get("datePublished")
        or post.get("datePublished")
        or post["date"]
    )
    date_modified = (
        front_matter.get("dateModified")
        or post.get("dateModified")
        or date_published
    )
    comments = (
        db.query(BlogComment)
        .filter_by(post_slug=slug, approved=True)
        .order_by(BlogComment.created_at)
        .all()
    )
    return templates.TemplateResponse("blog_post.html", {
        "request":        request, "mode": "blog",
        "user":           get_current_user(request),
        "lang":           get_lang(request), "t": get_t(request),
        "post":           post,
        "content":        html_content,
        "author":         front_matter.get("author", "") or "minesweeper.org",
        "authorurl":      front_matter.get("authorurl", "") if front_matter.get("authorurl", "").startswith(("https://", "http://")) else "",
        "publisher":      front_matter.get("publisher", "") or "minesweeper.org",
        "og_image":       _make_absolute_url(request, post.get("image") or front_matter.get("image", "")),
        "og_image_webp":  _webp_if_exists(post.get("image") or front_matter.get("image", "")),
        "date_published": date_published,
        "date_modified":  date_modified,
        "comments":       comments,
    })


@app.post("/api/blog/{slug}/comments")
async def submit_blog_comment(slug: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    if slug not in _BLOG_BY_SLUG:
        raise HTTPException(status_code=404, detail="Post not found")
    data = await request.json()
    body = (data.get("body") or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="Comment body required")
    if len(body) > 2000:
        raise HTTPException(status_code=400, detail="Comment too long (max 2000 chars)")
    comment = BlogComment(
        post_slug=slug,
        user_email=user["email"],
        display_name=user.get("display_name") or user.get("name") or user["email"],
        body=body,
        approved=False,
    )
    db.add(comment)
    db.commit()
    return {"ok": True, "message": "Your comment has been submitted and is awaiting review."}


@app.get("/privacy-policy")
async def privacy_policy_redirect():
    return RedirectResponse(url="/privacy", status_code=301)


@app.get("/terms-of-service")
async def terms_of_service_redirect():
    return RedirectResponse(url="/terms", status_code=301)


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    return templates.TemplateResponse("privacy.html", {
        "request": request, "mode": "privacy",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/piracy", response_class=HTMLResponse)
async def piracy_page(request: Request):
    return templates.TemplateResponse("piracy.html", {
        "request": request, "mode": "piracy",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    return templates.TemplateResponse("terms.html", {
        "request": request, "mode": "terms",
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
    return templates.TemplateResponse("profile.html", {
        "request":       request,
        "mode":          "profile",
        "user":          user,
        "public_id":     profile.public_id if profile else "",
        "is_public":     profile.is_public if profile else False,
        "favorite_game": profile.favorite_game if profile else "",
        "vanity_slug":   profile.vanity_slug if profile else "",
        "pref_sounds":   profile.pref_sounds   if profile else False,
        "pref_chording": profile.pref_chording if profile else True,
        "pref_skin":     profile.pref_skin     if profile else site_settings.active_skin(),
        "about_text":    profile.about_text    if profile else "",
        "fp_photos":     db.query(FifteenPuzzlePhoto).filter_by(user_email=user["email"]).order_by(FifteenPuzzlePhoto.created_at.desc()).all(),
        "fp_limit":      getattr(profile, "puzzle_storage_limit", 32) if profile else 32,
        "jigsaw_saves":  db.query(JigsawSavedGame).filter_by(user_email=user["email"]).order_by(JigsawSavedGame.updated_at.desc()).all(),
        "today":         datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/quests", response_class=HTMLResponse)
async def quests_page(request: Request):
    return templates.TemplateResponse("quests.html", {
        "request": request, "mode": "quests",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/variants", response_class=HTMLResponse)
async def variants_page(request: Request):
    return templates.TemplateResponse("variants.html", {
        "request": request, "mode": "variants",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


# ── Replay page ───────────────────────────────────────────────────────────────

@app.get("/variants/replay/", response_class=HTMLResponse)
async def replay_page(request: Request):
    return templates.TemplateResponse("replay.html", {
        "request": request, "mode": "replay",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


# ── Links Page ────────────────────────────────────────────────────────────────

@app.get("/links", response_class=HTMLResponse)
async def links_page(request: Request):
    return templates.TemplateResponse("links.html", {
        "request": request,
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


# ── 3BV Info ──────────────────────────────────────────────────────────────────

@app.get("/info/3bv", response_class=HTMLResponse)
async def info_3bv_page(request: Request):
    return templates.TemplateResponse("info_3bv.html", {
        "request": request,
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


# ── Board Generator ────────────────────────────────────────────────────────────

@app.get("/variants/board-generator", response_class=HTMLResponse)
async def board_generator_page(request: Request):
    return templates.TemplateResponse("board_generator.html", {
        "request": request, "mode": "board-generator",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
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
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
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
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None
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
        db.query(ReplayScore)
        .filter(ReplayScore.board_hash == board_hash, ReplayScore.variant == variant)
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


@app.get("/cylinder", response_class=HTMLResponse)
async def cylinder_beginner(request: Request):
    return templates.TemplateResponse("cylinder.html", {
        "request": request, "mode": "cylinder-beginner",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **CYLINDER_MODES["cylinder-beginner"]
    })


@app.get("/cylinder/intermediate", response_class=HTMLResponse)
async def cylinder_intermediate(request: Request):
    return templates.TemplateResponse("cylinder.html", {
        "request": request, "mode": "cylinder-intermediate",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **CYLINDER_MODES["cylinder-intermediate"]
    })


@app.get("/cylinder/expert", response_class=HTMLResponse)
async def cylinder_expert(request: Request):
    return templates.TemplateResponse("cylinder.html", {
        "request": request, "mode": "cylinder-expert",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **CYLINDER_MODES["cylinder-expert"]
    })


@app.get("/cylinder/custom", response_class=HTMLResponse)
async def cylinder_custom(request: Request):
    return templates.TemplateResponse("cylinder.html", {
        "request": request, "mode": "cylinder-custom",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "rows": 10, "cols": 10, "mines": 10,
    })


# ── Cylinder Leaderboard API ──────────────────────────────────────────────────

CYLINDER_MODES_VALID = {"easy", "intermediate", "expert", "custom"}

class CylinderScoreSubmit(BaseModel):
    name:         str          = Field(..., min_length=1, max_length=32)
    cyl_mode:     str          = Field(..., pattern="^(easy|intermediate|expert|custom)$")
    time_secs:    int          = Field(..., ge=1, le=999)
    time_ms:      Optional[int]  = Field(None, ge=1, le=3_600_000)
    rows:         int          = Field(..., ge=5,  le=30)
    cols:         int          = Field(..., ge=5,  le=50)
    mines:        int          = Field(..., ge=1,  le=999)
    no_guess:     bool           = False
    board_hash:   Optional[str]  = Field(None, max_length=128)
    bbbv:         Optional[int]  = Field(None, ge=1, le=9999)
    left_clicks:  Optional[int]  = Field(None, ge=0, le=99999)
    right_clicks: Optional[int]  = Field(None, ge=0, le=99999)
    chord_clicks: Optional[int]  = Field(None, ge=0, le=99999)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
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


@app.post("/api/cylinder-scores", status_code=201)
@limiter.limit("10/minute")
def submit_cylinder_score(payload: CylinderScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user  = get_current_user(request)
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None
    entry = CylinderScore(
        name         = payload.name,
        user_email   = user["email"] if user else None,
        cyl_mode     = payload.cyl_mode,
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
        client_type  = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"ok": True, "id": entry.id}


@app.get("/api/cylinder-scores/{cyl_mode}")
def get_cylinder_scores(cyl_mode: str, no_guess: bool = False, period: str = "alltime",
                        score_date: Optional[str] = Query(None, alias="date"),
                        season_num: Optional[int] = Query(None),
                        db: Session = Depends(get_db)):
    if cyl_mode not in CYLINDER_MODES_VALID:
        raise HTTPException(status_code=400, detail="Invalid mode")
    if period not in ("daily", "season", "alltime"):
        period = "alltime"

    sort_key = case(
        (CylinderScore.time_ms.isnot(None), CylinderScore.time_ms),
        else_=CylinderScore.time_secs * 1000
    )

    if no_guess:
        ng_filter = CylinderScore.no_guess == True
    else:
        ng_filter = (CylinderScore.no_guess == False) | CylinderScore.no_guess.is_(None)

    q = db.query(CylinderScore).filter(CylinderScore.cyl_mode == cyl_mode, ng_filter)

    if period == "daily":
        try:
            target = date.fromisoformat(score_date) if score_date else date.today()
        except ValueError:
            target = date.today()
        q = q.filter(CylinderScore.created_at >= target, CylinderScore.created_at < target + timedelta(days=1))
        top = q.order_by(sort_key.asc(), CylinderScore.created_at.asc()).limit(15).all()
        return _enrich_with_profiles(top, db)

    if period == "season":
        if season_num and season_num >= 1:
            s_start, s_end = get_season_range(season_num)
            q = q.filter(CylinderScore.created_at >= s_start, CylinderScore.created_at < s_end)
        else:
            today = date.today()
            q = q.filter(CylinderScore.created_at >= today.replace(day=1))

    raw = q.order_by(sort_key.asc(), CylinderScore.created_at.asc()).limit(500).all()
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


# ── Toroid Routes ─────────────────────────────────────────────────────────────

@app.get("/toroid", response_class=HTMLResponse)
async def toroid_beginner(request: Request):
    return templates.TemplateResponse("toroid.html", {
        "request": request, "mode": "toroid-beginner",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **TOROID_MODES["toroid-beginner"]
    })


@app.get("/toroid/intermediate", response_class=HTMLResponse)
async def toroid_intermediate(request: Request):
    return templates.TemplateResponse("toroid.html", {
        "request": request, "mode": "toroid-intermediate",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **TOROID_MODES["toroid-intermediate"]
    })


@app.get("/toroid/expert", response_class=HTMLResponse)
async def toroid_expert(request: Request):
    return templates.TemplateResponse("toroid.html", {
        "request": request, "mode": "toroid-expert",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **TOROID_MODES["toroid-expert"]
    })


@app.get("/toroid/custom", response_class=HTMLResponse)
async def toroid_custom(request: Request):
    return templates.TemplateResponse("toroid.html", {
        "request": request, "mode": "toroid-custom",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "rows": 10, "cols": 10, "mines": 10,
    })


# ── Toroid Leaderboard API ────────────────────────────────────────────────────

TOROID_MODES_VALID = {"easy", "intermediate", "expert", "custom"}

class ToroidScoreSubmit(BaseModel):
    name:         str          = Field(..., min_length=1, max_length=32)
    tor_mode:     str          = Field(..., pattern="^(easy|intermediate|expert|custom)$")
    time_secs:    int          = Field(..., ge=1, le=999)
    time_ms:      Optional[int]  = Field(None, ge=1, le=3_600_000)
    rows:         int          = Field(..., ge=5,  le=30)
    cols:         int          = Field(..., ge=5,  le=50)
    mines:        int          = Field(..., ge=1,  le=999)
    no_guess:     bool           = False
    board_hash:   Optional[str]  = Field(None, max_length=128)
    bbbv:         Optional[int]  = Field(None, ge=1, le=9999)
    left_clicks:  Optional[int]  = Field(None, ge=0, le=99999)
    right_clicks: Optional[int]  = Field(None, ge=0, le=99999)
    chord_clicks: Optional[int]  = Field(None, ge=0, le=99999)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
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


@app.post("/api/toroid-scores", status_code=201)
@limiter.limit("10/minute")
def submit_toroid_score(payload: ToroidScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user  = get_current_user(request)
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None
    entry = ToroidScore(
        name         = payload.name,
        user_email   = user["email"] if user else None,
        tor_mode     = payload.tor_mode,
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
        client_type  = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"ok": True, "id": entry.id}


@app.get("/api/toroid-scores/{tor_mode}")
def get_toroid_scores(tor_mode: str, no_guess: bool = False, period: str = "alltime",
                      score_date: Optional[str] = Query(None, alias="date"),
                      season_num: Optional[int] = Query(None),
                      db: Session = Depends(get_db)):
    if tor_mode not in TOROID_MODES_VALID:
        raise HTTPException(status_code=400, detail="Invalid mode")
    if period not in ("daily", "season", "alltime"):
        period = "alltime"

    sort_key = case(
        (ToroidScore.time_ms.isnot(None), ToroidScore.time_ms),
        else_=ToroidScore.time_secs * 1000
    )

    if no_guess:
        ng_filter = ToroidScore.no_guess == True
    else:
        ng_filter = (ToroidScore.no_guess == False) | ToroidScore.no_guess.is_(None)

    q = db.query(ToroidScore).filter(ToroidScore.tor_mode == tor_mode, ng_filter)

    if period == "daily":
        try:
            target = date.fromisoformat(score_date) if score_date else date.today()
        except ValueError:
            target = date.today()
        q = q.filter(ToroidScore.created_at >= target, ToroidScore.created_at < target + timedelta(days=1))
        top = q.order_by(sort_key.asc(), ToroidScore.created_at.asc()).limit(15).all()
        return _enrich_with_profiles(top, db)

    if period == "season":
        if season_num and season_num >= 1:
            s_start, s_end = get_season_range(season_num)
            q = q.filter(ToroidScore.created_at >= s_start, ToroidScore.created_at < s_end)
        else:
            today = date.today()
            q = q.filter(ToroidScore.created_at >= today.replace(day=1))

    raw = q.order_by(sort_key.asc(), ToroidScore.created_at.asc()).limit(500).all()
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


# ── Hexsweeper Routes ─────────────────────────────────────────────────────────

# Hex board cell count for radius R = 3R²−3R+1
# R=5 → 61 cells, R=7 → 127 cells, R=10 → 271 cells
HEXSWEEPER_MODES = {
    "hex-beginner":     {"radius": 5, "mines": 8},
    "hex-intermediate": {"radius": 7, "mines": 20},
    "hex-expert":       {"radius": 10, "mines": 57},
}


@app.get("/hexsweeper", response_class=HTMLResponse)
async def hexsweeper_beginner(request: Request):
    return templates.TemplateResponse("hexsweeper.html", {
        "request": request, "mode": "hex-beginner",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **HEXSWEEPER_MODES["hex-beginner"]
    })


@app.get("/hexsweeper/intermediate", response_class=HTMLResponse)
async def hexsweeper_intermediate(request: Request):
    return templates.TemplateResponse("hexsweeper.html", {
        "request": request, "mode": "hex-intermediate",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **HEXSWEEPER_MODES["hex-intermediate"]
    })


@app.get("/hexsweeper/expert", response_class=HTMLResponse)
async def hexsweeper_expert(request: Request):
    return templates.TemplateResponse("hexsweeper.html", {
        "request": request, "mode": "hex-expert",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **HEXSWEEPER_MODES["hex-expert"]
    })


@app.get("/hexsweeper/custom", response_class=HTMLResponse)
async def hexsweeper_custom(request: Request):
    return templates.TemplateResponse("hexsweeper.html", {
        "request": request, "mode": "hex-custom",
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
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
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


@app.post("/api/hexsweeper-scores", status_code=201)
@limiter.limit("10/minute")
def submit_hex_score(payload: HexscoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None
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
    return {"ok": True, "id": entry.id}


@app.get("/api/hexsweeper-scores/{hex_mode}")
def get_hex_scores(hex_mode: str, period: str = "alltime",
                   score_date: Optional[str] = Query(None, alias="date"),
                   season_num: Optional[int] = Query(None),
                   db: Session = Depends(get_db)):
    if hex_mode not in HEX_MODES_VALID:
        raise HTTPException(status_code=400, detail="Invalid mode")
    if period not in ("daily", "season", "alltime"):
        period = "alltime"

    sort_key = case(
        (HexsweeperScore.time_ms.isnot(None), HexsweeperScore.time_ms),
        else_=HexsweeperScore.time_secs * 1000
    )

    q = db.query(HexsweeperScore).filter(HexsweeperScore.hex_mode == hex_mode)

    if period == "daily":
        try:
            target = date.fromisoformat(score_date) if score_date else date.today()
        except ValueError:
            target = date.today()
        q = q.filter(HexsweeperScore.created_at >= target,
                     HexsweeperScore.created_at < target + timedelta(days=1))
        top = q.order_by(sort_key.asc(), HexsweeperScore.created_at.asc()).limit(15).all()
        return _enrich_with_profiles(top, db)

    if period == "season":
        if season_num and season_num >= 1:
            s_start, s_end = get_season_range(season_num)
            q = q.filter(HexsweeperScore.created_at >= s_start, HexsweeperScore.created_at < s_end)
        else:
            today = date.today()
            q = q.filter(HexsweeperScore.created_at >= today.replace(day=1))

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


# ── Worldsweeper (F55) ───────────────────────────────────────────────────────
# Legacy /globesweeper/* redirects — 301 to canonical /worldsweeper/* URLs

@app.get("/globesweeper")
async def redirect_globesweeper_beginner():
    return RedirectResponse(url="/worldsweeper", status_code=301)

@app.get("/globesweeper/intermediate")
async def redirect_globesweeper_intermediate():
    return RedirectResponse(url="/worldsweeper/intermediate", status_code=301)

@app.get("/globesweeper/expert")
async def redirect_globesweeper_expert():
    return RedirectResponse(url="/worldsweeper/expert", status_code=301)

@app.get("/globesweeper/custom")
async def redirect_globesweeper_custom():
    return RedirectResponse(url="/worldsweeper/custom", status_code=301)

@app.get("/globesweeper/leaderboard")
async def redirect_globesweeper_leaderboard():
    return RedirectResponse(url="/worldsweeper/leaderboard", status_code=301)

GLOBESWEEPER_MODES = {
    "dodecahedron": {"a": 1, "b": 0, "t_param": 1,  "face_count": 12,  "mines": 2},
    "beginner":     {"a": 1, "b": 1, "t_param": 3,  "face_count": 32,  "mines": 4},
    "intermediate": {"a": 2, "b": 1, "t_param": 7,  "face_count": 72,  "mines": 8},
    "expert":       {"a": 5, "b": 0, "t_param": 25, "face_count": 252, "mines": 50},
}
GLOBE_MODES_VALID = {"dodecahedron", "beginner", "intermediate", "expert", "custom"}


@app.get("/worldsweeper", response_class=HTMLResponse)
async def worldsweeper_beginner(request: Request):
    m = GLOBESWEEPER_MODES["beginner"]
    return templates.TemplateResponse("worldsweeper.html", {
        "request": request, "mode": "beginner",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@app.get("/worldsweeper/dodecahedron", response_class=HTMLResponse)
async def worldsweeper_dodecahedron(request: Request):
    m = GLOBESWEEPER_MODES["dodecahedron"]
    return templates.TemplateResponse("worldsweeper.html", {
        "request": request, "mode": "dodecahedron",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@app.get("/worldsweeper/intermediate", response_class=HTMLResponse)
async def worldsweeper_intermediate(request: Request):
    m = GLOBESWEEPER_MODES["intermediate"]
    return templates.TemplateResponse("worldsweeper.html", {
        "request": request, "mode": "intermediate",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@app.get("/worldsweeper/expert", response_class=HTMLResponse)
async def worldsweeper_expert(request: Request):
    m = GLOBESWEEPER_MODES["expert"]
    return templates.TemplateResponse("worldsweeper.html", {
        "request": request, "mode": "expert",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@app.get("/worldsweeper/custom", response_class=HTMLResponse)
async def worldsweeper_custom(request: Request):
    return templates.TemplateResponse("worldsweeper.html", {
        "request": request, "mode": "custom",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "a": 1, "b": 1, "t_param": 3, "face_count": 32, "mines": 4,
    })


@app.get("/worldsweeper/leaderboard", response_class=HTMLResponse)
async def worldsweeper_leaderboard(request: Request):
    return templates.TemplateResponse("worldsweeper_leaderboard.html", {
        "request": request,
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


class WorldsweeperScoreSubmit(BaseModel):
    name:        str           = Field(..., min_length=1, max_length=32)
    glob_mode:   str           = Field(..., pattern="^(dodecahedron|beginner|intermediate|expert|custom)$")
    time_ms:     int           = Field(..., ge=1, le=3_600_000)
    t_param:     int           = Field(..., ge=1, le=75)
    face_count:  int           = Field(..., ge=12, le=752)
    mines:       int           = Field(..., ge=1, le=750)
    bbbv:        Optional[int] = Field(None, ge=1, le=9999)
    left_clicks: Optional[int] = Field(None, ge=1, le=99999)
    board_hash:  Optional[str] = Field(None, max_length=128)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
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


@app.post("/api/worldsweeper-scores", status_code=201)
@limiter.limit("10/minute")
def submit_world_score(payload: WorldsweeperScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None
    entry = GlobesweeperScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        glob_mode   = payload.glob_mode,
        time_ms     = payload.time_ms,
        t_param     = payload.t_param,
        face_count  = payload.face_count,
        mines       = payload.mines,
        bbbv        = payload.bbbv,
        left_clicks = payload.left_clicks,
        board_hash  = payload.board_hash,
        guest_token = guest_token,
        client_type = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"ok": True, "id": entry.id}


@app.get("/api/worldsweeper-scores/{glob_mode}")
def get_world_scores(glob_mode: str, period: str = "alltime",
                     score_date: Optional[str] = Query(None, alias="date"),
                     db: Session = Depends(get_db)):
    if glob_mode not in GLOBE_MODES_VALID:
        raise HTTPException(status_code=400, detail="Invalid mode")
    if period not in ("daily", "alltime"):
        period = "alltime"

    q = db.query(GlobesweeperScore).filter(GlobesweeperScore.glob_mode == glob_mode)

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


@app.get("/cubesweeper", response_class=HTMLResponse)
async def cubesweeper_beginner(request: Request):
    m = CUBESWEEPER_MODES["beginner"]
    return templates.TemplateResponse("cubesweeper.html", {
        "request": request, "mode": "beginner",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@app.get("/cubesweeper/intermediate", response_class=HTMLResponse)
async def cubesweeper_intermediate(request: Request):
    m = CUBESWEEPER_MODES["intermediate"]
    return templates.TemplateResponse("cubesweeper.html", {
        "request": request, "mode": "intermediate",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@app.get("/cubesweeper/expert", response_class=HTMLResponse)
async def cubesweeper_expert(request: Request):
    m = CUBESWEEPER_MODES["expert"]
    return templates.TemplateResponse("cubesweeper.html", {
        "request": request, "mode": "expert",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@app.get("/cubesweeper/custom", response_class=HTMLResponse)
async def cubesweeper_custom(request: Request):
    return templates.TemplateResponse("cubesweeper.html", {
        "request": request, "mode": "custom",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "grid_size": 9, "mines": 10,
    })


@app.get("/cubesweeper/leaderboard", response_class=HTMLResponse)
async def cubesweeper_leaderboard(request: Request):
    return templates.TemplateResponse("cubesweeper_leaderboard.html", {
        "request": request,
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
    bbbv:        Optional[int] = Field(None, ge=1, le=999999)
    left_clicks: Optional[int] = Field(None, ge=0, le=9999999)
    board_hash:  Optional[str] = Field(None, max_length=512)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
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


@app.post("/api/cubesweeper-scores", status_code=201)
@limiter.limit("10/minute")
def submit_cube_score(payload: CubesweeperScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None
    entry = CubesweeperScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        cube_mode   = payload.cube_mode,
        grid_size   = payload.grid_size,
        time_ms     = payload.time_ms,
        mines       = payload.mines,
        no_guess    = payload.no_guess,
        bbbv        = payload.bbbv,
        left_clicks = payload.left_clicks,
        board_hash  = payload.board_hash,
        guest_token = guest_token,
        client_type = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"ok": True, "id": entry.id}


@app.get("/api/cubesweeper-scores/{cube_mode}")
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


@app.get("/minesweeperchess", response_class=HTMLResponse)
async def minesweeperchess(request: Request):
    return templates.TemplateResponse("minesweeperchess.html", {
        "request": request, "mode": "minesweeperchess",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/mobiussweeper", response_class=HTMLResponse)
async def mobiussweeper_beginner(request: Request):
    m = MOBIUSSWEEPER_MODES["beginner"]
    return templates.TemplateResponse("mobiussweeper.html", {
        "request": request, "mode": "beginner",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@app.get("/mobiussweeper/intermediate", response_class=HTMLResponse)
async def mobiussweeper_intermediate(request: Request):
    m = MOBIUSSWEEPER_MODES["intermediate"]
    return templates.TemplateResponse("mobiussweeper.html", {
        "request": request, "mode": "intermediate",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@app.get("/mobiussweeper/expert", response_class=HTMLResponse)
async def mobiussweeper_expert(request: Request):
    m = MOBIUSSWEEPER_MODES["expert"]
    return templates.TemplateResponse("mobiussweeper.html", {
        "request": request, "mode": "expert",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        **m,
    })


@app.get("/mobiussweeper/leaderboard", response_class=HTMLResponse)
async def mobiussweeper_leaderboard(request: Request):
    return templates.TemplateResponse("mobiussweeper_leaderboard.html", {
        "request": request,
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
    bbbv:        Optional[int] = Field(None, ge=1, le=999999)
    left_clicks: Optional[int] = Field(None, ge=0, le=9999999)
    board_hash:  Optional[str] = Field(None, max_length=512)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
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


@app.post("/api/mobiussweeper-scores", status_code=201)
@limiter.limit("10/minute")
def submit_mobius_score(payload: MobiussweeperScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None
    entry = MobiussweeperScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        mobius_mode = payload.mobius_mode,
        width       = payload.width,
        length      = payload.length,
        time_ms     = payload.time_ms,
        mines       = payload.mines,
        no_guess    = payload.no_guess,
        bbbv        = payload.bbbv,
        left_clicks = payload.left_clicks,
        board_hash  = payload.board_hash,
        guest_token = guest_token,
        client_type = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"ok": True, "id": entry.id}


@app.get("/api/mobiussweeper-scores/{mobius_mode}")
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


# ── PvP Leaderboard & Rankings API ───────────────────────────────────────────

@app.get("/api/pvp/leaderboard")
def get_pvp_leaderboard(period: str = "alltime",
                        score_date: Optional[str] = Query(None, alias="date"),
                        season_num: Optional[int] = Query(None),
                        submode: Optional[str] = Query(None),
                        db: Session = Depends(get_db)):
    """Return best PvP games ranked by winner's time (fastest first)."""
    if period not in ("daily", "season", "alltime"):
        period = "alltime"

    q = db.query(PvpResult)
    if submode in ("standard", "quick"):
        q = q.filter(PvpResult.submode == submode)

    if period == "daily":
        try:
            target = date.fromisoformat(score_date) if score_date else date.today()
        except ValueError:
            target = date.today()
        q = q.filter(PvpResult.created_at >= target,
                     PvpResult.created_at < target + timedelta(days=1))
        rows = q.order_by(PvpResult.elapsed_ms.asc()).limit(15).all()
        return [r.to_dict() for r in rows]

    if period == "season":
        if season_num and season_num >= 1:
            s_start, s_end = get_season_range(season_num)
            q = q.filter(PvpResult.created_at >= s_start,
                         PvpResult.created_at < s_end)
        else:
            today = date.today()
            q = q.filter(PvpResult.created_at >= today.replace(day=1))

    # Best game per winner (dedup by winner_email or winner_name)
    raw = q.order_by(PvpResult.elapsed_ms.asc()).limit(500).all()
    seen: set = set()
    top: list = []
    for r in raw:
        key = r.winner_email or r.winner_name or str(r.id)
        if key not in seen:
            seen.add(key)
            top.append(r.to_dict())
            if len(top) >= 15:
                break
    return top


@app.get("/api/pvp/rankings")
def get_pvp_rankings(period: str = "alltime",
                     score_date: Optional[str] = Query(None, alias="date"),
                     season_num: Optional[int] = Query(None),
                     submode: Optional[str] = Query(None),
                     db: Session = Depends(get_db),
                     response: Response = None):
    """Return players ranked by number of PvP wins."""
    if period not in ("daily", "season", "alltime"):
        period = "alltime"
    if response:
        response.headers["Cache-Control"] = "public, max-age=60"

    q = db.query(PvpResult)
    if submode in ("standard", "quick"):
        q = q.filter(PvpResult.submode == submode)

    if period == "daily":
        try:
            target = date.fromisoformat(score_date) if score_date else date.today()
        except ValueError:
            target = date.today()
        q = q.filter(PvpResult.created_at >= target,
                     PvpResult.created_at < target + timedelta(days=1))

    elif period == "season":
        if season_num and season_num >= 1:
            s_start, s_end = get_season_range(season_num)
            q = q.filter(PvpResult.created_at >= s_start,
                         PvpResult.created_at < s_end)
        else:
            today = date.today()
            q = q.filter(PvpResult.created_at >= today.replace(day=1))

    rows = q.all()

    # Count wins per player
    wins: dict = {}
    for r in rows:
        key   = r.winner_email or r.winner_name or "Anonymous"
        label = r.winner_name  or "Anonymous"
        if key not in wins:
            wins[key] = {"name": label, "email": r.winner_email, "wins": 0}
        wins[key]["wins"] += 1

    ranked = sorted(wins.values(), key=lambda x: x["wins"], reverse=True)
    top = ranked[:15]

    # Attach Elo rating and public profile URL for each ranked player
    emails = [p["email"] for p in top if p.get("email")]
    if emails:
        profiles = db.query(UserProfile).filter(UserProfile.email.in_(emails)).all()
        profile_map = {p.email: p for p in profiles}
        for p in top:
            prof = profile_map.get(p.get("email"))
            p["elo"] = prof.pvp_elo if prof else None
            if prof and prof.is_public:
                p["profile_url"] = f"/u/{prof.vanity_slug or prof.public_id}"
            else:
                p["profile_url"] = None

    return top


@app.get("/api/pvp/elo-rankings")
def get_pvp_elo_rankings(db: Session = Depends(get_db), response: Response = None):
    """Return players ranked by Elo rating (only players who have played at least one match)."""
    if response:
        response.headers["Cache-Control"] = "public, max-age=300"
    winner_emails = db.query(PvpResult.winner_email).filter(PvpResult.winner_email != None)
    loser_emails  = db.query(PvpResult.loser_email ).filter(PvpResult.loser_email  != None)
    played_emails = {row[0] for row in winner_emails.union(loser_emails).all()}
    if not played_emails:
        return []
    profiles = (
        db.query(UserProfile)
        .filter(UserProfile.email.in_(played_emails))
        .order_by(UserProfile.pvp_elo.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "name":        p.display_name,
            "elo":         p.pvp_elo,
            "profile_url": f"/u/{p.vanity_slug or p.public_id}" if p.is_public else None,
        }
        for p in profiles
    ]


@app.get("/api/pvp/player-card/{public_id}")
def pvp_player_card(public_id: str, db: Session = Depends(get_db)):
    """Lightweight stat card data for the PvP match header mouseover (F69)."""
    profile = db.query(UserProfile).filter(UserProfile.public_id == public_id).first()
    if not profile:
        return {}
    best_expert = (
        db.query(func.min(GameHistory.time_secs))
        .filter(GameHistory.user_email == profile.email, GameHistory.mode == "expert")
        .scalar()
    )
    wins   = db.query(func.count(PvpResult.id)).filter(PvpResult.winner_email == profile.email).scalar() or 0
    losses = db.query(func.count(PvpResult.id)).filter(PvpResult.loser_email  == profile.email).scalar() or 0
    return {
        "name":      profile.display_name,
        "elo":       profile.pvp_elo,
        "wins":      wins,
        "losses":    losses,
        "best_time": best_expert,
    }


@app.get("/tentaizu", response_class=HTMLResponse)
async def tentaizu_page(request: Request, date_param: str = Query(None, alias="date")):
    import re
    real_today = date.today().isoformat()
    puzzle_date = real_today
    if date_param and re.match(r"^\d{4}-\d{2}-\d{2}$", date_param):
        puzzle_date = date_param
    return templates.TemplateResponse("tentaizu.html", {
        "request": request, "mode": "tentaizu",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": puzzle_date,
        "real_today": real_today,
    })


@app.get("/tentaizu/how-to-play", response_class=HTMLResponse)
async def tentaizu_howto(request: Request):
    return templates.TemplateResponse("tentaizu_howto.html", {
        "request": request, "mode": "tentaizu-howto",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/tentaizu/strategy", response_class=HTMLResponse)
async def tentaizu_strategy(request: Request):
    return templates.TemplateResponse("tentaizu_strategy.html", {
        "request": request, "mode": "tentaizu-strategy",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/tentaizu/archive", response_class=HTMLResponse)
async def tentaizu_archive(request: Request):
    from datetime import timedelta
    today = date.today()
    past_dates = [(today - timedelta(days=i)).isoformat() for i in range(1, 91)]
    return templates.TemplateResponse("tentaizu_archive.html", {
        "request": request, "mode": "tentaizu-archive",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today.isoformat(),
        "past_dates": past_dates,
    })


# ── Easy 5×5 mode ─────────────────────────────────────────────────────────────

@app.get("/tentaizu/easy-5x5-6", response_class=HTMLResponse)
async def tentaizu_easy_page(request: Request):
    real_today = date.today().isoformat()
    return templates.TemplateResponse("tentaizu_easy.html", {
        "request": request, "mode": "tentaizu-easy",
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
    return templates.TemplateResponse("tentaizu_easy.html", {
        "request": request, "mode": "tentaizu-easy",
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
    import re
    valid_types = {"daily", "easy-5x5-6"}
    if puzzle_type not in valid_types:
        return RedirectResponse("/tentaizu", status_code=302)
    # Accept YYYYMMDD → convert to YYYY-MM-DD canonical form
    m = re.match(r"^(\d{4})(\d{2})(\d{2})$", date_str)
    if m:
        canonical = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        if puzzle_type == "daily":
            return RedirectResponse(f"/tentaizu/{canonical}", status_code=301)
        return RedirectResponse(f"/tentaizu/{puzzle_type}/{canonical}", status_code=301)
    # YYYY-MM-DD for daily → strip type prefix
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        if puzzle_type == "daily":
            return RedirectResponse(f"/tentaizu/{date_str}", status_code=301)
    return RedirectResponse("/tentaizu", status_code=302)


# Must be declared AFTER static sub-routes so /tentaizu/how-to-play etc. match first
@app.get("/tentaizu/{date_str}", response_class=HTMLResponse)
async def tentaizu_permalink(request: Request, date_str: str):
    import re
    real_today = date.today().isoformat()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return RedirectResponse("/tentaizu", status_code=302)
    return templates.TemplateResponse("tentaizu.html", {
        "request": request, "mode": "tentaizu",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": date_str,
        "real_today": real_today,
        "noindex": True,
    })


# ── Mosaic ────────────────────────────────────────────────────────────────────

@app.get("/mosaic", response_class=HTMLResponse)
async def mosaic_page(request: Request, seed: str = ""):
    return templates.TemplateResponse("mosaic_easy.html", {
        "request": request, "mode": "mosaic",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": date.today().isoformat(),
        "seed": seed.replace(".", "-"),
    })

@app.get("/mosaic/how-to-play", response_class=HTMLResponse)
async def mosaic_howto(request: Request):
    return templates.TemplateResponse("mosaic_howto.html", {
        "request": request, "mode": "mosaic-howto",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })

@app.get("/mosaic/easy", response_class=HTMLResponse)
async def mosaic_easy_redirect(request: Request):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/mosaic", status_code=301)

@app.get("/mosaic/standard", response_class=HTMLResponse)
async def mosaic_standard_page(request: Request, seed: str = ""):
    return templates.TemplateResponse("mosaic.html", {
        "request": request, "mode": "mosaic",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": date.today().isoformat(),
        "seed": seed.replace(".", "-"),
    })

@app.get("/mosaic/replay", response_class=HTMLResponse)
async def mosaic_replay_page(request: Request, seed: str = "", rows: int = 9, cols: int = 9):
    cell_size = 64 if rows <= 5 else 42
    return templates.TemplateResponse("mosaic_replay.html", {
        "request": request, "mode": "mosaic",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": date.today().isoformat(),
        "seed": seed, "rows": rows, "cols": cols, "cell_size": cell_size,
    })


# ── Mosaic Custom ──────────────────────────────────────────────────────────────

@app.get("/mosaic/custom/", response_class=HTMLResponse)
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
    return templates.TemplateResponse("mosaic_custom.html", {
        "request":   request, "mode": "mosaic",
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
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


@app.post("/api/mosaic-scores", status_code=201)
@limiter.limit("10/minute")
def submit_mosaic_score(payload: MosaicScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None
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
    return {"ok": True, "id": entry.id}


@app.get("/api/mosaic-scores/{puzzle_date}")
def get_mosaic_scores(puzzle_date: str, db: Session = Depends(get_db)):
    import re
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", puzzle_date):
        raise HTTPException(status_code=400, detail="Invalid date format")
    top = (
        db.query(MosaicScore)
        .filter(MosaicScore.puzzle_date == puzzle_date)
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
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


@app.post("/api/mosaic-easy-scores", status_code=201)
@limiter.limit("10/minute")
def submit_mosaic_easy_score(payload: MosaicEasyScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None
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
    return {"ok": True, "id": entry.id}


@app.get("/api/mosaic-easy-scores/{puzzle_date}")
def get_mosaic_easy_scores(puzzle_date: str, db: Session = Depends(get_db)):
    import re
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", puzzle_date):
        raise HTTPException(status_code=400, detail="Invalid date format")
    top = (
        db.query(MosaicEasyScore)
        .filter(MosaicEasyScore.puzzle_date == puzzle_date)
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
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


def _mosaic_custom_board_id(rows: int, cols: int, board_hash: str, board_mask: str) -> str:
    import hashlib
    raw = f"{rows}x{cols}:{board_hash}:{board_mask}"
    return hashlib.sha256(raw.encode()).hexdigest()


@app.post("/api/mosaic-custom-scores", status_code=201)
@limiter.limit("10/minute")
def submit_mosaic_custom_score(payload: MosaicCustomScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None
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
    return {"ok": True, "id": entry.id, "board_id": board_id}


@app.get("/api/mosaic-custom-scores/{board_id}")
def get_mosaic_custom_scores(board_id: str, db: Session = Depends(get_db)):
    import re
    if not re.match(r"^[0-9a-f]{64}$", board_id):
        raise HTTPException(status_code=400, detail="Invalid board_id")
    top = (
        db.query(MosaicCustomScore)
        .filter(MosaicCustomScore.board_id == board_id)
        .order_by(MosaicCustomScore.time_secs.asc(), MosaicCustomScore.created_at.asc())
        .limit(20)
        .all()
    )
    return _enrich_with_profiles(top, db)


# ── Tentaizu Leaderboard API ───────────────────────────────────────────────────

class TentaizuScoreSubmit(BaseModel):
    name:        str = Field(..., min_length=1, max_length=32)
    puzzle_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    time_secs:   int = Field(..., ge=0, le=99999)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


@app.post("/api/tentaizu-scores", status_code=201)
@limiter.limit("10/minute")
def submit_tentaizu_score(payload: TentaizuScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user  = get_current_user(request)
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None
    entry = TentaizuScore(
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
    record_score_submit("tentaizu", str(payload.puzzle_date))
    record_game_complete("tentaizu", mode="daily",
                         duration_ms=(payload.time_secs or 0) * 1000)
    return {"ok": True, "id": entry.id}


@app.get("/api/tentaizu-scores/{puzzle_date}")
def get_tentaizu_scores(puzzle_date: str, db: Session = Depends(get_db)):
    import re
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", puzzle_date):
        raise HTTPException(status_code=400, detail="Invalid date format")
    top = (
        db.query(TentaizuScore)
        .filter(TentaizuScore.puzzle_date == puzzle_date)
        .order_by(TentaizuScore.time_secs.asc(), TentaizuScore.created_at.asc())
        .limit(20)
        .all()
    )
    return _enrich_with_profiles(top, db)


# ── Tentaizu Easy (5×5) Leaderboard API ───────────────────────────────────────

class TentaizuEasyScoreSubmit(BaseModel):
    name:        str = Field(..., min_length=1, max_length=32)
    puzzle_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    time_secs:   int = Field(..., ge=0, le=99999)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


@app.post("/api/tentaizu-easy-scores", status_code=201)
@limiter.limit("10/minute")
def submit_tentaizu_easy_score(payload: TentaizuEasyScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user  = get_current_user(request)
    entry = TentaizuEasyScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        puzzle_date = payload.puzzle_date,
        time_secs   = payload.time_secs,
        client_type = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"ok": True, "id": entry.id}


@app.get("/api/tentaizu-easy-scores/{puzzle_date}")
def get_tentaizu_easy_scores(puzzle_date: str, db: Session = Depends(get_db)):
    import re
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", puzzle_date):
        raise HTTPException(status_code=400, detail="Invalid date format")
    top = (
        db.query(TentaizuEasyScore)
        .filter(TentaizuEasyScore.puzzle_date == puzzle_date)
        .order_by(TentaizuEasyScore.time_secs.asc(), TentaizuEasyScore.created_at.asc())
        .limit(20)
        .all()
    )
    return _enrich_with_profiles(top, db)


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
        stats[mode] = {
            "games_played": len(scores),
            "best_time":    min(times),
            "avg_time":     round(sum(times) / len(times), 1),
            "worst_time":   max(times),
            "recent":       [s.to_dict() for s in scores[:10]],
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
    _skin = payload.pref_skin if payload.pref_skin in site_settings.ALLOWED_SKINS else site_settings.DEFAULT_SKIN
    profile.pref_skin     = 'classic' if _skin == 'diana' else _skin
    db.commit()
    return {"ok": True, "public_id": profile.public_id}


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
        return templates.TemplateResponse("profile_private.html", {
            "request": request,
            "display_name": profile.display_name or "This player",
            "lang": get_lang(request), "t": get_t(request),
        }, status_code=200)
    return templates.TemplateResponse("profile_public.html", {
        "request":       request,
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
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
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


# ── Admin ─────────────────────────────────────────────────────────────────────
_admin_emails_raw = Config(".env")("ADMIN_EMAILS", default="")
ADMIN_EMAILS = {e.strip() for e in _admin_emails_raw.split(",") if e.strip()}

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user or user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")

    today = date.today()

    def _counts(model, mode_col):
        """Return (today_count, alltime_count) dicts keyed by mode value."""
        from sqlalchemy import cast, Date
        rows_all = (
            db.query(mode_col, func.count().label("n"))
            .group_by(mode_col)
            .all()
        )
        rows_today = (
            db.query(mode_col, func.count().label("n"))
            .filter(func.date(model.created_at) == today)
            .group_by(mode_col)
            .all()
        )
        return (
            {r[0]: r[1] for r in rows_today},
            {r[0]: r[1] for r in rows_all},
        )

    # Classic minesweeper (uses Score table for submitted scores, GameHistory for all plays)
    ms_today, ms_all = _counts(Score, Score.mode)
    gh_today, gh_all = _counts(GameHistory, GameHistory.mode)

    # Rush
    rush_today, rush_all = _counts(RushScore, RushScore.rush_mode)

    # Tentaizu (group by puzzle_date for today)
    tent_all_count = db.query(func.count()).select_from(TentaizuScore).scalar()
    tent_today_count = (
        db.query(func.count()).select_from(TentaizuScore)
        .filter(func.date(TentaizuScore.created_at) == today)
        .scalar()
    )

    # Cylinder / Toroid
    cyl_today, cyl_all = _counts(CylinderScore, CylinderScore.cyl_mode)
    tor_today, tor_all = _counts(ToroidScore, ToroidScore.tor_mode)

    # Users
    total_users = db.query(func.count()).select_from(UserProfile).scalar()
    new_users_today = (
        db.query(func.count()).select_from(UserProfile)
        .filter(func.date(UserProfile.created_at) == today)
        .scalar()
        if hasattr(UserProfile, "created_at") else "n/a"
    )

    # Git activity this week
    def _git(*args, **kwargs):
        return subprocess.check_output(
            args, cwd=os.path.dirname(os.path.abspath(__file__)),
            text=True, timeout=5,
        ).strip()

    try:
        git_head = _git("git", "rev-parse", "HEAD")
        week_since = (today - __import__("datetime").timedelta(days=today.weekday())).isoformat()
        log_lines = _git(
            "git", "log", f"--since={week_since}",
            "--format=%H|%an|%s",
        ).splitlines()
        git_commits_this_week = []
        contributors: dict = {}
        for line in log_lines:
            parts = line.split("|", 2)
            if len(parts) == 3:
                h, author, subject = parts
                git_commits_this_week.append({"hash": h[:7], "author": author, "subject": subject})
                contributors[author] = contributors.get(author, 0) + 1
        git_contributors = sorted(contributors.items(), key=lambda x: -x[1])
    except Exception:
        git_head = "unknown"
        git_commits_this_week = []
        git_contributors = []

    # Staging commit — fetch from localhost:8002/health
    staging_head = None
    try:
        import urllib.request, json as _json
        with urllib.request.urlopen("http://localhost:8002/health", timeout=2) as resp:
            staging_head = _json.loads(resp.read()).get("commit", "unknown")
    except Exception:
        staging_head = None

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "user": user,
        "lang": get_lang(request),
        "t": get_t(request),
        "today": today.isoformat(),
        "total_users": total_users,
        "new_users_today": new_users_today,
        "ms_today": ms_today,
        "ms_all": ms_all,
        "gh_today": gh_today,
        "gh_all": gh_all,
        "rush_today": rush_today,
        "rush_all": rush_all,
        "tent_today": tent_today_count,
        "tent_all": tent_all_count,
        "cyl_today": cyl_today,
        "cyl_all": cyl_all,
        "tor_today": tor_today,
        "tor_all": tor_all,
        "git_head": git_head,
        "git_commits_this_week": git_commits_this_week,
        "git_contributors": git_contributors,
        "staging_head": staging_head,
    })


@app.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user or user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")

    import json as _json
    from sqlalchemy import text

    # Signups per day for cumulative growth chart
    signup_rows = db.execute(text("""
        SELECT DATE(created_at) AS d, COUNT(*) AS cnt
        FROM user_profiles
        WHERE created_at IS NOT NULL
        GROUP BY DATE(created_at)
        ORDER BY d ASC
    """)).fetchall()
    cumulative, running = [], 0
    for r in signup_rows:
        running += r.cnt
        cumulative.append({"date": str(r.d), "total": running})
    chart_data = _json.dumps(cumulative)

    rows = db.execute(text("""
        SELECT
            u.email, u.display_name, u.public_id, u.vanity_slug, u.created_at,
            COALESCE(gh.cnt,   0) AS classic_games,
            COALESCE(s.cnt,    0) AS classic_scores,
            COALESCE(r.cnt,    0) AS rush_scores,
            COALESCE(c.cnt,    0) AS cyl_scores,
            COALESCE(t.cnt,    0) AS tor_scores,
            COALESCE(tent.cnt, 0) AS tent_scores,
            COALESCE(rp.cnt,   0) AS replay_scores,
            COALESCE(gh.cnt,   0) + COALESCE(s.cnt,    0) + COALESCE(r.cnt,  0) +
            COALESCE(c.cnt,    0) + COALESCE(t.cnt,    0) + COALESCE(tent.cnt,0) +
            COALESCE(rp.cnt,   0) AS total_games
        FROM user_profiles u
        LEFT JOIN (SELECT user_email, COUNT(*) cnt FROM game_history     GROUP BY user_email) gh   ON gh.user_email   = u.email
        LEFT JOIN (SELECT user_email, COUNT(*) cnt FROM scores            GROUP BY user_email) s    ON s.user_email    = u.email
        LEFT JOIN (SELECT user_email, COUNT(*) cnt FROM rush_scores       GROUP BY user_email) r    ON r.user_email    = u.email
        LEFT JOIN (SELECT user_email, COUNT(*) cnt FROM cylinder_scores   GROUP BY user_email) c    ON c.user_email    = u.email
        LEFT JOIN (SELECT user_email, COUNT(*) cnt FROM toroid_scores     GROUP BY user_email) t    ON t.user_email    = u.email
        LEFT JOIN (SELECT user_email, COUNT(*) cnt FROM tentaizu_scores   GROUP BY user_email) tent ON tent.user_email = u.email
        LEFT JOIN (SELECT user_email, COUNT(*) cnt FROM replay_scores     GROUP BY user_email) rp   ON rp.user_email   = u.email
        ORDER BY total_games DESC
    """)).fetchall()

    return templates.TemplateResponse("admin_users.html", {
        "request": request,
        "user": user,
        "lang": get_lang(request),
        "t": get_t(request),
        "users": rows,
        "chart_data": chart_data,
    })


def _fmt_bytes(n: int) -> str:
    """Return a human-readable byte size string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


@app.get("/admin/kanban", response_class=HTMLResponse)
def admin_kanban(request: Request):
    import re, os

    user = get_current_user(request)
    if not user or user.get("email") not in ADMIN_EMAILS:
        return RedirectResponse("/", status_code=302)

    kanban_path = os.path.join(os.path.dirname(__file__), "KANBAN.md")
    try:
        text = open(kanban_path).read()
    except FileNotFoundError:
        text = ""

    # Parse columns: split on ## headings
    columns = []
    for block in re.split(r'^## ', text, flags=re.MULTILINE):
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        col_name = lines[0].strip()
        cards = []
        for line in lines[1:]:
            line = line.strip()
            if not line.startswith('- '):
                continue
            line = line[2:].strip()
            # Extract assignee (@name at end)
            assignee_match = re.search(r'@(\S+)$', line)
            assignee = assignee_match.group(1) if assignee_match else None
            if assignee:
                line = line[:assignee_match.start()].strip()
            # Extract ID prefix (F#, B#, D#)
            id_match = re.match(r'^([FBD]\d+)\s+', line)
            card_id = id_match.group(1) if id_match else None
            description = line[id_match.end():].strip() if id_match else line
            cards.append({"id": card_id, "description": description, "assignee": assignee})
        columns.append({"name": col_name, "cards": cards})

    return templates.TemplateResponse("admin_kanban.html", {
        "request": request,
        "user": user,
        "t": get_t(request),
        "lang": get_lang(request),
        "mode": "admin",
        "columns": columns,
    })


@app.get("/admin/operations", response_class=HTMLResponse)
def admin_operations(request: Request, db: Session = Depends(get_db)):
    import json as _json

    user = get_current_user(request)
    if not user or user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")

    # ── Live snapshot ─────────────────────────────────────────────────────────
    disk = psutil.disk_usage("/")
    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()

    # ── Application stats ─────────────────────────────────────────────────────
    table_counts = {
        "Score (leaderboard)":    db.query(func.count()).select_from(Score).scalar(),
        "GameHistory":            db.query(func.count()).select_from(GameHistory).scalar(),
        "RushScore":              db.query(func.count()).select_from(RushScore).scalar(),
        "TentaizuScore":          db.query(func.count()).select_from(TentaizuScore).scalar(),
        "TentaizuEasyScore":      db.query(func.count()).select_from(TentaizuEasyScore).scalar(),
        "CylinderScore":          db.query(func.count()).select_from(CylinderScore).scalar(),
        "ToroidScore":            db.query(func.count()).select_from(ToroidScore).scalar(),
        "PvpResult":              db.query(func.count()).select_from(PvpResult).scalar(),
        "UserProfile":            db.query(func.count()).select_from(UserProfile).scalar(),
    }
    total_records = sum(table_counts.values())

    db_size_bytes = db.execute(
        text("SELECT SUM(data_length + index_length) "
             "FROM information_schema.tables WHERE table_schema = DATABASE()")
    ).scalar() or 0

    # ── Network stats ─────────────────────────────────────────────────────────
    net = psutil.net_io_counters()
    try:
        conns = psutil.net_connections(kind="tcp")
        active_connections = sum(1 for c in conns if c.status == "ESTABLISHED")
    except (psutil.AccessDenied, PermissionError):
        active_connections = None

    # ── Historical data for charts (last 48 hourly snapshots) ─────────────────
    history = (
        db.query(ServerStats)
        .order_by(ServerStats.recorded_at.desc())
        .limit(48)
        .all()
    )
    history = list(reversed(history))

    chart_labels     = [r.recorded_at.strftime("%-m/%-d %-I%p") for r in history]
    chart_cpu        = [round(r.cpu_percent, 1)  for r in history]
    chart_mem        = [round(r.mem_percent, 1)  for r in history]
    chart_disk       = [round(r.disk_percent, 1) for r in history]
    chart_db_mb      = [round(r.db_size_mb, 2)   for r in history]
    chart_net_sent   = [round((r.net_delta_sent or 0) / (1024 ** 2), 2) for r in history]
    chart_net_recv   = [round((r.net_delta_recv or 0) / (1024 ** 2), 2) for r in history]
    chart_requests   = [r.http_requests for r in history]

    return templates.TemplateResponse("admin_operations.html", {
        "request": request,
        "user": user,
        "lang": get_lang(request),
        "t": get_t(request),
        # live snapshot
        "disk_total":    _fmt_bytes(disk.total),
        "disk_used":     _fmt_bytes(disk.used),
        "disk_free":     _fmt_bytes(disk.free),
        "disk_percent":  disk.percent,
        "cpu_percent":   cpu_percent,
        "mem_total":     _fmt_bytes(mem.total),
        "mem_used":      _fmt_bytes(mem.used),
        "mem_free":      _fmt_bytes(mem.available),
        "mem_percent":   mem.percent,
        # app
        "table_counts":   table_counts,
        "total_records":  total_records,
        "db_size":        _fmt_bytes(db_size_bytes),
        # network live
        "net_bytes_sent":     _fmt_bytes(net.bytes_sent),
        "net_bytes_recv":     _fmt_bytes(net.bytes_recv),
        "net_packets_sent":   f"{net.packets_sent:,}",
        "net_packets_recv":   f"{net.packets_recv:,}",
        "active_connections": active_connections,
        # chart data (JSON strings)
        "chart_labels":   _json.dumps(chart_labels),
        "chart_cpu":      _json.dumps(chart_cpu),
        "chart_mem":      _json.dumps(chart_mem),
        "chart_disk":     _json.dumps(chart_disk),
        "chart_db_mb":    _json.dumps(chart_db_mb),
        "chart_net_sent": _json.dumps(chart_net_sent),
        "chart_net_recv": _json.dumps(chart_net_recv),
        "chart_requests": _json.dumps(chart_requests),
    })


@app.get("/admin/web_traffic", response_class=HTMLResponse)
def admin_web_traffic(request: Request, db: Session = Depends(get_db)):
    import json as _json
    import csv as _csv
    user = get_current_user(request)
    if not user or user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")

    rows = (
        db.query(WebTrafficStats)
        .order_by(WebTrafficStats.stat_date.asc())
        .all()
    )

    labels       = [str(r.stat_date)      for r in rows]
    total_req    = [r.total_requests       for r in rows]
    unique_ips   = [r.unique_ips           for r in rows]
    http_200     = [r.http_200             for r in rows]
    http_201     = [r.http_201             for r in rows]
    http_206     = [r.http_206             for r in rows]
    http_101     = [r.http_101             for r in rows]
    http_302     = [r.http_302             for r in rows]
    http_304     = [r.http_304             for r in rows]
    http_307     = [r.http_307             for r in rows]
    http_403     = [r.http_403             for r in rows]
    http_404     = [r.http_404             for r in rows]
    http_405     = [r.http_405             for r in rows]
    http_422     = [r.http_422             for r in rows]
    http_500     = [r.http_500             for r in rows]
    http_503     = [r.http_503             for r in rows]

    # ── Operations data (same as admin/operations) ────────────────────────────
    disk        = psutil.disk_usage("/")
    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem         = psutil.virtual_memory()
    net         = psutil.net_io_counters()
    try:
        conns = psutil.net_connections(kind="tcp")
        active_connections = sum(1 for c in conns if c.status == "ESTABLISHED")
    except (psutil.AccessDenied, PermissionError):
        active_connections = None

    table_counts = {
        "Score (leaderboard)": db.query(func.count()).select_from(Score).scalar(),
        "GameHistory":         db.query(func.count()).select_from(GameHistory).scalar(),
        "RushScore":           db.query(func.count()).select_from(RushScore).scalar(),
        "TentaizuScore":       db.query(func.count()).select_from(TentaizuScore).scalar(),
        "CylinderScore":       db.query(func.count()).select_from(CylinderScore).scalar(),
        "ToroidScore":         db.query(func.count()).select_from(ToroidScore).scalar(),
        "PvpResult":           db.query(func.count()).select_from(PvpResult).scalar(),
        "UserProfile":         db.query(func.count()).select_from(UserProfile).scalar(),
    }
    total_records = sum(table_counts.values())
    db_size_bytes = db.execute(
        text("SELECT SUM(data_length + index_length) "
             "FROM information_schema.tables WHERE table_schema = DATABASE()")
    ).scalar() or 0

    # ── AdSense earnings from analysis/report.csv ────────────────────────────
    _report_path = os.path.join(os.path.dirname(__file__), "analysis", "report.csv")
    earnings_rows = []
    try:
        with open(_report_path, newline="", encoding="utf-8") as _f:
            for r in _csv.DictReader(_f):
                earnings_rows.append({
                    "date":           r.get("Date", ""),
                    "earnings":       r.get("Estimated earnings (USD)", ""),
                    "page_views":     r.get("Page views", ""),
                    "page_rpm":       r.get("Page RPM (USD)", ""),
                    "impressions":    r.get("Impressions", ""),
                    "imp_rpm":        r.get("Impression RPM (USD)", ""),
                    "viewable":       r.get("Active View Viewable", ""),
                    "clicks":         r.get("Clicks", ""),
                })
        earnings_rows.sort(key=lambda x: x["date"])
    except OSError:
        pass

    earn_totals = {
        "earnings":    sum(float(r["earnings"])   for r in earnings_rows if r["earnings"]),
        "page_views":  sum(int(r["page_views"])   for r in earnings_rows if r["page_views"]),
        "impressions": sum(int(r["impressions"])  for r in earnings_rows if r["impressions"]),
        "clicks":      sum(int(r["clicks"])       for r in earnings_rows if r["clicks"]),
    }

    earn_labels   = _json.dumps([r["date"]       for r in earnings_rows])
    earn_earnings = _json.dumps([float(r["earnings"])  if r["earnings"]  else None for r in earnings_rows])
    earn_page_rpm = _json.dumps([float(r["page_rpm"])  if r["page_rpm"]  else None for r in earnings_rows])
    earn_imp_rpm  = _json.dumps([float(r["imp_rpm"])   if r["imp_rpm"]   else None for r in earnings_rows])
    earn_clicks   = _json.dumps([int(r["clicks"])      if r["clicks"]    else None for r in earnings_rows])
    earn_views    = _json.dumps([int(r["page_views"])  if r["page_views"] else None for r in earnings_rows])

    yesterday = date.today() - timedelta(days=1)
    url_traffic = get_url_traffic_stats(yesterday)

    history = list(reversed(
        db.query(ServerStats)
        .order_by(ServerStats.recorded_at.desc())
        .limit(48)
        .all()
    ))
    hr_labels    = [r.recorded_at.strftime("%-m/%-d %-I%p") for r in history]
    hr_cpu       = [round(r.cpu_percent, 1)  for r in history]
    hr_mem       = [round(r.mem_percent, 1)  for r in history]
    hr_disk      = [round(r.disk_percent, 1) for r in history]
    hr_db_mb     = [round(r.db_size_mb, 2)   for r in history]
    hr_net_sent  = [round((r.net_delta_sent or 0) / (1024 ** 2), 2) for r in history]
    hr_net_recv  = [round((r.net_delta_recv or 0) / (1024 ** 2), 2) for r in history]
    hr_requests  = [r.http_requests for r in history]

    return templates.TemplateResponse("admin_web_traffic.html", {
        "request":      request,
        "user":         user,
        "lang":         get_lang(request),
        "t":            get_t(request),
        "rows":         rows,
        "chart_labels": _json.dumps(labels),
        "total_req":    _json.dumps(total_req),
        "unique_ips":   _json.dumps(unique_ips),
        "http_200":     _json.dumps(http_200),
        "http_201":     _json.dumps(http_201),
        "http_206":     _json.dumps(http_206),
        "http_101":     _json.dumps(http_101),
        "http_302":     _json.dumps(http_302),
        "http_304":     _json.dumps(http_304),
        "http_307":     _json.dumps(http_307),
        "http_403":     _json.dumps(http_403),
        "http_404":     _json.dumps(http_404),
        "http_405":     _json.dumps(http_405),
        "http_422":     _json.dumps(http_422),
        "http_500":     _json.dumps(http_500),
        "http_503":     _json.dumps(http_503),
        "hr_labels":    _json.dumps(hr_labels),
        "hr_cpu":       _json.dumps(hr_cpu),
        "hr_mem":       _json.dumps(hr_mem),
        "hr_disk":      _json.dumps(hr_disk),
        "hr_db_mb":     _json.dumps(hr_db_mb),
        "hr_net_sent":  _json.dumps(hr_net_sent),
        "hr_net_recv":  _json.dumps(hr_net_recv),
        "hr_requests":  _json.dumps(hr_requests),
        # live snapshot
        "cpu_percent":        cpu_percent,
        "mem_used":           _fmt_bytes(mem.used),
        "mem_total":          _fmt_bytes(mem.total),
        "mem_free":           _fmt_bytes(mem.available),
        "mem_percent":        mem.percent,
        "disk_used":          _fmt_bytes(disk.used),
        "disk_total":         _fmt_bytes(disk.total),
        "disk_free":          _fmt_bytes(disk.free),
        "disk_percent":       disk.percent,
        "net_bytes_sent":     _fmt_bytes(net.bytes_sent),
        "net_bytes_recv":     _fmt_bytes(net.bytes_recv),
        "net_packets_sent":   f"{net.packets_sent:,}",
        "net_packets_recv":   f"{net.packets_recv:,}",
        "active_connections": active_connections,
        "table_counts":       table_counts,
        "total_records":      total_records,
        "db_size":            _fmt_bytes(db_size_bytes),
        "url_traffic":        url_traffic,
        "url_traffic_date":   str(yesterday),
        # AdSense earnings
        "earnings_rows":      earnings_rows,
        "earn_totals":        earn_totals,
        "earn_labels":        earn_labels,
        "earn_earnings":      earn_earnings,
        "earn_page_rpm":      earn_page_rpm,
        "earn_imp_rpm":       earn_imp_rpm,
        "earn_clicks":        earn_clicks,
        "earn_views":         earn_views,
    })


@app.get("/admin/blog", response_class=HTMLResponse)
def admin_blog(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user or user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")

    pending  = db.query(BlogComment).filter_by(approved=False).order_by(BlogComment.created_at).all()
    approved = db.query(BlogComment).filter_by(approved=True).order_by(BlogComment.created_at.desc()).limit(50).all()
    return templates.TemplateResponse("admin_blog.html", {
        "request": request,
        "user": user,
        "lang": get_lang(request),
        "t": get_t(request),
        "pending":  pending,
        "approved": approved,
    })


@app.post("/admin/blog/comments/{comment_id}/approve")
def admin_approve_comment(comment_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user or user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")
    comment = db.query(BlogComment).filter_by(id=comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Not found")
    comment.approved = True
    db.commit()
    return RedirectResponse("/admin/blog", status_code=303)


@app.post("/admin/blog/comments/{comment_id}/delete")
def admin_delete_comment(comment_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user or user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")
    comment = db.query(BlogComment).filter_by(id=comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(comment)
    db.commit()
    return RedirectResponse("/admin/blog", status_code=303)


@app.get("/admin/contact", response_class=HTMLResponse)
def admin_contact(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user or user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")
    unread = db.query(ContactMessage).filter_by(read=False).order_by(ContactMessage.created_at.desc()).all()
    read   = db.query(ContactMessage).filter_by(read=True).order_by(ContactMessage.created_at.desc()).limit(50).all()
    return templates.TemplateResponse("admin_contact.html", {
        "request": request,
        "user": user,
        "lang": get_lang(request),
        "t": get_t(request),
        "unread": unread,
        "read": read,
    })


@app.post("/admin/contact/{msg_id}/mark-read")
def admin_contact_mark_read(msg_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user or user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")
    msg = db.query(ContactMessage).filter_by(id=msg_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Not found")
    msg.read = True
    db.commit()
    return RedirectResponse("/admin/contact", status_code=303)


@app.post("/admin/contact/{msg_id}/delete")
def admin_contact_delete(msg_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user or user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")
    msg = db.query(ContactMessage).filter_by(id=msg_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(msg)
    db.commit()
    return RedirectResponse("/admin/contact", status_code=303)


@app.get("/admin/hscleaning", response_class=HTMLResponse)
def admin_hscleaning(
    request: Request,
    db: Session = Depends(get_db),
    mode: str = "beginner",
    date_str: str = "",
    board_hash: str = "",
    hmode: str = "all",
    no_guess: str = "all",
):
    user = get_current_user(request)
    if not user or user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")

    from datetime import date as _date
    target_date = date.today()
    if date_str:
        try:
            target_date = _date.fromisoformat(date_str)
        except ValueError:
            pass

    valid_modes = {"beginner", "intermediate", "expert", "custom"}
    if mode not in valid_modes:
        mode = "beginner"

    # Daily scores for selected mode + date
    daily_q = db.query(Score).filter(
        Score.mode == mode,
        func.date(Score.created_at) == target_date,
    ).order_by(Score.time_ms.asc(), Score.time_secs.asc())
    daily_scores = daily_q.limit(50).all()

    # Hash search results
    hash_scores = []
    if board_hash.strip():
        hq = db.query(Score).filter(Score.board_hash == board_hash.strip())
        if hmode in valid_modes:
            hq = hq.filter(Score.mode == hmode)
        if no_guess == "true":
            hq = hq.filter(Score.no_guess == True)
        elif no_guess == "false":
            hq = hq.filter(Score.no_guess == False)
        hash_scores = hq.order_by(Score.time_ms.asc(), Score.time_secs.asc()).limit(100).all()

    return templates.TemplateResponse("admin_hscleaning.html", {
        "request": request,
        "user": user,
        "lang": get_lang(request),
        "t": get_t(request),
        "mode": mode,
        "date_str": target_date.isoformat(),
        "daily_scores": daily_scores,
        "board_hash": board_hash.strip(),
        "hmode": hmode,
        "no_guess": no_guess,
        "hash_scores": hash_scores,
        "valid_modes": sorted(valid_modes),
    })


@app.post("/admin/hscleaning/delete/{score_id}")
def admin_hscleaning_delete(
    score_id: int,
    request: Request,
    db: Session = Depends(get_db),
    next_url: str = Query(default="/admin/hscleaning"),
):
    user = get_current_user(request)
    if not user or user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")
    score = db.query(Score).filter_by(id=score_id).first()
    if score:
        db.delete(score)
        db.commit()
    return RedirectResponse(next_url, status_code=303)


@app.get("/admin/analysis", response_class=HTMLResponse)
def admin_analysis(request: Request, doc: Optional[str] = None, folder: Optional[str] = None):
    import markdown as md_lib
    import os

    user = get_current_user(request)
    if not user or user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")

    analysis_dir = os.path.join(os.path.dirname(__file__), "analysis")
    download_exts = {".pptx", ".xlsx", ".docx", ".pdf"}

    # Validate folder param — no traversal, no nesting
    if folder and (".." in folder or "/" in folder or "\\" in folder):
        folder = None
    current_folder = None
    if folder:
        candidate = os.path.join(analysis_dir, folder)
        if os.path.isdir(candidate):
            current_folder = folder

    active_dir = os.path.join(analysis_dir, current_folder) if current_folder else analysis_dir

    # Always list subfolders from the root (one level only)
    folders = []
    docs = []
    downloads = []
    if os.path.isdir(analysis_dir):
        for name in sorted(os.listdir(analysis_dir)):
            if os.path.isdir(os.path.join(analysis_dir, name)) and not name.startswith("."):
                folders.append(name)

    if os.path.isdir(active_dir):
        for fname in sorted(os.listdir(active_dir)):
            fpath = os.path.join(active_dir, fname)
            if not os.path.isfile(fpath):
                continue
            if fname.endswith(".md") or fname.endswith(".html"):
                docs.append(fname.rsplit(".", 1)[0])
            elif any(fname.endswith(ext) for ext in download_exts):
                downloads.append(fname)

    content_html = None
    current_doc = None
    if doc and doc in docs:
        md_path   = os.path.join(active_dir, doc + ".md")
        html_path = os.path.join(active_dir, doc + ".html")
        if os.path.isfile(md_path):
            with open(md_path, encoding="utf-8") as f:
                content_html = md_lib.markdown(f.read(), extensions=["extra", "sane_lists"])
        elif os.path.isfile(html_path):
            with open(html_path, encoding="utf-8") as f:
                content_html = f.read()
        current_doc = doc

    # Resolve the actual filename (with extension) for the download link
    current_doc_file = None
    if current_doc:
        for ext in (".md", ".html"):
            if os.path.isfile(os.path.join(active_dir, current_doc + ext)):
                current_doc_file = current_doc + ext
                break

    return templates.TemplateResponse("admin_analysis.html", {
        "request":          request,
        "user":             user,
        "lang":             get_lang(request),
        "t":                get_t(request),
        "mode":             "admin",
        "folders":          folders,
        "current_folder":   current_folder,
        "docs":             docs,
        "downloads":        downloads,
        "content_html":     content_html,
        "current_doc":      current_doc,
        "current_doc_file": current_doc_file,
    })


@app.get("/admin/analysis/download")
def admin_analysis_download(request: Request, file: str):
    import os
    user = get_current_user(request)
    if not user or user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Allow at most one subfolder level (e.g. "folder/file.pdf").
    # Reject anything with ".." or backslashes, or more than one slash.
    if "\\" in file or ".." in file or file.count("/") > 1:
        raise HTTPException(status_code=400, detail="Invalid filename")

    analysis_dir = os.path.join(os.path.dirname(__file__), "analysis")
    path = os.path.realpath(os.path.join(analysis_dir, file))
    # Confirm resolved path is still inside analysis_dir
    if not path.startswith(os.path.realpath(analysis_dir) + os.sep):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path, filename=os.path.basename(file))


@app.get("/admin/analysis/{filename}")
def admin_analysis_by_path(filename: str, folder: Optional[str] = None):
    doc = filename.rsplit(".", 1)[0] if "." in filename else filename
    url = f"/admin/analysis?doc={doc}"
    if folder:
        url += f"&folder={folder}"
    return RedirectResponse(url, status_code=302)


# ── Nonosweeper scores ────────────────────────────────────────────────────────
# NOTE: must appear before the 3-segment archive catch-all below.

class NonosweeperScoreSubmit(BaseModel):
    name:        str = Field(..., min_length=1, max_length=32)
    puzzle_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    difficulty:  str = Field(..., pattern=r"^(beginner|intermediate|expert)$")
    time_secs:   int = Field(..., ge=0, le=99999)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


@app.post("/api/nonosweeper-scores", status_code=201)
@limiter.limit("10/minute")
def submit_nonosweeper_score(payload: NonosweeperScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None
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
    record_score_submit("nonosweeper", str(payload.puzzle_date))
    record_game_complete("nonosweeper", mode=payload.difficulty,
                         duration_ms=(payload.time_secs or 0) * 1000)
    return {"ok": True, "id": entry.id}


@app.get("/api/nonosweeper-scores/{puzzle_date}")
def get_nonosweeper_scores(
    puzzle_date: str,
    difficulty: str = Query("beginner"),
    db: Session = Depends(get_db),
):
    import re
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", puzzle_date):
        raise HTTPException(status_code=400, detail="Invalid date format")
    if difficulty not in ("beginner", "intermediate", "expert"):
        difficulty = "beginner"
    top = (
        db.query(NonosweeperScore)
        .filter(
            NonosweeperScore.puzzle_date == puzzle_date,
            NonosweeperScore.difficulty  == difficulty,
        )
        .order_by(NonosweeperScore.time_secs.asc(), NonosweeperScore.created_at.asc())
        .limit(20)
        .all()
    )
    return _enrich_with_profiles(top, db)


# ── Archive routes (must be last — parameterised path catches all 3-segment URLs) ─

_DATE_DAILY_RE   = __import__("re").compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_MONTHLY_RE = __import__("re").compile(r"^\d{4}-\d{2}$")

# ── Mahjong Solitaire ─────────────────────────────────────────────────────────

_MAH_INDEX_PATH     = os.path.join("static", "mah", "index.html")
_MAH_TURTLE_BOARD   = "2175883231"  # Turtle layout — fixed daily board


@app.get("/other/mahjong", response_class=HTMLResponse)
def mahjong_landing(request: Request):
    return RedirectResponse("/other/mahjong/daily", status_code=302)


@app.get("/other/mahjong/daily")
def mahjong_daily_page(request: Request):
    return RedirectResponse(f"/other/mahjong/?board={_MAH_TURTLE_BOARD}", status_code=302)


@app.get("/other/mahjong/")
def mahjong_game_root():
    if not os.path.isfile(_MAH_INDEX_PATH):
        raise HTTPException(status_code=503, detail="Game not yet deployed")
    return FileResponse(_MAH_INDEX_PATH)


@app.get("/other/mahjong/leaderboard", response_class=HTMLResponse)
def mahjong_leaderboard_page(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse("mj_leaderboard.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today,
    })


@app.get("/other/mahjong/how-to-play", response_class=HTMLResponse)
def mahjong_howtoplay_page(request: Request):
    return templates.TemplateResponse("mj_howtoplay.html", {
        "request": request, "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@app.get("/other/mahjong/{path:path}")
def mahjong_game_static(path: str):
    file_path = os.path.join("static", "mah", path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(_MAH_INDEX_PATH)


_UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)

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
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
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


@app.post("/api/mahjong-scores", status_code=201)
@limiter.limit("10/minute")
def submit_mahjong_score(payload: MahjongScoreSubmit, request: Request, db: Session = Depends(get_db)):
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
    record_score_submit("mahjong", payload.puzzle_date)
    record_game_complete("mahjong", mode="daily", duration_ms=payload.time_ms)
    return {"ok": True, "id": entry.id}


@app.get("/api/mahjong-scores")
def get_mahjong_scores(
    request: Request,
    puzzle_date: Optional[str] = Query(None, alias="date", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    season: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    all_time: Optional[bool] = Query(None, alias="all"),
    db: Session = Depends(get_db),
):
    LIMIT = 20
    if puzzle_date:
        top = (
            db.query(MahjongScore)
            .filter(MahjongScore.puzzle_date == puzzle_date)
            .order_by(MahjongScore.time_ms.asc(), MahjongScore.created_at.asc())
            .limit(LIMIT).all()
        )
    elif season:
        year, month = season.split("-")
        prefix = f"{year}-{month}"
        top = (
            db.query(MahjongScore)
            .filter(MahjongScore.puzzle_date.like(f"{prefix}%"))
            .order_by(MahjongScore.time_ms.asc(), MahjongScore.created_at.asc())
            .limit(LIMIT).all()
        )
    else:
        top = (
            db.query(MahjongScore)
            .order_by(MahjongScore.time_ms.asc(), MahjongScore.created_at.asc())
            .limit(LIMIT).all()
        )
    return _enrich_with_profiles(top, db)


# ── Jigsaw Puzzle ─────────────────────────────────────────────────────────────

_JIGSAW_PUZZLE_DIR = os.path.join("static", "img", "puzzle")
_JIGSAW_UPLOAD_DIR = os.path.join("static", "uploads", "jigsaw")
_JIGSAW_DIFFICULTIES = ("beginner", "intermediate", "expert")


_JIGSAW_APRIL_FOOLS = "CaptainHoneyStereogram.png"

def _jigsaw_daily_image(puzzle_date: str) -> str:
    """Return the image filename for the given date (seeded random selection).
    April 1st always returns the April Fools image; that image is excluded from
    the random pool on all other days.
    """
    if puzzle_date[5:] == "04-01":   # MM-DD portion
        return _JIGSAW_APRIL_FOOLS
    try:
        images = sorted(
            f for f in os.listdir(_JIGSAW_PUZZLE_DIR)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
            and f != _JIGSAW_APRIL_FOOLS
        )
    except OSError:
        images = []
    if not images:
        return ""
    import hashlib
    seed = int(hashlib.md5(puzzle_date.encode()).hexdigest(), 16)
    return images[seed % len(images)]


@app.get("/other/jigsaw", response_class=HTMLResponse)
def jigsaw_landing(request: Request):
    return RedirectResponse("/other/jigsaw/daily", status_code=302)


@app.get("/other/jigsaw/daily", response_class=HTMLResponse)
def jigsaw_daily_page(request: Request,
                      img: Optional[str] = Query(None),
                      diff: Optional[str] = Query(None)):
    import re
    today = date.today().isoformat()
    # Gallery can override image via ?img= query param
    if img and re.match(r'^[A-Za-z0-9_\-\.]{1,256}$', img):
        image_name = img
    else:
        image_name = _jigsaw_daily_image(today)
    difficulty = diff if diff in _JIGSAW_DIFFICULTIES else ""
    return templates.TemplateResponse("jigsaw_daily.html", {
        "request":    request,
        "mode":       "other",
        "user":       get_current_user(request),
        "lang":       get_lang(request),
        "t":          get_t(request),
        "today":      today,
        "image_name": image_name,
        "difficulty": difficulty,
        "photo_url":  None,
        "board_hash": None,
        "display_name": None,
    })


@app.get("/other/jigsaw/gallery", response_class=HTMLResponse)
def jigsaw_gallery_page(request: Request):
    try:
        images = sorted(
            f for f in os.listdir(_JIGSAW_PUZZLE_DIR)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        )
    except OSError:
        images = []
    return templates.TemplateResponse("jigsaw_gallery.html", {
        "request": request,
        "mode":    "other",
        "user":    get_current_user(request),
        "lang":    get_lang(request),
        "t":       get_t(request),
        "images":  images,
    })


@app.get("/other/jigsaw/generator", response_class=HTMLResponse)
def jigsaw_generator_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    photos = []
    limit = 32
    if user:
        photos = db.query(JigsawPhoto).filter_by(user_email=user["email"]).order_by(
            JigsawPhoto.created_at.desc()
        ).all()
        profile = db.query(UserProfile).filter_by(email=user["email"]).first()
        limit = getattr(profile, "puzzle_storage_limit", 32) if profile else 32
    return templates.TemplateResponse("jigsaw_generator.html", {
        "request": request,
        "mode":    "other",
        "user":    user,
        "lang":    get_lang(request),
        "t":       get_t(request),
        "photos":  photos,
        "limit":   limit,
    })


@app.get("/other/jigsaw/leaderboard", response_class=HTMLResponse)
def jigsaw_leaderboard_page(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse("jigsaw_leaderboard.html", {
        "request": request,
        "mode":    "other",
        "user":    get_current_user(request),
        "lang":    get_lang(request),
        "t":       get_t(request),
        "today":   today,
    })


@app.get("/other/jigsaw/how-to-play", response_class=HTMLResponse)
def jigsaw_howtoplay_page(request: Request):
    return templates.TemplateResponse("jigsaw_howtoplay.html", {
        "request": request,
        "mode":    "other",
        "user":    get_current_user(request),
        "lang":    get_lang(request),
        "t":       get_t(request),
    })


@app.get("/other/jigsaw/photo/{board_hash}", response_class=HTMLResponse)
def jigsaw_photo_play(request: Request, board_hash: str, difficulty: str = Query("beginner"),
                      db: Session = Depends(get_db)):
    import re
    if not re.match(r'^[A-Za-z0-9_\-]{10,128}$', board_hash):
        raise HTTPException(status_code=400, detail="Invalid board hash")
    if difficulty not in _JIGSAW_DIFFICULTIES:
        difficulty = "beginner"
    photo = db.query(JigsawPhoto).filter_by(board_hash=board_hash).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Puzzle not found")
    return templates.TemplateResponse("jigsaw_daily.html", {
        "request":      request,
        "mode":         "other",
        "user":         get_current_user(request),
        "lang":         get_lang(request),
        "t":            get_t(request),
        "today":        date.today().isoformat(),
        "image_name":   None,
        "photo_url":    f"/static/uploads/jigsaw/{photo.filename}",
        "board_hash":   board_hash,
        "display_name": photo.display_name or "Custom Puzzle",
        "difficulty":   difficulty,
    })


# ── Jigsaw API ────────────────────────────────────────────────────────────────

@app.get("/api/jigsaw/daily-image")
def jigsaw_daily_image_api(request: Request):
    today = date.today().isoformat()
    image_name = _jigsaw_daily_image(today)
    return {"image_name": image_name, "image_url": f"/static/img/puzzle/{image_name}"}


class JigsawScoreSubmit(BaseModel):
    name:        str = Field(..., min_length=1, max_length=32)
    puzzle_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    difficulty:  str
    image_name:  str = Field(..., min_length=1, max_length=256)
    time_ms:     int = Field(..., ge=1, le=99999999)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable() and ord(c) < 128)
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        if v not in ("beginner", "intermediate", "expert"):
            raise ValueError("Invalid difficulty")
        return v

    @field_validator("image_name")
    @classmethod
    def sanitize_image_name(cls, v: str) -> str:
        import re
        v = v.strip()
        if not re.match(r'^[A-Za-z0-9_\-\.]{1,256}$', v):
            raise ValueError("Invalid image name")
        return v


@app.post("/api/jigsaw-scores", status_code=201)
@limiter.limit("10/minute")
def submit_jigsaw_score(payload: JigsawScoreSubmit, request: Request,
                        db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None
    entry = JigsawScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        puzzle_date = payload.puzzle_date,
        difficulty  = payload.difficulty,
        image_name  = payload.image_name,
        time_ms     = payload.time_ms,
        guest_token = guest_token,
        client_type = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    record_score_submit("jigsaw", payload.puzzle_date)
    record_game_complete("jigsaw", mode=payload.difficulty, duration_ms=payload.time_ms)
    return {"ok": True, "id": entry.id}


@app.get("/api/jigsaw-scores")
def get_jigsaw_scores(
    request: Request,
    puzzle_date: Optional[str] = Query(None, alias="date",
                                       pattern=r"^\d{4}-\d{2}-\d{2}$"),
    difficulty:  Optional[str] = Query("beginner"),
    db: Session = Depends(get_db),
):
    import re
    if difficulty not in _JIGSAW_DIFFICULTIES:
        difficulty = "beginner"
    LIMIT = 20
    if puzzle_date:
        top = (
            db.query(JigsawScore)
            .filter(JigsawScore.puzzle_date == puzzle_date,
                    JigsawScore.difficulty == difficulty)
            .order_by(JigsawScore.time_ms.asc(), JigsawScore.created_at.asc())
            .limit(LIMIT).all()
        )
    else:
        today = date.today().isoformat()
        top = (
            db.query(JigsawScore)
            .filter(JigsawScore.puzzle_date == today,
                    JigsawScore.difficulty == difficulty)
            .order_by(JigsawScore.time_ms.asc(), JigsawScore.created_at.asc())
            .limit(LIMIT).all()
        )
    return _enrich_with_profiles(top, db)


class JigsawSavePayload(BaseModel):
    puzzle_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    difficulty:  str
    image_name:  str = Field(..., min_length=1, max_length=256)
    elapsed_ms:  int = Field(..., ge=0)
    piece_state: list = Field(default_factory=list)

class JigsawDeleteSavePayload(BaseModel):
    puzzle_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    difficulty:  str

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        if v not in ("beginner", "intermediate", "expert"):
            raise ValueError("Invalid difficulty")
        return v


@app.post("/api/jigsaw/save", status_code=200)
@limiter.limit("30/minute")
def jigsaw_save_game(payload: JigsawSavePayload, request: Request,
                     db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    import json as _json
    piece_state_json = _json.dumps(payload.piece_state)
    existing = (
        db.query(JigsawSavedGame)
        .filter_by(user_email=user["email"], puzzle_date=payload.puzzle_date,
                   difficulty=payload.difficulty)
        .first()
    )
    if existing:
        existing.elapsed_ms  = payload.elapsed_ms
        existing.piece_state = piece_state_json
        existing.image_name  = payload.image_name
    else:
        db.add(JigsawSavedGame(
            user_email  = user["email"],
            puzzle_date = payload.puzzle_date,
            difficulty  = payload.difficulty,
            image_name  = payload.image_name,
            elapsed_ms  = payload.elapsed_ms,
            piece_state = piece_state_json,
        ))
    db.commit()
    return {"ok": True}


@app.get("/api/jigsaw/resume")
def jigsaw_resume_game(request: Request,
                       puzzle_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
                       difficulty: str = Query("beginner"),
                       db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return {"saved": False}
    if difficulty not in _JIGSAW_DIFFICULTIES:
        return {"saved": False}
    saved = (
        db.query(JigsawSavedGame)
        .filter_by(user_email=user["email"], puzzle_date=puzzle_date, difficulty=difficulty)
        .first()
    )
    if not saved:
        return {"saved": False}
    import json as _json
    return {
        "saved":       True,
        "elapsed_ms":  saved.elapsed_ms,
        "image_name":  saved.image_name,
        "piece_state": _json.loads(saved.piece_state),
    }


@app.post("/api/jigsaw/delete-save", status_code=200)
def delete_jigsaw_save(payload: JigsawDeleteSavePayload, request: Request,
                       db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    if payload.difficulty not in _JIGSAW_DIFFICULTIES:
        raise HTTPException(status_code=400, detail="Invalid difficulty")
    save = (
        db.query(JigsawSavedGame)
        .filter_by(user_email=user["email"], puzzle_date=payload.puzzle_date,
                   difficulty=payload.difficulty)
        .first()
    )
    if not save:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(save)
    db.commit()
    return {"ok": True}


@app.post("/api/jigsaw/upload", status_code=201)
@limiter.limit("20/minute")
async def upload_jigsaw_photo(
    request: Request,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    display_name: str = Form(""),
    board_hash: str = Form(...),
):
    import re
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    if not re.match(r'^[A-Za-z0-9_\-]{10,128}$', board_hash):
        raise HTTPException(status_code=400, detail="Invalid board hash")
    if db.query(JigsawPhoto).filter_by(board_hash=board_hash).first():
        raise HTTPException(status_code=409, detail="Puzzle already exists")
    profile = db.query(UserProfile).filter_by(email=user["email"]).first()
    limit = getattr(profile, "puzzle_storage_limit", 32) if profile else 32
    count = db.query(JigsawPhoto).filter_by(user_email=user["email"]).count()
    if count >= limit:
        raise HTTPException(status_code=400, detail=f"Puzzle limit reached ({limit})")
    content_type = file.content_type or ""
    if content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=400, detail="Only JPG and PNG files are accepted")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")
    os.makedirs(_JIGSAW_UPLOAD_DIR, exist_ok=True)
    ext = ".jpg" if content_type == "image/jpeg" else ".png"
    safe_hash = re.sub(r'[^A-Za-z0-9_\-]', '', board_hash)
    filename = f"{safe_hash}{ext}"
    filepath = os.path.join(_JIGSAW_UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(data)
    entry = JigsawPhoto(
        user_email   = user["email"],
        filename     = filename,
        display_name = display_name.strip()[:128] or None,
        board_hash   = board_hash,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"ok": True, "url": f"/other/jigsaw/photo/{board_hash}"}


@app.post("/api/jigsaw/delete-photo/{board_hash}")
def delete_jigsaw_photo(board_hash: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    photo = db.query(JigsawPhoto).filter_by(board_hash=board_hash).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Not found")
    if photo.user_email != user["email"] and user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")
    filepath = os.path.join(_JIGSAW_UPLOAD_DIR, photo.filename)
    if os.path.isfile(filepath):
        os.remove(filepath)
    db.delete(photo)
    db.commit()
    return {"ok": True}


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

    return templates.TemplateResponse("archive_day.html", {
        "request":      request,
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

# ── Nonosweeper ───────────────────────────────────────────────────────────────

@app.get("/nonosweeper", response_class=HTMLResponse)
async def nonosweeper_page(request: Request, date_param: str = Query(None, alias="date")):
    print(f"[DEBUG] nonosweeper_page hit: {request.url}", flush=True)
    import re
    real_today = date.today().isoformat()
    puzzle_date = real_today
    if date_param and re.match(r"^\d{4}-\d{2}-\d{2}$", date_param):
        puzzle_date = date_param
    print(f"[DEBUG] nonosweeper_page puzzle_date={puzzle_date}", flush=True)
    try:
        response = templates.TemplateResponse("nonosweeper.html", {
            "request": request, "mode": "nonosweeper",
            "user": get_current_user(request),
            "lang": get_lang(request), "t": get_t(request),
            "today": puzzle_date,
            "real_today": real_today,
            "default_no_guess": get_lang(request) == "de",
        })
        print(f"[DEBUG] nonosweeper_page rendered successfully", flush=True)
        return response
    except Exception as e:
        print(f"[DEBUG] nonosweeper_page ERROR: {type(e).__name__}: {e}", flush=True)
        raise


@app.get("/nonosweeper/{date_str}", response_class=HTMLResponse)
async def nonosweeper_permalink(request: Request, date_str: str):
    print(f"[DEBUG] nonosweeper_permalink hit: {request.url}, date_str={date_str}", flush=True)
    import re
    real_today = date.today().isoformat()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        print(f"[DEBUG] nonosweeper_permalink invalid date_str, redirecting", flush=True)
        return RedirectResponse("/nonosweeper", status_code=302)
    try:
        response = templates.TemplateResponse("nonosweeper.html", {
            "request": request, "mode": "nonosweeper",
            "user": get_current_user(request),
            "lang": get_lang(request), "t": get_t(request),
            "today": date_str,
            "real_today": real_today,
            "noindex": True,
            "default_no_guess": get_lang(request) == "de",
        })
        print(f"[DEBUG] nonosweeper_permalink rendered successfully", flush=True)
        return response
    except Exception as e:
        print(f"[DEBUG] nonosweeper_permalink ERROR: {type(e).__name__}: {e}", flush=True)
        raise


# ── MVS static pages ──────────────────────────────────────────────────────────

_MVS_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "static", "mvs"))


@app.get("/mvs")
def mvs_root():
    return RedirectResponse("/mvs/index.html", status_code=302)


@app.get("/mvs/{path:path}")
def mvs_static(path: str):
    resolved = os.path.realpath(os.path.join(_MVS_DIR, path))
    if not resolved.startswith(_MVS_DIR + os.sep):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not os.path.isfile(resolved):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(resolved)
