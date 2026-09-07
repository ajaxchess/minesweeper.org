# Meowdoku Save Puzzle

**Status:** done  
**Feature ID:** F105  
**Author:** Richard Cross  
**Date:** 2026-09-06

---

Allow logged-in users to save puzzles they design in the Meowdoku Generator to their profile. A "Save Puzzle" button appears in the generator — enabled only when the puzzle is logically solvable — and saved puzzles appear in a new section on the user's profile page.

## Why

Users invest time designing Meowdoku puzzles they want to revisit or share later. Currently they can only copy a share link; if they lose that link, the puzzle is gone. Saving to profile provides a persistent personal library accessible from any device.

## Acceptance Criteria

- Save button is disabled when puzzle status is anything other than "Valid — logically solvable!"
- Save button is hidden (shows sign-in link) for unauthenticated users
- Each user can save up to 50 puzzles (unique by board hash)
- Duplicate saves are silently accepted (idempotent)
- Profile page shows a "Meowdoku Saved Puzzles" section with grid size, date saved, Play link, Delete button
- All new UI strings are in the translation system (27 languages)

## Implementation Notes

- **DB**: `meowdoku_saved_puzzles` table via `MeowdokuSavedPuzzle` model in `database_template.py`. Unique index on `(user_email, board_hash)`. 50-puzzle cap enforced at write time.
- **API**: `POST /api/meowdoku/saved-puzzles` (auth required, idempotent on duplicate hash), `DELETE /api/meowdoku/saved-puzzles/{id}` (owner-only).
- **Generator**: Save button added to `meowdoku_generator.html`. Enabled state mirrored from the validity status badge via `MutationObserver` on `#mk-gen-status`. Inline script runs after `meowdoku-generator.js`.
- **Profile**: `meowdoku_saves` query passed to `profile.html`; new section with Play links, per-item Delete, and Delete All.
- **Translations**: 8 new keys (`mk_gen_save_btn`, `mk_gen_saved`, `mk_gen_save_error`, `mk_gen_save_login`, `profile_mk_saves_title`, `profile_mk_saves_empty`, `profile_mk_saves_play`, `profile_mk_saves_delete`) translated to all 24 supported non-English languages via workflow agents.
- **Commit**: `0ee737a8`
