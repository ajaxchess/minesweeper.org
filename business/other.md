Minesweeper.org should have a https://minesweeper.org/other section with other puzzles that are not minesweeper variants or minesweeper puzzles. The /other landing page is a simple card grid (styled like /variants) listing all games in the section. The section is displayed as "Other Puzzles" throughout the site (nav, page titles, cards) even though the route is /other.

Under the other section, we want to include 15puzzle and sudoku.
Why are they on this site if they are not minesweeper, a minesweeper variant, or a minesweeper puzzle?  
We want our users to be able to take advantage of our sharing mechanism.  So each board should be specified by a unique hash that can be added as a parameter to the URL.
For some games we also want to provide a generator or other mechanism to allow the users to share something unique about their experience.
For some games we also provide a leaderboard and the games are timed.

For Sudoku, if a user plays a game and wants to share it, there should be a unique hash to that game that the use can share with friends.
For 15 puzzle, the user should be able to select a number of tiles, they should be places in a unique position specified by a hash, and the game should be guaranteed winable.
Registered users should also be able to upload a photo and have that photo appear on the puzzle.  15puzzle has 2 modes: the picture is scrambled by the tiles or the picture
is a background covered by the tiles.  If the picture is covered by the tiles, when you solve the puzzle, the picture is revealed.


