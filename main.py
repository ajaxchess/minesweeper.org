from datetime import date
from fastapi import FastAPI, Request, Depends, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from database import Score, GameHistory, GameMode, RushScore, TentaizuScore, CylinderScore, ToroidScore, UserProfile, get_db, init_db, SessionLocal
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
    "beginner":     {"rows": 10, "cols": 10, "mines": 10},
    "intermediate": {"rows": 16, "cols": 16, "mines": 40},
    "expert":       {"rows": 16, "cols": 30, "mines": 99},
}

CYLINDER_MODES = {
    "cylinder-beginner":     {"rows": 10, "cols": 10, "mines": 10},
    "cylinder-intermediate": {"rows": 16, "cols": 16, "mines": 40},
    "cylinder-expert":       {"rows": 16, "cols": 30, "mines": 99},
}

TOROID_MODES = {
    "toroid-beginner":     {"rows": 10, "cols": 10, "mines": 10},
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
async def set_lang(request: Request, lang: str = "en"):
    from fastapi.responses import Response
    if lang not in ("en", "eo", "de", "es", "th", "pgl", "uk", "fr"):
        lang = "en"
    next_url = request.headers.get("referer", "/")
    response = RedirectResponse(url=next_url)
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
            profile = UserProfile(email=email, display_name=user.get("name", "")[:32])
            db.add(profile)
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
    name:      str = Field(..., min_length=1, max_length=32)
    mode:      GameMode
    time_secs: int = Field(..., ge=1, le=999)
    rows:      int = Field(..., ge=5,  le=30)
    cols:      int = Field(..., ge=5,  le=50)
    mines:     int = Field(..., ge=1,  le=999)

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
        name       = payload.name,
        user_email = user["email"] if user else None,
        mode       = payload.mode,
        time_secs  = payload.time_secs,
        rows       = payload.rows,
        cols       = payload.cols,
        mines      = payload.mines,
    )
    db.add(score)

    # Persist permanent history for logged-in users
    if user:
        db.add(GameHistory(
            user_email = user["email"],
            name       = payload.name,
            mode       = payload.mode,
            time_secs  = payload.time_secs,
            rows       = payload.rows,
            cols       = payload.cols,
            mines      = payload.mines,
        ))

    db.commit()
    db.refresh(score)
    return {"ok": True, "id": score.id}


@app.get("/api/scores/{mode}")
def get_scores(mode: GameMode, db: Session = Depends(get_db)):
    today = date.today()
    top = (
        db.query(Score)
        .filter(Score.mode == mode, Score.created_at >= today)
        .order_by(Score.time_secs.asc(), Score.created_at.asc())
        .limit(15)
        .all()
    )
    return [s.to_dict() for s in top]


@app.get("/rush", response_class=HTMLResponse)
async def rush(request: Request):
    return templates.TemplateResponse("rush.html", {
        "request": request, "mode": "rush",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


# ── Rush Leaderboard API ───────────────────────────────────────────────────────

RUSH_MODES_VALID = {"easy", "normal", "hard"}

class RushScoreSubmit(BaseModel):
    name:          str = Field(..., min_length=1, max_length=32)
    rush_mode:     str = Field(..., pattern="^(easy|normal|hard)$")
    score:         int = Field(..., ge=0, le=9_999_999)   # elapsed + cleared_mines*5
    cleared_mines: int = Field(..., ge=0, le=99999)
    time_secs:     int = Field(..., ge=1, le=99999)
    cols:          int = Field(..., ge=9, le=30)

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
        time_secs     = payload.time_secs,
        cols          = payload.cols,
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
    return [s.to_dict() for s in top]


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
async def profile_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth/login")
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "mode":    "profile",
        "user":    user,
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
    name:      str = Field(..., min_length=1, max_length=32)
    cyl_mode:  str = Field(..., pattern="^(easy|intermediate|expert|custom)$")
    time_secs: int = Field(..., ge=1, le=999)
    rows:      int = Field(..., ge=5,  le=30)
    cols:      int = Field(..., ge=5,  le=50)
    mines:     int = Field(..., ge=1,  le=999)

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
        name       = payload.name,
        user_email = user["email"] if user else None,
        cyl_mode   = payload.cyl_mode,
        time_secs  = payload.time_secs,
        rows       = payload.rows,
        cols       = payload.cols,
        mines      = payload.mines,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"ok": True, "id": entry.id}


@app.get("/api/cylinder-scores/{cyl_mode}")
def get_cylinder_scores(cyl_mode: str, db: Session = Depends(get_db)):
    if cyl_mode not in CYLINDER_MODES_VALID:
        raise HTTPException(status_code=400, detail="Invalid mode")
    top = (
        db.query(CylinderScore)
        .filter(CylinderScore.cyl_mode == cyl_mode)
        .order_by(CylinderScore.time_secs.asc(), CylinderScore.created_at.asc())
        .limit(15)
        .all()
    )
    return [s.to_dict() for s in top]


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
    name:      str = Field(..., min_length=1, max_length=32)
    tor_mode:  str = Field(..., pattern="^(easy|intermediate|expert|custom)$")
    time_secs: int = Field(..., ge=1, le=999)
    rows:      int = Field(..., ge=5,  le=30)
    cols:      int = Field(..., ge=5,  le=50)
    mines:     int = Field(..., ge=1,  le=999)

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
        name       = payload.name,
        user_email = user["email"] if user else None,
        tor_mode   = payload.tor_mode,
        time_secs  = payload.time_secs,
        rows       = payload.rows,
        cols       = payload.cols,
        mines      = payload.mines,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"ok": True, "id": entry.id}


@app.get("/api/toroid-scores/{tor_mode}")
def get_toroid_scores(tor_mode: str, db: Session = Depends(get_db)):
    if tor_mode not in TOROID_MODES_VALID:
        raise HTTPException(status_code=400, detail="Invalid mode")
    top = (
        db.query(ToroidScore)
        .filter(ToroidScore.tor_mode == tor_mode)
        .order_by(ToroidScore.time_secs.asc(), ToroidScore.created_at.asc())
        .limit(15)
        .all()
    )
    return [s.to_dict() for s in top]


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
    return [s.to_dict() for s in top]


@app.get("/api/profile/stats")
def profile_stats(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)

    email  = user["email"]
    modes  = ["beginner", "intermediate", "expert", "custom"]
    stats  = {}

    for mode in modes:
        scores = (
            db.query(GameHistory)
            .filter(GameHistory.user_email == email, GameHistory.mode == mode)
            .order_by(GameHistory.created_at.desc())
            .all()
        )
        if not scores:
            stats[mode] = None
            continue
        times      = [s.time_secs for s in scores]
        stats[mode] = {
            "games_played": len(scores),
            "best_time":    min(times),
            "avg_time":     round(sum(times) / len(times), 1),
            "worst_time":   max(times),
            "recent":       [s.to_dict() for s in scores[:10]],
        }

    # Rush stats
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
            "games_played":  len(rush_scores),
            "best_score":    max(scores_list),
            "avg_score":     round(sum(scores_list) / len(scores_list), 1),
            "total_mines":   sum(mines_list),
            "recent":        [s.to_dict() for s in rush_scores[:10]],
        }
    else:
        stats["rush"] = None

    # Tentaizu stats
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
