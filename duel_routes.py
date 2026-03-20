"""
duel_routes.py — Page routes and WebSocket endpoint for head-to-head duels.
Mount this router in main.py with: app.include_router(duel_router)
"""
import uuid, json, asyncio
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user
from translations import get_lang, get_t
from duel import (
    create_game, get_game, manager,
    pvp_enqueue, pvp_dequeue, pvp_queue_length,
    pvp_quick_enqueue, pvp_quick_dequeue, pvp_quick_queue_length,
    ROWS, COLS, MINES, PVP_ROWS, PVP_COLS, PVP_MINES,
    QUICK_ROWS, QUICK_COLS, QUICK_MINES,
)
from database import PvpResult, UserProfile, SessionLocal

import settings as site_settings

duel_router = APIRouter()
templates   = Jinja2Templates(directory="templates")
templates.env.globals["DEFAULT_SKIN"]         = site_settings.DEFAULT_SKIN
templates.env.globals["active_skin"]          = site_settings.active_skin
templates.env.globals["solstice_banner"]      = site_settings.solstice_banner
templates.env.globals["equinox_banner"]       = site_settings.equinox_banner
templates.env.globals["diana_birthday_banner"] = site_settings.diana_birthday_banner
templates.env.globals["ga_tag"]               = ""  # not needed in duel routes

