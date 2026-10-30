B60 /leaderboard showed no Numbers Match scores and almost no Sudoku scores.
   Root causes, all in leaderboard_platform.py unless noted:
   (1) The Numbers Match card compared puzzle_date to the plain date, but ids carry the revision
       (2026-10-30-v3), so it was always empty; longer periods mixed every level.
   (2) One row per board_hash: every Sudoku Daily player shares the board, so only the first
       player of the day was listed.
   (3) Cards used the server's UTC day while both games use the New York day, so from 8 pm New
       York the daily cards pointed at tomorrow and went empty.
   (4) Only the Daily had a card; Easy, Medium, Hard and Expert scores appeared nowhere.
   (5) main.archive_guest_scores runs at midnight UTC (8 pm New York) and moved that day's guest
       Numbers Match scores out of the table mid-day.
   Fix: LeaderboardSpec.puzzle_id_tail / new_york_day / one_row_per_board; level cards for both
   games; the API no longer forces date.today(), so each card defaults to its own day; the archive
   keeps the current Numbers Match day. Tests: tests/test_leaderboard_puzzle_cards.py.

B59 Sudoku: finishing the Daily switched the leaderboard to Easy's (same as B57 in Numbers Match).
   Root cause: F-GAME-END rolls the Daily into an Easy game in place; startNextGame() then loaded the
   leaderboard for the new level, and the finished game's save only refreshed it when the levels matched.
   Fix: the next game leaves the leaderboard alone; once the finished game's score is saved,
   loadLeaderboard(game.difficulty) shows that level's ranking. Covered by
   tests/js/sudoku_behaviour.js (fails on the previous sudoku.js).

