"""
duel_routes.py — Page routes and WebSocket endpoint for head-to-head duels.
Mount this router in main.py with: app.include_router(duel_router)
"""
import uuid, json
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from duel import (
    create_game, get_game, manager,
    ROWS, COLS, MINES
)

duel_router = APIRouter()
templates   = Jinja2Templates(directory="templates")

# ── Page: create a new duel ───────────────────────────────────────────────────
@duel_router.get("/duel", response_class=HTMLResponse)
async def duel_lobby(request: Request):
    game      = create_game()
    player_id = uuid.uuid4().hex[:8]
    return templates.TemplateResponse("duel.html", {
        "request":   request,
        "game_id":   game.game_id,
        "player_id": player_id,
        "rows":      ROWS,
        "cols":      COLS,
        "mines":     MINES,
        "mode":      "duel",
        "is_creator": True,
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
    is_creator = len(game.players) == 0   # edge case: direct link before creator WS connects

    return templates.TemplateResponse("duel.html", {
        "request":    request,
        "game_id":    game_id,
        "player_id":  player_id,
        "rows":       ROWS,
        "cols":       COLS,
        "mines":      MINES,
        "mode":       "duel",
        "is_creator": is_creator,
    })

# ── WebSocket endpoint ────────────────────────────────────────────────────────
@duel_router.websocket("/ws/{game_id}/{player_id}")
async def duel_ws(ws: WebSocket, game_id: str, player_id: str):
    game = get_game(game_id)
    if not game:
        await ws.close(code=4004)
        return

    await ws.accept()

    # Register this player
    if not game.add_player(player_id, ws):
        await ws.send_json({"type": "error", "msg": "Game is full."})
        await ws.close(code=4003)
        return

    # Determine role labels
    role = "creator" if game.players[0].player_id == player_id else "challenger"

    # Notify the newly connected player
    await manager.send(ws, {
        "type":   "connected",
        "role":   role,
        "msg":    "Waiting for opponent…" if not game.both_connected() else "Opponent connected!",
    })

    # If both are now connected, notify everyone
    if game.both_connected():
        creator_id = game.players[0].player_id
        for p in game.players:
            await manager.send(p.ws, {
                "type":       "ready",
                "creator_id": creator_id,
                "msg":        "Both players connected! Waiting for creator to start…",
            })

    # ── Message loop ─────────────────────────────────────────────────────────
    try:
        while True:
            raw  = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            mtype = msg.get("type")

            # ── Start game (creator only) ─────────────────────────────────
            if mtype == "start":
                creator = game.players[0]
                if player_id != creator.player_id or game.active:
                    continue
                game.start()
                await manager.broadcast(game, {"type": "start", "msg": "Game started! Good luck!"})

            # ── Reveal a cell ─────────────────────────────────────────────
            elif mtype == "reveal":
                if not game.active or game.finished:
                    continue
                r = int(msg.get("r", -1))
                c = int(msg.get("c", -1))
                if not (0 <= r < ROWS and 0 <= c < COLS):
                    continue

                result = game.reveal(player_id, r, c)
                if not result:
                    continue

                p   = game.get_player(player_id)
                opp = game.opponent(player_id)

                # Send the acting player their board update
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

                # Send opponent a score-only update (they don't see your board)
                if opp and opp.ws:
                    await manager.send(opp.ws, {
                        "type":      "opp_update",
                        "opp_score": result["score"],
                        "opp_tiles": p.tiles_revealed,
                        # Alert opponent if this player just exploded or cleared
                        "opp_exploded": result.get("exploded", False),
                        "opp_cleared":  (not result.get("exploded") and
                                         result.get("opp_still_alive", False)),
                    })

                # Broadcast game-over if finished
                if result.get("finished"):
                    winner_id = result.get("winner")
                    scores    = game.scores_payload()
                    await manager.broadcast(game, {
                        "type":      "game_over",
                        "winner_id": winner_id,
                        "scores":    scores,
                        "elapsed":   round(game.elapsed()),
                    })

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
