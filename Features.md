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

F40 Server Health Checks
  - GET /iamatestfile.txt returns plain text "healthy" for uptime monitors and load balancer probes
  - GET /health returns service status; restricted to localhost only (403 for external requests)

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
