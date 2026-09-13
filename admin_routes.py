"""
admin_routes.py — Admin page and API route handlers for minesweeper.org.
Mount this router in main.py with: app.include_router(admin_router)
"""
import re, os, json, csv, subprocess, hashlib, logging
import logging.handlers as _log_handlers
import urllib.request
from datetime import date, timedelta, datetime, timezone
from typing import Optional
from urllib.parse import quote, urlparse

from fastapi import APIRouter, Request, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, text, case, select
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from starlette.config import Config

import psutil
import seo_checker

from database import (
    Score, FlaggedScore, UserProfile, UserRole, Pattern, PatternRevision,
    BlogComment, ContactMessage, EvilGameSession,
    FifteenPuzzlePhoto, FifteenPuzzleScore, MemberPuzzle,
    JigsawPhoto, JigsawScore,
    GameHistory, RushScore,
    TentaizuScore, TentaizuEasyScore,
    MosaicScore, MosaicEasyScore, MosaicCustomScore,
    CylinderScore, ToroidScore, HexsweeperScore, GlobesweeperScore,
    CubesweeperScore, MobiussweeperScore, ReplayScore,
    NonosweeperScore,
    PvpResult, ServerStats, WebTrafficStats, SeoRanking,
    Game2048Score, Game2048HexScore, MahjongScore, SchulteGridScore, SudokuScore,
    GameReplay, NumbersMatchScore,
    WC2026Match,
    SessionLocal, get_db,
)
from phase2_analyzer import GameAnalysis

from auth import get_current_user
from translations import get_lang, get_t
import settings as site_settings
from quest_catalog import quest_config
from wc2026_data import WC2026_BY_SLUG, WC2026_ROUND_LABELS

admin_router = APIRouter()

templates = Jinja2Templates(directory="templates")
templates.env.globals["quest_config"]          = quest_config
templates.env.globals["DEFAULT_SKIN"]          = site_settings.DEFAULT_SKIN
templates.env.globals["active_skin"]           = site_settings.active_skin
templates.env.globals["solstice_banner"]       = site_settings.solstice_banner
templates.env.globals["equinox_banner"]        = site_settings.equinox_banner
templates.env.globals["diana_birthday_banner"] = site_settings.diana_birthday_banner

# ── Constants ─────────────────────────────────────────────────────────────────
_JIGSAW_UPLOAD_DIR = os.path.join("static", "uploads", "jigsaw")

_APACHE_LOG_GLOB = "/var/log/apache2/minesweeper.org-ssl-access.log*"
_LOG_RE_URL = __import__("re").compile(
    r'\S+\s+\S+\s+\S+\s+\[(\d{2}/\w{3}/\d{4}):[^\]]+\]\s+"\S+\s+([^?\s#"]+)'
)

