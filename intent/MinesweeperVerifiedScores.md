# Classic Minesweeper — Verified Scores

**Status:** in-progress
**Feature ID:** F-MS-VERIFY
**Author:** Richard Cross
**Date:** 2026-11-11

---

## Problem / Motivation

`POST /api/scores` stores whatever time the browser sends. Anyone can post
`time_ms: 1` for Expert from the developer tools or `curl` and take first place on
the leaderboard we show on the home page. The 2026-11 security review found this on
about twenty score endpoints; only Numbers Match (F-NM-VERIFY) replays the game on
the server. Classic Beginner, Intermediate and Expert are the leaderboards players
care about most, so they come first.

We already have what a check needs. The browser records every click of a game as a
move log (`[t_ms, type, row, col]`, F74 Rewind), and `board_hash` is the complete
mine layout. The server can replay the log on that board and see for itself whether
the game was won, and when.

Replaying every game would spend server time on scores nobody will ever see. A
score only matters once it is on a high score list, so only those are checked.

---

## Success Criteria

- [ ] A classic score appears on a leaderboard only if the server replayed the
      game from its move log and the replay ends in a win on the submitted board.
- [ ] A game cannot claim less time than really passed since the server issued its
      start token, and each token can be used for one score.
- [ ] The time, 3BV and click counts shown for a verified score come from the
      replay, not from the request.
- [ ] Only scores that could reach a high score list are replayed; the rest are
      stored without replay and are not listed.
- [ ] A forged `POST /api/scores` (no log, or a log that does not win the board)
      never shows on any classic leaderboard, the archive or the leaderboard hub.
- [ ] The browser and the server apply identical click rules, enforced by a test
      that replays games recorded from the real `minesweeper.js`.
- [ ] Honest players notice nothing: no new prompt, no slower first click.

---

## Scope

**In this feature:**
- Signed one-time start token (`POST /api/scores/start`), fetched in the
  background on the first click of a game.
- `minesweeper.js` sends the move log, the token and the chording setting with the
  score.
- Server replay engine (`minesweeper_engine.py`) with the browser's exact rules.
- A verification status on every `scores` row and one shared filter used by every
  query that lists classic scores.
- Modes: beginner, intermediate, expert, custom and evil, on the web client.

**Out of scope (future):**
- The msmobile iOS/Android app. It posts scores without a move log, so its scores
  stay listed under a grace rule until an app release records the log (see Open
  Questions).
- Every other game (Rush, Cylinder, Toroid, Hexsweeper, 2048, …). Each needs its
  own move log and rules engine; the status column and the listing filter are
  written so they can be reused.
- Detecting a bot that really plays the board at human speed. A start token only
  proves that the wall-clock time passed.
- Re-verifying scores saved before this feature. Many have a linked
  `game_replays` row, so a later backfill is possible.
- Server-generated boards. The board is still generated in the browser on the
  first click.

---

## Key Design Decisions

**Flow**

1. First click of a game → the browser starts `POST /api/scores/start` without
   waiting for it. The server returns an `itsdangerous` token signed with
   `SECRET_KEY` holding a random nonce, timestamped at issue. No database write.
2. The player plays; every click is appended to the move log as today.
3. On a win the browser posts the score with three new fields: `log`, `game_token`
   and `chording` (the chord setting changes what a double-click does, so the
   server must know it).
4. The server decides whether the score is a leaderboard candidate (below). Only
   candidates are replayed.

**Which scores are candidates**

A score is a candidate when fewer than `SCORE_LIST_SIZE` (15) different players
have a better listed time today in the same mode and guess setting. This one test
covers every list: the daily list shows the best 15 scores and the weekly, monthly,
season, yearly and all-time lists show the best 15 players, and anyone beaten by 15
players today is beaten by the same 15 in every longer period.

Early in the day almost every score is a candidate. That is acceptable: a replay is
a few milliseconds even for Expert, far less than the bootcamp analysis each game
already triggers.

**Verification status** (`scores.verification`)

| Status | Meaning | Listed |
|---|---|---|
| `NULL` | Saved before this feature | yes |
| `verified` | Candidate, replay succeeded | yes |
| `app` | Candidate from the mobile app, no log available (grace rule) | yes |
| `unchecked` | Not a candidate, stored without replay | no |
| `unverified` | Candidate with no usable token or log | no |
| `failed` | Candidate whose replay or time check failed | no |

A score that fails is stored, not rejected with an error. An honest player in a
tab opened before the deploy still gets "score saved" and keeps the game in their
own history; a forger learns nothing from the response beyond `verified: false`;
and admins can see failed attempts on `/admin/hscleaning`.

`unchecked` scores are hidden so that deleting or flagging a score above them can
never promote an unreplayed score onto a list.

**What the replay checks**, in order:

1. Token signature and age (12 h max), nonce not used before.
2. `board_hash` decodes to exactly `mines` mines on a `rows × cols` board; for
   beginner, intermediate, expert and evil the dimensions match the mode.
3. The log is well formed: at most 10,000 entries, integer fields, coordinates on
   the board, timestamps never decreasing.
4. Replaying the log never reveals a mine, and the board is won exactly on the
   last entry.
5. The claimed `time_ms` is within 1.5 s after the last log entry, and is not
   longer than the wall-clock time since the token was issued plus 5 s.

For a verified score the server stores the 3BV it computes from the board and the
click counts it counts from the log.

**Rules the engine must share with `minesweeper.js`**

- A right-click cycles a hidden cell: none → flag → question mark → none.
- A left-click does nothing on a flagged or revealed cell; a question mark does not
  block it.
- An opening spreads through blank cells but skips cells carrying a flag or a
  question mark.
- A chord acts only on a revealed number whose flagged neighbours equal the
  number, and only when the player has chording on.
- Evil mode ignores every left-click before the first click on the top-right cell.
- Nothing is recorded after the game ends.

**Rollout switch** — `settings.SCORE_VERIFICATION_MODE`

- `enforce` (default): as described above.
- `observe`: replay candidates and record the status, but list everything as
  before. Useful for a few days after deploy to measure false failures.
- `off`: no replay, no status.

**Data model**

- `scores.verification VARCHAR(16) NULL`
- `scores.game_nonce VARCHAR(32) NULL`, unique index

---

## Open Questions

1. **Mobile app grace rule.** `X-Client-Type: ios_app` is a header anyone can send,
   so the grace rule is also a bypass for someone who reads this file. It is on by
   default (`SCORE_VERIFICATION_APP_GRACE`) because hiding every app score until
   the next app release punishes real players. Decide whether to keep it, and
   schedule move-log recording in msmobile so it can be removed.
2. **Per-board lists** (`/api/replay-scores`) merge classic scores for one board.
   They use the same filter, so an unreplayed score is not shown there either.
   Confirm that is what we want for shared custom boards.
3. **Guests' duplicate rule.** One guest score per `board_hash` is accepted
   site-wide today. With verification on, should a hidden score still block a
   later honest one on the same board? Boards are random, so this is theoretical.

---

## Implementation Notes

*Filled in when work completes.*
