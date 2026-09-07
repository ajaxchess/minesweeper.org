# Numbers Match — Implementation Plan

## Summary

A 9-column number-pairing puzzle game. Players clear the board by matching
identical numbers or pairs that sum to 10, connected via clear lines
(horizontal, vertical, diagonal, or horizontal wrap-around). Follows the
same daily/random dual-mode pattern as Tentaizu.

---

## Files to Create / Modify

| File | Action |
|------|--------|
| `database_template.py` | Add `NumbersMatchScore` model |
| `main.py` | Add page routes + score API |
| `templates/numbers_match.html` | New game page |
| `static/js/numbers_match.js` | New game engine |
| `static/css/numbers_match.css` | New stylesheet |

---

## Phase 1 — Database

Add to `database_template.py`:

```python
class NumbersMatchScore(Base):
    __tablename__ = "numbers_match_scores"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(32), nullable=False)
    user_email  = Column(String(256), nullable=True, index=True)
    puzzle_date = Column(String(10), nullable=False)   # YYYY-MM-DD or random hex
    score       = Column(Integer, nullable=False, default=0)
    time_secs   = Column(Integer, nullable=False)
    lines_added = Column(Integer, nullable=False, default=0)
    guest_token = Column(String(36), nullable=True, index=True)
    client_type = Column(String(32), nullable=False, server_default="na")
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_nm_scores_date_score_time", "puzzle_date", "score", "time_secs"),
    )
```

Note: leaderboard sorts by `score DESC, time_secs ASC` — unlike Tentaizu which
sorts by `time_secs ASC` only.

---

## Phase 2 — Backend (`main.py`)

### Pydantic model

```python
class NumbersMatchScoreSubmit(BaseModel):
    name:        str = Field(..., min_length=1, max_length=32)
    puzzle_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    score:       int = Field(..., ge=0, le=99999)
    time_secs:   int = Field(..., ge=0, le=99999)
    lines_added: int = Field(default=0, ge=0, le=999)
```

### Routes

```python
@app.get("/numbers-match", response_class=HTMLResponse)
async def numbers_match_page(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse("numbers_match.html", {
        "request": request,
        "mode": "numbers-match",
        "today": today,
        "real_today": today,
    })

@app.get("/numbers-match/{date_str}", response_class=HTMLResponse)
async def numbers_match_permalink(request: Request, date_str: str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return RedirectResponse("/numbers-match", status_code=302)
    return templates.TemplateResponse("numbers_match.html", {
        "request": request,
        "mode": "numbers-match",
        "today": date_str,
        "real_today": date.today().isoformat(),
    })

@app.post("/api/numbers-match-scores", status_code=201)
@limiter.limit("10/minute")
def submit_numbers_match_score(
    payload: NumbersMatchScoreSubmit,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request)
    if not user:
        if "guest_token" not in request.session:
            request.session["guest_token"] = str(uuid.uuid4())
        guest_token = request.session["guest_token"]
    else:
        guest_token = None

    entry = NumbersMatchScore(
        name        = sanitize_name(payload.name),
        user_email  = user["email"] if user else None,
        puzzle_date = payload.puzzle_date,
        score       = payload.score,
        time_secs   = payload.time_secs,
        lines_added = payload.lines_added,
        guest_token = guest_token,
        client_type = get_client_type(request),
    )
    db.add(entry)
    db.commit()
    flag_if_profane(db, "numbers_match_scores", entry.id, entry.name)
    record_score_submit("numbers_match", str(payload.puzzle_date))
    record_game_complete(
        "numbers_match",
        mode="daily",
        timestamp=datetime.now(timezone.utc),
        elapsed_seconds=payload.time_secs,
    )
    return {"id": entry.id}

@app.get("/api/numbers-match-scores/{puzzle_date}")
def get_numbers_match_scores(puzzle_date: str, db: Session = Depends(get_db)):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", puzzle_date):
        raise HTTPException(status_code=400, detail="Invalid date format")
    q = db.query(NumbersMatchScore).filter(
        NumbersMatchScore.puzzle_date == puzzle_date
    )
    q = exclude_flagged(q, NumbersMatchScore, db)
    top = (
        q
        .order_by(
            NumbersMatchScore.score.desc(),
            NumbersMatchScore.time_secs.asc(),
            NumbersMatchScore.created_at.asc(),
        )
        .limit(20)
        .all()
    )
    return [
        {
            "name": s.name,
            "score": s.score,
            "time_secs": s.time_secs,
            "lines_added": s.lines_added,
            "profile_url": get_profile_url(s.user_email) if s.user_email else None,
        }
        for s in top
    ]
```

