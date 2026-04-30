"""
duel.py — In-memory duel game engine + WebSocket connection manager.
Each DuelGame is ephemeral; nothing is persisted to the database.
"""
import random, time, asyncio, uuid, base64
from dataclasses import dataclass, field
from typing import Optional
from fastapi import WebSocket

# ── Constants ─────────────────────────────────────────────────────────────────
ROWS, COLS, MINES                   = 30, 16, 99   # Standard (private duel)
PVP_ROWS, PVP_COLS, PVP_MINES       = 24, 16, 75   # Standard PvP matchmaking
QUICK_ROWS, QUICK_COLS, QUICK_MINES = 20, 10, 35   # Quick mode (both duel and PvP)

POINTS_PER_TILE = 5
TIME_BONUS_BASE = 300

# ── Board helpers ─────────────────────────────────────────────────────────────
def _neighbors(r, c, rows, cols):
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                yield nr, nc

def _place_mines(rows, cols, mines, safe_r, safe_c):
    forbidden = {
        (safe_r + dr, safe_c + dc)
        for dr in range(-1, 2) for dc in range(-1, 2)
        if 0 <= safe_r + dr < rows and 0 <= safe_c + dc < cols
    }
    pool = [(r, c) for r in range(rows) for c in range(cols)
            if (r, c) not in forbidden]
    chosen   = random.sample(pool, mines)
    mine_set = set(map(tuple, chosen))

    board = [[0] * cols for _ in range(rows)]
    for (mr, mc) in mine_set:
        board[mr][mc] = -1
        for nr, nc in _neighbors(mr, mc, rows, cols):
            if board[nr][nc] != -1:
                board[nr][nc] += 1
    return mine_set, board

