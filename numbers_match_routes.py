"""
numbers_match_routes.py — Page and API route handlers for Numbers Match.
Mount this router in main.py with: app.include_router(numbers_match_router)
"""
import logging
import re as _re
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from itsdangerous import BadSignature, URLSafeTimedSerializer

from fastapi import APIRouter, Request, Depends, HTTPException, Query, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import (
    FlaggedScore, UserProfile, GameReplay,
    NumbersMatchScore, NumbersMatchDaily,
    get_db,
)
from auth import get_current_user, SECRET_KEY
from translations import get_lang, get_t, SUPPORTED_LANGS
import settings as site_settings
from quest_catalog import quest_config
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs
from numbers_match_generator import (
    generate_daily as _nm_generate_daily,
    NUMBERS_MATCH_TZ_NAME,
    NUMBERS_MATCH_BOARD_REVISION,
    numbers_match_today_str,
)
from numbers_match_engine import (
    InvalidReplay, MAX_EVENTS, VERIFIABLE_PUZZLE_ID, board_for_puzzle, replay,
)

logger = logging.getLogger(__name__)
numbers_match_router = APIRouter()
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


# ── Numbers Match API (board + scores) ────────────────────────────────────────

@numbers_match_router.get("/api/numbers-match-today")
def get_numbers_match_today(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {
        "today": numbers_match_today_str(),
        "timezone": NUMBERS_MATCH_TZ_NAME,
        "revision": NUMBERS_MATCH_BOARD_REVISION,
    }


@numbers_match_router.get("/api/numbers-match-board/{date_str}")
def get_numbers_match_board(
    date_str: str,
    response: Response,
    rev: str = Query(None),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    if not _re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise HTTPException(status_code=400, detail="Invalid date format")
    if rev:
        if not _re.match(r"^v\d+$", rev):
            raise HTTPException(status_code=400, detail="Invalid revision")
        result = _nm_generate_daily(date_str, seed_suffix=f":{rev}")
        return {
            "puzzle_date": date_str,
            "board_num":   result["board_num"],
            "rows":        result["rows"],
            "board_data":  result["board_data"],
            "revision":    rev,
        }
    row = db.query(NumbersMatchDaily).filter_by(puzzle_date=date_str).first()
    if row and row.rows != 4:
        db.delete(row)
        db.commit()
        row = None
    if not row:
        result = _nm_generate_daily(date_str)
        try:
            entry = NumbersMatchDaily(
                puzzle_date = date_str,
                board_num   = result["board_num"],
                rows        = result["rows"],
                board_data  = result["board_data"],
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            row = entry
        except IntegrityError:
            db.rollback()
            row = db.query(NumbersMatchDaily).filter_by(puzzle_date=date_str).first()
    return {
        "puzzle_date": row.puzzle_date,
        "board_num":   row.board_num,
        "rows":        row.rows,
        "board_data":  row.board_data,
    }


@numbers_match_router.get("/api/numbers-match-scores/{puzzle_date}")
def get_numbers_match_scores(puzzle_date: str, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    if not _re.match(r"^\d{4}-\d{2}-\d{2}(-(?:easy|medium|hard|expert))?(-v\d+)?$", puzzle_date):
        raise HTTPException(status_code=400, detail="Invalid date format")
    q = db.query(NumbersMatchScore).filter(NumbersMatchScore.puzzle_date == puzzle_date)
    q = exclude_flagged(q, NumbersMatchScore, db)
    all_rows = q.all()
    # Rank by score-to-time ratio: higher score achieved faster = better rank.
    # Tiebreak: higher raw score, then lower time.
    all_rows.sort(
        key=lambda r: (
            -(r.score / max(1, r.time_secs)),
            -r.score,
            r.time_secs,
        )
    )
    seen, top = set(), []
    for row in all_rows:
        key = row.name.strip().lower()
        if key not in seen:
            seen.add(key)
            top.append(row)
        if len(top) >= 20:
            break
    return _enrich_with_profiles(top, db)


# ── Numbers Match ─────────────────────────────────────────────────────────────

@numbers_match_router.get("/numbers-match", response_class=HTMLResponse)
async def numbers_match_page(request: Request):
    real_today = numbers_match_today_str()
    return templates.TemplateResponse(request, "numbers_match.html", {
        "mode":       "numbers-match",
        "user":       get_current_user(request),
        "lang":       get_lang(request),
        "t":          get_t(request),
        "today":      real_today,
        "real_today": real_today,
        "nm_revision": NUMBERS_MATCH_BOARD_REVISION,
        "nm_timezone": NUMBERS_MATCH_TZ_NAME,
    }, headers={"Cache-Control": "no-store"})


# Must be declared AFTER any future static sub-routes (e.g. /numbers-match/how-to-play)
@numbers_match_router.get("/numbers-match/{date_str}", response_class=HTMLResponse)
async def numbers_match_permalink(request: Request, date_str: str):
    real_today = numbers_match_today_str()
    if not _re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return RedirectResponse("/numbers-match", status_code=302)
    return templates.TemplateResponse(request, "numbers_match.html", {
        "mode":       "numbers-match",
        "user":       get_current_user(request),
        "lang":       get_lang(request),
        "t":          get_t(request),
        "today":      date_str,
        "real_today": real_today,
        "nm_revision": NUMBERS_MATCH_BOARD_REVISION,
        "nm_timezone": NUMBERS_MATCH_TZ_NAME,
        "noindex":    True,
    }, headers={"Cache-Control": "no-store"})


# ── Numbers Match Score API (F-NM-VERIFY: server replays every game) ──────────
#
# 1. When a leaderboard game starts, the client asks /api/numbers-match-start for a
#    signed game token (puzzle id + one-time nonce, timestamped by the server).
# 2. On a win it posts the token and its move log. The server rebuilds the board,
#    replays every move with numbers_match_engine, and stores the score and time
#    the replay produces — never the values the client reports.
# 3. The claimed play time may not exceed the wall-clock time since the token was
#    issued, and each token can be used for one score only.

GAME_TOKEN_SALT       = "numbers-match-game"
GAME_TOKEN_MAX_AGE_S  = 24 * 3600
TIME_TOLERANCE_MS     = 5000   # token fetch latency + clock jitter
MIN_MS_PER_MATCH      = 150    # two taps per match; faster than any human

_game_tokens = URLSafeTimedSerializer(SECRET_KEY, salt=GAME_TOKEN_SALT)


class NumbersMatchStart(BaseModel):
    puzzle_id: str = Field(..., max_length=40)


@numbers_match_router.post("/api/numbers-match-start")
@limiter.limit("60/minute")
def start_numbers_match_game(payload: NumbersMatchStart, request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    if not VERIFIABLE_PUZZLE_ID.match(payload.puzzle_id):
        raise HTTPException(status_code=400, detail="Puzzle is not on a leaderboard")
    token = _game_tokens.dumps({"p": payload.puzzle_id, "n": uuid.uuid4().hex})
    return {"token": token}


class NumbersMatchScoreSubmit(BaseModel):
    name:        str = Field(..., min_length=1, max_length=32)
    puzzle_date: str = Field(..., max_length=40)
    game_token:  str = Field(..., min_length=1, max_length=300)
    moves:       list[list[str | int]] = Field(..., min_length=1, max_length=MAX_EVENTS)
    # Client-side values, kept for drift logging only; the stored ones come from the replay.
    score:       Optional[int] = Field(default=None, ge=0, le=99999)
    time_secs:   Optional[int] = Field(default=None, ge=0, le=99999)
    lines_added: Optional[int] = Field(default=None, ge=0, le=999)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable())
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]


def _reject(detail: str):
    raise HTTPException(status_code=422, detail=detail)


@numbers_match_router.post("/api/numbers-match-scores", status_code=201)
@limiter.limit("10/minute")
def submit_numbers_match_score(
    payload: NumbersMatchScoreSubmit,
    request: Request,
    db: Session = Depends(get_db),
):
    from telemetry import record_score_submit, record_game_complete

    try:
        claims, issued_at = _game_tokens.loads(
            payload.game_token, max_age=GAME_TOKEN_MAX_AGE_S, return_timestamp=True)
    except BadSignature:
        _reject("Invalid or expired game token")
    if claims.get("p") != payload.puzzle_date:
        _reject("Game token is for a different puzzle")
    nonce = claims.get("n")
    if db.query(NumbersMatchScore.id).filter_by(game_nonce=nonce).first():
        _reject("This game was already submitted")

    rebuilt = board_for_puzzle(payload.puzzle_date)
    if rebuilt is None:
        _reject("Puzzle is not on a leaderboard")
    board, rows = rebuilt
    try:
        result = replay(board, rows, payload.moves)
    except InvalidReplay as e:
        logger.info("numbers match replay rejected (%s): %s", payload.puzzle_date, e)
        _reject(f"Game could not be verified: {e}")

    elapsed_ms = (datetime.now(timezone.utc) - issued_at).total_seconds() * 1000
    if result.time_ms > elapsed_ms + TIME_TOLERANCE_MS:
        _reject("Game time is longer than the time since the game started")
    if result.time_ms < result.matches * MIN_MS_PER_MATCH:
        _reject("Game was played too fast")

    time_secs = max(1, result.time_ms // 1000)
    if payload.score is not None and payload.score != result.score:
        logger.warning("numbers match score drift (%s): client=%s server=%s",
                       payload.puzzle_date, payload.score, result.score)

    user = get_current_user(request)
    guest_token = get_or_create_guest_token(request, user)
    entry = NumbersMatchScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        puzzle_date = payload.puzzle_date,
        score       = result.score,
        time_secs   = time_secs,
        lines_added = result.lines_added,
        guest_token = guest_token,
        client_type = get_client_type(request),
        game_nonce  = nonce,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    flag_if_profane(db, entry.__tablename__, entry.id, entry.name)
    record_score_submit("numbers_match", str(payload.puzzle_date))
    record_game_complete("numbers_match", mode="daily", duration_ms=result.time_ms)
    return {"ok": True, "id": entry.id, "score": result.score, "time_secs": time_secs}