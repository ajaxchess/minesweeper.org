"""
jigsaw_routes.py — Page and API route handlers for Jigsaw Puzzle.
Mount this router in main.py with: app.include_router(jigsaw_router)
"""
import os, json as _json, uuid, hashlib
from datetime import date
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Request, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from better_profanity import profanity as _profanity_checker

from database import (
    FlaggedScore, UserProfile, GameReplay,
    JigsawScore, JigsawSavedGame, JigsawPhoto,
    get_db,
)
from admin_routes import require_user, ADMIN_EMAILS
from auth import get_current_user
from translations import get_lang, get_t, SUPPORTED_LANGS
import settings as site_settings
from quest_catalog import quest_config
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs

jigsaw_router = APIRouter()
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
    seed = int(hashlib.md5(puzzle_date.encode(), usedforsecurity=False).hexdigest(), 16)
    return images[seed % len(images)]


@jigsaw_router.get("/other/jigsaw", response_class=HTMLResponse)
def jigsaw_landing(request: Request):
    return RedirectResponse("/other/jigsaw/daily", status_code=302)


@jigsaw_router.get("/other/jigsaw/daily", response_class=HTMLResponse)
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
    return templates.TemplateResponse(request, "jigsaw_daily.html", {
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


@jigsaw_router.get("/other/jigsaw/gallery", response_class=HTMLResponse)
def jigsaw_gallery_page(request: Request):
    try:
        images = sorted(
            f for f in os.listdir(_JIGSAW_PUZZLE_DIR)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        )
    except OSError:
        images = []
    return templates.TemplateResponse(request, "jigsaw_gallery.html", {
        "mode":    "other",
        "user":    get_current_user(request),
        "lang":    get_lang(request),
        "t":       get_t(request),
        "images":  images,
        "noindex": get_lang(request) != "en",
    })


@jigsaw_router.get("/other/jigsaw/generator", response_class=HTMLResponse)
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
    return templates.TemplateResponse(request, "jigsaw_generator.html", {
        "mode":    "other",
        "user":    user,
        "lang":    get_lang(request),
        "t":       get_t(request),
        "photos":  photos,
        "limit":   limit,
        "noindex": get_lang(request) != "en",
    })


@jigsaw_router.get("/other/jigsaw/leaderboard", response_class=HTMLResponse)
def jigsaw_leaderboard_page(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse(request, "jigsaw_leaderboard.html", {
        "mode":    "other",
        "user":    get_current_user(request),
        "lang":    get_lang(request),
        "t":       get_t(request),
        "today":   today,
    })


@jigsaw_router.get("/other/jigsaw/how-to-play", response_class=HTMLResponse)
def jigsaw_howtoplay_page(request: Request):
    return templates.TemplateResponse(request, "jigsaw_howtoplay.html", {
        "mode":    "other",
        "user":    get_current_user(request),
        "lang":    get_lang(request),
        "t":       get_t(request),
    })


@jigsaw_router.get("/other/jigsaw/photo/{board_hash}", response_class=HTMLResponse)
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
    user = get_current_user(request)
    if not photo.approved:
        if not user or user.get("email") != photo.user_email:
            raise HTTPException(status_code=404, detail="Puzzle not found")
        pending_review = True
    else:
        pending_review = False
    return templates.TemplateResponse(request, "jigsaw_daily.html", {
        "mode":           "other",
        "user":           user,
        "lang":           get_lang(request),
        "t":              get_t(request),
        "today":          date.today().isoformat(),
        "image_name":     None,
        "photo_url":      f"/static/uploads/jigsaw/{photo.filename}",
        "board_hash":     board_hash,
        "display_name":   photo.display_name or "Custom Puzzle",
        "difficulty":     difficulty,
        "pending_review": pending_review,
        # Not-yet-approved puzzles are only visible to their creator — don't
        # let them get indexed while pending moderation.
        "noindex":        pending_review,
    })


# ── Jigsaw API ────────────────────────────────────────────────────────────────

@jigsaw_router.get("/api/jigsaw/daily-image")
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
        v = "".join(c for c in v if c.isprintable())
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


@jigsaw_router.post("/api/jigsaw-scores", status_code=201)
@limiter.limit("10/minute")
def submit_jigsaw_score(payload: JigsawScoreSubmit, request: Request,
                        db: Session = Depends(get_db)):
    from telemetry import record_score_submit, record_game_complete
    user = get_current_user(request)
    guest_token = get_or_create_guest_token(request, user)
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
    flag_if_profane(db, entry.__tablename__, entry.id, entry.name)
    record_score_submit("jigsaw", payload.puzzle_date)
    record_game_complete("jigsaw", mode=payload.difficulty, duration_ms=payload.time_ms)
    return {"ok": True, "id": entry.id}


@jigsaw_router.get("/api/jigsaw-scores")
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
        q = db.query(JigsawScore).filter(JigsawScore.puzzle_date == puzzle_date,
                                         JigsawScore.difficulty == difficulty)
        q = exclude_flagged(q, JigsawScore, db)
        top = q.order_by(JigsawScore.time_ms.asc(), JigsawScore.created_at.asc()).limit(LIMIT).all()
    else:
        today = date.today().isoformat()
        q = db.query(JigsawScore).filter(JigsawScore.puzzle_date == today,
                                         JigsawScore.difficulty == difficulty)
        q = exclude_flagged(q, JigsawScore, db)
        top = q.order_by(JigsawScore.time_ms.asc(), JigsawScore.created_at.asc()).limit(LIMIT).all()
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


@jigsaw_router.post("/api/jigsaw/save", status_code=200)
@limiter.limit("30/minute")
def jigsaw_save_game(payload: JigsawSavePayload, request: Request,
                     db: Session = Depends(get_db)):
    user = require_user(request)
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


@jigsaw_router.get("/api/jigsaw/resume")
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


@jigsaw_router.post("/api/jigsaw/delete-save", status_code=200)
def delete_jigsaw_save(payload: JigsawDeleteSavePayload, request: Request,
                       db: Session = Depends(get_db)):
    user = require_user(request)
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


@jigsaw_router.post("/api/jigsaw/delete-all-saves", status_code=200)
def delete_all_jigsaw_saves(request: Request, db: Session = Depends(get_db)):
    user = require_user(request)
    deleted = db.query(JigsawSavedGame).filter_by(user_email=user["email"]).delete()
    db.commit()
    return {"ok": True, "deleted": deleted}


@jigsaw_router.post("/api/jigsaw/upload", status_code=201)
@limiter.limit("20/minute")
async def upload_jigsaw_photo(
    request: Request,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    display_name: str = Form(""),
    board_hash: str = Form(...),
):
    import re
    user = require_user(request)
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
    # Filename is server-generated (UUID); board_hash stored in DB record only
    _ext_map = {"image/jpeg": ".jpg", "image/png": ".png"}
    os.makedirs(_JIGSAW_UPLOAD_DIR, exist_ok=True)
    filename = uuid.uuid4().hex + _ext_map[content_type]
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


@jigsaw_router.post("/api/jigsaw/delete-photo/{board_hash}")
def delete_jigsaw_photo(board_hash: str, request: Request, db: Session = Depends(get_db)):
    user = require_user(request)
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
