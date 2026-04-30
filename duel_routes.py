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
    pvpbeta_enqueue, pvpbeta_dequeue, pvpbeta_queue_length,
    pvpbeta_quick_enqueue, pvpbeta_quick_dequeue, pvpbeta_quick_queue_length,
    ROWS, COLS, MINES, PVP_ROWS, PVP_COLS, PVP_MINES,
    QUICK_ROWS, QUICK_COLS, QUICK_MINES,
)
from database import PvpResult, UserProfile, SessionLocal

import settings as site_settings
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs

duel_router = APIRouter()

# Fixed identities for the three bot difficulty levels
BOT_EMAILS = {
    "easy":   "bot-easy@bot.minesweeper.org",
    "medium": "bot-medium@bot.minesweeper.org",
    "hard":   "bot-hard@bot.minesweeper.org",
}
BOT_NAMES = {
    "easy":   "🤖 Bot (Easy)",
    "medium": "🤖 Bot (Medium)",
    "hard":   "🤖 Bot (Hard)",
}
templates   = Jinja2Templates(directory="templates")
templates.env.globals["DEFAULT_SKIN"]         = site_settings.DEFAULT_SKIN
templates.env.globals["active_skin"]          = site_settings.active_skin
templates.env.globals["solstice_banner"]      = site_settings.solstice_banner
templates.env.globals["equinox_banner"]       = site_settings.equinox_banner
templates.env.globals["diana_birthday_banner"] = site_settings.diana_birthday_banner
templates.env.globals["ga_tag"]               = ""  # not needed in duel routes
templates.env.globals["get_breadcrumbs"]      = _get_breadcrumbs

# ── Page: duel lobby — creates a private room for the creator ─────────────────
@duel_router.get("/duel", response_class=HTMLResponse)
async def duel_lobby(request: Request, m: str = "standard"):
    if m == "quick":
        rows, cols, mines = QUICK_ROWS, QUICK_COLS, QUICK_MINES
    else:
        m = "standard"
        rows, cols, mines = PVP_ROWS, PVP_COLS, PVP_MINES
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

# ── Page: /duel/{game_id} — challenger joins an existing room ─────────────────
@duel_router.get("/duel/{game_id}", response_class=HTMLResponse)
async def duel_join(request: Request, game_id: str):
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
        "mode":       "pvp-beta",
        "submode":    m,
        "is_creator": False,
        "opp_delay":  site_settings.PVP_OPPONENT_BOARD_DELAY_SECS,
        "user":       get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })

# ── Page: PvP vs Bot lobby (difficulty picker) ────────────────────────────────
@duel_router.get("/pvp/bot", response_class=HTMLResponse)
async def pvp_bot_lobby(request: Request):
    return templates.TemplateResponse("pvp_bot_lobby.html", {
        "request": request,
        "user":    get_current_user(request),
        "lang":    get_lang(request), "t": get_t(request),
    })


