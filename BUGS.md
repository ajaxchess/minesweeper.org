
-- Fixed below --

B4 "New Duel" button text invisible in Diana/classic skin
   The global rule `html[data-skin="classic"] a { color: #ff3300 }` made the button
   text red-on-red (button background is also var(--accent) = #ff3300).
   Fixed by adding .duel-play-again and :visited to the button-styled links exception block.

B1 Custom game does not know your ID even if you are logged in

B2 If you play Intermediate, the "View Leaderboard" link takes you to the Beginner leaderboard.  This should take you to the Intermediate leaderboard.

B3 Board-specific leaderboard (replay page) does not show scores from the global leaderboard
   When a player's score is submitted through the normal game it goes into the scores table.
   The board-specific leaderboard only queried replay_scores, so those global scores were invisible
   on the replay/custom board leaderboard even though the player's board hash was present.
   Fixed by merging both tables in GET /api/replay-scores.