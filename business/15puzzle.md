15puzzle is not strictly a minesweeper puzzle, so it goes under other.
Routes are game-specific to allow sudoku and future games to coexist cleanly:

https://minesweeper.org/other              — hub page listing all games in the Other section
https://minesweeper.org/other/15puzzle     — 15-puzzle landing / daily game
https://minesweeper.org/other/15puzzle/daily      — daily 4×4 puzzle (same for all users each day)
https://minesweeper.org/other/15puzzle/custom     — custom board by size and hash
https://minesweeper.org/other/15puzzle/replay     — replay a board by hash (URL param or manual entry)
https://minesweeper.org/other/15puzzle/generator  — registered users only; create and save custom puzzles with optional photo upload
https://minesweeper.org/other/15puzzle/leaderboard — leaderboard for daily and custom boards

The 15 puzzle is most commonly known as the Gem Puzzle, Boss Puzzle, Game of Fifteen, or Mystic Square. It is also referred to as a sliding puzzle, sliding number puzzle, 16 puzzle, or by the French term Jeu de Taqui

The daily and custom puzzles should have leaderboards and each custom puzzle specified by a board hash should have a board-specific leaderboard. Leaderboards record time (ms) and move count. Scores are sorted primarily by time. Move count is displayed alongside time as an efficiency indicator, analogous to how minesweeper records clicks. The timer starts on the first tile move.
Guests can play all puzzle modes and submit scores to any leaderboard. Guest scores are purged at midnight UTC daily. Registered users retain their scores permanently. Only registered users can upload pictures and access the Generator. Accepted formats: JPG and PNG, 2MB maximum. Images are stored on the EC2 instance for now — a separate future feature will migrate storage to S3.

The photo display mode ("tiles" = photo scrambled onto the tiles, "reveal" = photo hidden as background, revealed on solve) is a URL parameter (e.g. `?mode=tiles` or `?mode=reveal`) and is also configurable by the player in the UI. When the puzzle is solved, the full photo is always revealed regardless of mode.

Photos are live immediately upon upload and publicly accessible to anyone with the puzzle URL. An admin page at https://minesweeper.org/admin/15puzzle-photos allows admins to review all uploaded photos (showing thumbnail, uploader email, upload date, and puzzle URL) and permanently delete any that violate content standards. The style and layout should follow https://minesweeper.org/admin/hscleaning as a reference.

The daily 15puzzle is a solvable 4×4 grid with 15 numbered tiles and 1 blank space (16 spaces total). The puzzle must be guaranteed solvable. The board is seeded by date (YYYY-MM-DD UTC) so every user gets the same puzzle on a given day. The puzzle resets at midnight UTC. Each day's puzzle has its own permanently saved leaderboard keyed by date, so historical daily leaderboards are never overwritten.

The custom page lets you generate a board of any size from 2×2 to 32×32. Width and height are set independently, so rectangular boards (e.g. 3×5) are allowed. The tiles are scrambled in a solvable pattern.  The tiles need to be scrambled in a solvable pattern.  
That board is given a unique hash that can be shared. The hash encodes the grid dimensions and the full tile sequence (including the blank position) as a base64url string. This ensures any board of any size can be reconstructed from the hash alone.
A user can replay the board at https://minesweeper.org/other/replay with the hash included as a parameter in the URL or entered in a field on the page.
The generator is only open to registered users. The generator allows you to make a custom board and upload a photo.  You can also choose if the photo is placed on the tiles
and scrambled or if it is a background that is revealed when you solve the puzzle.  Either way when you finish the puzzle/win, the image should be revealed.
The registered user can save puzzles from the Generator page. Saved puzzles are publicly accessible immediately upon save — anyone with the URL can play them. Users can delete their own saved puzzles, which permanently removes the puzzle and its URL. Users can save up to 32 puzzles by default. The allowed puzzle storage limit is stored as a per-user field in the user table so it can be adjusted on a per-user basis in the future.
