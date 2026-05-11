Minesweeper.org for iOS is a collection minesweeper games.
In the app store, this app should be called Minesweeper.org.
The app also contains supporting screens 
About This App
  App version
  Link to https://minesweeper.org
  Created by Regis.Consulting
  Contact support at ajaxchess@gmail.com or 312-224-1752
How-to-Play Minesweeper
Strategy & Tips
The content of these screens should be customized for mobile.  
Please load the content from the repo at build time and use them as static assets.
Update the assets at release time.
The existing minesweeper.org website does a browser detect for mobile, so we can pull
the content from the mobile version of these screens into the app.

The app features the classic minesweeper games with
  Beginner
  Intermediate
  Expert
  These all support both guess and no guess mode

The iOS app will only support English (at least this first version).

Generally each of these games consist of instructions (How to Play + Strategy & Tips), 
a board that you can interact with, 
a timer, and 
a high scores list.
When you win the game, if you have not entered your name you will be prompted and there will be a submit scores button.  If you enter a name, that will be stored in preferences. 
The app should make an API call to the minesweeper.org API to submit
the score. See APISpec.md for the full endpoint documentation including URL, HTTP method,
required headers, request/response format, and error handling.
The app should support all mobile UX features such as pinch to zoom in/zoom out and long
press to flag.  There should also be a flag mode button on the app.

The High Score list should show
Name
Time
3BV 
3BV/s -> (bbbv / (time_ms / 1000.0))
Efficiency (many minesweeper variants)
Board (A truncated hash of the board in the same format as the web version)
See EasyMinesweeperBoardHSforReference in minesweeper.org/mobile/ios/screenshots
First 8 characters are displayed.

Note that Efficiency is 3BV divided by the total number of clicks performed:
  Efficiency = bbbv / (left_clicks + right_clicks + chord_clicks)
This is computed client-side — the API does not return it directly.

This High Score list will be displayed below each board with the high scores for that day and board & Guess/No Guess mode
You can select Daily, by Season, or All Time to see the scores for those time periods.
Each minesweeper.org season is currently a month.

Each app should be able to submit games to the minesweeper.org server, but also continue to
run if the api calls are failing.  So, the app should function in offline mode.
During offline mode, if the score submission fails, the score can show up on the local high score board, but do not implement a retry logic to try to get the score to the server on fail.

The user preferences and name (for High Scores submission) will be stored locally by the app
using AsyncStorage with the following keys:
  "prefs:player_name"    — the player's display name for score submission
  "prefs:default_mode"   — which mode to start with on open: beginner, intermediate, or expert
  "prefs:default_guess"  — whether to default to guess or no-guess mode: "guess" or "noguess"
  "prefs:theme"          — light, dark, or auto

The game should use the Auto Light/Dark theme.  The game should use the Light theme in
the daytime and the Dark theme at night. The preferences should have the ability to lock
in to always use Light, always use Dark, or 
"Auto" where the theme changes by daytime/nighttime according to the iOS system settings.
  i.e. Auto is just follow the OS.

This version should support both iPhone and iPad

A future version of the app should support the ability to login with Google.
This will allow us to track a player's high scores and preferences across web and mobile.
For now, the leaderboard will show a mix of web and app scores.
The local device should cap the storage at the top 20 scores in each mode
(mode = board and guess/no guess, so we have 6 modes.)
Use AsyncStorage for local score persistence. Store each mode's scores as a JSON
array under a key per mode, e.g. "scores:beginner:guess" and "scores:beginner:noguess".
Keep the array sorted by time_ms ascending and trim to 20 entries after each insert.
Scores will be erased on reinstall.  Eventually the minesweeper.org service is about
preserving your scores for all time, even across reinstall.
Duplicate scores (same score on server and local) should be combined and displayed
as one score.
Deduplicate based on match of (mode + time_ms + board_hash).

A future version of the app should have the ability to serve ads through Google Admob.
https://minesweeper.org/app-ads.txt is served by the minesweeper.org website

The goal is to develop both an iOS and Android app.  
Performance is not that critical for minesweeper.  
We will use React Native with the Expo workflow

As part of the build process, for the static pages like strategy and how-to-play the team should render the html and save as a static file in the repo.
The team will need to save static rendered html in the folder static_html.
Run static_html/renderscript.sh before each release to regenerate these files.
The script fetches both pages using an iPhone user-agent and extracts the <main>
content into standalone self-contained HTML files:
  static_html/howtoplay_content.html  — use this in the app (How-to-Play screen)
  static_html/strategy_content.html   — use this in the app (Strategy screen)
The full-page files (howtoplay.html, strategy.html) are also saved for reference.
Load the _content files in a WebView within the app.

When the user is offline, the leaderboard updates with local scores.  If the user is online
the leaderboard should show a mix of local and server scores.

We need an App icon and splash screen for the App Store submission.  The team will be 
responsible for doing this.

The app locally generates boards, calculates 3BV, and verifies no-guess boards
using a client-side constraint solver. i.e. if the board generated does not satisfy the no-guess contraint, it will be regenerated until a board matching the requested requirements exists.

The API requires board_hash, bbbv, rows, cols, mines, time_ms. The app computes
all of these locally before submitting a score.

Board hash format: see BoardHashSpec.md for the exact bit-packing and base64
encoding. The React Native implementation is a direct copy of calcBoardHash()
from static/js/minesweeper.js (using Buffer instead of btoa).

No-guess solver: see NoGuessSolverSpec.md. The solver (isSolvable) and board
generator (placeMinesNoGuess) are already JavaScript in static/js/minesweeper.js
and can be copied into the app verbatim. No Python port is needed.

Note that the first version of the app will only have 3 board sizes.

App Store details

Developer account we will create an individual account under Richard Cross
Privacy policy URL https://minesweeper.org/privacy
Age rating — set to  4+
Category should be (Games > Puzzle)

Open issues:
None at this time.
