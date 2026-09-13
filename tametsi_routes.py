"""
tametsi_routes.py — Page and API route handlers for Tametsi puzzles.
Mount this router in main.py with: app.include_router(tametsi_router)
"""
import re, os, uuid, json as _json, logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Request, Depends, HTTPException, Query, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from better_profanity import profanity as _profanity_checker

from database import (
    FlaggedScore, GameHistory, GameReplay, UserProfile,
    TametsiBoard, TametsiDaily, TametsiScore,
    TametsiHexCompletion, TametsiHexTime, TametsiHexUserBoard,
    WC2026Score,
    GameMode,
    get_db, SessionLocal,
)
from tametsi_generator import (
    generate_board as _tametsi_generate_board,
    daily_rng    as _tametsi_daily_rng,
    LEVELS       as _TAMETSI_LEVELS,
)
from auth import get_current_user
from translations import get_lang, get_t, SUPPORTED_LANGS
import settings as site_settings
from quest_catalog import quest_config
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs

tametsi_router = APIRouter()
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
templates.env.globals["ga_tag"]                = ""
templates.env.globals["get_breadcrumbs"]       = _get_breadcrumbs

logger = logging.getLogger(__name__)


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


# ── Tametsi-local constants and helpers ──────────────────────────────────────

_TAMETSI_LEVEL_RE = re.compile(r"^(beginner|intermediate|expert)$")
_TAMETSI_HASH_RE  = re.compile(r"^[0-9a-f]{64}$")


def _tametsi_board_response(board_row: TametsiBoard) -> dict:
    return {
        "board_hash": board_row.board_hash,
        "rows":       board_row.rows,
        "cols":       board_row.cols,
        "mines":      board_row.mines,
        "bbbv":       board_row.bbbv,
        "board_data": board_row.board_data,
    }


# ── Tametsi HTML routes ───────────────────────────────────────────────────────

@tametsi_router.get("/puzzles/tametsi", response_class=HTMLResponse)
def puzzles_tametsi_redirect(request: Request):
    lang = get_lang(request)
    prefix = _safe_lang_prefix(lang)
    return RedirectResponse(_safe_relative_url(f"{prefix}/tametsi"), status_code=301)


@tametsi_router.get("/tametsi/board/{board_hash}", response_class=HTMLResponse)
async def tametsi_board_page(request: Request, board_hash: str):
    _hash = board_hash if re.match(r"^[0-9a-f]{64}$", board_hash) else None
    return templates.TemplateResponse(request, "tametsi.html", {
        "mode":         "tametsi",
        "user":         get_current_user(request),
        "lang":         get_lang(request),
        "t":            get_t(request),
        "initial_hash": _hash,
    })


@tametsi_router.get("/tametsi/replay/{replay_id}", response_class=HTMLResponse)
def tametsi_replay_page(replay_id: int, request: Request, db: Session = Depends(get_db)):
    replay = db.get(GameReplay, replay_id)
    if not replay or not replay.mode or not replay.mode.startswith("tametsi-"):
        raise HTTPException(status_code=404, detail="Replay not found")
    return templates.TemplateResponse(request, "tametsi_replay.html", {
        "user":      get_current_user(request),
        "t":         get_t(request),
        "replay_id": replay_id,
        "mode":      replay.mode,
        "outcome":   replay.outcome,
    })


@tametsi_router.get("/tametsi", response_class=HTMLResponse)
async def tametsi_page(request: Request):
    return templates.TemplateResponse(request, "tametsi.html", {
        "mode":         "tametsi",
        "user":         get_current_user(request),
        "lang":         get_lang(request),
        "t":            get_t(request),
        "initial_hash": None,
    })


# ── Tametsi API endpoints ─────────────────────────────────────────────────────