# ── Page: PvP vs Bot game ──────────────────────────────────────────────────────
@duel_router.get("/pvp/bot/play", response_class=HTMLResponse)
async def pvp_bot_play(request: Request, d: str = "medium", m: str = "standard"):
    d = d if d in ("easy", "medium", "hard") else "medium"
    if m == "quick":
        rows, cols, mines = QUICK_ROWS, QUICK_COLS, QUICK_MINES
    else:
        m = "standard"
        rows, cols, mines = PVP_ROWS, PVP_COLS, PVP_MINES
    player_id = uuid.uuid4().hex[:8]
    return templates.TemplateResponse("duel.html", {
        "request":        request,
        "game_id":        "",
        "player_id":      player_id,
        "rows":           rows,
        "cols":           cols,
        "mines":          mines,
        "mode":           "pvp-bot",
        "submode":        m,
        "bot_difficulty": d,
        "is_creator":     False,
        "opp_delay":      site_settings.PVP_OPPONENT_BOARD_DELAY_SECS,
        "user":           get_current_user(request),
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

    # F71: mine hit realloc — different message type, no game-over
    if result.get("mine_hit"):
        await manager.send(ws, {
            "type":           "mine_hit",
            "r":              result["r"],
            "c":              result["c"],
            "reset_cells":    result["reset_cells"],
            "updated_values": result["updated_values"],
            "mine_hits":      result["mine_hits"],
            "score":          result["score"],
            "tiles":          result["tiles"],
            "opp_score":      opp.score if opp else 0,
        })
        if opp and opp.ws:
            await manager.send(opp.ws, {
                "type":        "opp_mine_hit",
                "r":           result["r"],
                "c":           result["c"],
                "reset_cells": result["reset_cells"],
                "mine_hits":   result["mine_hits"],
                "opp_score":   result["score"],
                "opp_tiles":   result["tiles"],
            })
        return

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

    # Notify spectators of the cell reveal
    if game.spectators:
        spec_msg = {
            "type":           "spec_update",
            "player_id":      player_id,
            "newly_revealed": result["newly_revealed"],
            "board_values":   {
                f"{r},{c}": p.board[r][c]
                for r, c in result["newly_revealed"]
            },
            "score":    result["score"],
            "tiles":    p.tiles_revealed,
            "exploded": result.get("exploded", False),
        }
        for sw in list(game.spectators):
            await manager.send(sw, spec_msg)

    if result.get("finished"):
        winner_id = result.get("winner")
        scores = game.scores_payload()
        await manager.broadcast(game, {
            "type":       "game_over",
            "winner_id":  winner_id,
            "scores":     scores,
            "elapsed":    round(game.elapsed()),
            "board_hash": game.board_hash,
            "rows":       game.rows,
            "cols":       game.cols,
            "mines":      game.mines,
        })
        if game.is_pvp and winner_id:
            _save_pvp_result(game, winner_id)


async def _run_bot(game, bot_id: str, difficulty: str) -> None:
    """Drive the bot player through a game.  Runs as a background asyncio task."""
    from bots.minesweeper_bot import MinesweeperBot

    # Wait for game to start (or abort)
    while not game.active and not game.finished:
        await asyncio.sleep(0.05)
    if game.finished:
        return

    bot_state = game.get_player(bot_id)
    ai = MinesweeperBot(game.rows, game.cols, game.mines, difficulty)

    # Seed the AI with the shared pre-revealed cells
    for r, c in game.shared_prerev:
        ai.apply_reveal(r, c, game.shared_board[r][c])

    delay = ai.move_delay()

    while not game.finished:
        await asyncio.sleep(delay)
        if game.finished:
            break

        move = ai.next_move()
        if move is None:
            break

        r, c = move
        result = game.reveal(bot_id, r, c)
        if not result:
            continue

        # Update the AI's board knowledge from newly revealed cells
        for nr, nc in result.get("newly_revealed", []):
            ai.apply_reveal(nr, nc, bot_state.board[nr][nc])

        # Notify spectators of bot move
        if game.spectators:
            spec_msg = {
                "type":           "spec_update",
                "player_id":      bot_id,
                "newly_revealed": result.get("newly_revealed", []),
                "board_values":   {
                    f"{nr},{nc}": bot_state.board[nr][nc]
                    for nr, nc in result.get("newly_revealed", [])
                },
                "score":    bot_state.score,
                "tiles":    bot_state.tiles_revealed,
                "exploded": result.get("exploded", False),
            }
            for sw in list(game.spectators):
                await manager.send(sw, spec_msg)

        # Forward opp_update to the human player
        human = game.opponent(bot_id)
        if human and human.ws:
            await manager.send(human.ws, {
                "type":               "opp_update",
                "opp_score":          bot_state.score,
                "opp_tiles":          bot_state.tiles_revealed,
                "opp_exploded":       result.get("exploded", False),
                "opp_cleared":        (not result.get("exploded") and
                                       result.get("opp_still_alive", False)),
                "opp_newly_revealed": [
                    [nr, nc, bot_state.board[nr][nc]]
                    for nr, nc in result.get("newly_revealed", [])
                ],
            })

        if result.get("finished"):
            winner_id = result.get("winner")
            scores    = game.scores_payload()
            await manager.broadcast(game, {
                "type":       "game_over",
                "winner_id":  winner_id,
                "scores":     scores,
                "elapsed":    round(game.elapsed()),
                "board_hash": game.board_hash,
                "rows":       game.rows,
                "cols":       game.cols,
                "mines":      game.mines,
            })
            if winner_id:
                _save_pvp_result(game, winner_id)
            break


# ── WebSocket: vs Bot ─────────────────────────────────────────────────────────
@duel_router.websocket("/ws/pvp/bot/{player_id}")
async def pvp_bot_ws(ws: WebSocket, player_id: str,
                     d: str = "medium", m: str = "standard"):
    d = d if d in ("easy", "medium", "hard") else "medium"
    if m == "quick":
        rows, cols, mines, submode = QUICK_ROWS, QUICK_COLS, QUICK_MINES, "quick"
    else:
        rows, cols, mines, submode = PVP_ROWS, PVP_COLS, PVP_MINES, "standard"

    await ws.accept()

    # Create a game and add the human immediately
    game = create_game(rows=rows, cols=cols, mines=mines, submode=submode, is_pvp=True)
    game.add_player(player_id, ws)

    # Add a bot player (ws=None — it plays via _run_bot coroutine)
    bot_id = "bot_" + uuid.uuid4().hex[:6]
    game.add_player(bot_id, None)
    bot_p = game.get_player(bot_id)
    bot_p.name  = BOT_NAMES[d]
    bot_p.email = BOT_EMAILS[d]

    await ws.send_json({
        "type":    "matched",
        "game_id": game.game_id,
        "msg":     f"Bot opponent ready! ({d.capitalize()} difficulty) Get ready…",
    })

    await asyncio.sleep(3)
    game.start()
    await manager.broadcast(game, {
        "type": "start",
        "msg":  f"⚔️ vs Bot ({d.capitalize()}) — Good luck!",
        **game.start_payload(),
    })

    asyncio.create_task(_run_bot(game, bot_id, d))

    await _game_loop(ws, game, player_id)


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
                    opp = game.opponent(player_id)
                    if opp and opp.ws:
                        await manager.send(opp.ws, {"type": "opp_name", "name": p.name or "Anonymous"})
            elif mtype == "reveal":
                await _handle_reveal(ws, game, player_id, msg)
            elif mtype == "chat":
                text = msg.get("text", "").strip()[:200]
                if text:
                    p = game.get_player(player_id)
                    from_name = (p.name or "Anonymous") if p else "Anonymous"
                    await manager.broadcast(game, {
                        "type": "chat",
                        "from": from_name,
                        "pid":  player_id,
                        "text": text,
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


# ── PvP Beta: hidden routes for live user testing ─────────────────────────────
# Not linked from the main site. Uses isolated queues; results not saved to DB.

@duel_router.get("/pvpbeta", response_class=HTMLResponse)
async def pvpbeta_lobby(request: Request, m: str = "standard"):
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
        "mode":       "pvp-beta",
        "submode":    m,
        "is_creator": False,
        "opp_delay":  site_settings.PVP_OPPONENT_BOARD_DELAY_SECS,
        "user":       get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })

@duel_router.get("/pvpbeta/bot", response_class=HTMLResponse)
async def pvpbeta_bot_lobby(request: Request):
    return templates.TemplateResponse("pvpbeta_bot_lobby.html", {
        "request": request,
        "user":    get_current_user(request),
        "lang":    get_lang(request), "t": get_t(request),
    })

@duel_router.get("/pvpbeta/bot/play", response_class=HTMLResponse)
async def pvpbeta_bot_play(request: Request, d: str = "medium", m: str = "standard"):
    d = d if d in ("easy", "medium", "hard") else "medium"
    if m == "quick":
        rows, cols, mines = QUICK_ROWS, QUICK_COLS, QUICK_MINES
    else:
        m = "standard"
        rows, cols, mines = PVP_ROWS, PVP_COLS, PVP_MINES
    player_id = uuid.uuid4().hex[:8]
    return templates.TemplateResponse("duel.html", {
        "request":        request,
        "game_id":        "",
        "player_id":      player_id,
        "rows":           rows,
        "cols":           cols,
        "mines":          mines,
        "mode":           "pvp-bot-beta",
        "submode":        m,
        "bot_difficulty": d,
        "is_creator":     False,
        "opp_delay":      site_settings.PVP_OPPONENT_BOARD_DELAY_SECS,
        "user":           get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
    })

@duel_router.websocket("/ws/pvpbeta/{player_id}")
async def pvpbeta_ws(ws: WebSocket, player_id: str):
    await ws.accept()
    await ws.send_json({
        "type": "queued",
        "queue_pos": pvpbeta_queue_length() + 1,
        "msg": "Looking for an opponent…",
    })

    game = await pvpbeta_enqueue(player_id, ws)

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
            "msg":  "⚔️ PvP Beta match started! Good luck!",
            **game.start_payload(),
        })
        await _game_loop(ws, game, player_id)
    else:
        await _pvpbeta_wait_loop(ws, player_id)