---

## Phase 3 — Game Engine (`numbers_match.js`)

### Global State

```javascript
const G = {
    board:       [],     // flat array length rows*9; 0=empty, 1-9=number
    rows:        0,      // current row count (grows on addLines)
    cols:        9,
    score:       0,
    elapsed:     0,      // seconds since start
    timerHandle: null,
    selected:    null,   // flat index of first selected cell, or null
    history:     [],     // stack of {board, score, rows} snapshots — max 3
    undosLeft:   3,
    hintsLeft:   9,
    hintPair:    null,   // [i, j] currently highlighted hint, or null
    isPOTD:      false,
    puzzleId:    null,   // YYYY-MM-DD string for daily; random hex for random
    linesAdded:  0,
    won:         false,
};
```

### Board Number & Row Count

```javascript
const NM_EPOCH = '2024-01-01';

function getBoardNumber(dateStr) {
    const msPerDay = 86400000;
    return Math.floor((new Date(dateStr) - new Date(NM_EPOCH)) / msPerDay) + 1;
}

function getInitialRows(boardNum) {
    if (boardNum === 1)  return 3;
    if (boardNum <= 3)   return 4;
    if (boardNum <= 6)   return 5;
    if (boardNum <= 10)  return 6;
    if (boardNum <= 15)  return 7;
    if (boardNum <= 21)  return 8;
    if (boardNum <= 28)  return 9;
    // pattern: 7 boards per row-increase after row 9
    return 10 + Math.floor((boardNum - 29) / 7);
}
```

### Seeded RNG & Board Generation

```javascript
function mulberry32(seed) {
    return () => {
        seed |= 0; seed = seed + 0x6D2B79F5 | 0;
        let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
        t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
        return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
}

function fnv1a(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) {
        h ^= str.charCodeAt(i);
        h = Math.imul(h, 16777619);
    }
    return h >>> 0;
}

function generateBoard(seed, rows) {
    const rng = mulberry32(fnv1a(String(seed)));
    const total = rows * 9;
    // Base sequence: 1-9 repeated to fill the board
    const base = Array.from({ length: total }, (_, i) => (i % 9) + 1);
    // Fisher-Yates shuffle
    for (let i = total - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [base[i], base[j]] = [base[j], base[i]];
    }
    return base;
}
```

> **Note on solvability guarantee:** A naive shuffle does not guarantee solvability.
> The team must evaluate one of two approaches:
>
> **Option A (Recommended for v1):** Generate using the canonical Seeds starting
> sequence (1,2,…,9 repeated) without shuffling for daily boards — this is known
> to be solvable. Use the seed to vary starting point in the sequence. Validate
> against a BFS/DFS solver before deployment.
>
> **Option B:** Pre-generate and cache daily boards server-side (APScheduler job
> at 00:01 UTC) by running a solver and storing the board as JSON in the DB.
> The page route reads the cached board and embeds it in the template. This
> completely decouples generation complexity from the client.
>
> Option B is preferred if guaranteed solvability is a hard requirement.

### Adjacency Check

Two cells at flat indices `i` and `j` are adjacent if they share a clear line:

```javascript
function areAdjacent(i, j) {
    if (i === j) return false;
    const [lo, hi]   = i < j ? [i, j] : [j, i];
    const rowLo = Math.floor(lo / 9), colLo = lo % 9;
    const rowHi = Math.floor(hi / 9), colHi = hi % 9;
    const dr = rowHi - rowLo, dc = colHi - colLo;

    // Horizontal (same row)
    if (rowLo === rowHi) {
        for (let k = lo + 1; k < hi; k++)
            if (G.board[k] !== 0) return false;
        return true;
    }
    // Vertical (same column)
    if (colLo === colHi) {
        for (let k = lo + 9; k < hi; k += 9)
            if (G.board[k] !== 0) return false;
        return true;
    }
    // Diagonal
    if (Math.abs(dr) === Math.abs(dc)) {
        const stepC = dc > 0 ? 1 : -1;
        for (let s = 1; s < dr; s++)
            if (G.board[(rowLo + s) * 9 + colLo + s * stepC] !== 0) return false;
        return true;
    }
    // Horizontal wrap — flat path (lo+1 … hi-1 all empty)
    // Valid when none of the above direction checks matched.
    // This naturally handles single and multi-row wraps: the flat array
    // represents row-end → row-start as consecutive positions.
    for (let k = lo + 1; k < hi; k++)
        if (G.board[k] !== 0) return false;
    return true;
}
```