@tametsi_router.get("/api/tametsi/daily/{level}")
def tametsi_daily(level: str, db: Session = Depends(get_db)):
    if not _TAMETSI_LEVEL_RE.match(level):
        raise HTTPException(status_code=400, detail="Invalid level")
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily = db.query(TametsiDaily).filter_by(puzzle_date=date_str, level=level).first()
    if not daily:
        # Use a low attempt limit on the hot path so the worker thread is not blocked
        # for >1 s. The startup thread and cron job handle proper generation with full
        # MAX_ATTEMPTS. If this quick attempt fails, return 503 so the client retries.
        rows, cols, num_mines = _TAMETSI_LEVELS[level]
        try:
            board = _tametsi_generate_board(
                rows, cols, num_mines,
                rng=_tametsi_daily_rng(level, date_str),
                max_attempts=200,
            )
        except RuntimeError as e:
            logger.error(f"tametsi_daily on-request generation failed: {e}")
            raise HTTPException(status_code=503, detail="Daily puzzle not yet available; please retry shortly.")
        try:
            if not db.get(TametsiBoard, board.board_hash):
                db.add(TametsiBoard(
                    board_hash = board.board_hash,
                    rows       = board.rows,
                    cols       = board.cols,
                    mines      = len(board.mines),
                    bbbv       = board.bbbv,
                    board_data = board.board_data,
                ))
            daily = TametsiDaily(puzzle_date=date_str, level=level, board_hash=board.board_hash)
            db.add(daily)
            db.commit()
            db.refresh(daily)
        except Exception:
            db.rollback()
            # Another worker committed first; re-query to get what was stored.
            daily = db.query(TametsiDaily).filter_by(puzzle_date=date_str, level=level).first()
            if not daily:
                raise HTTPException(status_code=503, detail="Daily puzzle temporarily unavailable.")
    return _tametsi_board_response(db.get(TametsiBoard, daily.board_hash))


@tametsi_router.get("/api/tametsi/random/{level}")
def tametsi_random(level: str, db: Session = Depends(get_db)):
    if not _TAMETSI_LEVEL_RE.match(level):
        raise HTTPException(status_code=400, detail="Invalid level")
    rows, cols, num_mines = _TAMETSI_LEVELS[level]
    board = _tametsi_generate_board(rows, cols, num_mines)
    if not db.get(TametsiBoard, board.board_hash):
        db.add(TametsiBoard(
            board_hash = board.board_hash,
            rows       = board.rows,
            cols       = board.cols,
            mines      = len(board.mines),
            bbbv       = board.bbbv,
            board_data = board.board_data,
        ))
        db.commit()
    return _tametsi_board_response(db.get(TametsiBoard, board.board_hash))


@tametsi_router.get("/api/tametsi/board/{board_hash}")
def tametsi_load_board(board_hash: str, db: Session = Depends(get_db)):
    if not _TAMETSI_HASH_RE.match(board_hash):
        raise HTTPException(status_code=400, detail="Invalid board hash")
    board_row = db.get(TametsiBoard, board_hash)
    if not board_row:
        raise HTTPException(status_code=404, detail="Board not found")
    return _tametsi_board_response(board_row)


class TametsiScoreSubmit(BaseModel):
    board_hash:   str = Field(..., min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    level:        str = Field(..., pattern=r"^(beginner|intermediate|expert)$")
    is_daily:     bool
    name:         str = Field(..., min_length=1, max_length=32)
    time_ms:      int = Field(..., ge=1, le=9_999_999)
    bbbv:         int = Field(..., ge=1, le=10_000)
    left_clicks:  Optional[int] = None
    right_clicks: Optional[int] = None

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable())
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