# ── Page: create a new duel ───────────────────────────────────────────────────
@duel_router.get("/duel", response_class=HTMLResponse)
async def duel_lobby(request: Request, m: str = "standard"):
    if m == "quick":
        rows, cols, mines = QUICK_ROWS, QUICK_COLS, QUICK_MINES
    else:
        m = "standard"
        rows, cols, mines = ROWS, COLS, MINES
    game      = create_game(rows=rows, cols=cols, mines=mines, submode=m)
    player_id = uuid.uuid4().hex[:8]
    return templates.TemplateResponse("duel.html", {
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

# ── Page: join an existing duel ───────────────────────────────────────────────
@duel_router.get("/duel/{game_id}", response_class=HTMLResponse)
async def duel_join(request: Request, game_id: str):
    game = get_game(game_id)
    if not game:
        return HTMLResponse("<h2>Game not found or expired.</h2>", status_code=404)
    if game.finished:
        return HTMLResponse("<h2>This game has already ended.</h2>", status_code=410)

    player_id  = uuid.uuid4().hex[:8]
    is_creator = len(game.players) == 0

    return templates.TemplateResponse("duel.html", {
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

# ── Page: PvP matchmaking lobby ───────────────────────────────────────────────
@duel_router.get("/pvp", response_class=HTMLResponse)
async def pvp_lobby(request: Request, m: str = "standard"):
    if m == "quick":
        rows, cols, mines = QUICK_ROWS, QUICK_COLS, QUICK_MINES
    else:
        m = "standard"
        rows, cols, mines = PVP_ROWS, PVP_COLS, PVP_MINES
    player_id = uuid.uuid4().hex[:8]
    return templates.TemplateResponse("duel.html", {
        "request":    request,
        "game_id":    "",
        "player_id":  player_id,
        "rows":       rows,
        "cols":       cols,
        "mines":      mines,
        "mode":       "pvp",
        "submode":    m,
        "is_creator": False,
        "opp_delay":  site_settings.PVP_OPPONENT_BOARD_DELAY_SECS,
        "user":       get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })

# ── Page: PvP Leaderboard ─────────────────────────────────────────────────────
@duel_router.get("/pvp/leaderboard", response_class=HTMLResponse)
async def pvp_leaderboard_page(request: Request):
    return templates.TemplateResponse("pvp_leaderboard.html", {
        "request": request,
        "mode":    "pvp-leaderboard",
        "user":    get_current_user(request),
        "lang":    get_lang(request), "t": get_t(request),
    })

# ── Page: PvP Rankings ────────────────────────────────────────────────────────
@duel_router.get("/pvp/rankings", response_class=HTMLResponse)
async def pvp_rankings_page(request: Request):
    return templates.TemplateResponse("pvp_rankings.html", {
        "request": request,
        "mode":    "pvp-rankings",
        "user":    get_current_user(request),
        "lang":    get_lang(request), "t": get_t(request),
    })

# ── WebSocket: PvP matchmaking ────────────────────────────────────────────────
@duel_router.websocket("/ws/pvp/{player_id}")
async def pvp_ws(ws: WebSocket, player_id: str):
    await ws.accept()
    await ws.send_json({
        "type": "queued",
        "queue_pos": pvp_queue_length() + 1,
        "msg": "Looking for an opponent…",
    })

    game = await pvp_enqueue(player_id, ws)

    if game:
        await ws.send_json({
            "type":    "matched",
            "game_id": game.game_id,
            "msg":     "Opponent found! Get ready…",
        })
        await asyncio.sleep(3)
        game.start()
        await manager.broadcast(game, {
            "type": "start",
            "msg":  "⚔️ PvP match started! Good luck!",
            **game.start_payload(),
        })
        await _game_loop(ws, game, player_id)
    else:
        await _pvp_wait_loop(ws, player_id)


async def _pvp_wait_loop(ws: WebSocket, player_id: str):
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            mtype = msg.get("type")
            if mtype == "player_name":
                # Store the name on the PlayerState once paired into a game
                from duel import _games
                game = next((g for g in _games.values()
                             if g.get_player(player_id)), None)
                if game:
                    p = game.get_player(player_id)
                    if p:
                        p.name  = msg.get("name", "")[:32]
                        p.email = msg.get("email", "")[:256]
            elif mtype == "reveal":
                from duel import _games
                game = next((g for g in _games.values()
                             if g.get_player(player_id)), None)
                if game:
                    await _handle_reveal(ws, game, player_id, msg)
    except WebSocketDisconnect:
        pvp_dequeue(player_id)


def _calculate_elo(winner_rating: int, loser_rating: int, k: int = 32) -> tuple:
    """Return (new_winner_rating, new_loser_rating) using the Elo formula."""
    expected_winner = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
    new_winner = round(winner_rating + k * (1 - expected_winner))
    new_loser  = round(loser_rating  + k * (0 - (1 - expected_winner)))
    new_loser  = max(100, new_loser)   # floor at 100
    return new_winner, new_loser


def _save_pvp_result(game, winner_id: str):
    """Persist a completed PvP match to the database and update Elo ratings."""
    try:
        winner = game.get_player(winner_id) if winner_id else None
        loser  = game.opponent(winner_id)   if winner_id else None
        if not winner:
            return
        db = SessionLocal()
        try:
            row = PvpResult(
                winner_name  = winner.name  or "Anonymous",
                winner_email = winner.email or None,
                loser_name   = loser.name   if loser else None,
                loser_email  = loser.email  if loser else None,
                elapsed_ms   = int(game.elapsed() * 1000),
                submode      = game.submode,
                rows         = game.rows,
                cols         = game.cols,
                mines        = game.mines,
                board_hash   = game.board_hash,
            )
            db.add(row)

            # Update Elo ratings for logged-in players
            winner_profile = (
                db.query(UserProfile).filter(UserProfile.email == winner.email).first()
                if winner.email else None
            )
            loser_profile = (
                db.query(UserProfile).filter(UserProfile.email == loser.email).first()
                if loser and loser.email else None
            )
            winner_elo = winner_profile.pvp_elo if winner_profile else 1200
            loser_elo  = loser_profile.pvp_elo  if loser_profile  else 1200
            new_winner_elo, new_loser_elo = _calculate_elo(winner_elo, loser_elo)
            if winner_profile:
                winner_profile.pvp_elo = new_winner_elo
            if loser_profile:
                loser_profile.pvp_elo = new_loser_elo

            db.commit()
        finally:
            db.close()
    except Exception:
        pass  # never crash the game loop due to DB errors


async def _handle_reveal(ws, game, player_id, msg):
    if not game.active or game.finished:
        return
    r = int(msg.get("r", -1))
    c = int(msg.get("c", -1))
    if not (0 <= r < game.rows and 0 <= c < game.cols):
        return

    result = game.reveal(player_id, r, c)
    if not result:
        return

    p   = game.get_player(player_id)
    opp = game.opponent(player_id)

    await manager.send(ws, {
        "type":           "update",
        "newly_revealed": result["newly_revealed"],
        "board_values":   {
            f"{r},{c}": p.board[r][c]
            for r, c in result["newly_revealed"]
        },
        "exploded":  result.get("exploded", False),
        "score":     result["score"],
        "opp_score": opp.score if opp else 0,
        "tiles":     p.tiles_revealed,
    })

    if opp and opp.ws:
        await manager.send(opp.ws, {
            "type":         "opp_update",
            "opp_score":    result["score"],
            "opp_tiles":    p.tiles_revealed,
            "opp_exploded": result.get("exploded", False),
            "opp_cleared":  (not result.get("exploded") and
                             result.get("opp_still_alive", False)),
            # Cell values for rendering the opponent's board (client applies with delay)
            "opp_newly_revealed": [
                [row, col, p.board[row][col]]
                for row, col in result["newly_revealed"]
            ],
        })

    if result.get("finished"):
        winner_id = result.get("winner")
        scores = game.scores_payload()
        await manager.broadcast(game, {
            "type":       "game_over",
            "winner_id":  winner_id,
            "scores":     scores,
            "elapsed":    round(game.elapsed()),
            "board_hash": game.board_hash,
        })
        if game.is_pvp and winner_id:
            _save_pvp_result(game, winner_id)


async def _game_loop(ws: WebSocket, game, player_id: str):
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            mtype = msg.get("type")
            if mtype == "player_name":
                p = game.get_player(player_id)
                if p:
                    p.name  = msg.get("name", "")[:32]
                    p.email = msg.get("email", "")[:256]
            elif mtype == "reveal":
                await _handle_reveal(ws, game, player_id, msg)
    except WebSocketDisconnect:
        p = game.get_player(player_id)
        if p:
            p.ws = None
        opp = game.opponent(player_id)
        if opp and opp.ws and not game.finished:
            await manager.send(opp.ws, {
                "type": "opp_disconnected",
                "msg":  "Your opponent disconnected.",
            })

# ── WebSocket: Quick PvP matchmaking ─────────────────────────────────────────
@duel_router.websocket("/ws/pvp/quick/{player_id}")
async def pvp_quick_ws(ws: WebSocket, player_id: str):
    await ws.accept()
    await ws.send_json({
        "type": "queued",
        "queue_pos": pvp_quick_queue_length() + 1,
        "msg": "Looking for an opponent…",
    })

    game = await pvp_quick_enqueue(player_id, ws)

    if game:
        await ws.send_json({
            "type":    "matched",
            "game_id": game.game_id,
            "msg":     "Opponent found! Get ready…",
        })
        await asyncio.sleep(3)
        game.start()
        await manager.broadcast(game, {
            "type": "start",
            "msg":  "⚔️ Quick PvP match started! Good luck!",
            **game.start_payload(),
        })
        await _game_loop(ws, game, player_id)
    else:
        await _pvp_quick_wait_loop(ws, player_id)


async def _pvp_quick_wait_loop(ws: WebSocket, player_id: str):
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            mtype = msg.get("type")
            if mtype == "player_name":
                from duel import _games
                game = next((g for g in _games.values()
                             if g.get_player(player_id)), None)
                if game:
                    p = game.get_player(player_id)
                    if p:
                        p.name  = msg.get("name", "")[:32]
                        p.email = msg.get("email", "")[:256]
            elif mtype == "reveal":
                from duel import _games
                game = next((g for g in _games.values()
                             if g.get_player(player_id)), None)
                if game:
                    await _handle_reveal(ws, game, player_id, msg)
    except WebSocketDisconnect:
        pvp_quick_dequeue(player_id)


@duel_router.websocket("/ws/{game_id}/{player_id}")
async def duel_ws(ws: WebSocket, game_id: str, player_id: str):
    game = get_game(game_id)
    if not game:
        await ws.close(code=4004)
        return

    await ws.accept()

    if not game.add_player(player_id, ws):
        await ws.send_json({"type": "error", "msg": "Game is full."})
        await ws.close(code=4003)
        return

    role = "creator" if game.players[0].player_id == player_id else "challenger"

    await manager.send(ws, {
        "type": "connected",
        "role": role,
        "msg":  "Waiting for opponent…" if not game.both_connected() else "Opponent connected!",
    })

    if game.both_connected():
        creator_id = game.players[0].player_id
        for p in game.players:
            await manager.send(p.ws, {
                "type":       "ready",
                "creator_id": creator_id,
                "msg":        "Both players connected! Waiting for creator to start…",
            })

    try:
        while True:
            raw  = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            mtype = msg.get("type")

            if mtype == "start":
                creator = game.players[0]
                if player_id != creator.player_id or game.active:
                    continue
                game.start()
                await manager.broadcast(game, {
                    "type": "start",
                    "msg":  "Game started! Good luck!",
                    **game.start_payload(),
                })

            elif mtype == "player_name":
                p = game.get_player(player_id)
                if p:
                    p.name  = msg.get("name", "")[:32]
                    p.email = msg.get("email", "")[:256]

            elif mtype == "reveal":
                await _handle_reveal(ws, game, player_id, msg)

    except WebSocketDisconnect:
        p = game.get_player(player_id)
        if p:
            p.ws = None
        opp = game.opponent(player_id)
        if opp and opp.ws and not game.finished:
            await manager.send(opp.ws, {
                "type": "opp_disconnected",
                "msg":  "Your opponent disconnected.",
            })