# ── Score table map (table name → model, for flagged-score deletion) ──────────
_SCORE_TABLE_MAP: dict = {
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


# ── Utility helpers ───────────────────────────────────────────────────────────

def _safe_relative_url(url: str, fallback: str = "/") -> str:
    """Reject URLs that carry a scheme or netloc (open-redirect guard).
    urlparse is recognised by CodeQL as a URL sanitizer.

    Also rejects any backslash: per the WHATWG URL spec, browsers treat \
    as equivalent to / for special schemes (http/https/ws/wss/ftp/file), so
    "/\\evil.com" parses via urlparse as a harmless relative path (empty
    netloc) but browsers resolve it as //evil.com — a protocol-relative
    redirect to another origin. urlparse doesn't know about this browser
    quirk, so it can't be caught by the scheme/netloc check above."""
    if "\\" in url:
        return fallback
    if url.startswith("//"):
        return fallback
    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc:
        return fallback
    return url


def _round_or_none(value, decimals: int):
    """Round a Decimal/float to N places, or return None if input is None/NaN."""
    if value is None:
        return None
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return None


def _mask_email(player_id: str | None) -> str:
    """Mask an email or guest-token for admin display."""
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
        return f"{player_id[:8]}\u2026{player_id[-4:]}"
    return player_id


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


def _run_seo_rankings():
    db = SessionLocal()
    try:
        n = seo_checker.update_all_rankings(db)
        import logging as _lg
        _lg.getLogger(__name__).info("SEO ranking refresh complete (%d languages)", n)
    except Exception as exc:
        import logging as _lg
        _lg.getLogger(__name__).error("SEO ranking refresh failed: %s", exc)
    finally:
        db.close()


# ── Admin ─────────────────────────────────────────────────────────────────────
_admin_emails_raw = Config(".env")("ADMIN_EMAILS", default="")
ADMIN_EMAILS = {e.strip() for e in _admin_emails_raw.split(",") if e.strip()}

# ── Admin access logging ───────────────────────────────────────────────────────

_ADMIN_LOG_MAP = {
    "minesweeper.org":         "/var/log/uvicorn/minesweeper.org-login.log",
    "www.minesweeper.org":     "/var/log/uvicorn/minesweeper.org-login.log",
    "staging.minesweeper.org": "/var/log/uvicorn/staging.minesweeper.org-login.log",
}
_admin_loggers: dict[str, logging.Logger] = {}

def _get_admin_logger(log_path: str) -> logging.Logger:
    if log_path not in _admin_loggers:
        lg = logging.getLogger(f"admin_access:{log_path}")
        lg.setLevel(logging.INFO)
        lg.propagate = False
        try:
            handler = _log_handlers.RotatingFileHandler(
                log_path, maxBytes=10_000_000, backupCount=5, encoding="utf-8"
            )
        except OSError:
            handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        lg.addHandler(handler)
        _admin_loggers[log_path] = lg
    return _admin_loggers[log_path]

def _log_admin_access(request: Request, user: dict | None, success: bool, reason: str = "") -> None:
    host     = request.headers.get("host", "").split(":")[0].lower()
    log_path = _ADMIN_LOG_MAP.get(host, "/var/log/uvicorn/minesweeper.org-login.log")
    identity = user.get("email", "unknown") if user else "anonymous"
    path     = request.url.path
    if success:
        msg = f'ALLOW  {identity!r:40s} -> {path}  [host={host}]'
    else:
        msg = f'DENY   {identity!r:40s} -> {path}  reason={reason!r}  [host={host}]'
    _get_admin_logger(log_path).info(msg)

def require_user(request: Request) -> dict:
    """Return the authenticated user or raise HTTP 401."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    return user


def require_admin(request: Request, user: dict | None) -> None:
    if not user:
        _log_admin_access(request, user, success=False, reason="not_logged_in")
        raise HTTPException(status_code=403, detail="Forbidden")
    if user.get("email", "").lower() not in {e.lower() for e in ADMIN_EMAILS}:
        _log_admin_access(request, user, success=False, reason="email_not_in_admin_list")
        raise HTTPException(status_code=403, detail="Forbidden")
    _log_admin_access(request, user, success=True)


def user_has_role(db: Session, user: dict | None, role: str) -> bool:
    """True if user is in ADMIN_EMAILS (implicit all-roles) OR has the role in user_roles."""
    if not user:
        return False
    email = (user.get("email") or "").lower()
    if not email:
        return False
    if email in {e.lower() for e in ADMIN_EMAILS}:
        return True
    return db.query(UserRole).filter(
        func.lower(UserRole.email) == email,
        UserRole.role == role,
    ).first() is not None


def require_role(request: Request, user: dict | None, db: Session, role: str) -> None:
    """Gate a route on a named role. Admins implicitly hold every role."""
    if not user:
        _log_admin_access(request, user, success=False, reason="not_logged_in")
        raise HTTPException(status_code=403, detail="Forbidden")
    if not user_has_role(db, user, role):
        _log_admin_access(request, user, success=False, reason=f"missing_role:{role}")
        raise HTTPException(status_code=403, detail="Forbidden")
    _log_admin_access(request, user, success=True)


# ── Pattern wiki helpers ─────────────────────────────────────────────────────
_PATTERN_SECTIONS = [
    "Holes",
    "Holes+",
    "High Complexity",
    "Box Logic",
    "Inward Chains",
    "Chains",
    "Combinations",
    "Other",
]

_PATTERN_DIFFICULTIES = ["A", "B", "C", "D", "E"]


def _pattern_slugify(value: str) -> str:
    """Slug suitable for /patterns/{slug}. Lowercase, hyphenated, ASCII-only."""
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value[:128] or "pattern"


def _save_pattern_revision(db: Session, pattern: Pattern, editor_email: str | None,
                           edit_summary: str | None = None) -> None:
    """Snapshot the current state of a Pattern row into pattern_revisions."""
    db.add(PatternRevision(
        pattern_id      = pattern.id,
        slug            = pattern.slug,
        name            = pattern.name,
        aliases         = pattern.aliases,
        section         = pattern.section,
        depth           = pattern.depth,
        difficulty      = pattern.difficulty,
        parent_slug     = pattern.parent_slug,
        sort_order      = pattern.sort_order,
        body_md         = pattern.body_md,
        board_json      = pattern.board_json,
        board_image_url = pattern.board_image_url,
        legend          = pattern.legend,
        status          = pattern.status,
        editor_email    = editor_email,
        edit_summary    = edit_summary,
    ))


# ── Admin: 15-Puzzle photo moderation ─────────────────────────────────────────

@admin_router.get("/admin/15puzzle-photos", response_class=HTMLResponse)
def admin_15puzzle_photos(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    pending_photos = (
        db.query(FifteenPuzzlePhoto)
        .filter_by(approved=False)
        .order_by(FifteenPuzzlePhoto.created_at.desc())
        .all()
    )
    approved_photos = (
        db.query(FifteenPuzzlePhoto)
        .filter_by(approved=True)
        .order_by(FifteenPuzzlePhoto.created_at.desc())
        .all()
    )
    pending_members = (
        db.query(MemberPuzzle)
        .filter_by(approved=False)
        .order_by(MemberPuzzle.created_at.desc())
        .all()
    )
    approved_members = (
        db.query(MemberPuzzle)
        .filter_by(approved=True)
        .order_by(MemberPuzzle.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(request, "admin_15puzzle_photos.html", {
        "user": user,
        "lang": get_lang(request), "t": get_t(request),
        "pending_photos":   pending_photos,
        "approved_photos":  approved_photos,
        "pending_members":  pending_members,
        "approved_members": approved_members,
    })


@admin_router.post("/admin/15puzzle-photos/{board_hash}/delete")
def admin_delete_15puzzle_photo(board_hash: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    photo = db.query(FifteenPuzzlePhoto).filter_by(board_hash=board_hash).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Not found")
    filepath = os.path.join("static", "uploads", "15puzzle", photo.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    db.delete(photo)
    db.commit()
    return RedirectResponse("/admin/15puzzle-photos", status_code=303)


@admin_router.post("/admin/15puzzle-photos/{board_hash}/approve")
def admin_approve_15puzzle_photo(board_hash: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    photo = db.query(FifteenPuzzlePhoto).filter_by(board_hash=board_hash).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Not found")
    photo.approved = True
    db.commit()
    return RedirectResponse("/admin/15puzzle-photos", status_code=303)


@admin_router.post("/admin/15puzzle-photos/{board_hash}/unapprove")
def admin_unapprove_15puzzle_photo(board_hash: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    photo = db.query(FifteenPuzzlePhoto).filter_by(board_hash=board_hash).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Not found")
    photo.approved = False
    db.commit()
    return RedirectResponse("/admin/15puzzle-photos", status_code=303)


@admin_router.post("/admin/15puzzle-photos/member/{board_hash}/delete")
def admin_delete_member_puzzle(board_hash: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    puzzle = db.query(MemberPuzzle).filter_by(board_hash=board_hash).first()
    if not puzzle:
        raise HTTPException(status_code=404, detail="Not found")
    upload_dir = os.path.join("static", "uploads", "15puzzle")
    for fname in (puzzle.tile_filename, puzzle.reveal_filename):
        if fname:
            fpath = os.path.join(upload_dir, fname)
            if os.path.exists(fpath):
                os.remove(fpath)
    db.delete(puzzle)
    db.commit()
    return RedirectResponse("/admin/15puzzle-photos", status_code=303)


@admin_router.post("/admin/15puzzle-photos/member/{board_hash}/approve")
def admin_approve_member_puzzle(board_hash: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    puzzle = db.query(MemberPuzzle).filter_by(board_hash=board_hash).first()
    if not puzzle:
        raise HTTPException(status_code=404, detail="Not found")
    puzzle.approved = True
    db.commit()
    return RedirectResponse("/admin/15puzzle-photos", status_code=303)


@admin_router.post("/admin/15puzzle-photos/member/{board_hash}/unapprove")
def admin_unapprove_member_puzzle(board_hash: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    puzzle = db.query(MemberPuzzle).filter_by(board_hash=board_hash).first()
    if not puzzle:
        raise HTTPException(status_code=404, detail="Not found")
    puzzle.approved = False
    db.commit()
    return RedirectResponse("/admin/15puzzle-photos", status_code=303)


# ── Jigsaw photo moderation ───────────────────────────────────────────────────

@admin_router.get("/admin/jigsaw-photos", response_class=HTMLResponse)
def admin_jigsaw_photos(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    pending = (
        db.query(JigsawPhoto)
        .filter_by(approved=False)
        .order_by(JigsawPhoto.created_at.desc())
        .all()
    )
    approved = (
        db.query(JigsawPhoto)
        .filter_by(approved=True)
        .order_by(JigsawPhoto.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(request, "admin_jigsaw_photos.html", {
        "user": user,
        "lang": get_lang(request), "t": get_t(request),
        "pending": pending,
        "approved": approved,
    })


@admin_router.post("/admin/jigsaw-photos/{board_hash}/delete")
def admin_delete_jigsaw_photo(board_hash: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    photo = db.query(JigsawPhoto).filter_by(board_hash=board_hash).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Not found")
    filepath = os.path.join(_JIGSAW_UPLOAD_DIR, photo.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    db.delete(photo)
    db.commit()
    return RedirectResponse("/admin/jigsaw-photos", status_code=303)


@admin_router.post("/admin/jigsaw-photos/{board_hash}/approve")
def admin_approve_jigsaw_photo(board_hash: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    photo = db.query(JigsawPhoto).filter_by(board_hash=board_hash).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Not found")
    photo.approved = True
    db.commit()
    return RedirectResponse("/admin/jigsaw-photos", status_code=303)


@admin_router.post("/admin/jigsaw-photos/{board_hash}/unapprove")
def admin_unapprove_jigsaw_photo(board_hash: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    photo = db.query(JigsawPhoto).filter_by(board_hash=board_hash).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Not found")
    photo.approved = False
    db.commit()
    return RedirectResponse("/admin/jigsaw-photos", status_code=303)


@admin_router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)

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

    # Evil mode (page sessions)
    evil_all = db.query(func.count()).select_from(EvilGameSession).scalar()
    evil_today = (
        db.query(func.count()).select_from(EvilGameSession)
        .filter(func.date(EvilGameSession.created_at) == today)
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
        with urllib.request.urlopen("http://localhost:8002/health", timeout=2) as resp:  # nosec B310 — hardcoded localhost health check
            staging_head = _json.loads(resp.read()).get("commit", "unknown")
    except Exception:
        staging_head = None

    # ── Nav alert badges ──────────────────────────────────────────────────────
    alert_15p_photos = (
        db.query(func.count()).select_from(FifteenPuzzlePhoto).filter_by(approved=False).scalar() +
        db.query(func.count()).select_from(MemberPuzzle).filter_by(approved=False).scalar()
    ) > 0

    alert_jigsaw_photos = (
        db.query(func.count()).select_from(JigsawPhoto).filter_by(approved=False).scalar()
    ) > 0

    alert_hs_cleaning = (
        db.query(func.count()).select_from(FlaggedScore).scalar()
    ) > 0

    alert_blog = (
        db.query(func.count()).select_from(BlogComment).filter_by(approved=False).scalar()
    ) > 0

    alert_contact = (
        db.query(func.count()).select_from(ContactMessage).filter_by(read=False).scalar()
    ) > 0

    try:
        from datetime import timedelta as _td
        _four_h_ago = datetime.now(timezone.utc) - _td(hours=4)
        _latest_stats = db.query(ServerStats).order_by(ServerStats.recorded_at.desc()).first()
        alert_ops_disk = _latest_stats is not None and _latest_stats.disk_percent > 90
        _cpu_q = db.query(
            func.min(ServerStats.cpu_percent),
            func.min(ServerStats.recorded_at),
            func.count(),
        ).filter(ServerStats.recorded_at >= _four_h_ago).first()
        if _cpu_q and _cpu_q[2] > 0 and _cpu_q[0] is not None:
            _earliest = _cpu_q[1]
            if _earliest.tzinfo is None:
                _earliest = _earliest.replace(tzinfo=timezone.utc)
            _span_h = (datetime.now(timezone.utc) - _earliest).total_seconds() / 3600
            alert_ops_cpu = _cpu_q[0] > 50 and _span_h >= 4
        else:
            alert_ops_cpu = False
        alert_operations = alert_ops_disk or alert_ops_cpu
    except Exception:
        alert_operations = False

    return templates.TemplateResponse(request, "admin.html", {
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
        "evil_today": evil_today,
        "evil_all": evil_all,
        "cyl_today": cyl_today,
        "cyl_all": cyl_all,
        "tor_today": tor_today,
        "tor_all": tor_all,
        "git_head": git_head,
        "git_commits_this_week": git_commits_this_week,
        "git_contributors": git_contributors,
        "staging_head": staging_head,
        "alert_15p_photos":    alert_15p_photos,
        "alert_jigsaw_photos": alert_jigsaw_photos,
        "alert_hs_cleaning":   alert_hs_cleaning,
        "alert_operations":    alert_operations,
        "alert_blog":          alert_blog,
        "alert_contact":       alert_contact,
    })

@admin_router.get("/admin/bootcamp", response_class=HTMLResponse)
def admin_bootcamp(request: Request, db: Session = Depends(get_db)):
    """
    Admin dashboard for the Bootcamp / analyzer pipeline.

    Surfaces:
      - No-guess anomaly cases (forced-guess deaths in no-guess games)
      - Player adoption and level distribution
      - Analyzer throughput and pending backlog
      - Population-wide skill medians
    """
    user = get_current_user(request)
    require_admin(request, user)

    now = datetime.now(timezone.utc)
    week_ago  = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # ── 1. Top-line counts ────────────────────────────────────────────────────
    # One scan each instead of three separate queries per metric.
    from sqlalchemy import case as sa_case

    analyses_row = db.query(
        func.count(GameAnalysis.id).label("total"),
        func.count(sa_case((GameAnalysis.created_at >= week_ago,  GameAnalysis.id), else_=None)).label("week"),
        func.count(sa_case((GameAnalysis.created_at >= month_ago, GameAnalysis.id), else_=None)).label("month"),
    ).one()
    total_analyses = analyses_row.total or 0
    analyses_7d    = analyses_row.week  or 0
    analyses_30d   = analyses_row.month or 0

    players_row = db.query(
        func.count(func.distinct(GameAnalysis.player_id)).label("total"),
        func.count(func.distinct(sa_case(
            (GameAnalysis.created_at >= week_ago,  GameAnalysis.player_id), else_=None))).label("week"),
        func.count(func.distinct(sa_case(
            (GameAnalysis.created_at >= month_ago, GameAnalysis.player_id), else_=None))).label("month"),
    ).one()
    unique_players_total = players_row.total or 0
    unique_players_7d    = players_row.week  or 0
    unique_players_30d   = players_row.month or 0

    # Anomaly counts — single scan
    anomalies_row = db.query(
        func.count(GameAnalysis.id).label("total"),
        func.count(sa_case((GameAnalysis.created_at >= week_ago,  GameAnalysis.id), else_=None)).label("week"),
        func.count(sa_case((GameAnalysis.created_at >= month_ago, GameAnalysis.id), else_=None)).label("month"),
    ).filter(
        GameAnalysis.no_guess == True,
        GameAnalysis.death_cause == "forcedGuess",
    ).one()
    anomalies_total = anomalies_row.total or 0
    anomalies_7d    = anomalies_row.week  or 0
    anomalies_30d   = anomalies_row.month or 0

    # ── 2. Recent anomalies list (50 most recent) ────────────────────────────
    anomaly_rows = (
        db.query(GameAnalysis, GameReplay)
          .outerjoin(GameReplay, GameReplay.id == GameAnalysis.game_replay_id)
          .filter(GameAnalysis.no_guess == True)
          .filter(GameAnalysis.death_cause == "forcedGuess")
          .order_by(GameAnalysis.created_at.desc())
          .limit(50)
          .all()
    )
    anomalies = [
        {
            "id": ga.id,
            "game_replay_id": ga.game_replay_id,
            "player_id_masked": _mask_email(ga.player_id),
            "death_cause": ga.death_cause,
            "death_region": ga.death_region,
            "difficulty": (gr.mode if gr else "?"),
            "time_ms": (gr.time_ms if gr else None),
            "three_bv": (gr.bbbv if gr else None),
            "created_at": ga.created_at.strftime("%Y-%m-%d %H:%M") if ga.created_at else "",
            "replay_url": (
                "/variants/replay/?"
                + f"rows={gr.rows}&cols={gr.cols}&mines={gr.mines}"
                + f"&hash={quote(gr.board_hash or '', safe='')}"
                + (f"&date={gr.created_at.strftime('%Y-%m-%d')}" if gr and gr.created_at else "")
                + (f"&mode={gr.mode}" if gr and gr.mode else "")
                + "&game=standard"
                if ga.game_replay_id and gr and gr.board_hash else None
            ),
        }
        for ga, gr in anomaly_rows
    ]

    # ── 3. Bootcamp level distribution (latest level per player) ─────────────
    # Subquery: most recent game per player
    latest_subq = (
        db.query(
            GameAnalysis.player_id,
            func.max(GameAnalysis.created_at).label("latest"),
        )
        .filter(GameAnalysis.bootcamp_level.isnot(None))
        .group_by(GameAnalysis.player_id)
        .subquery()
    )
    level_rows = (
        db.query(GameAnalysis.bootcamp_level, func.count(GameAnalysis.id))
        .join(latest_subq,
              (GameAnalysis.player_id == latest_subq.c.player_id) &
              (GameAnalysis.created_at == latest_subq.c.latest))
        .group_by(GameAnalysis.bootcamp_level)
        .all()
    )
    level_distribution = {lv: 0 for lv in range(1, 8)}
    for lv, n in level_rows:
        if lv in level_distribution:
            level_distribution[lv] = n

    # ── 4. Population skill medians (standard mode, last 30 days) ────────────
    pop_q = (
        db.query(
            func.avg(GameAnalysis.ioe),
            func.avg(GameAnalysis.correctness),
            func.avg(GameAnalysis.hierarchy_compliance_pct),
            func.avg(GameAnalysis.three_bv_per_sec),
            func.avg(GameAnalysis.openings_guaranteed_taken),
            func.avg(GameAnalysis.openings_guaranteed_missed),
            func.avg(GameAnalysis.fishes_attempted),
            func.avg(GameAnalysis.avg_flag_value_score),
        )
        .filter(GameAnalysis.no_guess == False)
        .filter(GameAnalysis.created_at >= month_ago)
        .first()
    )
    population = {
        "ioe":               _round_or_none(pop_q[0], 3),
        "correctness":       _round_or_none(pop_q[1], 3),
        "hierarchy":         _round_or_none(pop_q[2], 3),
        "three_bv_per_sec":  _round_or_none(pop_q[3], 2),
        "openings_taken":    _round_or_none(pop_q[4], 1),
        "openings_missed":   _round_or_none(pop_q[5], 1),
        "fishes":            _round_or_none(pop_q[6], 1),
        "flag_value":        _round_or_none(pop_q[7], 2),
    }
    if population["openings_taken"] is not None and population["openings_missed"] is not None:
        total_op = (population["openings_taken"] or 0) + (population["openings_missed"] or 0)
        population["opening_take_rate"] = (
            round(population["openings_taken"] / total_op, 3) if total_op else None
        )
    else:
        population["opening_take_rate"] = None

    # ── 5. Analyses-per-day trend (last 30 days) ─────────────────────────────
    trend_rows = (
        db.query(
            func.date(GameAnalysis.created_at).label("day"),
            func.count(GameAnalysis.id).label("n"),
        )
        .filter(GameAnalysis.created_at >= month_ago)
        .group_by(func.date(GameAnalysis.created_at))
        .order_by("day")
        .all()
    )
    trend_labels = [r.day.strftime("%m-%d") if r.day else "" for r in trend_rows]
    trend_counts = [int(r.n) for r in trend_rows]

    # ── 6. Pending backlog (replays without an analysis row) ─────────────────
#    pending_replays = (
#        db.query(func.count(GameReplay.id))
#          .outerjoin(GameAnalysis, GameAnalysis.game_replay_id == GameReplay.id)
#          .filter(GameAnalysis.id.is_(None))
#          .scalar()
#    ) or 0

    pending_replays = (
        db.query(func.count(GameReplay.id))
           .outerjoin(GameAnalysis, GameAnalysis.game_replay_id == GameReplay.id)
           .filter(GameAnalysis.id.is_(None))
           .filter(GameReplay.board_hash.isnot(None))
           .filter(GameReplay.board_hash != "")
           .filter(GameReplay.log_json.isnot(None))
           .filter(GameReplay.log_json != "")
           .scalar()
    ) or 0

    unrecoverable_replays = (
        db.query(func.count(GameReplay.id))
           .outerjoin(GameAnalysis, GameAnalysis.game_replay_id == GameReplay.id)
           .filter(GameAnalysis.id.is_(None))
           .filter((GameReplay.board_hash.is_(None)) | (GameReplay.board_hash == ""))
           .scalar()
    ) or 0

    # ── 7. Mode mix (standard vs no-guess) ──────────────────────────────────
    mode_mix = (
        db.query(
            GameAnalysis.no_guess,
            func.count(GameAnalysis.id),
        )
        .filter(GameAnalysis.created_at >= month_ago)
        .group_by(GameAnalysis.no_guess)
        .all()
    )
    standard_count = sum(n for ng, n in mode_mix if not ng) or 0
    no_guess_count = sum(n for ng, n in mode_mix if ng) or 0

    return templates.TemplateResponse(request, "admin_bootcamp.html", {
        "mode": "admin_bootcamp",
        "user": user,
        "lang": get_lang(request),
        "t": get_t(request),
        # Top-line counts
        "total_analyses":        total_analyses,
        "analyses_7d":           analyses_7d,
        "analyses_30d":          analyses_30d,
        "unique_players_total":  unique_players_total,
        "unique_players_7d":     unique_players_7d,
        "unique_players_30d":    unique_players_30d,
        # Anomalies
        "anomalies_total":       anomalies_total,
        "anomalies_7d":          anomalies_7d,
        "anomalies_30d":         anomalies_30d,
        "anomalies":             anomalies,
        # Level distribution
        "level_distribution":    level_distribution,
        "level_distribution_total": sum(level_distribution.values()),
        # Population medians
        "population":            population,
        # Trend
        "trend_labels":          trend_labels,
        "trend_counts":          trend_counts,
        # Backlog + mode mix
        "pending_replays":       pending_replays,
        "standard_count":        standard_count,
        "no_guess_count":        no_guess_count,
    })


@admin_router.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)

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

    return templates.TemplateResponse(request, "admin_users.html", {
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


@admin_router.get("/admin/kanban", response_class=HTMLResponse)
def admin_kanban(request: Request):
    import re, os, glob

    user = get_current_user(request)
    if not user or user.get("email") not in ADMIN_EMAILS:
        return RedirectResponse("/", status_code=302)

    base_dir = os.path.dirname(__file__)
    GITHUB_INTENT = "https://github.com/ajaxchess/minesweeper.org/blob/main/intent/"
    STATUS_TO_COL = {"idea": "Backlog", "ready": "Backlog", "in-progress": "In Progress", "done": "Done"}

    # ── Intent files — source of truth for feature work ───────────────────────
    intent_cards = []
    for filepath in sorted(glob.glob(os.path.join(base_dir, "intent", "*.md"))):
        basename = os.path.basename(filepath)
        if basename.startswith("_"):
            continue
        try:
            content = open(filepath).read()
        except OSError:
            continue
        title_m  = re.search(r'^# (.+)$', content, re.MULTILINE)
        status_m = re.search(r'\*\*Status:\*\*\s*([\w-]+)', content)
        id_m     = re.search(r'\*\*Feature ID:\*\*\s*(\S+)', content)
        author_m = re.search(r'\*\*Author:\*\*\s*(.+)$', content, re.MULTILINE)

        status     = (status_m.group(1).strip() if status_m else "idea").lower()
        title      = title_m.group(1).strip() if title_m else basename.replace(".md", "").replace("_", " ")
        feature_id = id_m.group(1).strip() if id_m else None
        if feature_id in (None, "F-", "F-XXX"):
            feature_id = None
        author = author_m.group(1).strip() if author_m else None

        intent_cards.append({
            "id":          feature_id,
            "description": title,
            "assignee":    author,
            "status":      status,
            "ready":       status == "ready",
            "filename":    basename,
            "url":         GITHUB_INTENT + basename,
            "col":         STATUS_TO_COL.get(status, "Backlog"),
            "source":      "intent",
        })

    # ── KANBAN.md — operational and non-feature tasks ─────────────────────────
    ops_by_col = {}
    try:
        text = open(os.path.join(base_dir, "KANBAN.md")).read()
        for block in re.split(r'^## ', text, flags=re.MULTILINE):
            block = block.strip()
            if not block:
                continue
            lines = block.splitlines()
            col_name = lines[0].strip()
            for line in lines[1:]:
                line = line.strip()
                if not line.startswith("- "):
                    continue
                line = line[2:].strip()
                assignee_match = re.search(r'@(\S+)$', line)
                assignee = assignee_match.group(1) if assignee_match else None
                if assignee:
                    line = line[:assignee_match.start()].strip()
                id_match = re.match(r'^([FBD]\d+)\s+', line)
                card_id  = id_match.group(1) if id_match else None
                description = line[id_match.end():].strip() if id_match else line
                ops_by_col.setdefault(col_name, []).append({
                    "id": card_id, "description": description,
                    "assignee": assignee, "source": "ops",
                })
    except FileNotFoundError:
        pass

    # ── Merge: intent cards first (ready before idea), then ops tasks ──────────
    col_order = ["Backlog", "In Progress", "Review", "Done"]
    merged = {name: [] for name in col_order}

    for card in sorted(intent_cards, key=lambda c: (0 if c["status"] == "ready" else 1)):
        col = card.pop("col")
        if col in merged:
            merged[col].append(card)

    for col_name, ops_cards in ops_by_col.items():
        if col_name in merged:
            merged[col_name].extend(ops_cards)

    columns = [{"name": name, "cards": merged[name]} for name in col_order]

    return templates.TemplateResponse(request, "admin_kanban.html", {
        "user": user,
        "t": get_t(request),
        "lang": get_lang(request),
        "mode": "admin",
        "columns": columns,
    })


@admin_router.get("/admin/operations", response_class=HTMLResponse)
def admin_operations(request: Request, db: Session = Depends(get_db)):
    import json as _json

    user = get_current_user(request)
    require_admin(request, user)

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

    return templates.TemplateResponse(request, "admin_operations.html", {
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


@admin_router.get("/admin/web_traffic", response_class=HTMLResponse)
def admin_web_traffic(request: Request, db: Session = Depends(get_db)):
    import json as _json
    import csv as _csv
    user = get_current_user(request)
    require_admin(request, user)

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

    # ── Score submission API report ──────────────────────────────────────────
    _api_tables = [
        (Score,              "Minesweeper"),
        (GameHistory,        "Game History"),
        (RushScore,          "Rush"),
        (TentaizuScore,      "Tentaizu"),
        (TentaizuEasyScore,  "Tentaizu Easy"),
        (MosaicScore,        "Mosaic"),
        (MosaicEasyScore,    "Mosaic Easy"),
        (MosaicCustomScore,  "Mosaic Custom"),
        (CylinderScore,      "Cylinder"),
        (ToroidScore,        "Toroid"),
        (HexsweeperScore,    "Hexsweeper"),
        (GlobesweeperScore,  "Globesweeper"),
        (CubesweeperScore,   "Cubesweeper"),
        (MobiussweeperScore, "Mobiussweeper"),
        (ReplayScore,        "Replay"),
        (NonosweeperScore,   "Nonosweeper"),
        (FifteenPuzzleScore, "15 Puzzle"),
        (Game2048Score,      "2048"),
        (Game2048HexScore,   "2048 Hex"),
        (SchulteGridScore,   "Schulte Grid"),
        (SudokuScore,        "Sudoku"),
        (MahjongScore,       "Mahjong"),
        (JigsawScore,        "Jigsaw"),
    ]
    _ct_totals: dict = {}
    _game_rows = []
    for _model, _lbl in _api_tables:
        _ct_qry = (
            db.query(_model.client_type, func.count().label("n"))
            .group_by(_model.client_type)
            .all()
        )
        _game_n = 0
        for _ct, _n in _ct_qry:
            _k = _ct or "na"
            _ct_totals[_k] = _ct_totals.get(_k, 0) + _n
            _game_n += _n
        _game_rows.append({"label": _lbl, "total": _game_n})
    _game_rows.sort(key=lambda x: x["total"], reverse=True)

    _ct_known = [
        ("ios_app",        "iOS App"),
        ("android_app",    "Android App"),
        ("chrome",         "Chrome"),
        ("firefox",        "Firefox"),
        ("safari",         "Safari"),
        ("edge",           "Edge"),
        ("opera",          "Opera"),
        ("mobile_browser", "Mobile Browser"),
        ("browser",        "Other Browser"),
        ("na",             "Unknown"),
    ]
    _ct_rows = []
    _ct_seen = {k for k, _ in _ct_known}
    for _k, _d in _ct_known:
        if _ct_totals.get(_k, 0):
            _ct_rows.append({"label": _d, "count": _ct_totals[_k]})
    for _k, _n in _ct_totals.items():
        if _k not in _ct_seen and _n:
            _ct_rows.append({"label": _k, "count": _n})

    _api_total     = sum(r["total"] for r in _game_rows)
    _api_mobile_app = _ct_totals.get("ios_app", 0) + _ct_totals.get("android_app", 0)
    _api_mob_brow  = _ct_totals.get("mobile_browser", 0)
    _api_desktop   = sum(_ct_totals.get(k, 0) for k in ("chrome", "firefox", "safari", "edge", "opera", "browser"))
    _api_unknown   = _ct_totals.get("na", 0)
    _nz_games      = [r for r in _game_rows if r["total"] > 0]

    api_by_game      = _game_rows
    api_ct_breakdown = _ct_rows
    api_ct_labels    = _json.dumps([r["label"] for r in _ct_rows])
    api_ct_counts    = _json.dumps([r["count"] for r in _ct_rows])
    api_game_labels  = _json.dumps([r["label"] for r in _nz_games[:15]])
    api_game_counts  = _json.dumps([r["total"] for r in _nz_games[:15]])
    api_total        = _api_total
    api_mobile_app   = _api_mobile_app
    api_mob_brow     = _api_mob_brow
    api_desktop      = _api_desktop
    api_unknown      = _api_unknown

    return templates.TemplateResponse(request, "admin_web_traffic.html", {
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
        # API submission report
        "api_by_game":      api_by_game,
        "api_ct_breakdown": api_ct_breakdown,
        "api_ct_labels":    api_ct_labels,
        "api_ct_counts":    api_ct_counts,
        "api_game_labels":  api_game_labels,
        "api_game_counts":  api_game_counts,
        "api_total":        api_total,
        "api_mobile_app":   api_mobile_app,
        "api_mob_brow":     api_mob_brow,
        "api_desktop":      api_desktop,
        "api_unknown":      api_unknown,
    })


@admin_router.get("/admin/blog", response_class=HTMLResponse)
def admin_blog(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)

    pending  = db.query(BlogComment).filter_by(approved=False).order_by(BlogComment.created_at).all()
    approved = db.query(BlogComment).filter_by(approved=True).order_by(BlogComment.created_at.desc()).limit(50).all()
    return templates.TemplateResponse(request, "admin_blog.html", {
        "user": user,
        "lang": get_lang(request),
        "t": get_t(request),
        "pending":  pending,
        "approved": approved,
    })


@admin_router.post("/admin/blog/comments/{comment_id}/approve")
def admin_approve_comment(comment_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    comment = db.query(BlogComment).filter_by(id=comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Not found")
    comment.approved = True
    db.commit()
    return RedirectResponse("/admin/blog", status_code=303)


@admin_router.post("/admin/blog/comments/{comment_id}/delete")
def admin_delete_comment(comment_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    comment = db.query(BlogComment).filter_by(id=comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(comment)
    db.commit()
    return RedirectResponse("/admin/blog", status_code=303)


# ── Pattern Wiki Admin ───────────────────────────────────────────────────────
# Editors and admins can manage curated minesweeper patterns at /admin/patterns.
# Editors are granted via /admin/patterns/editors (admins only). All edits are
# snapshotted into pattern_revisions for audit + rollback.

def _parse_pattern_form(form_data) -> dict:
    """Pull and normalize fields from the admin pattern form. Raises HTTPException
    on malformed JSON for board_json / legend / aliases."""
    import json as _json_local

    def _json_or_none(s: str, field: str):
        s = (s or "").strip()
        if not s:
            return None
        try:
            return _json_local.loads(s)
        except Exception as e:
            raise HTTPException(status_code=400,
                                detail=f"Invalid JSON in '{field}': {e}")

    section = (form_data.get("section") or "").strip()
    if section not in _PATTERN_SECTIONS:
        raise HTTPException(status_code=400,
                            detail=f"Unknown section '{section}'. "
                                   f"Allowed: {', '.join(_PATTERN_SECTIONS)}")

    difficulty = (form_data.get("difficulty") or "").strip().upper() or None
    if difficulty and difficulty not in _PATTERN_DIFFICULTIES:
        raise HTTPException(status_code=400,
                            detail=f"Unknown difficulty '{difficulty}'")

    depth_raw = (form_data.get("depth") or "").strip()
    depth = int(depth_raw) if depth_raw else None
    if depth is not None and not (1 <= depth <= 20):
        raise HTTPException(status_code=400, detail="depth must be between 1 and 20")

    sort_raw = (form_data.get("sort_order") or "0").strip()
    try:
        sort_order = int(sort_raw)
    except ValueError:
        sort_order = 0

    status = (form_data.get("status") or "draft").strip().lower()
    if status not in ("draft", "published"):
        status = "draft"

    return {
        "name":            (form_data.get("name") or "").strip()[:128],
        "aliases":         _json_or_none(form_data.get("aliases"),    "aliases"),
        "section":         section,
        "depth":           depth,
        "difficulty":      difficulty,
        "parent_slug":     (form_data.get("parent_slug") or "").strip() or None,
        "sort_order":      sort_order,
        "body_md":         form_data.get("body_md") or "",
        "board_json":      _json_or_none(form_data.get("board_json"), "board_json"),
        "board_image_url": (form_data.get("board_image_url") or "").strip() or None,
        "legend":          _json_or_none(form_data.get("legend"),     "legend"),
        "status":          status,
    }


@admin_router.get("/admin/patterns", response_class=HTMLResponse)
def admin_patterns_list(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_role(request, user, db, "pattern_editor")

    rows = (
        db.query(Pattern)
        .order_by(Pattern.section, Pattern.sort_order, Pattern.name)
        .all()
    )
    # Group for display
    by_section: dict[str, list] = {}
    for p in rows:
        by_section.setdefault(p.section, []).append(p)

    return templates.TemplateResponse(request, "admin_patterns.html", {
        "user": user,
        "lang": get_lang(request),
        "t": get_t(request),
        "patterns_by_section": by_section,
        "sections": _PATTERN_SECTIONS,
        "total": len(rows),
        "is_admin": user and user.get("email", "").lower() in {e.lower() for e in ADMIN_EMAILS},
    })


@admin_router.get("/admin/patterns/new", response_class=HTMLResponse)
def admin_pattern_new_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_role(request, user, db, "pattern_editor")
    return templates.TemplateResponse(request, "admin_pattern_edit.html", {
        "user": user,
        "lang": get_lang(request),
        "t": get_t(request),
        "pattern": None,
        "sections": _PATTERN_SECTIONS,
        "difficulties": _PATTERN_DIFFICULTIES,
        "form_action": "/admin/patterns/new",
        "form_title": "New pattern",
    })


@admin_router.post("/admin/patterns/new")
async def admin_pattern_create(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_role(request, user, db, "pattern_editor")

    form = await request.form()
    fields = _parse_pattern_form(form)
    slug = (form.get("slug") or "").strip() or _pattern_slugify(fields["name"])
    slug = _pattern_slugify(slug)

    if not fields["name"]:
        raise HTTPException(status_code=400, detail="name is required")
    if db.query(Pattern).filter_by(slug=slug).first():
        raise HTTPException(status_code=409, detail=f"slug '{slug}' already exists")

    pattern = Pattern(
        slug         = slug,
        editor_email = user.get("email"),
        **fields,
    )
    db.add(pattern)
    db.commit()
    db.refresh(pattern)
    _save_pattern_revision(db, pattern, user.get("email"),
                           edit_summary=(form.get("edit_summary") or "Created").strip()[:256])
    db.commit()
    if not re.fullmatch(r'[a-z0-9][a-z0-9\-]{0,99}', pattern.slug):
        raise HTTPException(status_code=500, detail="Invalid pattern slug")
    return RedirectResponse(f"/admin/patterns/{quote(pattern.slug, safe='')}/edit", status_code=303)


@admin_router.get("/admin/patterns/{slug}/edit", response_class=HTMLResponse)
def admin_pattern_edit_form(slug: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_role(request, user, db, "pattern_editor")
    pattern = db.query(Pattern).filter_by(slug=slug).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    revisions = (
        db.query(PatternRevision)
        .filter_by(pattern_id=pattern.id)
        .order_by(PatternRevision.created_at.desc())
        .limit(20)
        .all()
    )
    return templates.TemplateResponse(request, "admin_pattern_edit.html", {
        "user": user,
        "lang": get_lang(request),
        "t": get_t(request),
        "pattern": pattern,
        "revisions": revisions,
        "sections": _PATTERN_SECTIONS,
        "difficulties": _PATTERN_DIFFICULTIES,
        "form_action": f"/admin/patterns/{slug}/edit",
        "form_title": f"Edit: {pattern.name}",
    })


@admin_router.post("/admin/patterns/{slug}/edit")
async def admin_pattern_update(slug: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_role(request, user, db, "pattern_editor")
    pattern = db.query(Pattern).filter_by(slug=slug).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    form = await request.form()
    fields = _parse_pattern_form(form)

    # Allow slug rename, but only to another non-conflicting slug.
    new_slug_raw = (form.get("slug") or "").strip()
    if new_slug_raw:
        new_slug = _pattern_slugify(new_slug_raw)
        if new_slug != pattern.slug:
            conflict = db.query(Pattern).filter_by(slug=new_slug).first()
            if conflict:
                raise HTTPException(status_code=409,
                                    detail=f"slug '{new_slug}' already exists")
            pattern.slug = new_slug

    for k, v in fields.items():
        setattr(pattern, k, v)
    pattern.editor_email = user.get("email")
    db.commit()
    db.refresh(pattern)
    _save_pattern_revision(db, pattern, user.get("email"),
                           edit_summary=(form.get("edit_summary") or "").strip()[:256] or None)
    db.commit()
    slug_match = re.fullmatch(r'[a-z0-9][a-z0-9\-]{0,99}', pattern.slug)
    if not slug_match:
        raise HTTPException(status_code=500, detail="Invalid pattern slug")
    return RedirectResponse(_safe_relative_url(f"/admin/patterns/{slug_match.group()}/edit"), status_code=303)  # codeql[py/url-redirection]


@admin_router.post("/admin/patterns/{slug}/delete")
def admin_pattern_delete(slug: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    # Deletion requires full admin — editors can move to status='draft' instead.
    require_admin(request, user)
    pattern = db.query(Pattern).filter_by(slug=slug).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    db.delete(pattern)
    db.commit()
    return RedirectResponse("/admin/patterns", status_code=303)


# ── Pattern editor list management (admin-only) ───────────────────────────────

@admin_router.get("/admin/patterns/editors", response_class=HTMLResponse)
def admin_pattern_editors(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    editors = (
        db.query(UserRole)
        .filter_by(role="pattern_editor")
        .order_by(UserRole.granted_at.desc())
        .all()
    )
    return templates.TemplateResponse(request, "admin_pattern_editors.html", {
        "user": user,
        "lang": get_lang(request),
        "t": get_t(request),
        "editors": editors,
        "admin_emails": sorted(ADMIN_EMAILS),
    })


@admin_router.post("/admin/patterns/editors/add")
async def admin_pattern_editor_add(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    note  = (form.get("note") or "").strip()[:256] or None
    if not email or "@" not in email or len(email) > 256:
        raise HTTPException(status_code=400, detail="Invalid email")

    existing = db.query(UserRole).filter_by(email=email, role="pattern_editor").first()
    if not existing:
        db.add(UserRole(
            email      = email,
            role       = "pattern_editor",
            granted_by = user.get("email"),
            note       = note,
        ))
        db.commit()
    return RedirectResponse("/admin/patterns/editors", status_code=303)


@admin_router.post("/admin/patterns/editors/{role_id}/remove")
def admin_pattern_editor_remove(role_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    role = db.query(UserRole).filter_by(id=role_id, role="pattern_editor").first()
    if not role:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(role)
    db.commit()
    return RedirectResponse("/admin/patterns/editors", status_code=303)

@admin_router.get("/admin/contact", response_class=HTMLResponse)
def admin_contact(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    unread = db.query(ContactMessage).filter_by(read=False).order_by(ContactMessage.created_at.desc()).all()
    read   = db.query(ContactMessage).filter_by(read=True).order_by(ContactMessage.created_at.desc()).limit(50).all()
    return templates.TemplateResponse(request, "admin_contact.html", {
        "user": user,
        "lang": get_lang(request),
        "t": get_t(request),
        "unread": unread,
        "read": read,
    })


@admin_router.post("/admin/contact/{msg_id}/mark-read")
def admin_contact_mark_read(msg_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    msg = db.query(ContactMessage).filter_by(id=msg_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Not found")
    msg.read = True
    db.commit()
    return RedirectResponse("/admin/contact", status_code=303)


@admin_router.post("/admin/contact/{msg_id}/delete")
def admin_contact_delete(msg_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    msg = db.query(ContactMessage).filter_by(id=msg_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(msg)
    db.commit()
    return RedirectResponse("/admin/contact", status_code=303)


# ── /admin/seo ────────────────────────────────────────────────────────────────

@admin_router.get("/admin/seo", response_class=HTMLResponse)
def admin_seo(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)

    # Latest snapshot for each language (subquery: max checked_at per lang)
    from sqlalchemy import select
    subq = (
        db.query(SeoRanking.lang, func.max(SeoRanking.checked_at).label("latest"))
        .group_by(SeoRanking.lang)
        .subquery()
    )
    rows = (
        db.query(SeoRanking)
        .join(subq, (SeoRanking.lang == subq.c.lang) & (SeoRanking.checked_at == subq.c.latest))
        .order_by(SeoRanking.lang)
        .all()
    )

    # Index by lang for easy template lookup; also include langs not yet checked
    rankings = {r.lang: r for r in rows}
    all_langs = list(seo_checker.LANG_SEO.keys())

    last_checked = max((r.checked_at for r in rows), default=None) if rows else None

    return templates.TemplateResponse(request, "admin_seo.html", {
        "user":         user,
        "lang":         get_lang(request),
        "t":            get_t(request),
        "rankings":     rankings,
        "all_langs":    all_langs,
        "lang_seo":     seo_checker.LANG_SEO,
        "last_checked": last_checked,
        "refresh_msg":  request.query_params.get("msg"),
        "bing_enabled": bool(seo_checker.BING_SEARCH_API_KEY),
    })


@admin_router.post("/admin/seo/refresh")
def admin_seo_refresh(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)

    def _run():
        _run_seo_rankings()

    background_tasks.add_task(_run)
    return RedirectResponse("/admin/seo?msg=refresh_started", status_code=303)


@admin_router.post("/admin/contact/delete-all-unread")
def admin_contact_delete_all_unread(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    db.query(ContactMessage).filter_by(read=False).delete()
    db.commit()
    return RedirectResponse("/admin/contact", status_code=303)


@admin_router.get("/admin/hscleaning", response_class=HTMLResponse)
def admin_hscleaning(
    request: Request,
    db: Session = Depends(get_db),
    mode: str = "beginner",
    date_str: str = "",
    board_hash: str = "",
    hmode: str = "all",
    no_guess: str = "all",
    page: int = 1,
):
    user = get_current_user(request)
    require_admin(request, user)

    from datetime import date as _date
    target_date = date.today()
    if date_str:
        try:
            target_date = _date.fromisoformat(date_str)
        except ValueError:
            pass

    valid_modes = {"beginner", "intermediate", "expert", "custom"}
    if mode not in valid_modes and mode != "all":
        mode = "beginner"

    PAGE_SIZE = 250
    page = max(1, page)

    # Daily scores for selected mode + date
    daily_q = db.query(Score).filter(
        func.date(Score.created_at) == target_date,
    )
    if mode != "all":
        daily_q = daily_q.filter(Score.mode == mode)
    daily_q = daily_q.order_by(Score.time_ms.asc(), Score.time_secs.asc())

    total_daily = daily_q.count()
    total_pages = max(1, (total_daily + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)
    daily_scores = daily_q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()

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

    flagged_scores = (
        db.query(FlaggedScore)
        .order_by(FlaggedScore.flagged_at.desc())
        .all()
    )

    # Resolve a display time for each flagged score.
    # Groups lookups by table so we only hit each table once.
    _TIME_FIELDS = {
        "scores":                  ("time_ms", "time_secs"),
        "rush_scores":             ("time_secs",),
        "tentaizu_scores":         ("time_secs",),
        "tentaizu_easy_scores":    ("time_secs",),
        "mosaic_scores":           ("time_secs",),
        "mosaic_easy_scores":      ("time_secs",),
        "mosaic_custom_scores":    ("time_secs",),
        "cylinder_scores":         ("time_secs",),
        "toroid_scores":           ("time_secs",),
        "replay_scores":           ("time_secs",),
        "hexsweeper_scores":       ("time_secs",),
        "nonosweeper_scores":      ("time_secs",),
        "numbers_match_scores":    ("time_secs",),
        "globesweeper_scores":     ("time_ms",),
        "cubesweeper_scores":      ("time_ms",),
        "mobiussweeper_scores":    ("time_ms",),
        "fifteen_puzzle_scores":   ("time_ms",),
        "game_2048_scores":        ("time_ms",),
        "game_2048hex_scores":     ("time_ms",),
        "schulte_grid_scores":     ("time_ms",),
        "sudoku_scores":           ("time_ms",),
        "mahjong_scores":          ("time_ms",),
        "jigsaw_scores":           ("time_ms",),
        "tametsi_scores":          ("time_ms",),
        "wc2026_scores":           ("solve_time_ms",),
    }
    def _fmt_flagged_time(table_name: str, score_id: int) -> str:
        fields = _TIME_FIELDS.get(table_name)
        if not fields:
            return "—"
        cols = ", ".join(fields)
        row = db.execute(
            text(f"SELECT {cols} FROM {table_name} WHERE id = :id"),
            {"id": score_id}
        ).fetchone()
        if not row:
            return "—"
        for i, field in enumerate(fields):
            val = row[i]
            if val is None:
                continue
            if "ms" in field:
                return f"{val / 1000:.3f}s"
            return f"{val:.3f}s"
        return "—"

    flagged_times = {
        f.id: _fmt_flagged_time(f.table_name, f.score_id)
        for f in flagged_scores
    }

    return templates.TemplateResponse(request, "admin_hscleaning.html", {
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
        "flagged_scores": flagged_scores,
        "flagged_times":  flagged_times,
        "page": page,
        "total_daily": total_daily,
        "total_pages": total_pages,
    })


@admin_router.post("/admin/hscleaning/delete/{score_id}")
def admin_hscleaning_delete(
    score_id: int,
    request: Request,
    db: Session = Depends(get_db),
    next_url: str = Query(default="/admin/hscleaning"),
):
    user = get_current_user(request)
    require_admin(request, user)
    score = db.query(Score).filter_by(id=score_id).first()
    if score:
        db.delete(score)
        db.commit()
    _p = urlparse(next_url)
    if not _p.scheme and not _p.netloc and _p.path.startswith("/admin/"):
        safe_next = "/" + _p.path.lstrip("/\\")  # normalize leading slashes
    else:
        safe_next = "/admin/hscleaning"
    return RedirectResponse(safe_next, status_code=303)


def _delete_flagged_and_score(flag: FlaggedScore, db) -> None:
    """Remove the flag row and optionally the underlying score row."""
    model = _SCORE_TABLE_MAP.get(flag.table_name)
    if model:
        score_row = db.query(model).filter_by(id=flag.score_id).first()
        if score_row:
            db.delete(score_row)
    db.delete(flag)


@admin_router.post("/admin/hscleaning/flagged/{flag_id}/delete")
def admin_flagged_delete(flag_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    flag = db.query(FlaggedScore).filter_by(id=flag_id).first()
    if flag:
        _delete_flagged_and_score(flag, db)
        db.commit()
    return RedirectResponse("/admin/hscleaning#flagged", status_code=303)


@admin_router.post("/admin/hscleaning/flagged/{flag_id}/unflag")
def admin_flagged_unflag(flag_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    flag = db.query(FlaggedScore).filter_by(id=flag_id).first()
    if flag:
        db.delete(flag)
        db.commit()
    return RedirectResponse("/admin/hscleaning#flagged", status_code=303)


@admin_router.post("/admin/hscleaning/flagged/delete-all")
def admin_flagged_delete_all(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    flags = db.query(FlaggedScore).all()
    for flag in flags:
        _delete_flagged_and_score(flag, db)
    db.commit()
    return RedirectResponse("/admin/hscleaning#flagged", status_code=303)


@admin_router.get("/admin/analysis", response_class=HTMLResponse)
def admin_analysis(request: Request, doc: Optional[str] = None, folder: Optional[str] = None,
                   src: Optional[str] = None):
    import markdown as md_lib
    import os

    user = get_current_user(request)
    require_admin(request, user)

    analysis_dir  = os.path.join(os.path.dirname(__file__), "analysis")
    real_analysis = os.path.realpath(analysis_dir)   # untainted constant — used for all containment checks
    download_exts = {".pptx", ".xlsx", ".docx", ".pdf"}
    source_exts   = {".ts", ".py", ".js"}

    # Validate folder param — only safe filesystem names; realpath containment confirms no escape.
    # active_dir is assigned the already-realpath-checked candidate (not re-derived from folder)
    # so CodeQL's taint trace from the request param is broken at this point.
    current_folder = None
    active_dir = real_analysis
    if folder and re.fullmatch(r'[A-Za-z0-9_-]+', folder):
        candidate = os.path.realpath(os.path.join(analysis_dir, folder))
        if candidate.startswith(real_analysis + os.sep) and os.path.isdir(candidate):
            current_folder = folder
            active_dir = candidate

    # Always list subfolders from the root (one level only)
    folders = []
    docs = []
    downloads = []
    source_files = []
    if os.path.isdir(analysis_dir):
        for name in sorted(os.listdir(analysis_dir)):
            if os.path.isdir(os.path.join(analysis_dir, name)) and not name.startswith("."):
                folders.append(name)

    if os.path.isdir(active_dir):
        for fname in sorted(os.listdir(active_dir)):
            fpath = os.path.join(active_dir, fname)
            if not os.path.isfile(fpath):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if fname.endswith(".md") or fname.endswith(".html"):
                docs.append(fname.rsplit(".", 1)[0])
            elif ext in download_exts:
                downloads.append(fname)
            elif ext in source_exts:
                source_files.append(fname)

    # Pre-build a map: doc-name → verified realpath, constructed entirely from the
    # directory listing (active_dir is already realpath-checked).  The VALUES of
    # this dict are server-computed paths with no user input; looking up by `doc`
    # (user input) returns an untainted path — no taint can flow to open().
    _doc_path_map: dict[str, tuple] = {}
    _doc_file_map: dict[str, str]   = {}
    for _d in docs:
        for _sfx, _is_html in ((".md", False), (".html", True)):
            _rp = os.path.realpath(os.path.join(active_dir, _d + _sfx))
            if _rp.startswith(real_analysis + os.sep) and os.path.isfile(_rp):
                _doc_path_map[_d] = (_rp, _is_html)
                _doc_file_map[_d] = _d + _sfx
                break

    content_html = None
    current_doc = None
    _doc_entry = _doc_path_map.get(doc) if doc else None
    if _doc_entry:
        _doc_realpath, _doc_is_html = _doc_entry
        with open(_doc_realpath, encoding="utf-8") as f:
            raw = f.read()
        content_html = raw if _doc_is_html else md_lib.markdown(raw, extensions=["extra", "sane_lists"])
        current_doc = _doc_file_map.get(doc, "").rsplit(".", 1)[0] or None

    # Resolve the actual filename (with extension) for the download link
    current_doc_file = _doc_file_map.get(doc) if doc else None

    # Source file viewer
    source_content = None
    current_src = None
    src = os.path.basename(src) if src else None  # strip any path components before lookup
    if src and src in source_files:
        real_src = os.path.realpath(os.path.join(active_dir, src))
        if real_src.startswith(real_analysis + os.sep) and os.path.isfile(real_src):
            with open(real_src, encoding="utf-8") as f:
                source_content = f.read()
            current_src = src

    return templates.TemplateResponse(request, "admin_analysis.html", {
        "user":             user,
        "lang":             get_lang(request),
        "t":                get_t(request),
        "mode":             "admin",
        "folders":          folders,
        "current_folder":   current_folder,
        "docs":             docs,
        "downloads":        downloads,
        "source_files":     source_files,
        "content_html":     content_html,
        "current_doc":      current_doc,
        "current_doc_file": current_doc_file,
        "source_content":   source_content,
        "current_src":      current_src,
    })


@admin_router.get("/admin/analysis/download")
def admin_analysis_download(request: Request, file: str):
    import os
    user = get_current_user(request)
    require_admin(request, user)

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


@admin_router.get("/admin/analysis/{filename}")
def admin_analysis_by_path(filename: str, folder: Optional[str] = None):
    doc_raw = filename.rsplit(".", 1)[0] if "." in filename else filename
    doc_match = re.fullmatch(r'[A-Za-z0-9_\-\.]{1,200}', doc_raw)
    if not doc_match:
        raise HTTPException(status_code=400, detail="Invalid filename")
    params = f"doc={quote(doc_match.group(), safe='')}"
    if folder:
        folder_match = re.fullmatch(r'[A-Za-z0-9_\-]{1,100}', folder)
        if not folder_match:
            raise HTTPException(status_code=400, detail="Invalid folder")
        params += f"&folder={quote(folder_match.group(), safe='')}"
    return RedirectResponse(_safe_relative_url(f"/admin/analysis?{params}"), status_code=302)  # codeql[py/url-redirection]


# ── Admin: match score management ────────────────────────────────────────────

@admin_router.get("/admin/wc2026-matches", response_class=HTMLResponse)
def wc2026_admin_matches(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    matches = (db.query(WC2026Match)
               .order_by(WC2026Match.match_date, WC2026Match.time_cdt)
               .all())
    return templates.TemplateResponse(request, "admin_wc2026_matches.html", {
        "user": user, "mode": "admin",
        "matches": matches,
        "by_slug": WC2026_BY_SLUG,
        "round_labels": WC2026_ROUND_LABELS,
    })


class WC2026MatchUpdate(BaseModel):
    match_id: int
    score1: Optional[int] = None
    score2: Optional[int] = None
    status: str

@admin_router.post("/api/admin/wc2026/update-match")
def wc2026_admin_update_match(payload: WC2026MatchUpdate,
                               request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    require_admin(request, user)
    if payload.status not in ("scheduled", "in_progress", "final"):
        return JSONResponse({"error": "Invalid status"}, status_code=400)
    row = db.query(WC2026Match).filter(WC2026Match.id == payload.match_id).first()
    if not row:
        return JSONResponse({"error": "Not found"}, status_code=404)
    row.score1  = payload.score1
    row.score2  = payload.score2
    row.status  = payload.status
    db.commit()
    return {"ok": True}