@tametsi_router.post("/api/tametsi/scores", status_code=201)
@limiter.limit("10/minute")
def submit_tametsi_score(
    payload: TametsiScoreSubmit,
    request: Request,
    db: Session = Depends(get_db),
):
    from telemetry import record_score_submit, record_game_complete
    board_row = db.get(TametsiBoard, payload.board_hash)
    if not board_row:
        raise HTTPException(status_code=404, detail="Unknown board hash")

    if payload.is_daily:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily = db.query(TametsiDaily).filter_by(
            puzzle_date=date_str, level=payload.level
        ).first()
        if not daily or daily.board_hash != payload.board_hash:
            raise HTTPException(status_code=400, detail="Board hash does not match today's daily puzzle")

    user = get_current_user(request)
    guest_token = get_or_create_guest_token(request, user)

    client_type = get_client_type(request)
    entry = TametsiScore(
        board_hash   = payload.board_hash,
        level        = payload.level,
        is_daily     = payload.is_daily,
        name         = payload.name,
        user_email   = user["email"] if user else None,
        guest_token  = guest_token,
        time_ms      = payload.time_ms,
        bbbv         = payload.bbbv,
        left_clicks  = payload.left_clicks,
        right_clicks = payload.right_clicks,
        client_type  = client_type,
    )
    db.add(entry)

    if user:
        db.add(GameHistory(
            user_email  = user["email"],
            name        = payload.name,
            mode        = GameMode.tametsi,
            time_secs   = payload.time_ms // 1000,
            time_ms     = payload.time_ms,
            rows        = board_row.rows,
            cols        = board_row.cols,
            mines       = board_row.mines,
            board_hash  = payload.board_hash,
            bbbv        = payload.bbbv,
            no_guess    = True,
            client_type = client_type,
        ))

    db.commit()
    db.refresh(entry)
    entry_id = entry.id   # capture before possible second commit expires the object
    flag_if_profane(db, entry.__tablename__, entry_id, payload.name)

    # Enforce 15-score cap for random boards
    if not payload.is_daily:
        all_ids = [
            r.id for r in (
                db.query(TametsiScore.id)
                .filter(TametsiScore.board_hash == payload.board_hash)
                .order_by(TametsiScore.time_ms.asc(), TametsiScore.created_at.asc())
                .all()
            )
        ]
        if len(all_ids) > 15:
            db.query(TametsiScore).filter(
                TametsiScore.id.in_(all_ids[15:])
            ).delete(synchronize_session=False)
            db.commit()

    record_score_submit("tametsi", payload.level)
    record_game_complete("tametsi", mode=payload.level, duration_ms=payload.time_ms)
    return {"ok": True, "id": entry_id}


@tametsi_router.get("/api/tametsi/leaderboard/{level}")
def tametsi_leaderboard_daily(level: str, db: Session = Depends(get_db), response: Response = None):
    if response:
        response.headers["Cache-Control"] = "public, max-age=60"
    if not _TAMETSI_LEVEL_RE.match(level):
        raise HTTPException(status_code=400, detail="Invalid level")
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily = db.query(TametsiDaily).filter_by(puzzle_date=date_str, level=level).first()
    if not daily:
        return []
    q = db.query(TametsiScore).filter(
        TametsiScore.board_hash == daily.board_hash,
        TametsiScore.is_daily   == True,
    )
    q = exclude_flagged(q, TametsiScore, db)
    top = (
        q.order_by(TametsiScore.time_ms.asc(), TametsiScore.created_at.asc())
        .limit(20)
        .all()
    )
    return _enrich_with_profiles(top, db)


@tametsi_router.get("/api/tametsi/leaderboard/board/{board_hash}")
def tametsi_leaderboard_board(board_hash: str, db: Session = Depends(get_db), response: Response = None):
    if response:
        response.headers["Cache-Control"] = "public, max-age=60"
    if not _TAMETSI_HASH_RE.match(board_hash):
        raise HTTPException(status_code=400, detail="Invalid board hash")
    q = db.query(TametsiScore).filter(TametsiScore.board_hash == board_hash)
    q = exclude_flagged(q, TametsiScore, db)
    top = (
        q.order_by(TametsiScore.time_ms.asc(), TametsiScore.created_at.asc())
        .limit(15)
        .all()
    )
    return _enrich_with_profiles(top, db)


