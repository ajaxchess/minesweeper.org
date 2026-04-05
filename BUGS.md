-- Fixed below --

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
