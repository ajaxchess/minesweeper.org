-- F-SUDOKU-GRADING: Create sudoku_puzzles table for pre-generated puzzle pool.
-- Run on the production database before pushing the code change.

CREATE TABLE IF NOT EXISTS sudoku_puzzles (
  id                INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  difficulty        VARCHAR(16) NOT NULL,
  givens            VARCHAR(81) NOT NULL,
  solution          VARCHAR(81) NOT NULL,
  board_hash        VARCHAR(64) NOT NULL,
  givens_count      INT NOT NULL,
  hardest_technique VARCHAR(32) NOT NULL,
  puzzle_date       VARCHAR(10) NULL,
  served_count      INT NOT NULL DEFAULT 0,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_sudoku_puzzles_hash (board_hash),
  INDEX ix_sudoku_puzzles_diff_date (difficulty, puzzle_date),
  INDEX ix_sudoku_puzzles_diff_served (difficulty, served_count)
);
