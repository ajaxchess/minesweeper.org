"""
fifteen_puzzle_routes.py — Page and API route handlers for the 15-Puzzle game.
Covers: daily/leaderboard/how-to-play pages, score API, photo generator,
        member puzzle generator, and variable grid sizes (3x3, 5x5…10x10).
Mount this router in main.py with: app.include_router(fifteen_puzzle_router)

Note: the variable-grid catch-all (/other/15puzzle/{grid}) must be declared
after all specific /other/15puzzle/* routes; include_router preserves order.
"""
import os
import uuid
import hashlib
from datetime import date
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Request, Depends, HTTPException, Query, File, Form, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from better_profanity import profanity as _profanity_checker

from database import (
    FlaggedScore, UserProfile, GameReplay,
    FifteenPuzzleScore, FifteenPuzzlePhoto, MemberPuzzle,
    get_db,
)
from auth import get_current_user
from admin_routes import require_user, ADMIN_EMAILS
from translations import get_lang, get_t, SUPPORTED_LANGS
import settings as site_settings
from quest_catalog import quest_config
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs

fifteen_puzzle_router = APIRouter()
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


# ── 15-Puzzle constants ────────────────────────────────────────────────────────

_VALID_GRID_SIZES = {"3x3", "4x4", "5x5", "6x6", "7x7", "8x8", "9x9", "10x10"}

_FP_POOL_DIR = os.path.join("static", "img", "puzzle")
_FP_POOL_EXTS = {".jpg", ".jpeg", ".png"}

_GRID_LABELS = {
    "3x3": "3×3", "4x4": "4×4", "5x5": "5×5", "6x6": "6×6",
    "7x7": "7×7", "8x8": "8×8", "9x9": "9×9", "10x10": "10×10",
}
_PUZZLE_GRID_SIZES = ["3x3", "5x5", "6x6", "7x7", "8x8", "9x9", "10x10"]  # 4x4 = /daily


def _daily_pool_image(today_str: str) -> str:
    """Return a /static/img/puzzle/... URL that rotates daily."""
    try:
        imgs = sorted(
            f for f in os.listdir(_FP_POOL_DIR)
            if os.path.splitext(f)[1].lower() in _FP_POOL_EXTS
        )
    except OSError:
        return ""
    if not imgs:
        return ""
    idx = int(hashlib.md5(today_str.encode(), usedforsecurity=False).hexdigest(), 16) % len(imgs)
    return f"/static/img/puzzle/{imgs[idx]}"


# ── 15-Puzzle page routes ──────────────────────────────────────────────────────

@fifteen_puzzle_router.get("/other/15puzzle", response_class=HTMLResponse)
def fifteen_puzzle_landing(request: Request):
    return RedirectResponse("/other/15puzzle/daily", status_code=302)


