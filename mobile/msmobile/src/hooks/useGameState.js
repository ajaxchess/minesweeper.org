/**
 * useGameState.js
 *
 * Game state management via useReducer.
 * Encapsulates all board logic so GameScreen stays clean.
 *
 * Mines are NOT placed until the first cell is tapped (first-click safety).
 * Before first click the board is in "pending" state — all cells covered.
 *
 * Move log (F-MS-VERIFY-APP): every move the reducer performs is recorded as
 * [t_ms, type, row, col] — 'l' reveal, 'r' flag toggle, 'c' chord — with t_ms
 * counted from the first reveal. The server replays it with these exact rules
 * (minesweeper_engine.replay(app_rules=True)) before the score is trusted, so a
 * change to REVEAL, TOGGLE_FLAG, CHORD or bfsReveal must also change the server
 * replay; regenerate tests/fixtures/msmobile_games.json with
 * `node tests/fixtures/gen_msmobile_games.js` (repo root) so the parity test checks it.
 */

import { useReducer, useCallback } from 'react';
import {
  BOARD_SIZES,
  placeMines,
  placeMinesNoGuess,
  neighbors,
} from '../gameEngine';

// ── State shape ───────────────────────────────────────────────────────────────

let nextGameId = 1;

export function makeInitialState(mode = 'beginner', noGuess = false) {
  const { rows, cols, mines } = BOARD_SIZES[mode];
  const n = rows * cols;
  return {
    gameId:      nextGameId++,   // a new start token is fetched for each game
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
    startTime:   null,           // action.now of the first reveal
    log:         [],             // move log, see the header
  };
}

// One move log entry. `now` comes from the action (Date.now() at the tap), so the
// reducer stays pure. Never goes backwards, which the server would reject.
function logMove(state, now, type, idx, startTime = state.startTime) {
  const last = state.log.length ? state.log[state.log.length - 1][0] : 0;
  const t = startTime != null && now != null ? Math.max(last, Math.round(now - startTime)) : last;
  return [...state.log, [t, type, Math.floor(idx / state.cols), idx % state.cols]];
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

export function reducer(state, action) {
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
      const startTime = started ? state.startTime : (action.now ?? null);
      const log = logMove(state, action.now, 'l', idx, startTime);

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
                 revealed: revealAll, explodedIdx: idx, leftClicks, startTime, log };
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
        startTime,
        log,
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
        log:         logMove(state, action.now, 'r', idx),
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
                 chordClicks: state.chordClicks + 1, log: logMove(state, action.now, 'c', idx) };
      }

      const isWon = checkWon(nextRevealed, mineSet, rows * cols);
      return { ...state, revealed: nextRevealed, won: isWon, over: isWon,
               chordClicks: state.chordClicks + 1, log: logMove(state, action.now, 'c', idx) };
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
  const revealCell   = useCallback((idx) => dispatch({ type: 'REVEAL',      idx, now: Date.now() }), []);
  const toggleFlag   = useCallback((idx) => dispatch({ type: 'TOGGLE_FLAG', idx, now: Date.now() }), []);
  const chordCell    = useCallback((idx) => dispatch({ type: 'CHORD',       idx, now: Date.now() }), []);

  return { state, newGame, setMode, setNoGuess, revealCell, toggleFlag, chordCell };
}
