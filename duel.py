"""
duel.py — In-memory duel game engine + WebSocket connection manager.
Each DuelGame is ephemeral; nothing is persisted to the database.
"""
import random, time, asyncio, uuid
from dataclasses import dataclass, field
from typing import Optional
from fastapi import WebSocket

# ── Constants ─────────────────────────────────────────────────────────────────
ROWS, COLS, MINES = 16, 30, 99          # Expert board
POINTS_PER_TILE   = 5
TIME_BONUS_BASE   = 300
SAFE_RADIUS       = 1                   # cells around first click guaranteed safe

# ── Board helpers ─────────────────────────────────────────────────────────────
def _neighbors(r, c):
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                yield nr, nc

def _place_mines(safe_r, safe_c):
    forbidden = {
        (safe_r + dr, safe_c + dc)
        for dr in range(-1, 2) for dc in range(-1, 2)
        if 0 <= safe_r + dr < ROWS and 0 <= safe_c + dc < COLS
    }
    pool = [(r, c) for r in range(ROWS) for c in range(COLS)
            if (r, c) not in forbidden]
    chosen = random.sample(pool, MINES)
    mine_set = set(map(tuple, chosen))

    board = [[0] * COLS for _ in range(ROWS)]
    for (mr, mc) in mine_set:
        board[mr][mc] = -1
        for nr, nc in _neighbors(mr, mc):
            if board[nr][nc] != -1:
                board[nr][nc] += 1
    return mine_set, board

def _bfs_reveal(board, revealed, r, c):
    """Returns list of newly revealed (r,c) cells."""
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
                (nr, nc) for nr, nc in _neighbors(cr, cc)
                if not revealed[nr][nc]
            )
    return newly

# ── Player state ──────────────────────────────────────────────────────────────
@dataclass
class PlayerState:
    player_id:  str
    ws:         Optional[WebSocket] = None
    revealed:   list = field(default_factory=lambda: [[False]*COLS for _ in range(ROWS)])
    mine_set:   set  = field(default_factory=set)
    board:      list = field(default_factory=lambda: [[0]*COLS for _ in range(ROWS)])
    started:    bool = False          # mines placed yet?
    exploded:   bool = False
    tiles_revealed: int = 0
    score:      int = 0

    def safe_tiles(self):
        return ROWS * COLS - MINES

    def percent_revealed(self):
        return self.tiles_revealed / self.safe_tiles()

    def compute_score(self, elapsed: float) -> int:
        tile_pts  = self.tiles_revealed * POINTS_PER_TILE
        pct       = self.percent_revealed()
        time_bonus = max(0, (TIME_BONUS_BASE - elapsed) * pct)
        return int(tile_pts + time_bonus)

# ── Duel game ─────────────────────────────────────────────────────────────────
class DuelGame:
    def __init__(self, game_id: str):
        self.game_id    = game_id
        self.players:   list[PlayerState] = []
        self.start_time: Optional[float]  = None
        self.active:    bool = False
        self.finished:  bool = False
        self.created_at: float = time.time()

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
        """Returns True if successfully added."""
        existing = self.get_player(pid)
        if existing:
            existing.ws = ws      # reconnect
            return True
        if self.is_full():
            return False
        self.players.append(PlayerState(player_id=pid, ws=ws))
        return True

    def start(self):
        self.active     = True
        self.start_time = time.time()

    def elapsed(self) -> float:
        if not self.start_time:
            return 0.0
        return time.time() - self.start_time

    def reveal(self, pid: str, r: int, c: int) -> dict:
        """
        Process a reveal action. Returns a result dict with keys:
          - newly_revealed: [(r,c), ...]
          - exploded: bool
          - score: int
          - finished: bool  (did this action end the game?)
          - winner: str | None
        """
        p = self.get_player(pid)
        if not p or p.exploded or self.finished or not self.active:
            return {}

        # First click for this player — place mines now
        if not p.started:
            p.mine_set, p.board = _place_mines(r, c)
            p.started = True

        if p.revealed[r][c]:
            return {}

        # Hit a mine
        if p.board[r][c] == -1:
            p.exploded = True
            p.score    = p.tiles_revealed * POINTS_PER_TILE  # no time bonus on explosion
            result     = {"newly_revealed": [(r, c)], "exploded": True,
                          "score": p.score}
            # Only end the game if the opponent is also done
            opp = self.opponent(pid)
            if not opp or opp.exploded or opp.tiles_revealed >= opp.safe_tiles():
                self.finished      = True
                result["finished"] = True
                result["winner"]   = self._determine_winner()
            else:
                # Opponent still playing — notify them but keep going
                result["finished"]       = False
                result["opp_still_alive"] = True
            return result

        # Safe reveal (BFS)
        newly = _bfs_reveal(p.board, p.revealed, r, c)
        p.tiles_revealed += len(newly)
        p.score           = p.compute_score(self.elapsed())

        result = {"newly_revealed": newly, "exploded": False, "score": p.score}

        # Check win condition: all safe tiles revealed
        if p.tiles_revealed >= p.safe_tiles():
            opp = self.opponent(pid)
            if opp:
                opp.score = opp.compute_score(self.elapsed())
            # Only end if opponent is also done
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
        if p1.score > p2.score:   return p1.player_id
        if p2.score > p1.score:   return p2.player_id
        return None  # draw

    def scores_payload(self):
        return {p.player_id: p.score for p in self.players}

# ── Global game store ─────────────────────────────────────────────────────────
_games: dict[str, DuelGame] = {}

def create_game() -> DuelGame:
    gid  = uuid.uuid4().hex[:10]
    game = DuelGame(gid)
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

# ── WebSocket manager ─────────────────────────────────────────────────────────
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
