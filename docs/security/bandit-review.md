# Bandit Review — 2026-10-11

Line-by-line review of every finding from Bandit 1.9.4, run with the same
excludes as CI plus `./mobile`, at **all** severity levels. CI only fails on
medium severity and medium confidence; the three medium findings here have low
confidence, so CI passes.

```
bandit -r . --exclude ./venv,./tests,./analysis,./python_prototypes,./mobile
```

**Result:** 72 findings (69 low, 3 medium). **2 are real** (one medium, one low),
11 are false positives, 58 are acceptable as written, and 1 (B105 in
`database.py`) is a duplicate: that file is a generated, git-ignored copy of
`database_template.py`.

| Verdict | Count |
|---------|-------|
| Real — fix recommended | 2 (B311: WC2026 board seed, PvP mine RNG) |
| False positive | 11 (B608 ×3, B105 ×3, B404 ×2, B603 ×2, B607 ×1) |
| Acceptable as written | 58 (B311 ×21, B110 ×9, B112 ×3, B101 ×25) |
| Duplicate (generated `database.py`) | 1 |

---

## Real findings

### R1 — WC2026 mine layouts can be computed before playing (B311, `wc2026_board.py:60`) — Medium

```python
raw = f"wc2026:{identity}:{country_slug}:{difficulty}:{play_count}"
rng = random.Random(int(hashlib.sha256(raw.encode()).hexdigest(), 16) & 0xFFFF_FFFF)
```

Every input to the seed is known to the player: `identity` is `u:<their email>`
or `g:<guest_token>` (the guest token is readable in the session cookie, which
is signed but not encrypted), plus the country, difficulty and their own play
count. The generator is in the public repo. A player can run `_make_board()`
locally and get the exact mine layout for their next board, which defeats the
server-side reveal validation and the WC2026 leaderboard.

**Fix:** mix a server secret into the seed, e.g.
`hmac.new(SECRET_KEY, raw, sha256)`. Layouts are stored in
`WC2026BoardState.mine_layout` when a board is created, so boards already in
progress are unaffected; only new boards change. Owner: WC2026 feature (@richard).

### R2 — PvP mines placed with the global Mersenne Twister (B311, `duel.py:36`) — Low

`_place_mines` uses `random.sample` from the shared module-level generator.
Mersenne Twister is predictable once enough output is observed, and every
finished duel reveals its mine positions. Recovering the state from
`random.sample` output is hard in practice (outputs are reduced and the same
generator is also consumed by the bot), so the risk is low, but the fix is
one line: `random.SystemRandom().sample(pool, mines)`.

---

## False positives

| ID | Location | Why it is not a problem |
|----|----------|-------------------------|
| B608 (medium) | `main.py:935`, `main.py:947` | `archive_guest_scores`: table and column names come from a hard-coded `specs` list; the only runtime values (`:src`, `:archived_at`) are bound parameters. |
| B608 (medium) | `admin_routes.py:1930` | `_fmt_flagged_time`: `table_name` must be a key of the hard-coded `_TIME_FIELDS` dict (unknown names return early); `id` is a bound parameter. |
| B105 | `database_template.py:21` | Placeholder `"the_password"`, replaced from `.env` at deploy time. |
| B105 | `main.py:1381`, `wc2026_routes.py:158` | The "password" is the dict key `guest_token` being set to `None`. |
| B404 | `main.py:10`, `admin_routes.py:5` | Import of `subprocess`; usage reviewed below. |
| B603 / B607 | `main.py:585` | `/health` runs the fixed command `git rev-parse HEAD` (no user input, no shell) and only answers requests from 127.0.0.1. |
| B603 | `admin_routes.py:565` | `_git()` is only called with fixed arguments (`rev-parse HEAD`, `git log ...`), no shell, 5 s timeout, inside the admin dashboard. |

---

## Acceptable as written

### B311 — non-cryptographic `random` (21)

Each one generates game content where predictability does not matter, because
the result is shown to the player anyway or is deliberately deterministic:

| Location | Use | Why acceptable |
|----------|-----|----------------|
| `numbers_match_generator.py:65` | Daily board shuffle, seeded from the date | Board is fully visible; determinism is the point (same board for everyone). |
| `tametsi_generator.py:212`, `:258` | Tametsi daily puzzles, seeded from level + date | Logic puzzle shown in full; same puzzle for everyone by design. |
| `sudoku_routes.py:178` | Seed for a random (non-daily) Sudoku | Puzzle is shown in full; no leaderboard advantage from predicting it. |
| `phase7_drills/generator.py` ×12 (354, 369, 382, 414, 449, 774, 902, 1023, 1161, 1217, 1308, 1363) | Training drill boards from explicit seeds | Deterministic seeds are required for reproducible drills; no competition. |
| `bots/minesweeper_bot.py` ×4 (59, 61, 65, 167) | Bot move choice | Only affects how the bot plays. |
| `duel_routes.py:510` | PvP bot picks a cell | Only affects how the bot plays. |

### B110 / B112 — `except: pass` / `except: continue` (9 + 3)

| Location | Context | Why acceptable |
|----------|---------|----------------|
| `duel.py:457, 490, 521, 552, 571`, `duel_routes.py:659` | `ws.send_json(...)` to a player who may have disconnected | A dead socket must not crash matchmaking; the disconnect is handled by the receive loop. |
| `duel_routes.py:672, 1046, 1106` | `json.loads` of a WebSocket message | Malformed client messages are skipped instead of killing the connection. Correct behaviour. |
| `duel_routes.py:333` | DB write inside the game loop | Intentional ("never crash the game loop"). **Improvement:** log the exception (`logger.exception`) so lost writes are visible; not a security issue. |
| `phase7_drills/schema_sql.py:154, 162` | Probing for a DB engine, falling back to the next option | Fallback chain; the function still raises if none works. |

### B101 — `assert` (25)

All in `phase7_drills/smoke_test.py`, a standalone test script. Asserts are the
intended check mechanism there and the file is not imported by the app.

---

## Follow-ups

1. **R1** — HMAC the WC2026 seed with `SECRET_KEY` (owner: @richard).
2. **R2** — `SystemRandom` for PvP mine placement (owner: @earl, PvP).
3. Log instead of silently passing in `duel_routes.py:333`.
4. Exclude `./phase7_drills/smoke_test.py` from Bandit, or add `# nosec B101`,
   to keep the report focused.
