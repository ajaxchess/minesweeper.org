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
  Globesweeper
  3D cube

Puzzles
  Tentaizu
  Mosaic
  Nonosweeper

  Schulte
  15puzzle
  2048
  Sudoku
  

Collections
  League of Minesweeper
    Classic Minesweeper
    Nonosweeper
    Schulte
    15puzzle
    2048
    Sudoku

Generally each of these games consist of instructions, 
a board that you can interact with, 
a way to share the board with other people,
a timer, and 
a global high scores list.
Usually the score is just the time, but other ratings such as 
Efficiency (many minesweeper variants)
Rows or mines found (rush).
Board configurations can be shared via a url that contains:
one or more hashes that capture the configuration and 
parameters such as size of the board.
Each board configuration has a leaderboard of games played that are unique to that leaderboard.  That leaderboard should 
For a classic minesweeper custom game, this consists of board size and a hash of all 
the mine locations on that board.
For a Mosaic custom board, this consists of a board size, a hash of all the mine locations on that board, and a mask for which cells are not revealed.
Note that the special board configurations do not have a no guess mode because
the mines are already allocated.  When a leaderboard is built for a custom board, the
guess/no guess parameter in the database should be ignored and only the hash matched.
Some configurations are featured, such as the game of the day for Tentaizu.
Minesweeper.org also provides board editors for some game types.
The customer boards can be shared via copying and pasting the URL, 
but we eventually want to support posting a board and high score on by 
email, Facebook or X.

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

The site has an admin section where the server administrators can monitor resource usage 
and game activity.





