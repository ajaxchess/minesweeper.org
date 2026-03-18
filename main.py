from datetime import date
import uuid
from typing import Optional
from fastapi import FastAPI, Request, Depends, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from pydantic import BaseModel, Field, field_validator
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from database import Score, GameHistory, GameMode, RushScore, TentaizuScore, TentaizuEasyScore, CylinderScore, ToroidScore, UserProfile, get_db, init_db, SessionLocal
from duel_routes import duel_router
from duel import cleanup_old_games
from auth import oauth, get_current_user, set_session_user, clear_session, SECRET_KEY
from starlette.config import Config
from translations import get_lang, get_t
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Minesweeper")
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="127.0.0.1")
app.include_router(duel_router)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, https_only=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.globals["ga_tag"] = Config(".env")("GA_TAG", default="")

# ── SEO: robots.txt and sitemap ───────────────────────────────────────────────
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
        "Disallow: /static/\n\n"
        "Sitemap: https://minesweeper.org/sitemap.xml\n"
    )
    return PlainTextResponse(content)

@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap(request: Request):
    return templates.TemplateResponse(
        "sitemap.xml",
        {"request": request, "today": date.today().isoformat()},
        media_type="application/xml",
    )

@app.get("/ads.txt", include_in_schema=False)
async def ads_txt():
    return FileResponse("ads.txt", media_type="text/plain")

GAME_MODES = {
    "beginner":     {"rows": 9, "cols": 9, "mines": 10},
    "intermediate": {"rows": 16, "cols": 16, "mines": 40},
    "expert":       {"rows": 16, "cols": 30, "mines": 99},
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

# ── Daily score reset ─────────────────────────────────────────────────────────
def reset_scores():
    db = SessionLocal()
    try:
        deleted = db.query(Score).delete()
        db.commit()
        logger.info(f"Daily score reset complete — {deleted} rows removed.")
    except Exception as e:
        db.rollback()
        logger.error(f"Score reset failed: {e}")
    finally:
        db.close()

scheduler = BackgroundScheduler(timezone="UTC")
scheduler.add_job(reset_scores,      CronTrigger(hour=0, minute=0))   # midnight UTC
scheduler.add_job(cleanup_old_games, CronTrigger(hour="*"))             # hourly

# Create DB tables and start scheduler on startup
@app.on_event("startup")
def startup():
    init_db()
    scheduler.start()
    logger.info("Scheduler started — scores reset daily at midnight UTC.")

@app.on_event("shutdown")
def shutdown():
    scheduler.shutdown()
    logger.info("Scheduler shut down.")

# ── Page Routes ───────────────────────────────────────────────────────────────

@app.get("/set-lang")
async def set_lang(request: Request, lang: str = "en", next: Optional[str] = None):
    if lang not in ("en", "eo", "de", "es", "th", "pgl", "uk", "fr", "ko", "ja"):
        lang = "en"
    # Use explicit next param, then referer, then home
    redirect_to = next or request.headers.get("referer", "/")
    # Safety: only allow relative URLs to prevent open redirect
    if redirect_to.startswith("http"):
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

# ── Auth routes ───────────────────────────────────────────────────────────────

@app.get("/auth/login")
async def login(request: Request):
    next_url = request.query_params.get("next", "/")
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
def submit_score(payload: ScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user  = get_current_user(request)
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
        ))

    db.commit()
    db.refresh(score)
    return {"ok": True, "id": score.id}


def _enrich_with_profiles(scores: list, db) -> list:
    """Add profile_url to score dicts for entries with a user_email."""
    emails = [s.user_email for s in scores if s.user_email]
    if not emails:
        return [s.to_dict() for s in scores]

    profiles = (
        db.query(UserProfile.email, UserProfile.vanity_slug, UserProfile.public_id)
        .filter(UserProfile.email.in_(emails))
        .all()
    )
    url_map: dict = {}
    for p in profiles:
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


