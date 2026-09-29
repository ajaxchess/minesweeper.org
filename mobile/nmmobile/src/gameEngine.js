'use strict';

export const NM_COLS = 9;
export const NM_EPOCH = '2024-01-01';

// Pair colours: 1↔9 red, 2↔8 blue, 3↔7 green, 4↔6 orange, 5↔5 purple
export const NM_COLORS = [
  '',
  '#e53935', // 1
  '#1976d2', // 2
  '#388e3c', // 3
  '#f57c00', // 4
  '#7b1fa2', // 5
  '#f57c00', // 6
  '#388e3c', // 7
  '#1976d2', // 8
  '#e53935', // 9
];

// ── Seeded RNG ─────────────────────────────────────────────────────────────────
function mulberry32(seed) {
  return () => {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function fnv1a(s) {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h;
}

// ── Board number / row count (mirrors numbers_match_generator.py) ──────────────
export function boardNumber(dateStr) {
  return Math.floor((new Date(dateStr) - new Date(NM_EPOCH)) / 86400000) + 1;
}

export function initialRows(_boardNum) {
  return 4;
}

export function collapseEmptyRows(board, rows) {
  const newBoard = [];
  for (let r = 0; r < rows; r++) {
    const row = board.slice(r * NM_COLS, (r + 1) * NM_COLS);
    if (row.some(v => v !== 0)) newBoard.push(...row);
  }
  return { board: newBoard, rows: newBoard.length / NM_COLS };
}

export function generateBoardClient(seed, rows) {
  const total = rows * NM_COLS;
  const base  = Array.from({ length: total }, (_, i) => (i % NM_COLS) + 1);
  const rng   = mulberry32(fnv1a(String(seed)));
  for (let i = total - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [base[i], base[j]] = [base[j], base[i]];
  }
  return base;
}

// ── Core matching rules ────────────────────────────────────────────────────────
export function canMatch(a, b) {
  return a !== 0 && b !== 0 && (a === b || a + b === 10);
}

export function areAdjacent(board, i, j) {
  if (i === j) return false;
  const [lo, hi]   = i < j ? [i, j] : [j, i];
  const rowLo = Math.floor(lo / NM_COLS), colLo = lo % NM_COLS;
  const rowHi = Math.floor(hi / NM_COLS), colHi = hi % NM_COLS;
  const dr = rowHi - rowLo, dc = colHi - colLo;

  // Horizontal — same row
  if (rowLo === rowHi) {
    for (let k = lo + 1; k < hi; k++) if (board[k] !== 0) return false;
    return true;
  }
  // Vertical — same column
  if (colLo === colHi) {
    for (let k = lo + NM_COLS; k < hi; k += NM_COLS) if (board[k] !== 0) return false;
    return true;
  }
  // Diagonal
  if (Math.abs(dr) === Math.abs(dc)) {
    const stepC = dc > 0 ? 1 : -1;
    for (let s = 1; s < dr; s++)
      if (board[(rowLo + s) * NM_COLS + colLo + s * stepC] !== 0) return false;
    return true;
  }
  // Horizontal wrap — flat path (row-end → next row-start treated as consecutive)
  for (let k = lo + 1; k < hi; k++) if (board[k] !== 0) return false;
  return true;
}

export function calcPairScore(board, i, j) {
  const [lo, hi]   = i < j ? [i, j] : [j, i];
  const rowLo = Math.floor(lo / NM_COLS), colLo = lo % NM_COLS;
  const rowHi = Math.floor(hi / NM_COLS), colHi = hi % NM_COLS;
  const dr = rowHi - rowLo, dc = colHi - colLo;
  let empty = 0;

  if (rowLo === rowHi) {
    for (let k = lo + 1; k < hi; k++) if (board[k] === 0) empty++;
  } else if (colLo === colHi) {
    for (let k = lo + NM_COLS; k < hi; k += NM_COLS) if (board[k] === 0) empty++;
  } else if (Math.abs(dr) === Math.abs(dc)) {
    const stepC = dc > 0 ? 1 : -1;
    for (let s = 1; s < dr; s++)
      if (board[(rowLo + s) * NM_COLS + colLo + s * stepC] === 0) empty++;
  } else {
    for (let k = lo + 1; k < hi; k++) if (board[k] === 0) empty++;
  }

  return 1 + Math.min(4, empty);
}

export function countRowClearBonus(newBoard, prevBoard, rows) {
  let bonus = 0;
  for (let r = 0; r < rows; r++) {
    const start     = r * NM_COLS;
    const nowEmpty  = newBoard.slice(start, start + NM_COLS).every(v => v === 0);
    const hadValues = prevBoard.slice(start, start + NM_COLS).some(v => v !== 0);
    if (nowEmpty && hadValues) bonus += 10;
  }
  return bonus;
}

export function getAxisCells(board, idx) {
  const hovRow = Math.floor(idx / NM_COLS);
  const hovCol = idx % NM_COLS;
  const result = [];
  for (let j = 0; j < board.length; j++) {
    if (j === idx) continue;
    const r = Math.floor(j / NM_COLS);
    const c = j % NM_COLS;
    const isWrap = (hovCol === 0 && j === idx - 1) ||
                   (hovCol === NM_COLS - 1 && j === idx + 1);
    if (r === hovRow || c === hovCol ||
        (r - hovRow) === (c - hovCol) || (r - hovRow) === -(c - hovCol) || isWrap) {
      result.push(j);
    }
  }
  return result;
}

export function findHint(board) {
  const len = board.length;
  for (let i = 0; i < len - 1; i++) {
    if (board[i] === 0) continue;
    for (let j = i + 1; j < len; j++) {
      if (board[j] === 0) continue;
      if (canMatch(board[i], board[j]) && areAdjacent(board, i, j)) return [i, j];
    }
  }
  return null;
}

// ── Time formatting ────────────────────────────────────────────────────────────
export function fmtTime(secs) {
  return `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}`;
}

// ── Today string (UTC) ─────────────────────────────────────────────────────────
export function getTodayString() {
  return new Date().toISOString().slice(0, 10);
}