async def _pvpbeta_wait_loop(ws: WebSocket, player_id: str):
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
                        opp = game.opponent(player_id)
                        if opp and opp.ws:
                            public_id = None
                            if p.email:
                                db = SessionLocal()
                                try:
                                    prof = db.query(UserProfile).filter(UserProfile.email == p.email).first()
                                    public_id = prof.public_id if prof else None
                                finally:
                                    db.close()
                            await manager.send(opp.ws, {
                                "type": "opp_name",
                                "name": p.name or "Anonymous",
                                "public_id": public_id,
                            })
    except WebSocketDisconnect:
        pvpbeta_dequeue(player_id)


@duel_router.websocket("/ws/pvpbeta/quick/{player_id}")
async def pvpbeta_quick_ws(ws: WebSocket, player_id: str):
    await ws.accept()
    await ws.send_json({
        "type": "queued",
        "queue_pos": pvpbeta_quick_queue_length() + 1,
        "msg": "Looking for an opponent…",
    })

    game = await pvpbeta_quick_enqueue(player_id, ws)

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
            "msg":  "⚔️ Quick PvP Beta match started! Good luck!",
            **game.start_payload(),
        })
        await _game_loop(ws, game, player_id)
    else:
        await _pvpbeta_quick_wait_loop(ws, player_id)


