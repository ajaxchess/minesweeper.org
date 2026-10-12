# Sudoku — Difficulty by Solving Technique

**Status:** idea
**Feature ID:** F-SUDOKU-GRADING
**Author:** Gisela Velazco
**Date:** 2026-10-12

---

## Problem / Motivation

Sudoku difficulty is currently set only by the number of givens (F-SUDOKU-HARDER
lowered them to easy 32, medium 28, hard 25, expert 22, daily 28). Givens are a
weak proxy: a 25-given puzzle can fall to singles alone while a 30-given one may
need an X-Wing. Players still find every level easy. Newspaper Sudokus grade
puzzles by the hardest technique a human needs to solve them.

---

## Success Criteria

- [ ] Each difficulty requires a defined set of techniques and no technique
      beyond it (e.g. easy: singles only; expert: needs at least one advanced technique).
- [ ] Players report a clear step in difficulty between levels.
- [ ] The daily puzzle is the same for every player and stays reproducible from its seed.
- [ ] Generation stays fast enough on a phone (target < 2 s), or puzzles are pre-generated.

---

## Scope

**In this feature:**
- A logical solver that applies techniques in order of difficulty and reports
  the hardest one used: naked/hidden singles, naked/hidden pairs and triples,
  pointing pairs / box-line reduction, X-Wing, Swordfish, XY-Wing (to be confirmed).
- Mapping from hardest technique to difficulty level.
- Generator that keeps generating/removing until the puzzle grades into the
  requested level.

**Out of scope (future):**
- Showing the technique needed as a hint to the player.

---

## Key Design Decisions

*Open questions:*
- Client-side generation (current) vs. server-side pre-generation of a daily
  pool: grading with advanced techniques may be too slow in the browser.
- Whether to keep a minimum/maximum number of givens per level alongside the
  technique grade.
- What to do with leaderboard history recorded before the change (times are
  not comparable across the change).

---

## Implementation Notes

*Filled in when work completes.*
