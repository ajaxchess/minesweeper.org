---
title: "Nonosweeper's No Guess Mode: Every Puzzle, Solvable by Logic Alone"
publisher: "Lady Di's Mines"
image: "/static/img/Nono_Guess_Required.png"
author: "Richard Cross"
authorurl: "https://minesweeper.org"
datePublished: 2026-04-11T00:00:00Z
---

# Nonosweeper Gets a No Guess Mode

We've just shipped a new toggle for [Nonosweeper](/nonosweeper): **No Guess mode**. Turn it on and every puzzle — Beginner, Intermediate, or Expert — is guaranteed to be solvable by logic alone, with no coin-flip moments.

---

## The Problem It Solves

Nonogram puzzles are supposed to be about deduction. You study the row and column clues, work out which cells must be mines and which must be safe, and step through the solution methodically. That's the appeal.

But not every randomly-generated puzzle plays fair. Take the board below:

![A Nonosweeper puzzle with a 50/50 guess required on the final four cells](/static/img/Nono_Guess_Required.png)

This puzzle is nearly solved — 45 of 49 cells are already determined. But the final four cells reduce to a pure 50/50. The clues don't give you enough information to distinguish the two possible mine placements. You have to guess, and half the time you lose through no fault of your own.

---

## How No Guess Mode Works

When you enable the toggle, the puzzle generator runs a **constraint-propagation solver** on every candidate board before presenting it to you. The solver simulates solving the nonogram using only the clues:

1. For each row and column, it finds every valid arrangement of mine-blocks that fits the clue given what's already known.
2. Any cell that is a mine in *all* valid arrangements for its row or column is marked as a definite mine. Any cell that is safe in all valid arrangements is marked as definite safe.
3. This repeats — each newly deduced cell constrains its row and column further — until no more progress can be made.

If every cell is determined at the end of that process, the puzzle passes. If any cell is still ambiguous, the generator tries a different seed and repeats until it finds a board that passes.

The check is deterministic for the Puzzle of the Day, so everyone playing in No Guess mode on the same day gets the same board.

---

## Where to Find It

The toggle sits just below the difficulty buttons on the [Nonosweeper](/nonosweeper) page. It works across all three grid sizes and your preference is saved between sessions. Switch it on, pick your difficulty, and enjoy a puzzle you know you can crack.

*— The Lady Di's Mines Team*
