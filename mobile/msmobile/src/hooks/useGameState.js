/**
 * useGameState.js
 *
 * Game state management via useReducer.
 * Encapsulates all board logic so GameScreen stays clean.
 *
 * Mines are NOT placed until the first cell is tapped (first-click safety).
 * Before first click the board is in "pending" state — all cells covered.
 */

import { useReducer, useCallback } from 'react';
import {
  BOARD_SIZES,
  placeMines,
  placeMinesNoGuess,
  neighbors,
} from '../gameEngine';

// ── State shape ───────────────────────────────────────────────────────────────

function makeInitialState(mode = 'beginner', noGuess = false) {
  const { rows, cols, mines } = BOARD_SIZES[mode];
  const n = rows * cols;
  return {
    mode,
    noGuess,
    rows,
    cols,
    mines,
    board:       null,           // null until first click
    mineSet:     null,
    revealed:    new Uint8Array(n),
    flagged:     new Uint8Array(n),
    explodedIdx: -1,             // index of the mine that was hit
    started:     false,          // true after first click (mines placed)
    over:        false,
    won:         false,
    leftClicks:  0,
    rightClicks: 0,
    chordClicks: 0,
  };
}

// ── BFS reveal helper ─────────────────────────────────────────────────────────
// Mutates a copy of `revealed` in place and returns it.

function bfsReveal(startIdx, board, mineSet, revealed, rows, cols) {
  const next = new Uint8Array(revealed);
  const queue = [startIdx];
  while (queue.length) {
    const idx = queue.pop();
    if (next[idx] || mineSet.has(idx)) continue;
    next[idx] = 1;
    const r = Math.floor(idx / cols), c = idx % cols;
    if (board[r][c] === 0) {
      for (const [nr, nc] of neighbors(r, c, rows, cols)) {
        const ni = nr * cols + nc;
        if (!next[ni] && !mineSet.has(ni)) queue.push(ni);
      }
    }
  }
  return next;
}

function checkWon(revealed, mineSet, total) {
  let revealedCount = 0;
  for (let i = 0; i < total; i++) if (revealed[i]) revealedCount++;
  return revealedCount === total - mineSet.size;
}

// ── Reducer ───────────────────────────────────────────────────────────────────

function reducer(state, action) {
  switch (action.type) {

    case 'NEW_GAME':
      return makeInitialState(action.mode ?? state.mode, action.noGuess ?? state.noGuess);

    case 'SET_MODE':
      return makeInitialState(action.mode, state.noGuess);

    case 'SET_NO_GUESS':
      return makeInitialState(state.mode, action.noGuess);

    case 'REVEAL': {
      const { idx } = action;
      const { rows, cols, mines, noGuess, revealed, flagged, started, over, won } = state;
      if (over || won) return state;
      if (flagged[idx]) return state;
      if (revealed[idx]) return state;

      let board    = state.board;
      let mineSet  = state.mineSet;
      let leftClicks = state.leftClicks + 1;

      // First click — place mines now (safe zone around clicked cell)
      if (!started) {
        const safeR = Math.floor(idx / cols);
        const safeC = idx % cols;
        const result = noGuess
          ? placeMinesNoGuess(rows, cols, mines, safeR, safeC)
          : placeMines(rows, cols, mines, safeR, safeC);
        board   = result.board;
        mineSet = result.mineSet;
      }

      // Hit a mine
      if (mineSet.has(idx)) {
        const revealAll = new Uint8Array(rows * cols).fill(0);
        for (const mi of mineSet) revealAll[mi] = 1;
        return { ...state, board, mineSet, started: true, over: true,
                 revealed: revealAll, explodedIdx: idx, leftClicks };
      }

      // Safe cell — BFS reveal
      const nextRevealed = bfsReveal(idx, board, mineSet, revealed, rows, cols);
      const isWon = checkWon(nextRevealed, mineSet, rows * cols);

      return {
        ...state,
        board,
        mineSet,
        started:  true,
        revealed: nextRevealed,
        won:      isWon,
        over:     isWon,
        leftClicks,
      };
    }

    case 'TOGGLE_FLAG': {
      const { idx } = action;
      const { revealed, flagged, over, won } = state;
      if (over || won) return state;
      if (revealed[idx]) return state;

      const nextFlagged = new Uint8Array(flagged);
      nextFlagged[idx] = nextFlagged[idx] ? 0 : 1;
      return {
        ...state,
        flagged:     nextFlagged,
        rightClicks: state.rightClicks + 1,
      };
    }

    case 'CHORD': {
      // Reveal all non-flagged neighbours of a revealed numbered cell
      // if the flagged neighbour count matches the cell's value.
      const { idx } = action;
      const { board, mineSet, revealed, flagged, rows, cols, over, won } = state;
      if (over || won) return state;
      if (!revealed[idx]) return state;

      const r = Math.floor(idx / cols), c = idx % cols;
      const cellVal = board[r][c];
      if (cellVal <= 0) return state;

      const ns = neighbors(r, c, rows, cols);
      const flagCount = ns.filter(([nr, nc]) => flagged[nr * cols + nc]).length;
      if (flagCount !== cellVal) return state;

      // Reveal all unflagged, unrevealed neighbours
      let nextRevealed = revealed;
      let hitMine = false;
      let explodedIdx = -1;

      for (const [nr, nc] of ns) {
        const ni = nr * cols + nc;
        if (revealed[ni] || flagged[ni]) continue;
        if (mineSet.has(ni)) {
          hitMine = true;
          explodedIdx = ni;
          break;
        }
        nextRevealed = bfsReveal(ni, board, mineSet, nextRevealed, rows, cols);
      }

      if (hitMine) {
        const revealAll = new Uint8Array(rows * cols).fill(0);
        for (const mi of mineSet) revealAll[mi] = 1;
        return { ...state, over: true, revealed: revealAll, explodedIdx,
                 chordClicks: state.chordClicks + 1 };
      }

      const isWon = checkWon(nextRevealed, mineSet, rows * cols);
      return { ...state, revealed: nextRevealed, won: isWon, over: isWon,
               chordClicks: state.chordClicks + 1 };
    }

    default:
      return state;
  }
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export default function useGameState(initialMode = 'beginner', initialNoGuess = false) {
  const [state, dispatch] = useReducer(reducer, makeInitialState(initialMode, initialNoGuess));

  const newGame      = useCallback((mode, noGuess) => dispatch({ type: 'NEW_GAME',    mode, noGuess }), []);
  const setMode      = useCallback((mode)          => dispatch({ type: 'SET_MODE',    mode }),          []);
  const setNoGuess   = useCallback((noGuess)       => dispatch({ type: 'SET_NO_GUESS', noGuess }),      []);
  const revealCell   = useCallback((idx)           => dispatch({ type: 'REVEAL',      idx }),           []);
  const toggleFlag   = useCallback((idx)           => dispatch({ type: 'TOGGLE_FLAG', idx }),           []);
  const chordCell    = useCallback((idx)           => dispatch({ type: 'CHORD',       idx }),           []);

  return { state, newGame, setMode, setNoGuess, revealCell, toggleFlag, chordCell };
}