async def _pvpbeta_quick_wait_loop(ws: WebSocket, player_id: str):
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
                        opp = game.opponent(player_id)
                        if opp and opp.ws:
                            public_id = None
                            if p.email:
                                db = SessionLocal()
                                try:
                                    prof = db.query(UserProfile).filter(UserProfile.email == p.email).first()
                                    public_id = prof.public_id if prof else None
                                finally:
                                    db.close()
                            await manager.send(opp.ws, {
                                "type": "opp_name",
                                "name": p.name or "Anonymous",
                                "public_id": public_id,
                            })
    except WebSocketDisconnect:
        pvpbeta_quick_dequeue(player_id)


@duel_router.websocket("/ws/pvpbeta/bot/{player_id}")
async def pvpbeta_bot_ws(ws: WebSocket, player_id: str,
                         d: str = "medium", m: str = "standard"):
    d = d if d in ("easy", "medium", "hard") else "medium"
    if m == "quick":
        rows, cols, mines, submode = QUICK_ROWS, QUICK_COLS, QUICK_MINES, "quick"
    else:
        rows, cols, mines, submode = PVP_ROWS, PVP_COLS, PVP_MINES, "standard"

    await ws.accept()

    game = create_game(rows=rows, cols=cols, mines=mines, submode=submode, is_pvp=False, use_frontier=True)
    game.add_player(player_id, ws)

    bot_id = "bot_" + uuid.uuid4().hex[:6]
    game.add_player(bot_id, None)
    bot_p = game.get_player(bot_id)
    bot_p.name  = BOT_NAMES[d]
    bot_p.email = BOT_EMAILS[d]

    await ws.send_json({
        "type":    "matched",
        "game_id": game.game_id,
        "msg":     f"Bot opponent ready! ({d.capitalize()} difficulty) Get ready…",
    })

    await asyncio.sleep(3)
    game.start()
    await manager.broadcast(game, {
        "type": "start",
        "msg":  f"⚔️ vs Bot ({d.capitalize()}) — Good luck!",
        **game.start_payload(),
    })

    asyncio.create_task(_run_bot(game, bot_id, d))
    await _game_loop(ws, game, player_id)