### Value Check

```javascript
function canMatch(a, b) {
    return a !== 0 && b !== 0 && (a === b || a + b === 10);
}
```

### Pair Score

```javascript
function calcPairScore(i, j) {
    const [lo, hi]   = i < j ? [i, j] : [j, i];
    const rowLo = Math.floor(lo / 9), colLo = lo % 9;
    const rowHi = Math.floor(hi / 9), colHi = hi % 9;
    const dr = rowHi - rowLo, dc = colHi - colLo;
    let empty = 0;

    if (rowLo === rowHi) {
        for (let k = lo + 1; k < hi; k++) if (G.board[k] === 0) empty++;
    } else if (colLo === colHi) {
        for (let k = lo + 9; k < hi; k += 9) if (G.board[k] === 0) empty++;
    } else if (Math.abs(dr) === Math.abs(dc)) {
        const stepC = dc > 0 ? 1 : -1;
        for (let s = 1; s < dr; s++)
            if (G.board[(rowLo + s) * 9 + colLo + s * stepC] === 0) empty++;
    } else {
        for (let k = lo + 1; k < hi; k++) if (G.board[k] === 0) empty++;
    }

    return 1 + Math.min(4, empty);   // base +1, far-apart bonus up to +4
}
```

### Row-Clear Bonus

```javascript
function applyRowClearBonus(prevBoard) {
    let bonus = 0;
    for (let r = 0; r < G.rows; r++) {
        const start = r * 9;
        const nowEmpty  = G.board.slice(start, start + 9).every(v => v === 0);
        const hadValues = prevBoard.slice(start, start + 9).some(v => v !== 0);
        if (nowEmpty && hadValues) bonus += 10;
    }
    return bonus;
}
```

### Match Flow

```javascript
function doMatch(i, j) {
    const prevBoard = [...G.board];
    G.board[i] = 0;
    G.board[j] = 0;
    G.score += calcPairScore(i, j);       // +1 base + far-apart bonus
    G.score += applyRowClearBonus(prevBoard); // +10 per newly cleared row
    if (G.board.every(v => v === 0)) {
        G.score += 150;                   // board-clear bonus
        G.won = true;
        stopTimer();
        showWinOverlay();
    }
    renderBoard();
    updateScoreDisplay();
}
```

### Undo

```javascript
function saveHistory() {
    G.history.push({ board: [...G.board], score: G.score, rows: G.rows });
    if (G.history.length > 3) G.history.shift();
}

function doUndo() {
    if (G.undosLeft <= 0 || G.history.length === 0) return;
    const snap = G.history.pop();
    G.board = snap.board;
    G.score = snap.score;
    G.rows  = snap.rows;
    G.undosLeft--;
    G.selected = null;
    renderBoard();
    updateScoreDisplay();
    updateToolCounts();
}
```

### Hint

```javascript
function findHint() {
    const len = G.board.length;
    for (let i = 0; i < len - 1; i++) {
        if (G.board[i] === 0) continue;
        for (let j = i + 1; j < len; j++) {
            if (G.board[j] === 0) continue;
            if (canMatch(G.board[i], G.board[j]) && areAdjacent(i, j))
                return [i, j];
        }
    }
    return null;
}

function doHint() {
    if (G.hintsLeft <= 0) return;
    G.hintPair = findHint();
    G.hintsLeft--;
    renderBoard();        // re-render with hint cells highlighted
    updateToolCounts();
}
```

### Add Lines

```javascript
function addLines() {
    const remaining = G.board.filter(v => v !== 0);
    if (remaining.length === 0) return;
    while (remaining.length % 9 !== 0) remaining.push(0);
    G.board = [...G.board, ...remaining];
    G.rows += remaining.length / 9;
    G.linesAdded++;
    renderBoard();
}
```

### Score Submission

```javascript
async function saveScore(name) {
    const r = await fetch('/api/numbers-match-scores', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify({
            name,
            puzzle_date: G.puzzleId,
            score:       G.score,
            time_secs:   Math.max(1, G.elapsed),
            lines_added: G.linesAdded,
        }),
    });
    if (r.ok) {
        localStorage.setItem('nm_name', name);
        loadLeaderboard(G.puzzleId);
    }
}
```