B58 pip-audit (Security Scan workflow) failed: two new advisories in Python dependencies.
   certifi 2026.4.22 (PYSEC-2026-4320): bundled emSign ECC Root CA - G3 whose intermediates have
   compromised keys — on-path interception of the server's outbound TLS. opentelemetry-api 1.44.0
   (CVE-2026-114603): O(N^2) tracestate parsing, reachable on every request through the FastAPI
   instrumentation (Apache's default ~8 KB header limit reduced the impact).
   Fix: certifi 2026.10.23; OpenTelemetry 1.45.1 / instrumentation 0.66b1 (pins in requirements.in;
   requirements.txt and requirements.lock regenerated on Linux, only these packages changed).
   Verified setup_telemetry() with OTel enabled: a 50 KB tracestate is now cut at 8192 characters.
   Found while verifying: opentelemetry-instrumentation-sqlalchemy supports SQLAlchemy < 2.1.0 and we
   run 2.1.3 (since PR #56), so DB queries are not instrumented — not fixed here.

B57 Numbers Match: winning the Daily switched the leaderboard to Easy's.
   Root cause: F-GAME-END starts the next game right after a win (Daily -> today's ranked Easy),
   and _startGame loaded the leaderboard of every new ranked game, so the Daily ranking the
   player had just entered was replaced before they could see it.
   Fix: games started automatically after a win (autoNext) keep the leaderboard as is; when the
   finished game's score is saved, showLeaderboardFor() shows that puzzle's ranking. Only a mode
   the player picks switches it. Covered by tests/js/numbers_match_game_end.js.

B56 Puzzles menu empty and Google Analytics missing on pages served by *_routes.py modules.
   Root cause: since the route extraction refactor (883ef01, 2026-09-14) each *_routes.py module
   builds its own Jinja2Templates with a partial copy of main.py's globals: no puzzle_games (the
   Puzzles mega-menu and drawer only showed "All Puzzles") and ga_tag = "" (no GA script). Live
   check 2026-10-12: / and /tentaizu listed 24 puzzles and loaded GA; /numbers-match and
   /other/sudoku/* listed 0 and had no GA. 20 router modules affected (blog, duel, numbers match,
   sudoku, mahjong, jigsaw, nonosweeper, wc2026, ...).
   Fix: main._sync_router_template_globals() copies every global a router lacks and main's GA tag
   into each router's template environment (router-specific values such as speff's
   page_localized and each env's url_for are kept). Tests in tests/test_game_catalog.py.

B55 Sudoku scores dated tomorrow in the evening (Americas).
   Root cause: sudoku_routes.py used date.today() (server clock, UTC), so from 20:00 New York
   time the daily puzzle, the score's puzzle_date and the "Today" leaderboard all moved to the
   next day, while Numbers Match uses the America/New_York day. The leaderboard Date column
   also showed created_at, a UTC timestamp.
   Fix: Sudoku uses numbers_match_today_str() (America/New_York) for every "today", and the
   leaderboard Date column shows puzzle_date. Scores saved before the fix keep their UTC date;
   the daily seed depends only on the date string, so they still match that day's puzzle.
   Tests in tests/test_sudoku.py freeze the clock at 01:22 UTC.

B54 /mobile/nmmobile (mobile web Numbers Match) returned HTTP 500 since 2026-05-12.
   Root cause: a3475a6 translated the template's strings ({{ t.* }}) but the route in main.py
   never passed `t`, so Jinja raised UndefinedError: 't' is undefined. The page also loaded
   numbers_match.js?v=17 and style.css?v=48, and had no data-revision / data-timezone, so even
   once rendered it would run stale cached JS that cannot submit verified scores (F-NM-VERIFY).
   Fix: pass lang, t, nm_revision and nm_timezone from the route; load the same numbers_match.js
   and style.css versions as the main page. Tests in tests/test_numbers_match.py check the page
   renders, uses the same asset versions, and has every element numbers_match.js looks up.

B53 Production installed different Python dependency versions than staging tested.
   Root cause: staging installs requirements.lock (hash-checked) but production installed
   requirements.txt without hashes, and a failed pip install only printed a warning. Dependabot
   bumps only requirements.txt (PR #56), so the files drifted: SQLAlchemy 2.0.53 vs 2.1.3,
   FastAPI, uvicorn, cryptography, pymysql, markdown, and urllib3 2.7.0 (3 CVEs) vs 2.8.0.
   Fix: regenerate requirements.lock from requirements.txt (pip-compile --generate-hashes, on Linux);
   production, GCP scripts and install_ubuntu.sh now install the lock with --require-hashes; a failed
   production install rolls the code back and exits without restarting;
   tests/test_requirements_sync.py fails CI when the two files pin different versions.

B52 Numbers Match saves 0:01 as the time for every completed game; on-screen timer stuck at 0:00.
   Root cause: base.html loads minesweeper.js with `defer` (added in f0d4909, 2026-05-13), so it
   now executes AFTER numbers_match.js. Both declare global `startTimer`/`stopTimer`, and the
   later script wins: Numbers Match called minesweeper.js's timer (which updates `state`, not
   `G`), so `G.startTime` was never set, `G.elapsed` stayed 0, and `Math.max(1, 0)` sent 1s.
   Fix: rename the Numbers Match functions to `nmStartTimer`/`nmStopTimer` and bump
   numbers_match.js to ?v=19. Scores saved before the fix keep their 1s time.

B51 CodeQL: Uncontrolled data used in path expression — main.py admin/analysis route.
   Root cause: real_base = os.path.realpath(active_dir) was derived from user-supplied
   `folder` param, making all startsWith(real_base) checks tainted-vs-tainted comparisons
   that CodeQL cannot treat as sanitization.
   Fixes:
   - Compute real_analysis = os.path.realpath(analysis_dir) once (untainted constant)
     and use it for all containment checks instead of real_base.
   - Replace ".." in folder string check with re.fullmatch(r'[A-Za-z0-9_-]+', folder)
     which CodeQL recognises as sanitization, plus realpath+startsWith guard.
   - For doc reads: assign md_real/html_real once, check once, open once (avoids TOCTOU
     and makes the single sanitized variable clear to CodeQL's taint tracker).
   - For src reads: realpath computed inline → startsWith(real_analysis) checked before open.

B50 CodeQL: DOM text reinterpreted as HTML in archive_index.html, fifteen_puzzle_generator.js,
   fifteen_puzzle_member_generator.js, jigsaw_generator.html.
   (1) archive_index.html:82 — `window.location.href` built from unvalidated DOM select/input
       values. Fixed by allowlist-checking mode and guess values and regex-validating the date
       before constructing the URL.
   (2) fifteen_puzzle_generator.js:197 and fifteen_puzzle_member_generator.js:156 — `img.src`
       assigned directly from `URL.createObjectURL(file)` without confirming the URL is a
       blob: origin. Fixed by checking `startsWith('blob:')` before assigning to src.
   (3) CSS injection: `backgroundImage = 'url(' + blobUrl + ')'` — unquoted URL in CSS
       string. Fixed by wrapping in double-quotes: `'url("' + blobUrl + '")'`.
   (4) jigsaw_generator.html:222 — same `img.src = URL.createObjectURL(f)` pattern; same
       blob: startsWith guard applied.

B43 /other/mahjong missing h1 — route was a 302 redirect with no HTML body.
   Bing Webmaster Tools flagged the URL as missing h1 because a redirect response
   has no HTML content. Fix: serve static/mah/index.html directly at /other/mahjong;
   the SPA's <base href="/other/mahjong/"> keeps all asset paths valid.

B42 meta_kw_* duplicate keys in translations.py put wrong-language keywords in 4 locales.
   Python dict duplicate-key semantics (last wins) caused: en → Russian keywords,
   eo → Portuguese keywords, es → Italian keywords, pl → Thai keywords.
   The correct keywords already existed in the proper locale blocks (ru, pt, it, th);
   the misplaced duplicates in en/eo/es/pl were removed.
   Fix: removed 4 lines each from en, eo, es, pl locale blocks in translations.py.

B41 Mosaic "Puzzle of the Day" badge label hardcoded English in mosaic.js.
   mosaic.js overwrote the server-rendered translated label on every game init.
   Fix: expose ms_label_potd / ms_label_random via window.T; use in mosaic.js.

B40 rush.html SEO article body is hardcoded English — not localised for any locale.
   The SEO <article> block (h2, sections, FAQs) has no translation keys; it renders
   in English on all locale-prefixed URLs (e.g. /tl/rush, /de/rush, etc.).
   Fix: extract all body text into rush_body_* translation keys and translate for
   all 15 locales (en, eo, de, es, th, uk, fr, ko, ja, zh, pl, tl, ru, pt, it).

B39 main.py admin analysis page: path traversal via user-controlled src/doc params.
   CodeQL flagged line 7289: src (query param) used in open() after only an
   in-list guard that CodeQL does not recognise as sanitization.
   Fixed by adding os.path.realpath() containment checks for both the doc and
   src paths, asserting the resolved path starts with realpath(active_dir).

B38 replay.js leaderboard title built with innerHTML from user-controlled HASH.
   CodeQL flagged line 626: HASH (from ?hash= URL param) flowed into innerHTML
   via esc() which CodeQL does not recognise as a sanitizer.
   Fixed by replacing innerHTML with DOM construction (createElement/textContent/
   setAttribute), so HASH only reaches safe DOM property sinks.

B37 profile.html updateFlag() sets img.src from unvalidated select value.
   CodeQL flagged both country-flag and wc2026-flag updateFlag() functions: sel.value
   is user-controlled (editable via devtools) and was used directly in a URL path
   without validation, enabling path traversal or protocol injection.
   Fixed by adding /^[a-z]{2}$/ guard before building the flag image URL.

B36 Jigsaw generator page body is all English for non-English locales.
   Template jigsaw_generator.html uses hardcoded English strings for all UI text.
   Fixed by extracting to jgen_* translation keys and translating for all 12 locales.

B35 Mosaic how-to-play page body is all English for non-English locales.
   Fixed by extracting to ms_howto_* keys and translating for all 12 locales.

B34 CSP blocks csi.gstatic.com (connect-src) and ep1.adtrafficquality.google (img-src).
   Google AdSense SODAR loads a tracking pixel from ep1.adtrafficquality.google via img-src,
   and the Google CSI (Client-Side Instrumentation) beacon hits csi.gstatic.com via connect-src.
   Fixed by adding *.adtrafficquality.google to img-src and csi.gstatic.com to connect-src.

B33 Admin bootcamp replay links use ?id= which replay.js does not handle, so clicking them loads a
   blank/default board instead of the intended game.
   Fixed by building the full replay URL from GameReplay fields (rows, cols, mines, board_hash,
   created_at, mode) so the link opens the correct board directly.

B32 Tametsi, Evil NG, Custom, and 2026 World Cup pages show English SEO content for non-English locales
   Templates tametsi.html, evil.html, custom.html, and wc2026_main.html had hardcoded English
   title/description/keywords with no translation keys — all non-English locale URLs returned
   identical English meta content, causing Bing/Google to flag them as duplicates.
   Fixed by: adding meta_title_*, meta_desc_*, meta_kw_* keys to all 17 locales in translations.py
   and updating templates to use {{ t.meta_title_* }} etc.

B31 /beginner URL returns the beginner game page instead of redirecting to /
   Google Search Console flagged https://minesweeper.org/beginner as a "Duplicate, Google chose
   different canonical than user" issue because it served the same content as / but had its own URL.
   Fixed by: adding a 301 redirect from /beginner to / in main.py.

B30 Mosaic game pages (standard, how-to-play) show English SEO content for non-English locales
   mosaic.html and mosaic_howto.html had hardcoded English title/description/keywords.
   Google Search Console flagged /uk/mosaic/how-to-play and /es/mosaic/standard as
   "Duplicate, Google chose different canonical than user".
   Fixed by: adding meta_title_mosaic, meta_desc_mosaic, meta_kw_mosaic, meta_title_mosaic_howto,
   meta_desc_mosaic_howto, meta_kw_mosaic_howto to all 17 locales in translations.py and updating
   both templates to use translation keys.

B29 Blog post <title> tags too long for Bing Webmaster Tools (>70 chars)
   Posts with long titles (e.g. "Nonosweeper's No Guess Mode: Every Puzzle,
   Solvable by Logic Alone") had " — minesweeper.org Blog" appended unconditionally,
   producing titles of 89 and 79 characters that Bing flagged as too long.
   Fixed by: computing page_title in the blog_post route — the suffix is appended
   only when the total is ≤ 60 characters (Google's stricter threshold), otherwise
   the bare post title is used. Short posts keep the branding; long ones drop it.

B28 Homepage and difficulty pages show English SEO content for non-English locales
   The 69 seo_* translation keys (seo_beg_*, seo_int_*, seo_exp_*, seo_about_*,
   seo_diff_*, seo_tips_*, seo_beyond_*) were only present in the English and German
   locales. All 15 other locales fell back to English via ChainMap, so visiting
   /?lang=es or /intermediate?lang=ko always rendered English headings and body text.
   Fixed by: adding all 69 seo_* keys to the 15 remaining locales (es, fr, eo, th,
   pgl, uk, ko, ja, zh, zh-hant, pl, tl, ru, pt, it) in translations.py.

B27 Hexsweeper meta description always shows in English regardless of locale
   hexsweeper.html hardcodes _desc using {% set _desc = "..." %} in English instead
   of pulling from the translation dictionary. No meta_desc_hexsweeper_* keys existed
   in translations.py, so the template had no way to render localised descriptions.
   Fixed by: adding meta_desc_hexsweeper_{beginner,intermediate,expert,custom} to all
   17 locales in translations.py; updating hexsweeper.html to use t["meta_desc_..."].

-- Fixed below --

B25 /strategy returns 500 internal server error
   strategy.html had {% block jsonld %} defined twice — once with a simple Article
   schema and once with a BreadcrumbList + Article. Jinja2 raises
   TemplateAssertionError on duplicate block names, causing a 500 on every request.
   Fixed by: merging both into a single block containing the BreadcrumbList and
   the Article with the publisher logo retained from the first definition.

B24 PvP vs Bot: bot makes zero moves (silent asyncio crash + stale AI knowledge after mine-hit)
   Two bugs combined to prevent the bot from making any visible progress:
   1. asyncio.create_task silently swallows unhandled exceptions — any crash in _run_bot
      would kill the task without any log output.
   2. After an F71 mine-hit realloc, the bot AI's `known` grid was not updated: reset cells
      kept their old revealed values (0-8) instead of being marked HIDDEN again, causing the
      solver to skip them as candidates and eventually lock up on hard boards.
   Fixed by: splitting _run_bot into a wrapper+inner pair so all exceptions are caught and
   logged via the "bot_runner" logger; resetting reallocated cells to HIDDEN in the AI after
   each mine-hit, then re-applying the updated board values for cells that remain revealed;
   also now sending opp_mine_hit to the human so their board reflects the bot's mine hits.

B23 AdSense scripts, fonts, and sensor events blocked by CSP / Permissions-Policy
   Multiple CSP and Permissions-Policy headers were too restrictive for AdSense:
   - fundingchoicesmessages.google.com blocked by script-src (consent dialog)
   - fonts.googleapis.com blocked by style-src (Roboto font in consent UI)
   - pagead2.googlesyndication.com/pagead/ping blocked by connect-src
   - deviceorientation/devicemotion events blocked by Permissions-Policy
     (AdSense iframes require accelerometer and gyroscope delegation)
   Fixed by: adding fundingchoicesmessages.google.com to script-src,
   fonts.googleapis.com to style-src, pagead2.googlesyndication.com to
   connect-src, and accelerometer=*/gyroscope=* to Permissions-Policy in
   the add_security_headers middleware (main.py).

B22 Deployment script not promoting to production

B21 Google Search Console not handling language canonical tag:
   {% if lang and lang != 'en' %}?lang={{ lang }}{% endif %} added to base.html
   By Claude Cowork

B20 Nonosweeper leaderboard always 404
   The GET /api/nonosweeper-scores/{puzzle_date} route was registered after the
   3-segment catch-all /{mode}/{date_str}/{guess_mode} (the archive route).
   FastAPI matched /api/nonosweeper-scores/2026-03-29 as mode=api before
   reaching the correct handler, raising HTTPException(404) because "api" is
   not in ARCHIVE_MODES.
   Fixed by: moving the nonosweeper scores section above the archive catch-all
   block in main.py (which is explicitly commented "must be last").

B18 PvP boards misaligned at /pvpbeta
   Player board #board had padding: 8px; opponent board #opp-board had 4px.
   Also .duel-board-col-label had no min-height so the opponent label (with
   "3s delay" badge) was taller, shifting the board down.
   Fixed by: overriding #board padding to 4px in duel context and adding
   min-height: 2.2em + flex centering to .duel-board-col-label.

B19 Nonosweeper "Could not load scores" after submitting score
   _apply_migrations() was missing user_email and guest_token for
   nonosweeper_scores — servers where the table predated those columns had
   unknown-column errors on SELECT. Also archive_guest_scores() omitted
   NonosweeperScore, so guest scores accumulated indefinitely.
   Fixed by: adding migrations to database_template.py, adding NonosweeperScore
   to the archive list, and improving JS error display to show HTTP status code.

B17 Season and All Time leaderboards only show today's scores
   reset_scores() at midnight deleted all web scores including registered users,
   leaving only ios_app/android_app scores in the table. Season and all-time
   queries therefore found no registered user history.
   Fixed by: adding Score.user_email.is_(None) to the reset filter so only
   anonymous guest web scores are cleared nightly. App scores and registered
   user scores are now both preserved across days.

B16 No-guess scores missing from replay page leaderboard
   The replay link on the no-guess leaderboard always passed game=standard,
   so the replay page fetched standard scores (no_guess=False) and found nothing.
   Also "no-guess" was absent from REPLAY_VARIANTS_VALID, causing a 400 before
   reaching the existing no-guess query branch.
   Fixed by: passing game=no-guess in the replay link when currentNoGuess is true
   (leaderboard.html), adding "no-guess" to REPLAY_VARIANTS_VALID (main.py),
   and updating the replay leaderboard title/tab logic for no-guess (replay.js).
   examplescreenshots/BeginnerNoGuessTodayHighScores
   examplescreenshots/ReplayHasNoScores

B15 Private-profile users shown as clickable links on leaderboard
   Users with an account but is_public=False had a /u/{public_id} URL generated
   in the leaderboard url_map, producing a clickable name that 404'd.
   Fixed by checking is_public in both url_map builders (scores API and replay
   leaderboard enrichment) so private users get no link.
   Also hardened /u/{slug}: if the profile exists but is private, returns a
   friendly "Private Profile" page (HTTP 200) instead of a raw 404.

B14 Win/loss overlay covers the entire viewport on beginner/intermediate/expert
   The JS appends #game-overlay to #game-result (a sibling of #board).
   .overlay uses position:absolute; inset:0, but there is no positioned ancestor
   between #game-result and <body>, so the overlay stretches to cover the whole page.
   Fixed by adding #game-result .overlay { position: static; margin-top: 0.75rem; }
   so the result panel flows naturally below the board.
   Variant pages (cylinder, toroid) are unaffected — their overlay is appended
   directly to #board which already has position:relative.

B13 Tentaizu bridge sentence not centered
   The <p class="tz-bridge-sentence"> element had no CSS rule, so it rendered left-aligned
   while the rest of the page is centered.
   Fixed by adding .tz-bridge-sentence { text-align: center; } to style.css.

B12 Protocol-relative open redirect in /set-lang
   The redirect_to parameter was only checked for a leading "/", allowing "//evil.com"
   to redirect off-site. Fixed by also rejecting values that start with "//".

B11 authorurl blog front matter used in <a href> without validation
   An authorurl like "javascript:alert(1)" would execute script when clicked.
   Fixed by only accepting authorurl values that start with "https://" or "http://".

B10 No rate limiting on score submission endpoints
   All nine score submission endpoints were unprotected, allowing unlimited POST requests.
   Fixed by adding slowapi with a 10/minute per-IP limit on all score endpoints.

B9 No CSRF protection on state-changing /api/ endpoints
   POST endpoints under /api/ accepted requests from any origin with no origin check.
   Fixed by adding an HTTP middleware that requires X-Requested-With: XMLHttpRequest on
   all /api/ POSTs; added the header to every fetch() call in JS and templates.

B8 Open redirect in OAuth /auth/login via unvalidated next parameter
   The next query parameter was stored in session and used as the post-login redirect
   target without validation, allowing redirect to arbitrary URLs.
   Fixed by rejecting any next value that doesn't start with "/" or starts with "//".

B7 /health endpoint disclosing git commit hash publicly
   The /health route was publicly accessible and returned the git SHA.
   Fixed by returning 403 for any request not originating from 127.0.0.1 or ::1,
   and updated the staging deploy script to use http://127.0.0.1:8002/health.

B6 TentaizuEasy name validator missing printable-ASCII filter
   TentaizuEasyScoreSubmit.sanitize_name only stripped whitespace, unlike every other
   score model which also filters to printable ASCII (ord < 128).
   Fixed by applying the same "isprintable() and ord(c) < 128" filter.

B5 Game Over / You Won overlay mis-positioned on Cylinder (and any variant) board
   #board is a CSS grid, so the overlay div became the last grid item and landed
   in the bottom-left corner instead of covering the board.
   Fixed by giving .overlay position:absolute; inset:0; z-index:10 so it sits over
   the board (#board already had position:relative).

B4 "New Duel" button text invisible in Diana/classic skin
   The global rule `html[data-skin="classic"] a { color: #ff3300 }` made the button
   text red-on-red (button background is also var(--accent) = #ff3300).
   Fixed by adding .duel-play-again and :visited to the button-styled links exception block.

B3 Board-specific leaderboard (replay page) does not show scores from the global leaderboard
   When a player's score is submitted through the normal game it goes into the scores table.
   The board-specific leaderboard only queried replay_scores, so those global scores were invisible
   on the replay/custom board leaderboard even though the player's board hash was present.
   Fixed by merging both tables in GET /api/replay-scores.

B2 If you play Intermediate, the "View Leaderboard" link takes you to the Beginner leaderboard.  This should take you to the Intermediate leaderboard.

B1 Custom game does not know your ID even if you are logged in