@fifteen_puzzle_router.get("/other/15puzzle/daily", response_class=HTMLResponse)
def fifteen_puzzle_daily(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse(request, "fifteen_puzzle_daily.html", {
        "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today,
        "grid_size": "4x4", "grid_n": 4, "grid_label": "4×4",
        "photo_url": _daily_pool_image(today), "photo_mode": "tiles", "reveal_url": "",
        "board_hash": "", "display_name": "",
    })


@fifteen_puzzle_router.get("/other/15puzzle/leaderboard", response_class=HTMLResponse)
def fifteen_puzzle_leaderboard_page(request: Request, grid: str = Query(default="4x4")):
    if grid not in _VALID_GRID_SIZES:
        grid = "4x4"
    today = date.today().isoformat()
    return templates.TemplateResponse(request, "fifteen_puzzle_leaderboard.html", {
        "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today,
        "grid_size": grid,
    })


@fifteen_puzzle_router.get("/other/15puzzle/how-to-play", response_class=HTMLResponse)
def fifteen_puzzle_howtoplay(request: Request):
    return templates.TemplateResponse(request, "fifteen_puzzle_howtoplay.html", {
        "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


# ── 15-Puzzle API ──────────────────────────────────────────────────────────────

class FifteenPuzzleScoreSubmit(BaseModel):
    name:        str = Field(..., min_length=1, max_length=32)
    puzzle_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    grid_size:   str = Field(default="4x4")
    time_ms:     int = Field(..., ge=0, le=9999999)
    moves:       int = Field(..., ge=1, le=99999)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = v.strip()
        v = "".join(c for c in v if c.isprintable())
        if not v:
            raise ValueError("Name must contain printable characters")
        return v[:32]

    @field_validator("grid_size")
    @classmethod
    def validate_grid_size(cls, v: str) -> str:
        if v not in _VALID_GRID_SIZES:
            return "4x4"
        return v


@fifteen_puzzle_router.post("/api/fifteen-puzzle-scores", status_code=201)
@limiter.limit("10/minute")
def submit_fifteen_puzzle_score(payload: FifteenPuzzleScoreSubmit, request: Request, db: Session = Depends(get_db)):
    from telemetry import record_score_submit, record_game_complete
    user = get_current_user(request)
    guest_token = get_or_create_guest_token(request, user)
    entry = FifteenPuzzleScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        puzzle_date = payload.puzzle_date,
        grid_size   = payload.grid_size,
        time_ms     = payload.time_ms,
        moves       = payload.moves,
        guest_token = guest_token,
        client_type = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    flag_if_profane(db, entry.__tablename__, entry.id, entry.name)
    record_score_submit("fifteen_puzzle", payload.puzzle_date)
    record_game_complete("fifteen_puzzle", mode="daily", duration_ms=payload.time_ms)
    return {"ok": True, "id": entry.id}


@fifteen_puzzle_router.get("/api/fifteen-puzzle-scores/{puzzle_date}")
def get_fifteen_puzzle_scores(puzzle_date: str, grid: str = Query(default="4x4"), db: Session = Depends(get_db)):
    import re
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", puzzle_date):
        raise HTTPException(status_code=400, detail="Invalid date format")
    if grid not in _VALID_GRID_SIZES:
        grid = "4x4"
    q = (
        db.query(FifteenPuzzleScore)
        .filter(FifteenPuzzleScore.puzzle_date == puzzle_date,
                FifteenPuzzleScore.grid_size   == grid)
    )
    q = exclude_flagged(q, FifteenPuzzleScore, db)
    top = (
        q
        .order_by(FifteenPuzzleScore.time_ms.asc(), FifteenPuzzleScore.created_at.asc())
        .limit(20)
        .all()
    )
    return _enrich_with_profiles(top, db)


# ── 15-Puzzle generator ────────────────────────────────────────────────────────

@fifteen_puzzle_router.get("/other/15puzzle/generator", response_class=HTMLResponse)
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
    return templates.TemplateResponse(request, "fifteen_puzzle_generator.html", {
        "mode": "other",
        "user": user,
        "lang": get_lang(request), "t": get_t(request),
        "photos": photos,
        "limit": limit,
    })


@fifteen_puzzle_router.get("/other/15puzzle/photo/{board_hash}", response_class=HTMLResponse)
def fifteen_puzzle_photo_play(request: Request, board_hash: str, mode: str = Query("tiles"), db: Session = Depends(get_db)):
    import re
    if not re.match(r'^[A-Za-z0-9_\-]{10,128}$', board_hash):
        raise HTTPException(status_code=404, detail="Not found")
    photo = db.query(FifteenPuzzlePhoto).filter_by(board_hash=board_hash).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Puzzle not found")
    user = get_current_user(request)
    if not photo.approved:
        if not user or user.get("email") != photo.user_email:
            raise HTTPException(status_code=404, detail="Puzzle not found")
        pending_review = True
    else:
        pending_review = False
    if mode not in ("tiles", "reveal"):
        mode = photo.photo_mode
    return templates.TemplateResponse(request, "fifteen_puzzle_daily.html", {
        "mode": "other",
        "user": user,
        "lang": get_lang(request), "t": get_t(request),
        "today": date.today().isoformat(),
        "grid_size": "4x4", "grid_n": 4, "grid_label": "4×4",
        "photo_url": f"/static/uploads/15puzzle/{photo.filename}",
        "photo_mode": mode,
        "reveal_url": "",
        "board_hash": board_hash,
        "display_name": photo.display_name or "",
        "pending_review": pending_review,
        "noindex": True,
    })


@fifteen_puzzle_router.post("/api/fifteen-puzzle/upload-photo", status_code=201)
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
    user = require_user(request)

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

    # Save file — filename is server-generated (UUID), board_hash stored in DB only
    _ext_map = {"image/jpeg": ".jpg", "image/png": ".png"}
    upload_dir = os.path.join("static", "uploads", "15puzzle")
    os.makedirs(upload_dir, exist_ok=True)
    filename = uuid.uuid4().hex + _ext_map[content_type]
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


@fifteen_puzzle_router.post("/api/fifteen-puzzle/delete-photo/{board_hash}")
def delete_fifteen_puzzle_photo(board_hash: str, request: Request, db: Session = Depends(get_db)):
    user = require_user(request)
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


@fifteen_puzzle_router.post("/api/fifteen-puzzle/delete-all-photos")
def delete_all_fifteen_puzzle_photos(request: Request, db: Session = Depends(get_db)):
    user = require_user(request)
    photos = db.query(FifteenPuzzlePhoto).filter_by(user_email=user["email"]).all()
    for photo in photos:
        filepath = os.path.join("static", "uploads", "15puzzle", photo.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        db.delete(photo)
    db.commit()
    return {"ok": True, "deleted": len(photos)}


# ── Member Puzzle (secret dual-image generator) ───────────────────────────────

@fifteen_puzzle_router.get("/other/15puzzle/membergenerator", response_class=HTMLResponse)
def fifteen_puzzle_member_generator_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    puzzles = []
    if user:
        puzzles = (
            db.query(MemberPuzzle)
            .filter_by(user_email=user["email"])
            .order_by(MemberPuzzle.created_at.desc())
            .all()
        )
    return templates.TemplateResponse(request, "fifteen_puzzle_membergenerator.html", {
        "mode": "other",
        "user": user,
        "lang": get_lang(request), "t": get_t(request),
        "puzzles": puzzles,
        "noindex": True,
    })


@fifteen_puzzle_router.get("/other/15puzzle/memberphoto/{board_hash}", response_class=HTMLResponse)
def fifteen_puzzle_member_photo_play(request: Request, board_hash: str, db: Session = Depends(get_db)):
    import re
    if not re.match(r'^[A-Za-z0-9_\-]{10,128}$', board_hash):
        raise HTTPException(status_code=404, detail="Not found")
    puzzle = db.query(MemberPuzzle).filter_by(board_hash=board_hash).first()
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")
    user = get_current_user(request)
    if not puzzle.approved:
        owner_email = puzzle.user_email
        if not owner_email or not user or user.get("email") != owner_email:
            raise HTTPException(status_code=404, detail="Puzzle not found")
        pending_review = True
    else:
        pending_review = False
    return templates.TemplateResponse(request, "fifteen_puzzle_daily.html", {
        "mode": "other",
        "user": user,
        "lang": get_lang(request), "t": get_t(request),
        "today": date.today().isoformat(),
        "grid_size": "4x4", "grid_n": 4, "grid_label": "4×4",
        "photo_url": f"/static/uploads/15puzzle/{puzzle.tile_filename}",
        "photo_mode": "tiles",
        "reveal_url": f"/static/uploads/15puzzle/{puzzle.reveal_filename}",
        "board_hash": board_hash,
        "display_name": puzzle.display_name or "",
        "pending_review": pending_review,
        "noindex": True,
    })


@fifteen_puzzle_router.post("/api/fifteen-puzzle/upload-member", status_code=201)
@limiter.limit("10/minute")
async def upload_member_puzzle(
    request: Request,
    db: Session = Depends(get_db),
    tile_file: UploadFile = File(...),
    reveal_file: UploadFile = File(...),
    display_name: str = Form(""),
    board_hash: str = Form(...),
):
    import re
    user = get_current_user(request)  # optional — not required

    if not re.match(r'^[A-Za-z0-9_\-]{10,128}$', board_hash):
        raise HTTPException(status_code=400, detail="Invalid board hash")

    if db.query(MemberPuzzle).filter_by(board_hash=board_hash).first():
        raise HTTPException(status_code=409, detail="A puzzle with this board already exists")

    # Filenames are server-generated (UUID-based); board_hash is stored in the DB record only
    _ext_map = {"image/jpeg": ".jpg", "image/png": ".png"}
    upload_dir = os.path.join("static", "uploads", "15puzzle")
    upload_dir_abs = os.path.abspath(upload_dir)
    os.makedirs(upload_dir_abs, exist_ok=True)

    filenames = {}
    for label, upload in (("tile", tile_file), ("reveal", reveal_file)):
        content_type = upload.content_type or ""
        if content_type not in ("image/jpeg", "image/png"):
            raise HTTPException(status_code=400, detail=f"Only JPG and PNG accepted ({label} image)")
        data = await upload.read()
        if len(data) > 2 * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"File too large — max 2 MB ({label} image)")
        safe_label = {"tile": "tile", "reveal": "reveal"}[label]  # whitelist gate for CodeQL path-expression check
        filename = f"{uuid.uuid4().hex}_{safe_label}{_ext_map[content_type]}"
        target_path = os.path.abspath(os.path.join(upload_dir_abs, filename))
        if os.path.commonpath([upload_dir_abs, target_path]) != upload_dir_abs:
            raise HTTPException(status_code=400, detail="Invalid upload path")
        with open(target_path, "wb") as f:
            f.write(data)
        filenames[label] = filename

    entry = MemberPuzzle(
        board_hash      = board_hash,
        tile_filename   = filenames["tile"],
        reveal_filename = filenames["reveal"],
        display_name    = display_name.strip()[:128] or None,
        user_email      = user["email"] if user else None,
    )
    db.add(entry)
    db.commit()
    return {"ok": True, "url": f"/other/15puzzle/memberphoto/{board_hash}"}


# ── 15-Puzzle variable grid sizes (3x3, 5x5 … 10x10) ─────────────────────────
# This route must be declared after all specific /other/15puzzle/* routes.

@fifteen_puzzle_router.get("/other/15puzzle/{grid}", response_class=HTMLResponse)
def fifteen_puzzle_grid_page(request: Request, grid: str):
    if grid not in _PUZZLE_GRID_SIZES:
        raise HTTPException(status_code=404)
    n = int(grid.split("x")[0])
    label = _GRID_LABELS[grid]
    today = date.today().isoformat()
    return templates.TemplateResponse(request, "fifteen_puzzle_daily.html", {
        "mode": "other",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "today": today,
        "grid_size": grid,
        "grid_n": n,
        "grid_label": label,
        "photo_url": _daily_pool_image(today), "photo_mode": "tiles", "reveal_url": "",
        "board_hash": "", "display_name": "",
    })
