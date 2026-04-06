Create a Jigsaw feature.  There should be a sample picture of Diana in
minesweeper.org/static/img/puzzle that will be our baseline.

Beginner 100 pieces
Intermediate 500 pieces
Expert 1000 pieces

The daily jigsaw page will start with the day's jigsaw image.
Initially, the daily image is selected randomly from static/img/puzzle/.
Future: /admin/jigsaw allows admins to assign a specific image to each date (puzzle queue).
Until an image is explicitly assigned for a date, the random selection is used as fallback.
You then choose a number of pieces, the puzzle scrambles

The jigsaw page should have a board where the pieces are placed,
a space to the right where the pieces are stashed (randomly scattered and piled on top
of each other, as if tipped out of a box), and a small
version of the original picture below and left justified with the main puzzle space.

All the puzzles are timed, but can be paused.
There is a daily leaderboard for each difficulty level (Beginner, Intermediate, Expert).
Authenticated users can pause the puzzle and come back to the puzzle
later.
There should be a restart button, a button that takes you to the image gallery, and a timer.

The image gallery page shows thumbnails of every image in static/img/puzzle/.
Clicking a thumbnail lets you choose a difficulty and start a jigsaw of that image.
New images are added to the gallery simply by dropping them into that directory.

Pieces are traditional interlocking jigsaw shapes (tabs and blanks on each edge).

Ideally, when two pieces that go together are brought close 
to each other on the board, they should snap together.
Snap distance is a fixed threshold (not user-configurable — keeps the UI simple for all ages).
It would be great if we had a snapping sound when the pieces connect.
The snapping sound respects a mute preference (mute button on the game page).

Mobile/touch: drag and touch supported.

There should also be a puzzle generator page.
This allows an authenticated user to upload an image and share the
image and puzzle type (number of pieces) with a friend via URL.
Guests can play but cannot upload images.


