# Classic Minesweeper App — Move Log for Verified Scores

**Status:** idea
**Feature ID:** F-MS-VERIFY-APP
**Author:** Richard Cross
**Date:** 2026-11-26

---

## Problem / Motivation

F-MS-VERIFY replays classic scores from the website on the server before they can
be trusted on a high score list. The mobile app (`mobile/msmobile`, iOS and Android)
sends no move log and no start token, so its scores cannot be replayed. Today they are
saved as `app` and listed anyway under `SCORE_VERIFICATION_APP_GRACE`.

That grace rule is a hole: the app is recognised only by the `X-Client-Type` request
header, so anyone can post a fake time with `X-Client-Type: ios_app` and it will be
listed, even in `enforce` mode. In the last 7 days (to 2026-11-26) 52 of 217 classic
scores came in as `app` (all others verified, none failed — see
`/admin/score-verification`, F-MS-VERIFY-STATS). We cannot turn the grace rule off,
and so cannot close the hole, until the app sends a move log the server can replay.

---

## Success Criteria

- [ ] A game won in the app (iOS and Android) is submitted with a start token, a move
      log and the board, and is saved as `verified`.
- [ ] Honest app games never fail verification: replaying games recorded from the app's
      own game code gives the same result on the server (parity test, like the web's).
- [ ] Scores from app builds released before this feature are still accepted while
      players upgrade; after an agreed date the grace rule is switched off and an
      app score without a valid log is no longer listed in `enforce` mode.
- [ ] `/admin/score-verification` shows app scores moving from `app` to `verified`
      (by client), so we can see when it is safe to switch the grace rule off.

---

## Scope

**In this feature:**
- msmobile records every tap as `[t_ms, type, row, col]` (`l` reveal, `r` flag,
  `c` chord) from the first reveal, exactly like the website's F74 Rewind log.
- msmobile asks `POST /api/scores/start` for a start token when a game starts and
  sends `game_token`, `log`, `board_hash` and `chording` with the score.
- The app's click rules are brought in line with the server replay (see below), or the
  server learns the app's rules — one of the two, decided before building.
- A parity fixture recorded from msmobile's reducer (`useGameState.js`) and a server
  test that replays it, like `tests/fixtures/minesweeper_js_games.json`.
- New app builds for iOS and Android.

**Out of scope (future):**
- Numbers Match in `mobile/nmmobile` (F-NM-VERIFY) and the other games.
- Offline play: a game started without a network connection has no start token. It is
  saved as `unverified` and kept on the phone (the app already saves scores locally).

---

## Key Design Decisions

**The app's rules differ from the server's replay in two places** (checked
2026-11-26 against `mobile/msmobile/src/hooks/useGameState.js` and
`minesweeper_engine.py`). Either would make honest app games fail:

1. **Flags.** The app toggles a flag on and off. The website (and so the server)
   cycles flag → question mark → nothing. Replayed on the server, an app player who
   removes a flag leaves a question mark, which the server's flood fill will not open
   and a chord does not count. *Options:* the app logs a flag removal as two `r`
   entries, or the score says `"marks": false` and the server replays two-state flags.
   Recommended: the server option (`marks`), because it is explicit and testable.
2. **Flood fill through flags.** When the app opens an empty area it also opens cells
   the player had flagged by mistake; the server leaves marked cells closed. A game
   with a wrong flag inside an empty area wins in the app but not on the server.
   Recommended: change the app to leave flagged cells closed, as the website does.

**Other points:**
- `t_ms` counts from the first reveal; the server checks that the last move is no
  later than the time since the start token was issued (plus 5 s).
- The start token is fetched at New Game, not at the first tap, so a slow network does
  not delay play; if it has not arrived when the game is won, wait up to 3 s, then
  submit without it (the score is saved as `unverified`).
- **Android identifies itself as `ios_app`.** `apiService.js` hard-codes
  `X-Client-Type: ios_app` for both platforms. Fix it to send `android_app` on Android
  so the statistics page can tell them apart.
- **Ending the grace rule.** Old builds keep sending no log. Options: switch
  `SCORE_VERIFICATION_APP_GRACE` off once most players have upgraded (watch the `app`
  count fall on `/admin/score-verification`), or have new builds send an app version
  header and apply the grace rule only to older versions. Decide before release.
- Classic click rules would then exist in three places (website, server, app); add the
  app to the "Known Issues" note in `CLAUDE.md` with the command that regenerates its
  parity fixture.
