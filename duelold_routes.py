"""
duelold_routes.py — Copy of the /duel page served at /duelold.
Not linked from the main site navigation.
"""
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user
from translations import get_lang, get_t
from duel import (
    create_game, get_game,
    ROWS, COLS, MINES, QUICK_ROWS, QUICK_COLS, QUICK_MINES,
)
import settings as site_settings
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs

duelold_router = APIRouter()

templates = Jinja2Templates(directory="templates")
templates.env.globals["DEFAULT_SKIN"]          = site_settings.DEFAULT_SKIN
templates.env.globals["active_skin"]           = site_settings.active_skin
templates.env.globals["solstice_banner"]       = site_settings.solstice_banner
templates.env.globals["equinox_banner"]        = site_settings.equinox_banner
templates.env.globals["diana_birthday_banner"] = site_settings.diana_birthday_banner
templates.env.globals["ga_tag"]                = ""
templates.env.globals["get_breadcrumbs"]       = _get_breadcrumbs


@duelold_router.get("/duelold", response_class=HTMLResponse)
async def duelold_lobby(request: Request, m: str = "standard"):
    if m == "quick":
        rows, cols, mines = QUICK_ROWS, QUICK_COLS, QUICK_MINES
    else:
        m = "standard"
        rows, cols, mines = ROWS, COLS, MINES
    game      = create_game(rows=rows, cols=cols, mines=mines, submode=m)
    player_id = uuid.uuid4().hex[:8]
    return templates.TemplateResponse("duelold.html", {
        "request":    request,
        "game_id":    game.game_id,
        "player_id":  player_id,
        "rows":       rows,
        "cols":       cols,
        "mines":      mines,
        "mode":       "duel",
        "submode":    m,
        "is_creator": True,
        "opp_delay":  site_settings.PVP_OPPONENT_BOARD_DELAY_SECS,
        "user":       get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })


@duelold_router.get("/duelold/{game_id}", response_class=HTMLResponse)
async def duelold_join(request: Request, game_id: str):
    game = get_game(game_id)
    if not game:
        return templates.TemplateResponse("duel_error.html", {
            "request": request, "lang": get_lang(request), "t": get_t(request),
            "code": 404, "title": "Game not found",
            "message": "This duel has expired or never existed. Games are kept for 2 hours.",
        }, status_code=404)
    if game.finished:
        return templates.TemplateResponse("duel_error.html", {
            "request": request, "lang": get_lang(request), "t": get_t(request),
            "code": 410, "title": "Game already ended",
            "message": "This duel has already finished. Start a new one!",
        }, status_code=410)

    player_id  = uuid.uuid4().hex[:8]
    is_creator = len(game.players) == 0

    return templates.TemplateResponse("duelold.html", {
        "request":    request,
        "game_id":    game_id,
        "player_id":  player_id,
        "rows":       game.rows,
        "cols":       game.cols,
        "mines":      game.mines,
        "mode":       "duel",
        "submode":    game.submode,
        "is_creator": is_creator,
        "opp_delay":  site_settings.PVP_OPPONENT_BOARD_DELAY_SECS,
        "user":       get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })
