List of active features

F8 Improved Mobile Browser Support

F9 SEO improvements
   For general SEO improvements.  If the improvement is for a specific platform, use Bing SEO improvements or Google SEO improvements

F13 Quests

F14 Website Analytics Google Analytics

F15 Website Analytics on local admin page at /admin and subpages

F16 Add a blog

F19 Secret admin mode that displays site statistics

F20 Tentaizu theme

F22 Google SEO improvements

F23 PVP/Duel improvements
    View opponent's board beside your board for PVP
      Do we want a delay before we see you opponent's latest move?
        * i.e. Suppose you have been playing for 20 seconds, opponent board
          shows their state as of 15 seconds.
          What is the right amount of delay?  0 could be the right answer
    Implement a first click clear for both you and opponent
    Implement changes in behavoir when you click a mine
    Implement rating system similar to Chess Elo
      Display rating on profile
      Match making based on rating
    Replay feature and game board hash?
    Implement same features for Duel
    Implement bots

F24 Add Kanban board to admin section of the site and create a link

F26 Mosaic game mode

F27 Tentaizu game improvements

F28 Blog comments
  Logged-in users can comment on blog posts
  Comments require admin approval before appearing
  Admin moderation page at /admin/blog

F29 PvP bot opponent
   Constraint-based Minesweeper AI in bots/minesweeper_bot.py (easy/medium/hard).
   Bot lobby at /pvp/bot; game at /pvp/bot/play?m=standard&d=medium.
   "🤖 vs Bot" tab added to the PvP mode switcher.

F30 PvP rankings sortable columns
   Wins and Elo columns in win rankings table are clickable to toggle ascending/descending sort.

F31 Archive anonymous PvP results nightly
   Daily cron job moves PvP results with no registered winner to anonymous_pvp_results backup table.

F42 Mosaic how-to-play page and expanded mega menu
  - New page at /mosaic/how-to-play (templates/mosaic_howto.html) with rules, controls,
    solving patterns, and strategy — parallel structure to /tentaizu/how-to-play
  - Subnav cards added to /mosaic/standard and /mosaic (easy) linking to each other
    and to /mosaic/how-to-play
  - Mega menu Puzzles group expanded: Mosaic Daily (9×9), Mosaic Easy (5×5),
    How to Play Mosaic — replacing the single Mosaic card

F36 Mega menu navigation for dark / light / tentaizu skins
  - Replaces the old flat nav with a 5-group drop-down mega menu on non-classic skins
  - Groups: Play (Beginner/Intermediate/Expert/Custom/Rush/Leaderboard), PvP, Puzzles, Variants, More
  - Classic (Diana) skin retains its existing sidebar nav unchanged
  - Each group opens a full-width panel of icon+title+description cards on click
  - CSS scoped to html:not([data-skin="classic"]); JS toggleMega() opens/closes panels

F38 Light theme

F39 Use light theme during daylight hours based on client browser local time, defaulting to dark otherwise

F41 SEO structured data and page differentiation
  - Self-referencing JSON-LD url on variant and tool pages (cylinder, toroid, board-generator, replay)
    Previously all inherited the homepage url from base.html; each page now declares its own canonical url in JSON-LD
  - board-generator and replay use WebApplication schema type (more accurate than VideoGame for interactive tools)
  - /pvp differentiated from /duel: distinct title, meta description, canonical, keywords, og:*, and JSON-LD
    /pvp now targets "competitive minesweeper / minesweeper ranked / minesweeper elo" keyword cluster
    /duel retains its "challenge a friend / 1v1" positioning

F43 XYZZY Cheat Code (Replay mode only)
  - Classic Windows 98/2000/XP Minesweeper easter egg faithfully recreated
  - Activation sequence: type "xyzzy", press Shift+Enter, then press Shift
  - A 1×1 pixel appears at top-left corner: black = mine under cursor, white = safe
  - Available on /variants/replay/ only (not standard, competitive, or daily games)
  - Requires login — guests see a toast with a Google login link instead
  - Games completed with cheat active are excluded from the replay leaderboard
  - Documented in /how-to-play#cheatcode with history of the XYZZY origin
    (Colossal Cave Adventure, 1975)

