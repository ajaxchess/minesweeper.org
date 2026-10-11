# Numbers Match — Verified Scores

**Status:** done
**Feature ID:** F-NM-VERIFY (part of F-NM)
**Author:** Gisela Velazco
**Date:** 2026-10-11

---

## Problem / Motivation

The score API stored whatever score and time the browser sent. Anyone could
post `score=99999, time_secs=1` from the developer tools or `curl` and take
first place, and the score-per-second ranking made fake short times even more
valuable. Blocking F12 does not help: requests can be sent without a browser.
The only real fix is for the server to compute the score itself.

---

## Success Criteria

- [x] A score is stored only if the server can replay the game move by move from
      the original board and every move is legal.
- [x] The stored score and time come from the replay, never from the client.
- [x] A game cannot claim to have taken less wall-clock time than really passed
      since it started, or be played faster than a human can tap.
- [x] Each game can be submitted once.
- [x] Web, mobile app and server use identical rules, enforced by tests.

---

## Scope

**In this feature:**
- Signed one-time game token issued when a leaderboard game starts.
- Move log recorded by the web client and the nmmobile app.
- Server-side replay engine (`numbers_match_engine.py`).
- nmmobile switched to the website's boards (New York date, server revision,
  deterministic difficulty boards) so the server can rebuild them; this also
  puts mobile and web players on the same leaderboards.

**Out of scope (future):**
- Bot detection beyond the minimum time per match (a solver that plays at human
  speed is still accepted).
- Re-verifying scores saved before this feature.

---

## Key Design Decisions

**Flow**

1. Leaderboard game starts → client `POST /api/numbers-match-start {puzzle_id}`.
   The server returns an `itsdangerous` token signed with `SECRET_KEY`
   containing the puzzle id and a random nonce, timestamped at issue.
2. Client plays and records every event (see format below).
3. On a win, client `POST /api/numbers-match-scores` with `name`, `puzzle_date`,
   `game_token` and `moves`. `score`, `time_secs` and `lines_added` may still be
   sent but are only used to log client/server drift.
4. Server checks, in order: token signature and age (24 h max) → token puzzle
   matches → nonce not used before → board can be rebuilt → replay is legal and
   clears the board → replay time ≤ time since the token was issued + 5 s →
   replay time ≥ 150 ms × matches. Any failure returns 422 with the reason.
5. Stores the replay's score, `max(1, time_ms // 1000)` seconds, lines added and
   the nonce (`numbers_match_scores.game_nonce`).

**Move log** — list of `[kind, t_ms, ...]`, `t_ms` = ms since the first cell
press (0 before it), never decreasing:

| Event | Meaning |
|-------|---------|
| `["m", t, i, j]` | match cells `i` and `j` (indices into the board at that moment) |
| `["h", t]` | hint used (only logged when a pair existed and a hint was spent) |
| `["u", t]` | undo |
| `["a", t]` | add lines |

**Which boards can be verified** — only puzzle ids the server can rebuild:
`YYYY-MM-DD-vN` (daily, `generate_daily(date, ":vN")`) and
`YYYY-MM-DD-{easy|medium|hard|expert}-vN` (difficulty, `generateBoardClient`
seeded with the puzzle id, ported to Python). Anything else is not on a
leaderboard.

**Mobile app** — decision 2026-10-11: submissions without a move log are
rejected, not stored as unverified. The nmmobile code in this repo is updated;
a store build that predates this change can no longer save scores.

**Why not disable F12** — DevTools blocking is bypassed through the browser menu,
`curl` or a proxy, and breaks accessibility tools. Server-side replay makes
DevTools useless for cheating.

---

## Implementation Notes

- `numbers_match_engine.py`: rules, `board_for_puzzle()`, `replay()`; Python
  ports of mulberry32 / FNV-1a for difficulty boards.
- `numbers_match_routes.py`: `/api/numbers-match-start`, verified
  `/api/numbers-match-scores`. Constants `TIME_TOLERANCE_MS = 5000`,
  `MIN_MS_PER_MATCH = 150`, `GAME_TOKEN_MAX_AGE_S = 24 h`.
- `database_template.py`: `NumbersMatchScore.game_nonce` + idempotent migration.
- `static/src/js/numbers_match.js` (`?v=21`): `logMove()`, `requestGameToken()`;
  the win time shown uses the same rounding as the server.
- nmmobile: reducer records moves with timestamps from the dispatcher;
  `fetchToday()` / `startGame()` in `apiService.js`; daily and difficulty boards
  match the website; leaderboard screen defaults to today's `YYYY-MM-DD-vN`.
- **Parity tests** — `tests/fixtures/numbers_match_js_games.json` holds games
  played by the real web client in Node (`gen_numbers_match_js_games.js`, stub
  DOM, its own click/hint/undo/add-lines handlers) and by the nmmobile reducer
  (`gen_numbers_match_mobile_games.mjs`). `tests/test_numbers_match_engine.py`
  replays them all and requires identical boards and scores; it also covers
  tampering (illegal/dropped moves, extra hints/undos/add lines, bad timestamps,
  malformed events). `tests/test_numbers_match.py` covers the API (forged and
  reused tokens, wrong puzzle, legacy payloads, time checks).
  **Regenerate both fixtures after any rule change** in the web JS, the mobile
  engine or `numbers_match_engine.py`.
