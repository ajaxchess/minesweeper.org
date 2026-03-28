Minesweeper.org for iOS is a collection minesweeper games.
The app also contains supporting screens 
About This App
How-to-Play Minesweeper
Strategy & Tips
The content of these screens should be customized for moblie.  
The existing minesweeper.org website does a browser detect for mobile, so we can pull
the content from the mobile version of these screens into the app.

The app features the classic minesweeper games with
  Beginner
  Intermediate
  Expert
  These all support both guess and no guess mode

The iOS app will only support English (at least this first version).

Generally each of these games consist of instructions, 
a board that you can interact with, 
a timer, and 
a high scores list.
When you win the game, the app should make a API call to the minesweeper.org API to submit
the score
The app should support all mobile US features such as pinch to zoom in/zoom out and long
press to flat.  There should also be a flag mode button on the app.

The High Score list should show
Name
Time
3BV
3BV/s
Efficiency (many minesweeper variants)
Board

This High Score list will be displayed below each board with the high scores for that day and board & Guess/No Guess mode
You can select Daily, by Season, or All Time to see the scores for those time periods.

Each app should be able to submit games to the minesweeper.org server, but also continue to
run f the api calls are failing.  So, the app should function in offline mode.

The user preferences and name (for High Scores submission) will be stored locally by the app.
Preferences, which mode to start with on open:
  Beginner, Intemediate or Expert
  Guess/No Guess


A future version of the site should support the ability to login with Google.
This will allow us to track a player's high scores and preferences across web and mobile.

A future version of the app should have the ability to serve ads through Google Admob.
https://minesweeper.org/app-ads.txt is served by the minesweeper.org website
