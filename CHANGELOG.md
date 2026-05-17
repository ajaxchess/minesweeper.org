# minesweeper.org Session Changelog

## Session: 2026-05-16

### F97 Tametsi 2026 World Cup — Guest Play
Brought the `/2026worldcup` tree in line with the project's guest-play-then-claim convention. Non-logged-in visitors can now pick a fan team, play Easy/Hard Tametsi boards, and earn points for that country. Logging in remains the path to appear on the individual "biggest fans" leaderboard.

- Spec addendum appended to `FeatureRequests/TametsiWorldCup.md` covering motivation, schema delta, identity model, endpoint behaviour, anti-abuse, leaderboard semantics, and merge-on-login.
- Schema (`database_template.py`): made `wc2026_board_states.email` and `wc2026_scores.email` nullable; added `guest_token VARCHAR(36) NULL` (with matching indexes) to both tables. New idempotent `_migrate_wc2026_guest_play(conn)` runs the column-nullability and index DDL from `_apply_migrations()`.
- Identity helpers in `main.py`: `_wc_player_identity(request, db)` resolves the player as either a logged-in email or a guest session UUID; `_wc_ensure_guest_token(request)` issues a `request.session["guest_token"]` lazily; `_wc_lookup_board(...)` factors the repeated board-row lookup.
- Endpoint changes (`main.py`): every `/api/wc2026/board/*` route plus `/api/wc2026/set-fan` now accepts guests instead of returning 401. `/api/wc2026/board/{slug}/{difficulty}/solve` carries `@limiter.limit("5/minute")` and a per-cookie 200 pts/day soft cap (`WC2026_GUEST_DAILY_POINT_CAP`); response includes `is_guest` and `capped` flags.
- Board generation (`wc2026_board.py`): `get_or_create_board` and `_make_board` accept `(email=None, ..., guest_token=None)`; deterministic seed includes a prefix (`u:` / `g:`) so guest and account identity spaces can't collide.
- Page routes: `/2026worldcup/{slug}` now renders boards for any player carrying a fan flag (guest cookie or logged-in profile). Leaderboard queries: `_country_leaderboard` and `_individual_leaderboard` filter to `email IS NOT NULL`; `_fan_country_leaderboard` aggregates everything so guest points roll into country totals.
- Templates: `wc2026_country.html` and `wc2026_main.html` now show four banner states (logged-in + flag / logged-in no flag / guest + flag / guest no flag). The "Log in to play" gate on the country page is gone; the play-gate now only checks `wc_fan`. The guest-with-flag banner includes an inline "Change team" picker. Three new translation keys (`wc_guest_login_cta`, `wc_guest_pick_team_prompt`, `wc_change_team`) ship with English fallbacks via Jinja `default`.
- Client (`static/js/tametsi_wc.js`): solve banner appends a "Log in to claim..." CTA when `result.is_guest`, and a red cap-warning when `result.capped`.
- Merge-on-login (`/auth/callback`): extended the existing `guest_token` claim loop to cover `WC2026Score` (reassign email + null token + copy display_name from profile) and `WC2026BoardState` (conflict-aware merge — existing logged-in board wins, otherwise reassign guest row). Also copies any session `wc2026_fan` onto `UserProfile.wc2026_fan` if the new profile didn't already have one.

### Follow-ups
- Translation backfill for `wc_guest_login_cta`, `wc_guest_pick_team_prompt`, `wc_change_team` across the 9 supported languages (tracked as F100).

## Session: 2026-03-15

### About Page
- Added 2025 World Championship winner: Xian-Yao Zhang (stan kimi), held in Madrid.

### Localization
- Added **Korean** (`ko`) full translation (93 keys).
- Added **Japanese** (`ja`) full translation (93 keys).
- Added `nav_rush` translation key for all 9 languages (the "Rush" nav item was previously untranslated).
- Added `ko` and `ja` to the allowed languages in `/set-lang`.
- Added KO / JA options to the language selector in `base.html`.

### Tentaizu Page
- Added history entry: *2008–2009 — The puzzle appeared regularly in Southwest Airlines' Spirit magazine, popularising the game with western audiences.*

### Quests Page
- Removed the word "permanently" from the rewards section text.

### Easy 5×5 Tentaizu — Score Saving Bug Fix
- Root cause: `puzzle_date` DB column was `String(10)`, too short for the prefixed key `easy5x5:YYYY-MM-DD` the JS was sending.
- Fix: created a dedicated `TentaizuEasyScore` table in `database_template.py`.
- Added `/api/tentaizu-easy-scores` POST and GET endpoints in `main.py`.
- Updated `static/js/tentaizu_easy.js` to use the new endpoint with a plain `YYYY-MM-DD` date.

### Diana / Classic Theme — Fuzzy Links Bug Fix
- Root cause: `html[data-skin="classic"] nav a:visited` (specificity 0,2,3) was overriding `.game-landing-links a` (0,2,2), setting link colour to `#ffffff` on a light background.
- Fix: extended the `.game-landing-links` rule to also cover `:visited`, giving it specificity (0,3,2) which wins.

### Duel Board Orientation
- Swapped `ROWS` and `COLS` constants (30×16 → 16×30) so the private duel board is portrait, matching PvP.

### Quick Mode — Duel & PvP
- Added `QUICK_ROWS, QUICK_COLS, QUICK_MINES = 20, 10, 35` constants to `duel.py`.
- `DuelGame` now stores a `submode` field (`"standard"` or `"quick"`).
- `create_game()` accepts a `submode` parameter.
- Added a separate quick PvP matchmaking queue (`_pvp_quick_queue`) with `pvp_quick_enqueue / dequeue / queue_length` helpers.
- `/duel?m=quick` and `/pvp?m=quick` routes serve the quick board; default is `standard`.
- `/duel/{game_id}` now reads dimensions from the game object instead of hardcoded constants.
- Added `/ws/pvp/quick/{player_id}` WebSocket endpoint for quick PvP matchmaking.
- Added **Standard / ⚡ Quick** mode selector tabs to the duel/pvp page UI.
- PvP badge now shows dynamic dimensions instead of hardcoded `24×16, 75 mines`.
- `duel.js` reads `data-submode` and connects to the correct WS endpoint; "New Duel" rematch link preserves the current mode.

### Blog — "Lady Di's Mines"
- Renamed the blog title from "Blog" to **Lady Di's Mines** (page `<h1>`, `<title>`, and OG title).
- Added `ladydi-walks-minefield.png` to `static/img/` (served at `/static/img/ladydi-walks-minefield.png`).
- Added `saaspocalypse.png` to `static/img/` (served at `/static/img/saaspocalypse.png`).
- Added `image` and `publisher` front matter fields to `blog/lady-di-blog-post.md`.
- Added `image` and `datePublished` front matter fields to `blog/1_saaspocalypse-blog-post.md`.
- Blog post route now reads `image`, `publisher`, and `datePublished` from front matter and passes them to the template.
- Added `{% block jsonld %}` to `blog_post.html` generating a `schema.org/BlogPosting` JSON-LD block with `headline`, `url`, `datePublished`, `description`, `image`, `author`, and `publisher`.
- `datePublished` in JSON-LD uses the full ISO 8601 datetime (e.g. `2026-03-15T15:00:00Z`) when provided; falls back to the plain date string.
- Added `{% block og_image %}` override to `blog_post.html` so the front matter image is used for social sharing.
- Added hero image display in the blog article body (`<img class="blog-article-image">`).
- Added `.blog-article-image` CSS rule (max-width 520 px, centred, rounded corners).
- Added `.duel-mode-tabs` / `.duel-mode-tab` CSS for the new mode selector tabs.
