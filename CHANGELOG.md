# minesweeper.org Session Changelog

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
