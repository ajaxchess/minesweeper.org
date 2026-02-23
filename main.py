from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from database import Score, GameMode, get_db, init_db

app = FastAPI(title="Minesweeper")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

GAME_MODES = {
    "beginner":     {"rows": 10, "cols": 10, "mines": 10},
    "intermediate": {"rows": 16, "cols": 16, "mines": 40},
    "expert":       {"rows": 16, "cols": 30, "mines": 99},
}

# Create DB tables on startup
@app.on_event("startup")
def startup():
    init_db()

# ── Page Routes ───────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, "mode": "beginner", **GAME_MODES["beginner"]
    })

@app.get("/intermediate", response_class=HTMLResponse)
async def intermediate(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, "mode": "intermediate", **GAME_MODES["intermediate"]
    })

@app.get("/expert", response_class=HTMLResponse)
async def expert(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, "mode": "expert", **GAME_MODES["expert"]
    })

@app.get("/custom", response_class=HTMLResponse)
async def custom(request: Request):
    return templates.TemplateResponse("custom.html", {
        "request": request, "mode": "custom"
    })

@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(request: Request):
    return templates.TemplateResponse("leaderboard.html", {
        "request": request, "mode": "leaderboard"
    })

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
def submit_score(payload: ScoreSubmit, db: Session = Depends(get_db)):
    score = Score(
        name      = payload.name,
        mode      = payload.mode,
        time_secs = payload.time_secs,
        rows      = payload.rows,
        cols      = payload.cols,
        mines     = payload.mines,
    )
    db.add(score)
    db.commit()
    db.refresh(score)
    return {"ok": True, "id": score.id}


@app.get("/api/scores/{mode}")
def get_scores(mode: GameMode, db: Session = Depends(get_db)):
    top = (
        db.query(Score)
        .filter(Score.mode == mode)
        .order_by(Score.time_secs.asc(), Score.created_at.asc())
        .limit(15)
        .all()
    )
    return [s.to_dict() for s in top]
