List of active features

F8 Improved Mobile Browser Support

F9 SEO improvements
   For general SEO improvements.  If the improvement is for a specific platform, use Bing SEO improvements or Google SEO improvements

F10 Multiple skin support (Default for minesweeper.org will be called Dark)

F11 Implement Tentaizu on a sub-page https:/minesweeper.org/tentaizu
    The puzzle of the day starts with 10 mines on a 7x7 board.  Some of the tiles that do not contain mines are revealed with the number of mines near them also shows.  The puzzle of the day should be solvable with the revealed numbers.
    See https://puzzle-minesweeper.com
    If your flag or blank contradicts a number, that number should highlight letting you know that you made a mistake
    You should be able to toggle between flag, blank, and unknown
    See also https://github.com/hellpig/minesweeper-puzzle-generator

F12 Cylinder variant

F13 Quests

F14 Website Analytics Google Analytics

F15 Website Analytics on local admin page at /admin and subpages

F16 Add a blog

F17 Add linkedin link

F18 Theme selection in url

F19 Secret admin mode that displays site statistics

F20 Tentaizu theme

F21 Bing SEO improvements

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

F25 Add timed banner support for special days

F26 Mosaic game mode

F27 Tentaizu game improvements

F28 Blog comments
  Logged-in users can comment on blog posts

F29 PvP bot opponent
   Constraint-based Minesweeper AI in bots/minesweeper_bot.py (easy/medium/hard).
   Bot lobby at /pvp/bot; game at /pvp/bot/play?m=standard&d=medium.
   "🤖 vs Bot" tab added to the PvP mode switcher.

F30 PvP rankings sortable columns
   Wins and Elo columns in win rankings table are clickable to toggle ascending/descending sort.

F31 Archive anonymous PvP results nightly
   Daily cron job moves PvP results with no registered winner to anonymous_pvp_results backup table.
  Comments require admin approval before appearing
  Admin moderation page at /admin/blog

D2 Add feature request code to the beginning of the commit message
   If the commit has to do with the Tentaizu theme, the commit message should be
   of the form:
   F20 <Description of update>

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

F33 Continuous Integration
  - Environment variable ENVIRONMENT identifies the running environment (dev, staging, prod)
  - GitHub repo and local development use ENVIRONMENT=dev
  - Future environments (staging, prod) will be added as the pipeline is built out
  - URL mapping:
      dev     → localhost
      staging → dev.minesweeper.org
      prod    → minesweeper.org

F32 Add chat support to the website
  - Global lobby chat visible to all logged-in users
  - In-game chat during PvP duels (between the two players)
  - WebSocket-based (reuse existing WS infrastructure)
  - Messages stored in DB for moderation; auto-expire after 24h
  - Admin moderation: delete messages from /admin

D1 Document the environment
  Development is done on a Mac, Linux desktop, or Windows desktop and 
  pushed to an Ubuntu server on AWS