@app.get("/api/scores/{mode}")
def get_scores(mode: GameMode, no_guess: bool = False,
               period: str = "daily", db: Session = Depends(get_db)):
    if period not in ("daily", "season", "alltime"):
        period = "daily"

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
        q = q.filter(Score.created_at >= date.today())
        top = q.order_by(sort_key.asc(), Score.created_at.asc()).limit(15).all()
        return _enrich_with_profiles(top, db)

    if period == "season":
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
def submit_rush_score(payload: RushScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user  = get_current_user(request)
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
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
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
async def contact_page(request: Request):
    return templates.TemplateResponse("contact.html", {
        "request": request, "mode": "contact",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


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


# ── Blog ──────────────────────────────────────────────────────────────────────

# Post registry — add a new entry here for each new post.
# date:    ISO 8601 date string (YYYY-MM-DD)
# file:    path relative to the repo root
# excerpt: one-sentence summary shown on the index page
BLOG_POSTS = [
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


@app.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(request: Request, slug: str):
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
    return templates.TemplateResponse("blog_post.html", {
        "request":       request, "mode": "blog",
        "user":          get_current_user(request),
        "lang":          get_lang(request), "t": get_t(request),
        "post":          post,
        "content":       html_content,
        "author":        front_matter.get("author", ""),
        "authorurl":     front_matter.get("authorurl", ""),
        "publisher":     front_matter.get("publisher", ""),
        "og_image":      front_matter.get("image", ""),
        "date_published": date_published,
    })


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    return templates.TemplateResponse("privacy.html", {
        "request": request, "mode": "privacy",
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
        "pref_skin":     profile.pref_skin     if profile else "dark",
        "about_text":    profile.about_text    if profile else "",
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
def submit_cylinder_score(payload: CylinderScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user  = get_current_user(request)
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
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"ok": True, "id": entry.id}


@app.get("/api/cylinder-scores/{cyl_mode}")
def get_cylinder_scores(cyl_mode: str, no_guess: bool = False, period: str = "alltime",
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
        q = q.filter(CylinderScore.created_at >= date.today())
        top = q.order_by(sort_key.asc(), CylinderScore.created_at.asc()).limit(15).all()
        return _enrich_with_profiles(top, db)

    if period == "season":
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
def submit_toroid_score(payload: ToroidScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user  = get_current_user(request)
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
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"ok": True, "id": entry.id}


@app.get("/api/toroid-scores/{tor_mode}")
def get_toroid_scores(tor_mode: str, no_guess: bool = False, period: str = "alltime",
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
        q = q.filter(ToroidScore.created_at >= date.today())
        top = q.order_by(sort_key.asc(), ToroidScore.created_at.asc()).limit(15).all()
        return _enrich_with_profiles(top, db)

    if period == "season":
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
    })


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
def submit_tentaizu_score(payload: TentaizuScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user  = get_current_user(request)
    entry = TentaizuScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        puzzle_date = payload.puzzle_date,
        time_secs   = payload.time_secs,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
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
        return v.strip()


@app.post("/api/tentaizu-easy-scores", status_code=201)
def submit_tentaizu_easy_score(payload: TentaizuEasyScoreSubmit, request: Request, db: Session = Depends(get_db)):
    user  = get_current_user(request)
    entry = TentaizuEasyScore(
        name        = payload.name,
        user_email  = user["email"] if user else None,
        puzzle_date = payload.puzzle_date,
        time_secs   = payload.time_secs,
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
    for mode in ["beginner", "intermediate", "expert", "custom"]:
        scores = (
            db.query(GameHistory)
            .filter(GameHistory.user_email == email, GameHistory.mode == mode)
            .order_by(GameHistory.created_at.desc())
            .all()
        )
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
    pref_skin:     str  = 'dark'


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
    profile.pref_skin     = payload.pref_skin if payload.pref_skin in ('dark', 'classic') else 'dark'
    db.commit()
    return {"ok": True, "public_id": profile.public_id}


@app.get("/u/{slug}", response_class=HTMLResponse)
async def public_profile_page(request: Request, slug: str, db: Session = Depends(get_db)):
    # Accept either vanity slug or UUID
    profile = (
        db.query(UserProfile).filter(UserProfile.vanity_slug == slug).first()
        or db.query(UserProfile).filter(UserProfile.public_id == slug).first()
    )
    if not profile or not profile.is_public:
        raise HTTPException(status_code=404, detail="Profile not found")
    return templates.TemplateResponse("profile_public.html", {
        "request":       request,
        "mode":          "profile",
        "display_name":  profile.display_name,
        "favorite_game": profile.favorite_game or "",
        "public_id":     profile.public_id,
        "vanity_slug":   profile.vanity_slug or "",
        "about_text":    profile.about_text or "",
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
ADMIN_EMAILS = {"ajaxchess@gmail.com", "ecgero@gmail.com", "gwarpp@gmail.com"}

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
    })
