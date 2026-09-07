---
Feature ID: F105
Title: Meowdoku Save Puzzle
Status: in-progress
Author: Richard Cross
---

## What

Allow logged-in users to save puzzles they design in the Meowdoku Generator to their profile. A "Save Puzzle" button appears in the generator — enabled only when the puzzle is logically solvable — and saved puzzles appear in a new section on the user's profile page.

## Why

Users invest time designing Meowdoku puzzles they want to revisit or share later. Currently they can only copy a share link; if they lose that link, the puzzle is gone. Saving to profile provides a persistent personal library accessible from any device.

## Acceptance Criteria

- Save button is disabled when puzzle status is anything other than "Valid — logically solvable!"
- Save button is hidden (or shows "Sign in") for unauthenticated users
- Each user can save up to 50 puzzles (unique by board hash)
- Duplicate saves are silently accepted (idempotent — no error if already saved)
- Profile page shows a "Meowdoku Saved Puzzles" section with: grid thumbnail color, size, date saved, Play link, Delete button
- All new UI strings are in the translation system (27 languages)

## Implementation Notes

- DB: `meowdoku_saved_puzzles` table via `MeowdokuSavedPuzzle` model in `database_template.py`
- API: `POST /api/meowdoku/saved-puzzles`, `DELETE /api/meowdoku/saved-puzzles/{id}`
- Generator JS hook: observes `#mk-gen-status` class changes via MutationObserver to mirror the enabled state
- Board hash is the existing base64url encoding from `boardHash()` in `meowdoku.js`
- Translation keys prefixed `mk_gen_save_` and `profile_mk_saves_`