F44 Custom Mosaic Board Leaderboard
  - When a Mosaic board is loaded via hash+mask params (/mosaic/custom/?hash=...&mask=...),
    show a per-board leaderboard keyed by (hash, mask) — similar to the Replay page's per-hash leaderboard
  - Logged-in users' times are saved automatically on win; guests get a name-entry form
  - The board ID is derived from the hash+mask pair (e.g. SHA-256 or concatenation)
  - DB table: mosaic_custom_scores (board_id, name, time_secs, solved_at)
  - API: POST /api/mosaic-custom-scores  GET /api/mosaic-custom-scores/<board_id>
  - The custom board template sets data-score-api to the new endpoint when hash+mask are present
  - Random/generated custom boards (no hash param) remain leaderboard-free

F45 Automated Test Suite
  - pytest-based test suite in tests/ covering all score submission and retrieval APIs
  - tests/conftest.py bootstraps an in-memory SQLite database so tests run without MySQL
  - Overrides FastAPI's get_db dependency; patches _apply_migrations() (MySQL-specific) to no-op
  - Sets dummy env vars for Google OAuth so auth.py can be imported in CI without credentials
  - Test modules:
      test_health.py     — /health, /robots.txt, /sitemap.xml, homepage, 404 handler
      test_csrf.py       — CSRF middleware (X-Requested-With guard) on all POST /api/* routes
      test_scores.py     — Classic game score submission (all modes) and leaderboard ordering
      test_mosaic.py     — Mosaic daily, easy, and custom-board (F44) leaderboard
      test_tentaizu.py   — Tentaizu daily and easy scores
      test_variants.py   — Cylinder, Toroid, and Replay score APIs
      test_validation.py — Pydantic validation: 422 returned for all invalid payloads
  - Run with: pytest (configured in pytest.ini; testpaths=tests)

F47 Purpose-built og:image for Tentaizu (1200×630)
  - Replace static/img/og-tentaizu.png with a purpose-built 1200×630 image
  - Image should clearly represent the Tentaizu game: 7×7 star-placement grid,
    number clues, dark/space theme consistent with the Tentaizu skin
  - Used as og:image and twitter:image on all 5 Tentaizu pages:
    /tentaizu, /tentaizu/easy-5x5-6, /tentaizu/how-to-play,
    /tentaizu/strategy, /tentaizu/archive
  - Current placeholder: screenshot crop from TentaizuPuzzle20260320Equinox.png

F48 Purpose-built og:image for Mosaic (1200×630)
  - Replace static/img/og-mosaic.png with a purpose-built 1200×630 image
  - Image should clearly represent the Mosaic game: filled black/white grid
    with number clues, showing a partially or fully solved puzzle
  - Used as og:image and twitter:image on all 5 Mosaic pages:
    /mosaic, /mosaic/standard, /mosaic/custom, /mosaic/how-to-play,
    /mosaic/replay
  - Current placeholder: MosaicExample.png (small, square — not ideal)

F50 Flower Garden Theme (dark night-garden + light day-garden)
  - New skin pair: `flower` (night) and `flower-light` (day), following the
    dark/light auto-switch pattern in resolveDefaultSkin (base.html)
  - Auto-switches flower-light during 06:00–20:00 local time; flower at night
  - User can pin either variant via the theme selector (localStorage key "skin")
  - Mine icon: 🌸 (cherry blossom) replaces 💣 in all game JS files
      getMineEmoji() already checks data-skin for tentaizu (⭐) — add flower check
      Files: minesweeper.js, cylinder.js, toroid.js, rush.js, duel.js,
             spectate.js, replay.js (and any inline assignments)
  - Flag icon: 🌷 (tulip on stem) replaces 🚩 in all game JS files
      Same files as mine icon — replace el.textContent = '🚩' with getFlagEmoji()
      helper that returns '🌷' for flower/flower-light, '🚩' otherwise
  - CSS — `flower` (dark night-garden palette):
      Background: deep plum / midnight green (#1a0d2e, #0d1f0d)
      Cells hidden: mossy dark green; revealed: soft dark cream
      Numbers: warm botanical colors replacing the standard blue/green/red set
      Mine cell background: deep burgundy (consistent with current dark skin)
      Detonated cell: dark rose
  - CSS — `flower-light` (day-garden palette):
      Background: soft sage / pale petal (#f0f5e8, #fdf6f0)
      Cells hidden: light sage green; revealed: warm white
      Numbers: rich botanical greens/pinks/purples
      Mine cell background: rose pink
      Detonated cell: vivid coral
  - Mega menu: add "🌸 Flower Garden" to the skin switcher (non-classic nav)
  - base.html resolveDefaultSkin: extend to respect flower/flower-light pair
    when stored skin is one of the flower variants
  - Skin name mapping: "flower" → "flower-light" for daytime auto-switch
    (mirror the "dark" → "light" mapping already in place)

F52 Hexsweeper — Hexagonal Minesweeper Variant
  Minesweeper played on a hexagonal-shaped board of pointy-top hexagonal tiles.
  Each cell has 6 neighbours instead of 8, which changes strategy significantly.

  ── Board sizes (hexagonal boards — axial radius R, diameter = 2R-1) ──────────
    Beginner:     R=5  → diameter 9,  61 cells, ~8 mines  (13% — matches beginner ratio)
    Intermediate: R=7  → diameter 13, 127 cells, ~20 mines (16% — matches intermediate ratio)
    Expert:       R=10 → diameter 19, 271 cells, ~56 mines (21% — matches expert ratio)
  All mine counts are tunable via HEXSWEEPER_MINES dict in settings.py.
  A hexagonal board of radius R contains 3R²-3R+1 cells.
  Cell set: all axial coords (q, r) where max(|q|, |r|, |q+r|) ≤ R-1.

  ── Coordinate system ────────────────────────────────────────────────────────
  Use axial coordinates (q, r); the third cube coordinate s = -q-r is implicit.
  Six neighbours of (q, r): (q+1,r), (q-1,r), (q,r+1), (q,r-1), (q+1,r-1), (q-1,r+1)
  Canonical cell index for hashing: sort cells by (r, q) then assign 0-based index.

  ── Rendering ────────────────────────────────────────────────────────────────
  Render using SVG (inline in a <div id="hex-board">).
  Use pointy-top hexagons with hex size S px (default S=28 for beginner, scaled for larger).
  Pixel center of axial cell (q, r):
    x = S * √3 * (q + r/2)
    y = S * 3/2 * r
  SVG origin offset so board is centred in the viewport.
  Each cell is a <polygon points="…"> with 6 vertices.
  Cell states via CSS class: .hx-hidden, .hx-revealed, .hx-flagged,
    .hx-question, .hx-mine, .hx-mine-detonated, .hx-n1…hx-n6
  Left-click: reveal; Right-click / long-press: cycle flag → question → clear.
  First click is always safe (regenerate board if needed).

  ── Hash / board encoding ─────────────────────────────────────────────────────
  Same approach as existing board-generator:
    Sort cells by canonical index (r asc, q asc).
    Build a bit-array: bit i = 1 if cell i is a mine.
    Base64url-encode the byte array → board hash string.
  Decode: same process in reverse.
  Hash is shown as a permalink after the first reveal, same as /variants/replay/.

  ── Routes ───────────────────────────────────────────────────────────────────
    GET /hexsweeper               → beginner (R=5, 8 mines)
    GET /hexsweeper/intermediate  → intermediate (R=7, 20 mines)
    GET /hexsweeper/expert        → expert (R=10, 56 mines)
    GET /hexsweeper/custom        → custom (form: radius 3–15, mine count)
    GET /hexsweeper/generator     → hex board generator (click cells to place mines,
                                    shows hash + mine count, generates replay link)
    GET /hexsweeper/leaderboard   → best times per mode

  ── Templates ────────────────────────────────────────────────────────────────
    templates/hexsweeper.html          — shared base template (parameterised)
    templates/hexsweeper_intermediate.html
    templates/hexsweeper_expert.html
    templates/hexsweeper_custom.html
    templates/hexsweeper_generator.html
    templates/hexsweeper_leaderboard.html

  ── JS ───────────────────────────────────────────────────────────────────────
  static/js/hexsweeper.js — single JS file for all hex game pages.
  Key functions:
    generateHexCells(R)            → sorted array of {q,r} objects (canonical order)
    hexCenter(q, r, S)             → {x, y} pixel center
    hexPolygonPoints(cx, cy, S)    → SVG points string for pointy-top hex
    buildSVGBoard(cells, S)        → creates <polygon> elements, wires click/rightclick
    generateMines(cells, count, safeIdx)  → Set of mine indices (avoids safeIdx)
    countNeighbourMines(idx, mineSet, cells, cellIndex) → integer 0–6
    revealCell(idx)                → flood-fill BFS for zero-count cells
    boardToHash(mineSet, cells)    → base64url string
    hashToBoard(hash, cells)       → Set of mine indices
    renderCell(idx)                → updates <polygon> class + <text> child
    getMineEmoji() / getFlagEmoji() → respects active skin (🌸/🌷 for flower, etc.)

  ── Database ─────────────────────────────────────────────────────────────────
  New table: hexsweeper_scores
    id          INT AUTO_INCREMENT PRIMARY KEY
    mode        VARCHAR(20)   -- 'beginner' | 'intermediate' | 'expert' | 'custom'
    board_hash  VARCHAR(128)  -- NULL for daily/random; set for hash-based boards
    user_email  VARCHAR(255)
    display_name VARCHAR(64)
    time_ms     INT
    no_guess    TINYINT DEFAULT 0
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP

  ── API ──────────────────────────────────────────────────────────────────────
    POST /api/hexsweeper-scores          → submit score (time_ms, mode, board_hash, display_name)
    GET  /api/hexsweeper-scores/{mode}   → leaderboard for mode (top 20, today + all-time)

  ── Nav / sitemap ────────────────────────────────────────────────────────────
  Add Hexsweeper to the Variants group in the mega menu (non-classic nav).
  Add /hexsweeper, /hexsweeper/intermediate, /hexsweeper/expert,
      /hexsweeper/custom, /hexsweeper/leaderboard to sitemap.xml.

  ── Skin support ─────────────────────────────────────────────────────────────
  SVG cells styled via CSS variable overrides: --hex-hidden, --hex-revealed,
  --hex-mine, --hex-border, --hex-text. Each existing skin (dark, light,
  tentaizu, flower/flower-light, classic) gets a hex-specific colour block
  in style.css. getMineEmoji() / getFlagEmoji() from minesweeper.js apply.

  ── No-guess mode ────────────────────────────────────────────────────────────
  Deferred to a follow-on feature — hex no-guess generation is non-trivial.
  Board generator will note whether a board is logically solvable.

F53 Daily Archive Leaderboard Pages

  Purpose
  ──────────────────────────────────────────────────────────────────────────────
  Provide permanently-addressable, fully server-rendered (no JS required) daily
  high-score pages for Beginner, Intermediate, and Expert minesweeper.  These
  pages are spider-friendly and serve as a historical record of top scores by
  authenticated users for each calendar day.

  URL scheme
  ──────────────────────────────────────────────────────────────────────────────
  /beginner/<YYYY-MM-DD>/guess          — Beginner, standard (guess allowed)
  /beginner/<YYYY-MM-DD>/no_guess       — Beginner, no-guess mode
  /intermediate/<YYYY-MM-DD>/guess
  /intermediate/<YYYY-MM-DD>/no_guess
  /expert/<YYYY-MM-DD>/guess
  /expert/<YYYY-MM-DD>/no_guess

  Index / date-picker page
  ──────────────────────────────────────────────────────────────────────────────
  /archive                              — Archive index page
    - Date input (defaults to today) + a "Go" button
    - Mode tabs: Beginner / Intermediate / Expert
    - Guess toggle: Standard / No-Guess
    - On submit: navigates to /<mode>/<date>/<guess|no_guess>
    - Lists the most recent 30 days that have at least one score as links
      (one list per mode, but driven by a single combined query for speed)

  Score selection rules
  ──────────────────────────────────────────────────────────────────────────────
  - Authenticated users only: WHERE user_email IS NOT NULL
    (end-of-day cron already removes guest rows, but the query enforces it)
  - One row per player: best time_ms (or time_secs * 1000 if time_ms is NULL)
  - Date window: created_at >= <date> 00:00:00 UTC
                 created_at <  <date+1> 00:00:00 UTC
  - mode = <beginner|intermediate|expert>
  - no_guess = <True for no_guess path, False for guess path>
  - ORDER BY effective_ms ASC
  - LIMIT 100

  Page content (server-rendered HTML, no JS required)
  ──────────────────────────────────────────────────────────────────────────────
  1. h1: "Beginner Scores — 2026-03-25" (mode + date)
  2. Mode tabs: Beginner | Intermediate | Expert (links, not JS tabs)
  3. Guess toggle: Standard | No-Guess (links)
  4. Score table columns:
       # | Name | Time | Board | Mines | 3BV | 3BV/s | Eff | Board Hash
     - # → rank (1-based)
     - Name → display name (user_email masked)
     - Time → time_ms/1000 formatted to 3 dp (e.g. 12.345s), fallback time_secs
     - Board → rows×cols (e.g. 9×9)
     - Mines → mines count
     - 3BV → bbbv (or — if null)
     - 3BV/s → bbbv / (time_ms/1000), 2 dp (or —)
     - Eff → bbbv / (left_clicks + chord_clicks) * 100%, 0 dp (or —)
     - Board Hash → link to /variants/replay?hash=...&rows=...&cols=...&mines=...
       if board_hash is not null, otherwise —
  5. Play buttons below table:
       ← Play Beginner | Play Intermediate | Play Expert
  6. Explanation paragraph (rendered from translation key):
       "These are the best times posted by registered players on <date>.
        Guest scores are not included. Each player appears once — their
        personal best for the day."

  404 handling
  ──────────────────────────────────────────────────────────────────────────────
  - Invalid date string → 404
  - Valid date but no scores → render page with empty table and a
    "No scores recorded for this day." message (not a 404)

  SEO
  ──────────────────────────────────────────────────────────────────────────────
  - <title>: "Beginner Daily Scores — 2026-03-25 | minesweeper.org"
  - <meta description>: "Top Beginner minesweeper times for 2026-03-25.
      Server-rendered leaderboard of registered players."
  - <link rel="canonical"> pointing to the canonical URL
  - <link rel="prev"/"next"> for date pagination (previous/next day with scores)
  - robots: index, follow (public pages)
  - /archive: index page, robots: index, follow
  - Add all 6 daily-archive URL patterns to sitemap.xml with
    lastmod = today and priority = 0.6

  Routes (main.py)
  ──────────────────────────────────────────────────────────────────────────────
  GET /archive
      → render templates/archive_index.html
      Query: for each mode, fetch last 30 distinct dates with ≥1 auth score

  GET /{mode}/{date}/{guess_mode}
      where mode ∈ {beginner, intermediate, expert}
      and   date matches r"\d{4}-\d{2}-\d{2}"
      and   guess_mode ∈ {guess, no_guess}
      → render templates/archive_day.html
      Validates date; returns 404 on invalid date string.

  Template files
  ──────────────────────────────────────────────────────────────────────────────
  templates/archive_index.html  — date picker + recent days list
  templates/archive_day.html    — static score table for one day

  Translation keys needed (add to all 17 languages)
  ──────────────────────────────────────────────────────────────────────────────
  archive_title          "Daily Archive"
  archive_desc           "Browse daily high-score leaderboards for each difficulty."
  archive_go             "Go"
  archive_recent         "Recent days"
  archive_no_scores      "No scores recorded for this day."
  archive_explanation    "These are the best times posted by registered players
                          on {date}. Guest scores are not included. Each player
                          appears once — their personal best for the day."
  archive_standard       "Standard"
  archive_no_guess       "No-Guess"

  Notes
  ──────────────────────────────────────────────────────────────────────────────
  - Do NOT add hexsweeper or other variants to this feature; keep it to the
    core three difficulties (beginner / intermediate / expert).
  - The /archive index page is the entry point linked from the leaderboard page.
  - Mode tabs use <a href="..."> links so they work without JavaScript.
  - The score table uses existing .lb-table CSS class for visual consistency.

F51 Blog post announcing the Flower Garden theme
  - Write a blog entry at /blog/flower-garden-theme announcing the new 🌸 skin
  - Cover: what it is (night garden / day garden), how to activate (theme picker
    in the More menu or ?theme=flower URL param), what changed (mines = 🌸,
    flags = 🌷, deep plum night palette / sage green day palette)
  - Include a screenshot showing the day and night variants side by side
  - Target audience: returning players who might not notice the new theme
  - Assign to Bill

F49 Purpose-built og:image for Rush (1200×630)
  - Replace static/img/og-rush.png with a purpose-built 1200×630 image
  - Image should clearly represent Minesweeper Rush: the cascading row mechanic,
    timer/score display, dark theme consistent with the Rush skin
  - Used as og:image and twitter:image on all 3 Rush pages:
    /rush, /rush/how-to-play, /rush/leaderboard
  - Current placeholder: RushOGFirstAttempt.png (cropped from 1443×700 screenshot)

F46 OpenTelemetry Instrumentation for AWS Bedrock Observability
  - telemetry.py: setup_telemetry(app, db_engine) initialises OTLP tracing; no-op when
    OTEL_EXPORTER_OTLP_ENDPOINT is unset so dev environments need no extra infrastructure
  - Instruments FastAPI (every HTTP request → span) via opentelemetry-instrumentation-fastapi
  - Instruments SQLAlchemy (every DB query → child span) via opentelemetry-instrumentation-sqlalchemy
  - Exports via OTLP HTTP to the AWS Distro for OpenTelemetry (ADOT) Collector,
    which forwards traces to X-Ray and metrics to CloudWatch for Bedrock to consume
  - Resource attributes: service.name, service.version, deployment.environment
  - Optional auth headers via OTEL_EXPORTER_OTLP_HEADERS (comma-separated key=value)
  - New .env vars: OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_EXPORTER_OTLP_HEADERS
  - Packages: opentelemetry-api, opentelemetry-sdk, opentelemetry-instrumentation-fastapi,
    opentelemetry-instrumentation-sqlalchemy, opentelemetry-exporter-otlp-proto-http

F40 Server Health Checks and Deploy Gate
  - GET /iamatestfile.txt returns plain text "healthy" for uptime monitors and load balancer probes
  - GET /health returns service status; restricted to localhost only (403 for external requests)
  - Staging deploy script runs smoke tests (/, /pvp, /duel, /tentaizu) after every deploy:
      Pass → writes SHA to /home/ubuntu/deploy_state/last_good_commit
      Fail → writes SHA to blocked_commit, reverts staging to last known good commit
  - Staging cron skips any commit listed in blocked_commit; clears block when a new commit arrives
  - Production deploy script only promotes commits present in last_good_commit (staging-blessed)
  - State files live at /home/ubuntu/deploy_state/ (runtime, not in git)

-- Addressed --

F1 User Profile
  Login with Google
  Save user info in a database

F2 Multiplayer game mode
  Implement Websockets
  Modify game to make it easier to find matches
  Save game history to database

F3 Implement No Guessing mode

F4 Implement run off git repo and restart on successful commit

F5 Multilanguage support
  Languages: EN, EO, DE, ES, TH, PGL, UK, FR, KO, JA, ZH, ZH-HANT, PL, TL (Tagalog)

F6 Support Minesweeper Rush mode

F7 Allow chording as an optional feature: https://minesweeper.fandom.com/wiki/Chording

F10 Multiple skin support (Default for minesweeper.org will be called Dark)

F11 Implement Tentaizu on a sub-page https:/minesweeper.org/tentaizu
    The puzzle of the day starts with 10 mines on a 7x7 board.  Some of the tiles that do not contain mines are revealed with the number of mines near them also shows.  The puzzle of the day should be solvable with the revealed numbers.
    See https://puzzle-minesweeper.com
    If your flag or blank contradicts a number, that number should highlight letting you know that you made a mistake
    You should be able to toggle between flag, blank, and unknown
    See also https://github.com/hellpig/minesweeper-puzzle-generator

F12 Cylinder variant

F17 Add linkedin link

F18 Theme selection in url

F21 Bing SEO improvements

F25 Add timed banner support for special days

F32 Add chat support to the website
  - Global lobby chat visible to all logged-in users
  - In-game chat during PvP duels (between the two players)
  - WebSocket-based (reuse existing WS infrastructure)
  - Messages stored in DB for moderation; auto-expire after 24h
  - Admin moderation: delete messages from /admin

F33 Continuous Integration
  - Environment variable ENVIRONMENT identifies the running environment (dev, staging, prod)
  - GitHub repo and local development use ENVIRONMENT=dev
  - Future environments (staging, prod) will be added as the pipeline is built out
  - URL mapping:
      dev     → localhost
      staging → dev.minesweeper.org
      prod    → minesweeper.org

F34 Board Generator
  - Interactive grid at /variants/board-generator where you click cells to place mines
  - Shows board hash (base64 bit-array encoding), mine count, and 3BV for Standard/Cylinder/Toroid topologies
  - Generates shareable links: /variants/replay/ (play the board) and /mosaic/custom/ (solve as Mosaic)
  - Board hash format: bit i of byte i>>3 is set if cell index i is a mine

F35 Mosaic Custom Board
  - /mosaic/custom/ — configurable custom Mosaic board page
  - Without params: form to select rows (3–20), cols (3–20), and difficulty (easy/standard/hard)
  - With ?hash=...&rows=...&cols=... params: loads a specific board from the board generator
  - "Hide Numbers" button in win overlay — toggles hint number visibility on the solved board
  - "Hide Numbers" button also available on /mosaic and /mosaic/easy after solving

F37 Links Page at /links
  - Static curated links page at /links
  - Link sections are maintained in FeatureRequests/links-page.md; rebuild the page when new links are added
  - Sections (in order):
      Landmines        — Halo Trust and organizations removing landmines
      Princess Di      — Pages about Diana and her landmine-clearing work
      Minesweeper Theory — 3BV wiki, strategy videos, general theory
      Play Minesweeper — Sites to play (include Google Minesweeper)
      Tentaizu         — puzzle-minesweeper.com and related
      Mosaic           — puzzle-minesweeper.com + how-to-play video
      Minesweeper Rush — Steam store page
      Minesweeper Variants — Variants advent calendar and related
      Vibe Coding      — Vibe coding resources
      Git Repos        — minesweeper.org, Tentaizu generator, Mosaic
  - Route: GET /links → templates/links.html
  - No dynamic data; pure Jinja2 template with info-page styling
  - Add nav link where appropriate

D1 Document the environment
  Development is done on a Mac, Linux desktop, or Windows desktop and
  pushed to an Ubuntu server on AWS

D2 Add feature request code to the beginning of the commit message
   If the commit has to do with the Tentaizu theme, the commit message should be
   of the form:
   F20 <Description of update>
