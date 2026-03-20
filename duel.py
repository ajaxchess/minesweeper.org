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
    def __init__(self, game_id: str, rows: int = ROWS, cols: int = COLS, mines: int = MINES, submode: str = "standard", is_pvp: bool = False):
        self.game_id     = game_id
        self.rows        = rows
        self.cols        = cols
        self.mines       = mines
        self.submode     = submode
        self.is_pvp      = is_pvp
        self.players:    list[PlayerState] = []
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

        # Hit a mine
        if p.board[r][c] == -1:
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

def create_game(rows=ROWS, cols=COLS, mines=MINES, submode="standard", is_pvp=False) -> DuelGame:
    gid  = uuid.uuid4().hex[:10]
    game = DuelGame(gid, rows=rows, cols=cols, mines=mines, submode=submode, is_pvp=is_pvp)
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

manager = ConnectionManager()