# ── Page: spectate an existing duel ──────────────────────────────────────────
@duel_router.get("/duel/{game_id}/watch", response_class=HTMLResponse)
async def duel_watch(request: Request, game_id: str):
    game = get_game(game_id)
    if not game:
        return templates.TemplateResponse("duel_error.html", {
            "request": request, "lang": get_lang(request), "t": get_t(request),
            "code": 404, "title": "Game not found",
            "message": "This duel has expired or never existed. Games are kept for 2 hours.",
        }, status_code=404)
    spec_id = uuid.uuid4().hex[:8]
    user    = get_current_user(request)
    return templates.TemplateResponse("spectate.html", {
        "request":  request,
        "game_id":  game_id,
        "spec_id":  spec_id,
        "rows":     game.rows,
        "cols":     game.cols,
        "mines":    game.mines,
        "user":     user,
        "lang":     get_lang(request),
        "t":        get_t(request),
    })


# ── WebSocket: spectator ───────────────────────────────────────────────────────
@duel_router.websocket("/ws/{game_id}/spectate/{spec_id}")
async def spectate_ws(ws: WebSocket, game_id: str, spec_id: str):
    game = get_game(game_id)
    if not game:
        await ws.close(code=4004)
        return

    await ws.accept()
    game.add_spectator(ws)
    await manager.send(ws, game.spectate_init_payload())

    spec_name = "Spectator"
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            mtype = msg.get("type")
            if mtype == "spectator_name":
                spec_name = (msg.get("name", "") or "Spectator")[:32]
            elif mtype == "chat":
                text = msg.get("text", "").strip()[:200]
                if text:
                    await manager.broadcast(game, {
                        "type": "chat",
                        "from": f"👁 {spec_name}",
                        "pid":  spec_id,
                        "text": text,
                    })
    except WebSocketDisconnect:
        game.remove_spectator(ws)


@duel_router.websocket("/ws/{game_id}/{player_id}")
async def duel_ws(ws: WebSocket, game_id: str, player_id: str):
    game = get_game(game_id)
    if not game:
        await ws.close(code=4004)
        return

    await ws.accept()

    if not game.add_player(player_id, ws):
        await ws.send_json({"type": "watch_redirect", "game_id": game_id})
        await ws.close(code=4000)
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

            elif mtype == "chat":
                text = msg.get("text", "").strip()[:200]
                if text:
                    p = game.get_player(player_id)
                    from_name = (p.name or "Anonymous") if p else "Anonymous"
                    await manager.broadcast(game, {
                        "type": "chat",
                        "from": from_name,
                        "pid":  player_id,
                        "text": text,
                    })

            elif mtype == "rematch":
                if game.finished:
                    if game.rematch_game_id is None:
                        new_game = create_game(
                            rows=game.rows, cols=game.cols, mines=game.mines,
                            submode=game.submode, is_pvp=False,
                        )
                        game.rematch_game_id = new_game.game_id
                    for p in game.players:
                        if p.ws:
                            await manager.send(p.ws, {
                                "type":    "rematch_ready",
                                "game_id": game.rematch_game_id,
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
