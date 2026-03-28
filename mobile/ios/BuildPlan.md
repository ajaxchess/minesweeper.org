# Minesweeper.org Mobile App — Build Plan

## Overview

React Native + Expo managed workflow. Target: iOS and Android.
See Outline.md for full requirements, APISpec.md, BoardHashSpec.md, and NoGuessSolverSpec.md for technical specs.

---

## Phases

### Phase 1 — Project Scaffolding
Initialize the Expo managed workflow project, set up React Navigation for the
screen stack, configure the theme provider, and wire up AsyncStorage. Nothing
app-specific — just the skeleton everything else builds on.

**Deliverables:**
- Expo project initialized under `mobile/app/`
- React Navigation stack configured (Game, Leaderboard, HowToPlay, Strategy, Settings, About)
- AsyncStorage wired and accessible via a shared service module
- Theme context provider in place (auto/light/dark)

---

### Phase 2 — Core Game Engine
Port four functions from `static/js/minesweeper.js` verbatim into a
`gameEngine.js` module: `neighbors`, `placeMines`, `placeMinesNoGuess` /
`isSolvable`, `calc3BV`, and `calcBoardHash`. These are pure JS with no DOM
dependency and require no changes except swapping `btoa` for `Buffer`.

Write unit tests against the known test vectors in `BoardHashSpec.md` and
`NoGuessSolverSpec.md` before wiring to any UI.

**Deliverables:**
- `src/gameEngine.js` with all ported functions
- Unit tests passing for all BoardHashSpec.md test vectors
- Unit tests confirming isSolvable returns correct results for known boards

---

### Phase 3 — Board UI & Touch Handling
Render the mine grid as a React Native component. Implement all touch
interactions and the game timer.

**Deliverables:**
- `BoardView` component rendering cells, numbers, flags, mines for all 3 board sizes
- Tap to reveal, long-press to flag, flag mode toggle button
- Chord tap (reveal numbered cell when adjacent flag count matches value)
- Pinch-to-zoom on the board
- Timer starting on first tap, stopping on win/loss
- Works correctly on both iPhone and iPad screen sizes

---

### Phase 4 — Win Flow & Score Submission
On win: compute `board_hash`, `bbbv`, `efficiency`, elapsed `time_ms`.
Prompt for player name if not yet stored. POST to `/api/scores`.
Store locally on failure.

**Deliverables:**
- Post-win modal: stats display, name prompt (if unset), Submit Score button
- `apiService.js`: POST `/api/scores` with `X-Requested-With: XMLHttpRequest`
  and `X-Client-Type: ios_app` headers (see APISpec.md)
- On API failure: save score to AsyncStorage `scores:{mode}:{guess}` key
- On API success: save score with server `id` to AsyncStorage for deduplication
- AsyncStorage scores capped at top 20 per mode, sorted by `time_ms` ascending

---

### Phase 5 — Leaderboard
Fetch server scores and merge with local scores. Display below the board.

**Deliverables:**
- `GET /api/scores/{mode}` with `period` selector (Daily / Season / All Time)
- Local + server score merge, deduplicated on `(mode + time_ms + board_hash)`
- Leaderboard table columns: Name | Time | 3BV | 3BV/s | Efficiency | Board
  - 3BV/s = `bbbv / (time_ms / 1000.0)`
  - Efficiency = `bbbv / (left_clicks + right_clicks + chord_clicks)` (client-side)
  - Board = first 8 characters of `board_hash`
- Period toggle: Daily / Season / All Time

---

### Phase 6 — Supporting Screens
Static and WebView-based content screens.

**Deliverables:**
- **About screen**: app version, link to minesweeper.org, "Created by Regis.Consulting",
  support contact ajaxchess@gmail.com / 312-224-1752
- **How-to-Play screen**: WebView loading `static_html/howtoplay_content.html`
- **Strategy screen**: WebView loading `static_html/strategy_content.html`
- **Settings screen**: player name, default mode (beginner/intermediate/expert),
  default guess/no-guess, theme (auto/light/dark)
  - Persisted via AsyncStorage keys: `prefs:player_name`, `prefs:default_mode`,
    `prefs:default_guess`, `prefs:theme`

---

### Phase 7 — Theme System
Follow OS by default; allow lock to light or dark in preferences.

**Deliverables:**
- Auto mode: uses React Native `useColorScheme()` — light during day, dark at night
  matching iOS system setting
- Light and Dark modes: override OS setting, persisted in `prefs:theme`
- Theme applied globally via context; all screens styled accordingly

---

### Phase 8 — App Store Preparation

**Deliverables:**
- App icon and splash screen at all required Expo/App Store dimensions
- `app.json` configured: bundle ID, version, display name "Minesweeper.org",
  category Games > Puzzle, age rating 4+, privacy URL https://minesweeper.org/privacy
- EAS Build producing a production IPA
- TestFlight build uploaded and tested
- App Store submission under Richard Cross individual developer account

---

## Task List

| # | Phase | Task | Status |
|---|---|---|---|
| 1 | 1 | Initialize Expo project, configure React Navigation, AsyncStorage, theme provider | pending |
| 2 | 2a | Port neighbors, placeMines, placeMinesNoGuess, isSolvable into gameEngine.js | pending |
| 3 | 2b | Port calc3BV and calcBoardHash; validate against spec test vectors | pending |
| 4 | 3a | Build Board component — render cells, mines, numbers, flags for all 3 board sizes | done |
| 5 | 3b | Implement touch handling — tap, long-press, flag mode button, chord tap, pinch-to-zoom | done |
| 6 | 3c | Implement game timer — starts on first tap, stops on win/loss | done |
| 7 | 4a | Implement AsyncStorage service — prefs keys and score keys (6 modes, top 20, sorted) | done |
| 8 | 4b | Implement API service — POST /api/scores with required headers | done |
| 9 | 4c | Implement win flow — compute stats, name prompt, submit, offline fallback | pending |
| 10 | 5a | Implement leaderboard fetch — GET /api/scores/{mode} with period selector | pending |
| 11 | 5b | Implement score merge and deduplication — local + server on (mode + time_ms + board_hash) | pending |
| 12 | 5c | Build leaderboard UI — Name, Time, 3BV, 3BV/s, Efficiency, Board hash (8 chars) | pending |
| 13 | 6a | Build About screen | pending |
| 14 | 6b | Build How-to-Play and Strategy screens as WebViews | pending |
| 15 | 6c | Build Settings screen | pending |
| 16 | 7 | Implement theme system — auto/light/dark, persisted in AsyncStorage | pending |
| 17 | 8a | Design and produce app icon and splash screen assets | pending |
| 18 | 8b | Configure app.json for App Store submission | pending |
| 19 | 8c | EAS Build, TestFlight, App Store submission | pending |

---

## Parallelization Notes

Tasks 1–12 follow a strict dependency chain (scaffold → engine → UI → scores → leaderboard).

Tasks 13–16 (supporting screens + theme) are independent of the game engine and
can be developed concurrently with Phases 3–5 by a second developer.

Task 17 (icon/splash) can be done at any time before Task 18.

---

## Risk Items

**Phase 3b — Touch handling**: tap / long-press / chord / pinch all coexisting
on React Native gesture responders is the most finicky UI work in the project.
Prototype this early.

**Phase 5b — Score deduplication**: edge case where a score was submitted
offline and later appears on the server. Must match on all three of
`(mode + time_ms + board_hash)` and prefer the server record (which has an `id`).

**Phase 8c — App Store review**: Apple review timelines are unpredictable.
Submit early. Ensure the privacy policy URL is live at https://minesweeper.org/privacy
before submission.