def _board_hash(mine_set, rows, cols) -> str:
    """Base64-encode mine positions as a bit array (same format as the rest of the site)."""
    bits = bytearray((rows * cols + 7) // 8)
    for (mr, mc) in mine_set:
        idx = mr * cols + mc
        bits[idx >> 3] |= 1 << (idx & 7)
    return base64.b64encode(bytes(bits)).decode()

def _bfs_reveal(board, revealed, rows, cols, r, c):
    """Returns list of newly revealed (r, c) cells."""
    newly = []
    queue = [(r, c)]
    while queue:
        cr, cc = queue.pop()
        if revealed[cr][cc]:
            continue
        revealed[cr][cc] = True
        newly.append((cr, cc))
        if board[cr][cc] == 0:
            queue.extend(
                (nr, nc) for nr, nc in _neighbors(cr, cc, rows, cols)
                if not revealed[nr][nc]
            )
    return newly

def _expand_playable(rows: int, cols: int, cells) -> set:
    """Return all board cells within Chebyshev distance 2 of any cell in `cells`."""
    result = set()
    for (r, c) in cells:
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    result.add((nr, nc))
    return result

# ── Player state ──────────────────────────────────────────────────────────────
@dataclass
class PlayerState:
    player_id: str
    rows:      int
    cols:      int
    mines:     int
    ws:        Optional[WebSocket] = None
    revealed:  list = field(default_factory=list)
    mine_set:  set  = field(default_factory=set)
    board:     list = field(default_factory=list)
    started:        bool = False
    exploded:       bool = False
    tiles_revealed: int  = 0
    score:          int  = 0
    name:           str  = ""
    email:          str  = ""
    playable_set:   set  = field(default_factory=set)  # F70: empty = no frontier enforcement
    mine_hits:      int  = 0                           # F71: mine-hit counter

    def __post_init__(self):
        if not self.revealed:
            self.revealed = [[False] * self.cols for _ in range(self.rows)]
        if not self.board:
            self.board = [[0] * self.cols for _ in range(self.rows)]

    def safe_tiles(self):
        return self.rows * self.cols - self.mines

    def percent_revealed(self):
        return self.tiles_revealed / self.safe_tiles()

    def compute_score(self, elapsed: float) -> int:
        tile_pts   = self.tiles_revealed * POINTS_PER_TILE
        pct        = self.percent_revealed()
        time_bonus = max(0, (TIME_BONUS_BASE - elapsed) * pct)
        return int(tile_pts + time_bonus)

# ── Duel game ─────────────────────────────────────────────────────────────────
class DuelGame:
    def __init__(self, game_id: str, rows: int = ROWS, cols: int = COLS, mines: int = MINES, submode: str = "standard", is_pvp: bool = False, use_frontier: bool = False):
        self.game_id      = game_id
        self.rows         = rows
        self.cols         = cols
        self.mines        = mines
        self.submode      = submode
        self.is_pvp       = is_pvp
        self.use_frontier = use_frontier  # F70
        self.players:    list[PlayerState] = []
        self.spectators: list              = []   # list[WebSocket]
        self.rematch_game_id: Optional[str] = None
        self.start_time: Optional[float]   = None
        self.active:     bool = False
        self.finished:   bool = False
        self.created_at: float = time.time()

        # ── Shared board — same for both players ──────────────────────────────
        # Generate with a safe start at the board center so both players
        # begin with the same pre-revealed opening area.
        safe_r, safe_c = rows // 2, cols // 2
        self.shared_mine_set, self.shared_board = _place_mines(
            rows, cols, mines, safe_r, safe_c
        )
        self.board_hash = _board_hash(self.shared_mine_set, rows, cols)

        # BFS from center to find pre-revealed cells (the shared opening)
        _init_rev = [[False] * cols for _ in range(rows)]
        self.shared_prerev = _bfs_reveal(
            self.shared_board, _init_rev, rows, cols, safe_r, safe_c
        )

    # ── Accessors ─────────────────────────────────────────────────────────────
    def get_player(self, pid: str) -> Optional[PlayerState]:
        return next((p for p in self.players if p.player_id == pid), None)

    def opponent(self, pid: str) -> Optional[PlayerState]:
        return next((p for p in self.players if p.player_id != pid), None)

    def is_full(self) -> bool:
        return len(self.players) >= 2

    def both_connected(self) -> bool:
        return len(self.players) == 2 and all(p.ws for p in self.players)

    # ── Actions ───────────────────────────────────────────────────────────────
    def add_spectator(self, ws) -> None:
        self.spectators.append(ws)

    def remove_spectator(self, ws) -> None:
        if ws in self.spectators:
            self.spectators.remove(ws)

    def spectate_init_payload(self) -> dict:
        """Full current board state for a newly connected spectator."""
        players_data = []
        for p in self.players:
            cells = [
                [r, c, p.board[r][c]]
                for r in range(self.rows)
                for c in range(self.cols)
                if p.revealed[r][c]
            ]
            players_data.append({
                "player_id": p.player_id,
                "name":      p.name or "Anonymous",
                "score":     p.score,
                "tiles":     p.tiles_revealed,
                "exploded":  p.exploded,
                "cells":     cells,
            })
        return {
            "type":    "spec_init",
            "status":  "active" if self.active else ("finished" if self.finished else "waiting"),
            "players": players_data,
            "elapsed": self.elapsed(),
            "rows":    self.rows,
            "cols":    self.cols,
            "mines":   self.mines,
        }

    def add_player(self, pid: str, ws: WebSocket) -> bool:
        existing = self.get_player(pid)
        if existing:
            existing.ws = ws
            return True
        if self.is_full():
            return False
        self.players.append(PlayerState(
            player_id=pid, ws=ws,
            rows=self.rows, cols=self.cols, mines=self.mines
        ))
        return True

    def start(self):
        self.active     = True
        self.start_time = time.time()
        # Apply shared board and pre-revealed opening to every player
        for p in self.players:
            p.mine_set = set(self.shared_mine_set)
            p.board    = [row[:] for row in self.shared_board]
            for pr, pc in self.shared_prerev:
                p.revealed[pr][pc] = True
            p.tiles_revealed = len(self.shared_prerev)
            p.score          = p.tiles_revealed * POINTS_PER_TILE
            p.started        = True
            if self.use_frontier:  # F70
                p.playable_set = _expand_playable(self.rows, self.cols, self.shared_prerev)

    def start_payload(self) -> dict:
        """Data to include in the 'start' broadcast so clients can render the opening."""
        return {
            "prerev": self.shared_prerev,
            "board_values": {
                f"{r},{c}": self.shared_board[r][c]
                for r, c in self.shared_prerev
            },
            "board_hash":   self.board_hash,
            "prerev_score": len(self.shared_prerev) * POINTS_PER_TILE,
        }

    def reconnect_payload(self, pid: str) -> dict:
        """Full current game state for a player reconnecting mid-game."""
        p   = self.get_player(pid)
        opp = self.opponent(pid)
        my_rev     = [[r, c]            for r in range(self.rows) for c in range(self.cols) if p.revealed[r][c]]
        board_vals = {f"{r},{c}": p.board[r][c] for r, c in my_rev}
        opp_rev    = [[r, c, opp.board[r][c]] for r in range(self.rows) for c in range(self.cols)
                      if opp.revealed[r][c]] if opp else []
        return {
            "active":       self.active,
            "elapsed":      round(self.elapsed()),
            "my_revealed":  my_rev,
            "board_values": board_vals,
            "my_score":     p.score,
            "my_tiles":     p.tiles_revealed,
            "opp_revealed": opp_rev,
            "opp_score":    opp.score    if opp else 0,
            "opp_tiles":    opp.tiles_revealed if opp else 0,
            "opp_name":     opp.name     if opp else "",
        }

    def elapsed(self) -> float:
        if not self.start_time:
            return 0.0
        return time.time() - self.start_time

    def reveal(self, pid: str, r: int, c: int) -> dict:
        p = self.get_player(pid)
        if not p or p.exploded or self.finished or not self.active:
            return {}

        if not (0 <= r < self.rows and 0 <= c < self.cols):
            return {}

        if p.revealed[r][c]:
            return {}

        # F70: reject clicks outside the playable frontier
        if p.playable_set and (r, c) not in p.playable_set:
            return {}

        # Hit a mine
        if p.board[r][c] == -1:
            if self.use_frontier:  # F71: realloc instead of instant loss
                return self._mine_hit_realloc(p, r, c)
            p.exploded = True
            p.score    = p.tiles_revealed * POINTS_PER_TILE  # no time bonus on explosion
            result     = {"newly_revealed": [(r, c)], "exploded": True, "score": p.score}
            opp = self.opponent(pid)
            if not opp or opp.exploded or opp.tiles_revealed >= opp.safe_tiles():
                self.finished      = True
                result["finished"] = True
                result["winner"]   = self._determine_winner()
            else:
                result["finished"]        = False
                result["opp_still_alive"] = True
            return result

        # Safe reveal (BFS flood fill)
        newly = _bfs_reveal(p.board, p.revealed, self.rows, self.cols, r, c)
        p.tiles_revealed += len(newly)
        p.score           = p.compute_score(self.elapsed())
        # F70: expand playable frontier to include cells within Chebyshev 2 of newly revealed
        if p.playable_set:
            p.playable_set.update(_expand_playable(self.rows, self.cols, newly))

        result = {"newly_revealed": newly, "exploded": False, "score": p.score}

        # Check win condition
        if p.tiles_revealed >= p.safe_tiles():
            opp = self.opponent(pid)
            if opp:
                opp.score = opp.compute_score(self.elapsed())
            if not opp or opp.exploded or opp.tiles_revealed >= opp.safe_tiles():
                self.finished      = True
                result["finished"] = True
                result["winner"]   = self._determine_winner()
            else:
                result["finished"]        = False
                result["opp_still_alive"] = True

        return result

    def _mine_hit_realloc(self, p: 'PlayerState', r: int, c: int) -> dict:
        """F71: Scramble the 3×3 around (r,c); no player loss."""
        # 1. 3×3 cells clamped to board
        cells_3x3 = [
            (nr, nc)
            for dr in range(-1, 2) for dc in range(-1, 2)
            for nr, nc in [(r + dr, c + dc)]
            if 0 <= nr < self.rows and 0 <= nc < self.cols
        ]

        # 2. Count mines in 3×3, then shuffle them within the same 9 cells
        mine_count = sum(1 for (nr, nc) in cells_3x3 if p.board[nr][nc] == -1)
        positions  = list(cells_3x3)
        random.shuffle(positions)
        new_mines  = set(positions[i] for i in range(mine_count))

        # 3. Update mine_set
        for cell in cells_3x3:
            p.mine_set.discard(cell)
        p.mine_set.update(new_mines)

        # 4. Count tiles lost (previously revealed safe cells in 3×3)
        tiles_lost = sum(
            1 for (nr, nc) in cells_3x3
            if p.revealed[nr][nc] and p.board[nr][nc] != -1
        )

        # 5. Reset all 3×3 cells to unrevealed
        for (nr, nc) in cells_3x3:
            p.revealed[nr][nc] = False

        # 6. Recalculate board values for the 5×5 area (all cells neighbouring 3×3)
        for ar in range(max(0, r - 2), min(self.rows, r + 3)):
            for ac in range(max(0, c - 2), min(self.cols, c + 3)):
                if (ar, ac) in p.mine_set:
                    p.board[ar][ac] = -1
                else:
                    p.board[ar][ac] = sum(
                        1 for (br, bc) in _neighbors(ar, ac, self.rows, self.cols)
                        if (br, bc) in p.mine_set
                    )

        # 7. Update tiles/score
        p.tiles_revealed -= tiles_lost
        if p.tiles_revealed < 0:
            p.tiles_revealed = 0
        p.score     = p.compute_score(self.elapsed())
        p.mine_hits += 1

        # 8. Recompute frontier from current revealed state (F70 interaction)
        if p.playable_set:
            revealed_cells = [
                (rr, cc)
                for rr in range(self.rows)
                for cc in range(self.cols)
                if p.revealed[rr][cc]
            ]
            p.playable_set = _expand_playable(self.rows, self.cols, revealed_cells)

        # 9. Build updated_values: new board vals for 3×3 + adjacent revealed cells
        cells_to_send = set(cells_3x3)
        for ar in range(max(0, r - 2), min(self.rows, r + 3)):
            for ac in range(max(0, c - 2), min(self.cols, c + 3)):
                if (ar, ac) not in cells_to_send and p.revealed[ar][ac]:
                    cells_to_send.add((ar, ac))
        updated_values = {f"{nr},{nc}": p.board[nr][nc] for (nr, nc) in cells_to_send}

        return {
            "mine_hit":       True,
            "r":              r,
            "c":              c,
            "reset_cells":    cells_3x3,
            "updated_values": updated_values,
            "mine_hits":      p.mine_hits,
            "score":          p.score,
            "tiles":          p.tiles_revealed,
        }

    def _determine_winner(self):
        """Pick winner by score. Returns player_id or None for a draw."""
        if len(self.players) < 2:
            return self.players[0].player_id if self.players else None
        p1, p2 = self.players
        if p1.score > p2.score: return p1.player_id
        if p2.score > p1.score: return p2.player_id
        return None  # draw

    def scores_payload(self):
        return {p.player_id: p.score for p in self.players}

# ── Global game store ─────────────────────────────────────────────────────────
_games: dict[str, DuelGame] = {}

def create_game(rows=ROWS, cols=COLS, mines=MINES, submode="standard", is_pvp=False, use_frontier=False) -> DuelGame:
    gid  = uuid.uuid4().hex[:10]
    game = DuelGame(gid, rows=rows, cols=cols, mines=mines, submode=submode, is_pvp=is_pvp, use_frontier=use_frontier)
    _games[gid] = game
    return game

def get_game(gid: str) -> Optional[DuelGame]:
    return _games.get(gid)

def cleanup_old_games():
    """Remove games older than 2 hours. Called by the scheduler."""
    cutoff = time.time() - 7200
    stale  = [gid for gid, g in _games.items() if g.created_at < cutoff]
    for gid in stale:
        del _games[gid]

# ── PvP matchmaking queue ─────────────────────────────────────────────────────
_pvp_queue: list[dict] = []

async def pvp_enqueue(player_id: str, ws: WebSocket) -> Optional[DuelGame]:
    """
    Add player to the queue. If another player is waiting, pair them
    into a new PvP game and return it. Otherwise return None.
    """
    global _pvp_queue
    _pvp_queue = [e for e in _pvp_queue if e["player_id"] != player_id]

    if _pvp_queue:
        opponent = _pvp_queue.pop(0)
        game = create_game(rows=PVP_ROWS, cols=PVP_COLS, mines=PVP_MINES, is_pvp=True)
        game.add_player(opponent["player_id"], opponent["ws"])
        game.add_player(player_id, ws)
        try:
            await opponent["ws"].send_json({
                "type":    "matched",
                "game_id": game.game_id,
                "msg":     "Opponent found! Get ready…",
            })
        except Exception:
            pass
        return game
    else:
        _pvp_queue.append({"player_id": player_id, "ws": ws})
        return None

def pvp_dequeue(player_id: str):
    """Remove a player from the queue (on disconnect)."""
    global _pvp_queue
    _pvp_queue = [e for e in _pvp_queue if e["player_id"] != player_id]

def pvp_queue_length() -> int:
    return len(_pvp_queue)

# ── Quick PvP matchmaking queue ───────────────────────────────────────────────
_pvp_quick_queue: list[dict] = []

async def pvp_quick_enqueue(player_id: str, ws: WebSocket) -> Optional[DuelGame]:
    global _pvp_quick_queue
    _pvp_quick_queue = [e for e in _pvp_quick_queue if e["player_id"] != player_id]

    if _pvp_quick_queue:
        opponent = _pvp_quick_queue.pop(0)
        game = create_game(rows=QUICK_ROWS, cols=QUICK_COLS, mines=QUICK_MINES, submode="quick", is_pvp=True)
        game.add_player(opponent["player_id"], opponent["ws"])
        game.add_player(player_id, ws)
        try:
            await opponent["ws"].send_json({
                "type":    "matched",
                "game_id": game.game_id,
                "msg":     "Opponent found! Get ready…",
            })
        except Exception:
            pass
        return game
    else:
        _pvp_quick_queue.append({"player_id": player_id, "ws": ws})
        return None

def pvp_quick_dequeue(player_id: str):
    global _pvp_quick_queue
    _pvp_quick_queue = [e for e in _pvp_quick_queue if e["player_id"] != player_id]

def pvp_quick_queue_length() -> int:
    return len(_pvp_quick_queue)

# ── PvP Beta matchmaking queue (isolated; results not saved) ──────────────────
_pvpbeta_queue: list[dict] = []

async def pvpbeta_enqueue(player_id: str, ws) -> Optional[DuelGame]:
    global _pvpbeta_queue
    _pvpbeta_queue = [e for e in _pvpbeta_queue if e["player_id"] != player_id]
    if _pvpbeta_queue:
        opponent = _pvpbeta_queue.pop(0)
        game = create_game(rows=PVP_ROWS, cols=PVP_COLS, mines=PVP_MINES, is_pvp=False, use_frontier=True)
        game.add_player(opponent["player_id"], opponent["ws"])
        game.add_player(player_id, ws)
        try:
            await opponent["ws"].send_json({
                "type":    "matched",
                "game_id": game.game_id,
                "msg":     "Opponent found! Get ready…",
            })
        except Exception:
            pass
        return game
    else:
        _pvpbeta_queue.append({"player_id": player_id, "ws": ws})
        return None

def pvpbeta_dequeue(player_id: str):
    global _pvpbeta_queue
    _pvpbeta_queue = [e for e in _pvpbeta_queue if e["player_id"] != player_id]

def pvpbeta_queue_length() -> int:
    return len(_pvpbeta_queue)

# ── Quick PvP Beta matchmaking queue ──────────────────────────────────────────
_pvpbeta_quick_queue: list[dict] = []

async def pvpbeta_quick_enqueue(player_id: str, ws) -> Optional[DuelGame]:
    global _pvpbeta_quick_queue
    _pvpbeta_quick_queue = [e for e in _pvpbeta_quick_queue if e["player_id"] != player_id]
    if _pvpbeta_quick_queue:
        opponent = _pvpbeta_quick_queue.pop(0)
        game = create_game(rows=QUICK_ROWS, cols=QUICK_COLS, mines=QUICK_MINES, submode="quick", is_pvp=False, use_frontier=True)
        game.add_player(opponent["player_id"], opponent["ws"])
        game.add_player(player_id, ws)
        try:
            await opponent["ws"].send_json({
                "type":    "matched",
                "game_id": game.game_id,
                "msg":     "Opponent found! Get ready…",
            })
        except Exception:
            pass
        return game
    else:
        _pvpbeta_quick_queue.append({"player_id": player_id, "ws": ws})
        return None

def pvpbeta_quick_dequeue(player_id: str):
    global _pvpbeta_quick_queue
    _pvpbeta_quick_queue = [e for e in _pvpbeta_quick_queue if e["player_id"] != player_id]

def pvpbeta_quick_queue_length() -> int:
    return len(_pvpbeta_quick_queue)

# ── WebSocket connection manager ──────────────────────────────────────────────
class ConnectionManager:
    async def send(self, ws: WebSocket, data: dict):
        try:
            await ws.send_json(data)
        except Exception:
            pass

    async def broadcast(self, game: DuelGame, data: dict):
        for p in game.players:
            if p.ws:
                await self.send(p.ws, data)
        for ws in list(game.spectators):
            await self.send(ws, data)

manager = ConnectionManager()