# ── Tametsi History ───────────────────────────────────────────────────────────

_TAMETSI_HISTORY_MODES    = {"all", "beginner", "intermediate", "expert", "wc_easy", "wc_hard"}
_TAMETSI_HISTORY_PAGE_SIZE = 50


@tametsi_router.get("/tametsi-history")
def tametsi_history_api(
    request: Request,
    mode: str = "all",
    page: int = 1,
    db: Session = Depends(get_db),
):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)
    if mode not in _TAMETSI_HISTORY_MODES:
        return JSONResponse({"error": "Invalid mode"}, status_code=400)
    page = max(1, page)

    email = user["email"]
    rows = []

    if mode in ("all", "beginner", "intermediate", "expert"):
        levels = (
            ["beginner", "intermediate", "expert"] if mode == "all"
            else [mode]
        )
        q = (
            db.query(TametsiScore)
            .filter(TametsiScore.user_email == email, TametsiScore.level.in_(levels))
            .all()
        )
        for r in q:
            rows.append({
                "source":       "tametsi",
                "mode":         r.level,
                "date":         r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
                "time_ms":      r.time_ms,
                "bbbv":         r.bbbv,
                "left_clicks":  r.left_clicks,
                "right_clicks": r.right_clicks,
                "is_daily":     r.is_daily,
                "country_slug": None,
                "sort_key":     r.created_at,
            })

    if mode in ("all", "wc_easy", "wc_hard"):
        difficulties = (
            ["easy", "hard"] if mode == "all"
            else ["easy" if mode == "wc_easy" else "hard"]
        )
        q = (
            db.query(WC2026Score)
            .filter(WC2026Score.email == email, WC2026Score.difficulty.in_(difficulties))
            .all()
        )
        for r in q:
            rows.append({
                "source":       "wc2026",
                "mode":         f"wc_{r.difficulty}",
                "date":         r.solved_at.strftime("%Y-%m-%d %H:%M") if r.solved_at else "",
                "time_ms":      r.solve_time_ms,
                "bbbv":         r.bbbv,
                "left_clicks":  r.left_clicks,
                "right_clicks": r.right_clicks,
                "is_daily":     False,
                "country_slug": r.country_slug,
                "sort_key":     r.solved_at,
            })

    rows.sort(key=lambda x: x["sort_key"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    for r in rows:
        del r["sort_key"]

    total = len(rows)
    pages = max(1, (total + _TAMETSI_HISTORY_PAGE_SIZE - 1) // _TAMETSI_HISTORY_PAGE_SIZE)
    page  = min(page, pages)
    start = (page - 1) * _TAMETSI_HISTORY_PAGE_SIZE
    games = rows[start: start + _TAMETSI_HISTORY_PAGE_SIZE]

    return {"games": games, "total": total, "page": page, "pages": pages}


@tametsi_router.get("/tametsi/history", response_class=HTMLResponse)
def tametsi_history_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(request, "tametsi_history.html", {
        "user":    user,
        "lang":    get_lang(request),
        "t":       get_t(request),
        "mode":    "tametsi",
    })


@tametsi_router.get("/api/tametsi/replay/{replay_id}")
def get_tametsi_replay(replay_id: int, db: Session = Depends(get_db)):
    replay = db.get(GameReplay, replay_id)
    if not replay or not replay.mode or not replay.mode.startswith("tametsi-"):
        raise HTTPException(status_code=404, detail="Replay not found")
    board = db.get(TametsiBoard, replay.board_hash) if replay.board_hash else None
    return {
        "id":               replay.id,
        "mode":             replay.mode,
        "rows":             replay.rows,
        "cols":             replay.cols,
        "mines":            replay.mines,
        "board_hash":       replay.board_hash,
        "time_ms":          replay.time_ms,
        "outcome":          replay.outcome,
        "bbbv":             replay.bbbv,
        "left_clicks":      replay.left_clicks,
        "right_clicks":     replay.right_clicks,
        "chord_clicks":     replay.chord_clicks,
        "cells_revealed":   replay.cells_revealed,
        "cells_total_safe": replay.cells_total_safe,
        "created_at":       replay.created_at.isoformat() if replay.created_at else None,
        "log":              _json.loads(replay.log_json) if replay.log_json else [],
        "board_data":       board.board_data if board else None,
    }


# ── Tametsi Hex Campaign ──────────────────────────────────────────────────────

class TametsiHexCompletePayload(BaseModel):
    puzzle_id: int
    time_ms: Optional[int] = None


@tametsi_router.get("/tametsi/hex", response_class=HTMLResponse)
def tametsi_hex_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    completions: list[int] = []
    if user:
        completions = [
            r.puzzle_id
            for r in db.query(TametsiHexCompletion)
                       .filter(TametsiHexCompletion.email == user["email"])
                       .all()
        ]
    return templates.TemplateResponse(request, "tametsi_hex.html", {
        "user":        user,
        "t":           get_t(request),
        "lang":        get_lang(request),
        "mode":        "tametsi-hex",
        "completions": completions,
    })


@tametsi_router.post("/api/tametsi-hex/complete", status_code=200)
def tametsi_hex_complete(payload: TametsiHexCompletePayload,
                          request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    if payload.puzzle_id not in range(1, 20):
        raise HTTPException(status_code=400, detail="Invalid puzzle_id")
    existing = (
        db.query(TametsiHexCompletion)
          .filter_by(email=user["email"], puzzle_id=payload.puzzle_id)
          .first()
    )
    if not existing:
        db.add(TametsiHexCompletion(email=user["email"], puzzle_id=payload.puzzle_id))
    if payload.time_ms and payload.time_ms > 0:
        existing_time = (
            db.query(TametsiHexTime)
              .filter_by(email=user["email"], puzzle_id=payload.puzzle_id)
              .first()
        )
        if not existing_time:
            db.add(TametsiHexTime(email=user["email"], puzzle_id=payload.puzzle_id,
                                  time_ms=payload.time_ms))
        elif payload.time_ms < existing_time.time_ms:
            existing_time.time_ms = payload.time_ms
    db.commit()
    return {"ok": True}


class TametsiHexEditorSavePayload(BaseModel):
    board_hash: str


@tametsi_router.post("/api/tametsi-hex/editor/save", status_code=200)
def tametsi_hex_editor_save(payload: TametsiHexEditorSavePayload,
                             request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    h = payload.board_hash.strip()
    if not h or len(h) > 64 or not all(c in '0123456789abcdefghijklmnopqrstuvwxyz-' for c in h):
        raise HTTPException(status_code=400, detail="Invalid board_hash")
    existing = db.query(TametsiHexUserBoard).filter_by(
        email=user["email"], board_hash=h).first()
    if not existing:
        db.add(TametsiHexUserBoard(email=user["email"], board_hash=h))
        db.commit()
    return {"ok": True}


@tametsi_router.get("/tametsi-hex/best-times")
def tametsi_hex_best_times(db: Session = Depends(get_db)):
    rows = (
        db.query(TametsiHexTime, UserProfile)
          .join(UserProfile, TametsiHexTime.email == UserProfile.email, isouter=True)
          .order_by(TametsiHexTime.puzzle_id,
                    TametsiHexTime.time_ms,
                    TametsiHexTime.created_at.desc())
          .all()
    )
    result: dict = {}
    counts: dict = {}
    for t, p in rows:
        pid = t.puzzle_id
        if pid not in result:
            result[pid] = []
            counts[pid] = 0
        if counts[pid] >= 10:
            continue
        name = (p.display_name if p else None) or "Anonymous"
        profile_url = (f"/u/{p.vanity_slug or p.public_id}"
                       if p and p.is_public else None)
        result[pid].append({"name": name, "time_ms": t.time_ms,
                             "profile_url": profile_url})
        counts[pid] += 1
    return result
