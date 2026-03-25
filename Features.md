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
