import { useReducer, useCallback } from 'react';
import {
  NM_COLS,
  canMatch,
  areAdjacent,
  calcPairScore,
  countRowClearBonus,
  collapseEmptyRows,
  findHint,
} from '../gameEngine';

const HINT_COST       = 3;
const UNDO_COST       = 5;
const ADD_LINES_LIMIT = 5;

const INITIAL_STATE = {
  board:         [],
  rows:          0,
  diffRows:      4,
  score:         0,
  selected:      null,
  hintPair:      null,
  history:       [],
  undosLeft:     3,
  hintsLeft:     9,
  addLinesLeft:  ADD_LINES_LIMIT,
  isPOTD:        false,
  puzzleId:      null,
  linesAdded:    0,
  won:             false,
  started:         false,
  scoreSaved:      false,
  addLinesFlash:   false,
  showConnections: false,
  // F-NM-VERIFY: the server replays this log (see numbers_match_engine.py).
  moves:           [],
  startTime:       null,
  gameToken:       null,
};

// ms since the first cell press, 0 before it.
function moveTime(state, now) {
  return state.startTime ? now - state.startTime : 0;
}

// Exported for the server parity fixtures (tests/fixtures/gen_numbers_match_js_games.js).
export function reducer(state, action) {
  switch (action.type) {

    case 'INIT':
      return {
        ...INITIAL_STATE,
        board:    [...action.boardData],
        rows:     action.rows,
        diffRows: action.rows,
        isPOTD:   action.isPOTD,
        puzzleId: action.puzzleId,
      };

    case 'SET_TOKEN':
      return action.puzzleId === state.puzzleId ? { ...state, gameToken: action.token } : state;

    case 'CELL_PRESS': {
      const { idx } = action;
      if (state.won || state.board[idx] === 0) return state;

      const startTime = state.startTime ?? action.now;
      const base = { ...state, hintPair: null, started: true, startTime };

      if (state.selected === null) return { ...base, selected: idx };
      if (state.selected === idx)  return { ...base, selected: null };

      if (
        canMatch(state.board[state.selected], state.board[idx]) &&
        areAdjacent(state.board, state.selected, idx)
      ) {
        const prevBoard = [...state.board];
        const newBoard  = [...state.board];
        newBoard[state.selected] = 0;
        newBoard[idx]            = 0;

        let score = state.score + calcPairScore(state.board, state.selected, idx);
        score += countRowClearBonus(newBoard, prevBoard, state.rows);

        const won = newBoard.every(v => v === 0);
        if (won) score += 150;

        const history = [
          ...state.history,
          { board: prevBoard, score: state.score, rows: state.rows,
            linesAdded: state.linesAdded, addLinesLeft: state.addLinesLeft },
        ];
        if (history.length > 3) history.shift();

        const collapsed = won ? { board: newBoard, rows: state.rows } : collapseEmptyRows(newBoard, state.rows);
        const moves = [...state.moves, ['m', action.now - startTime, state.selected, idx]];
        return { ...base, board: collapsed.board, rows: collapsed.rows, score, selected: null, history, won, moves };
      }

      return { ...base, selected: idx };
    }

    case 'UNDO': {
      if (state.undosLeft <= 0 || state.history.length === 0 || state.won) return state;
      const snap    = state.history[state.history.length - 1];
      const history = state.history.slice(0, -1);
      return {
        ...state,
        board:        snap.board,
        score:        Math.max(0, snap.score - UNDO_COST),
        rows:         snap.rows,
        linesAdded:   snap.linesAdded,
        addLinesLeft: snap.addLinesLeft ?? ADD_LINES_LIMIT,
        undosLeft:    state.undosLeft - 1,
        selected:     null,
        hintPair:     null,
        history,
        moves:        [...state.moves, ['u', moveTime(state, action.now)]],
      };
    }

    case 'HINT': {
      if (state.hintsLeft <= 0 || state.won) return state;
      const pair = findHint(state.board);
      if (!pair) return { ...state, addLinesFlash: true };
      return {
        ...state,
        selected:      null,
        hintPair:      pair,
        hintsLeft:     state.hintsLeft - 1,
        score:         Math.max(0, state.score - HINT_COST),
        addLinesFlash: false,
        moves:         [...state.moves, ['h', moveTime(state, action.now)]],
      };
    }

    case 'CLEAR_FLASH':
      return { ...state, addLinesFlash: false };

    case 'TOGGLE_CONNECTIONS':
      return { ...state, showConnections: !state.showConnections };

    case 'DISMISS_WIN':
      return { ...state, won: false, started: false };

    case 'ADD_LINES': {
      if (state.won || state.addLinesLeft <= 0) return state;
      const remaining = state.board.filter(v => v !== 0);
      if (!remaining.length) return state;
      const history = [
        ...state.history,
        { board: [...state.board], score: state.score, rows: state.rows,
          linesAdded: state.linesAdded, addLinesLeft: state.addLinesLeft },
      ];
      if (history.length > 3) history.shift();
      while (remaining.length % NM_COLS !== 0) remaining.push(0);
      return {
        ...state,
        board:         [...state.board, ...remaining],
        rows:          state.rows + remaining.length / NM_COLS,
        linesAdded:    state.linesAdded + 1,
        addLinesLeft:  state.addLinesLeft - 1,
        selected:      null,
        hintPair:      null,
        addLinesFlash: false,
        history,
        moves:         [...state.moves, ['a', moveTime(state, action.now)]],
      };
    }

    default:
      return state;
  }
}

export default function useGameState() {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);

  const initGame          = useCallback((boardData, rows, puzzleId, isPOTD) =>
    dispatch({ type: 'INIT', boardData, rows, puzzleId, isPOTD }), []);
  // Timestamps are taken here, not in the reducer, so the reducer stays pure.
  const pressCell         = useCallback((idx) => dispatch({ type: 'CELL_PRESS', idx, now: Date.now() }), []);
  const undo              = useCallback(() => dispatch({ type: 'UNDO', now: Date.now() }), []);
  const hint              = useCallback(() => dispatch({ type: 'HINT', now: Date.now() }), []);
  const addLines          = useCallback(() => dispatch({ type: 'ADD_LINES', now: Date.now() }), []);
  const setToken          = useCallback((puzzleId, token) =>
    dispatch({ type: 'SET_TOKEN', puzzleId, token }), []);
  const clearFlash        = useCallback(() => dispatch({ type: 'CLEAR_FLASH' }), []);
  const toggleConnections = useCallback(() => dispatch({ type: 'TOGGLE_CONNECTIONS' }), []);
  const dismissWin        = useCallback(() => dispatch({ type: 'DISMISS_WIN' }), []);

  return { state, initGame, pressCell, undo, hint, addLines, setToken, clearFlash, toggleConnections, dismissWin };
}