---

## Phase 4 — HTML Template (`numbers_match.html`)

Extend `base.html`. Key sections:

```
<div id="nm-board" data-today="{{ today }}" data-real-today="{{ real_today }}"
     data-username="{{ username or '' }}">

  <!-- Mode toolbar -->
  <div class="nm-toolbar">
    <button id="nm-daily-btn">Daily</button>
    <button id="nm-random-btn">🎲 Random</button>
  </div>

  <!-- Stats bar -->
  <div class="nm-stats">
    <span id="nm-timer">0:00</span>
    <span id="nm-score">0</span>
    <span id="nm-undo-count">↩ 3</span>
    <span id="nm-hint-count">💡 9</span>
  </div>

  <!-- Action bar -->
  <div class="nm-actions">
    <button id="nm-undo-btn">Undo</button>
    <button id="nm-hint-btn">Hint</button>
    <button id="nm-add-btn">Add Lines</button>
  </div>

  <!-- Game grid — cells rendered by JS -->
  <div id="nm-grid"></div>

  <!-- Win overlay -->
  <div id="nm-overlay" class="hidden">
    <div id="nm-result">
      <p>Score: <strong id="nm-final-score"></strong></p>
      <p>Time:  <strong id="nm-final-time"></strong></p>
      <input id="nm-name-input" maxlength="32" placeholder="Your name">
      <button id="nm-submit-btn">Submit</button>
    </div>
  </div>

  <!-- Leaderboard -->
  <div id="nm-leaderboard"></div>
</div>
```

---

## Phase 5 — Stylesheet (`numbers_match.css`)

Key rules:

- `#nm-grid` — CSS grid, `grid-template-columns: repeat(9, 1fr)`, square cells
- `.nm-cell` — base cell style; font-weight bold; cursor pointer
- `.nm-cell.selected` — highlighted border/background
- `.nm-cell.hint` — distinct highlight colour (yellow glow)
- `.nm-cell[data-val="1"]` … `[data-val="9"]` — number colour palette
  (e.g., warm red for 1/9 pairs, blue for 2/8, green for 3/7, purple for 4/6,
  orange for 5/5)
- `.nm-cell.empty` — grey or transparent, no cursor
- Responsive: on narrow screens, reduce cell padding; keep 9 columns

---

## Scoring Reference

| Event | Points |
|-------|--------|
| Pair removed | +1 |
| Far-apart bonus | +1 per empty cell between pair (max +4) |
| Full row cleared | +10 |
| Board cleared | +150 |

Leaderboard sort: `score DESC`, then `time_secs ASC`.

---

## Open Questions (resolve before implementation starts)

| # | Question | Recommendation |
|---|----------|----------------|
| 1 | **Board generation solvability** | Use Option B (server-side pre-generation + solver) for daily boards. Random mode uses client-side shuffle without solvability guarantee. |
| 2 | **Epoch date for board numbering** | Confirm date with team (suggest 2024-01-01). |
| 3 | **Odd cell counts** | Rows × 9 may be odd (e.g., 3 rows = 27 cells). The "Add Lines" mechanic makes these solvable. Confirm this is acceptable per spec. |
| 4 | **Random mode leaderboard** | No score submission for random mode (matches Tentaizu pattern). |
| 5 | **"Check" tool** | Skip for v1 per spec ("TBD"). Add a disabled button as placeholder. |
| 6 | **i18n** | Add translations for all labels to `translations.py` before launch. |
| 7 | **Number colour palette** | Choose 5 colours for pairs (1/9, 2/8, 3/7, 4/6, 5/5). |

---

## Estimated Effort

| Phase | Owner | Est. |
|-------|-------|------|
| DB model | Any | 30 min |
| Backend routes | Any | 1 hr |
| Game engine JS | Senior dev | 4–5 hr |
| HTML template | Any | 1–2 hr |
| CSS | Any | 1–2 hr |
| Board solver (if Option B) | Senior dev | 2–3 hr |
| QA / manual testing | All | 2 hr |
| **Total** | | **~12–16 hr** |

---

## Delivery Order

1. Confirm open questions with team
2. `database_template.py` additions
3. `main.py` additions
4. `numbers_match.js` — state, board gen, adjacency, scoring
5. `numbers_match.html` + `numbers_match.css`
6. Manual QA: daily mode, random mode, undo, hint, add-lines, win flow, leaderboard
7. Add i18n strings
