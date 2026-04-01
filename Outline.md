Minesweeper.org is a collection of games that are loosely in the style of Minesweeper.
The site also contains supporting pages and tools.
It features the 
Classic minesweeper games
  Beginner
  Intermediate
  Expert
  Custom
  Leaderboard
  These all support no guess mode

Arcade games like
  Rush

PVP Multiplayer games like
  PVP (matchmaking against next available human or bot)
  Duel (play against a specific opponent)

Variants
  Cylinder (Supports no guess mode)
  Toroid (Supports no guess mode)
  Hexsweeper
  Worldsweeper
  3D cube

Minesweeper Puzzles
  Tentaizu
  Mosaic
  Nonosweeper

Other Puzzles
  Schulte
  15puzzle
  2048
  Sudoku

Generally each of these games consist of 
instructions and history, 
a board that you can interact with, 
a way to share that board with other people,
a timer, 
possible game specific additional scoring like number of mines removed,
possible game complexitiy measurements like 3BV,
possible game efficiency measures such as number of clicks, -> Efficiency = clicks made vs number of clicks necessary to win board,
a global high scores list.

i.e.
Usually the score is just the time, but other ratings such as 
Efficiency (many minesweeper variants)
Rows cleared or mines found (rush).

Board configurations can be shared via a url that contains:
one or more hashes that capture the configuration and 
parameters such as size of the board.
Each board configuration has a leaderboard of games played that are unique to that leaderboard.
So for classic minesweeper Beginner board, there should be hash for that board:
CAgCDAAIkACQAAA=
To play this board, the URL is 
https://minesweeper.org/variants/replay/?rows=9&cols=9&mines=10&hash=CAgCDAAIkACQAAA%3D&date=2026-04-01&mode=beginner&game=standard
There is a Board High Scores list for this hash.  As of 20260331, the Board High Scores List has
"Richard" and "William Murray".  These scores will stay attached to this board, because while there is a daily cleaner, both of these users are registered.

For a Mosaic custom board, the parameters consist of a board size, a hash of all the mine locations on that board, and a mask for which cells are not revealed.
Note that the special board configurations do not have a no guess mode because
the mines are already allocated.  
When a leaderboard is built for a custom board, the guess/no guess parameter in the database should be ignored and only the hash matched.
Some configurations/specific hashes are featured, such as the game of the day for Tentaizu.
Minesweeper.org also provides board editors for some game types.
The customer boards can be shared via copying and pasting the URL, 
but we eventually want to support posting a board and high score on by 
email, Facebook or Twitter.

The board editor should show any complexity calculations for that type of board.  
For instance, 
https://minesweeper.org/variants/board-generator
is a generator for minesweeper standard, toroid, and cylinder | plus a Mosaic generator.
This shows the 3BV complexity value of the board that you have generated.  
This allows users to explore board configurations and 3BV.
In general, the site should explain how to play each game, tips for playing better/faster, and explanations of properties like complexity related to that game.
Example:
Standard Minesweeper:
How to Play:
https://minesweeper.org/how-to-play
Strategy & Tips:
https://minesweeper.org/strategy
Discussion of the 3BV complexity and board configurations
https://minesweeper.org/info/3bv
Ideally, there should be a summary of the history
TBD
and
A discussion of the mathematical analysis of the puzzle, which would be a discussion similar to this video:
https://www.youtube.com/watch?v=ycPDDnQh2qE

The minesweeper.org api and websockets infrastructure should be able to support
other clients such as an
Android or iOS app.  
Developing one or more apps should be on the roadmap.  It might make sense to have a
Classic Minesweeper app
League of Minesweeper app
Each app should be able to submit games to the minesweeper.org server, but also run in 
offline mode.

The site should support the ability to login.  
Currently we support using Google as identity provider.
This allows us to track a player's high scores and preferences.

The site and apps have one or more themes that govern how the site and game render.

The site supports a blog where games, announcements, and discussions happen.

The site supports permanent pages like How-to-Play guides and 
a global links collection of minesweeper.org related sites.

The site and any mobile clients support the ability to serve ads.

The site has an admin section where the server administrators can monitor resource usage 
and game activity.





