"""
duel_routes.py — Page routes and WebSocket endpoint for head-to-head duels.
Mount this router in main.py with: app.include_router(duel_router)
"""
import uuid, json, asyncio
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user
from duel import (
    create_game, get_game, manager,
    pvp_enqueue, pvp_dequeue, pvp_queue_length,
    ROWS, COLS, MINES, PVP_ROWS, PVP_COLS, PVP_MINES
)

duel_router = APIRouter()
templates   = Jinja2Templates(directory="templates")

# ── Page: create a new duel ───────────────────────────────────────────────────
@duel_router.get("/duel", response_class=HTMLResponse)
async def duel_lobby(request: Request):
    game      = create_game()
    player_id = uuid.uuid4().hex[:8]
    return templates.TemplateResponse("duel.html", {
        "request":    request,
        "game_id":    game.game_id,
        "player_id":  player_id,
        "rows":       ROWS,
        "cols":       COLS,
        "mines":      MINES,
        "mode":       "duel",
        "is_creator": True,
        "user":       get_current_user(request),   # ← added
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
        "rows":       ROWS,
        "cols":       COLS,
        "mines":      MINES,
        "mode":       "duel",
        "is_creator": is_creator,
        "user":       get_current_user(request),   # ← added
    })

# ── Page: PvP matchmaking lobby ───────────────────────────────────────────────
@duel_router.get("/pvp", response_class=HTMLResponse)
async def pvp_lobby(request: Request):
    player_id = uuid.uuid4().hex[:8]
    return templates.TemplateResponse("duel.html", {
        "request":    request,
        "game_id":    "",
        "player_id":  player_id,
        "rows":       PVP_ROWS,
        "cols":       PVP_COLS,
        "mines":      PVP_MINES,
        "mode":       "pvp",
        "is_creator": False,
        "user":       get_current_user(request),   # ← added
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
        })
        await _game_loop(ws, game, player_id)
    else:
        await _pvp_wait_loop(ws, player_id)


async def _pvp_wait_loop(ws: WebSocket, player_id: str):
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            if msg.get("type") == "reveal":
                from duel import _games
                game = next((g for g in _games.values()
                             if g.get_player(player_id)), None)
                if game:
                    await _handle_reveal(ws, game, player_id, msg)
    except WebSocketDisconnect:
        pvp_dequeue(player_id)


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
        })

    if result.get("finished"):
        scores = game.scores_payload()
        await manager.broadcast(game, {
            "type":      "game_over",
            "winner_id": result.get("winner"),
            "scores":    scores,
            "elapsed":   round(game.elapsed()),
        })


async def _game_loop(ws: WebSocket, game, player_id: str):
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            if msg.get("type") == "reveal":
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
                await manager.broadcast(game, {"type": "start", "msg": "Game started! Good luck!"})

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
