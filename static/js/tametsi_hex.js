'use strict';

const THEX_SQRT3 = Math.sqrt(3);
const THEX_SVG_NS = 'http://www.w3.org/2000/svg';
const THEX_DIRS = [[1,0],[-1,0],[0,1],[0,-1],[1,-1],[-1,1]];
const THEX_ADJ_COLORS = ['','#1565c0','#2e7d32','#c62828','#0d47a1','#b71c1c','#00695c','#4a148c','#424242'];
const THEX_QUESTION = -2; // board value for "?" cells — safe but give no information

const THEX_PUZZLES = {
  1: {
    R: 2,
    mines: new Set(['0,-1','1,-1','1,0']),
    startRevealed: {'-1,0':1,'0,0':3,'0,1':1},
    tutorialText: '<strong>Tutorial 1 — Tiny Board (R=2, 3 mines):</strong> Watch the two counters above the board. <strong>🚩 flags / total</strong> tracks how many flags you\'ve placed. <strong>💣 mines left</strong> (top-right) counts unflagged mines — when it hits 0, every remaining hidden cell is safe to reveal. Right-click to flag a suspected mine. Use the numbers to deduce mine locations and click every safe cell to win.',
  },
  2: {
    R: 3,
    mines: new Set(['1,0','0,-1','1,-1','2,-1']),
    startRevealed: {'-1,0':1,'0,0':3,'0,1':1},
    tutorialText: '<strong>Tutorial 2 — Medium Board (R=3, 4 mines):</strong> Same starting clues as Tutorial 1, but the board is larger with more hidden cells. Build a deduction chain from the revealed numbers to identify each mine\'s location.',
  },
  3: {
    R: 4,
    mines: new Set(['-2,0','-1,-1','-1,-2','0,-3','2,-3','3,-3','3,-2','3,-1','2,1','-1,2','1,2','-2,3']),
    startRevealed: {'-2,-1':3,'-3,0':1,'-3,1':1},
    tutorialText: '<strong>Tutorial 3 — Full Board (R=4, 12 mines):</strong> A larger board with more mines spread across the hex grid. When you reveal a cell with 0 mine-neighbours, its neighbours are uncovered automatically — use that cascade to open up new deduction opportunities.',
  },
  4: {
    R: 3,
    mines: new Set(['0,-1','2,-1','2,0']),
    startRevealed: {'0,-2':1,'1,-2':1,'-1,-1':1},
    questionCells: new Set(['-1,0','0,0','1,0']),
    tutorialText: '<strong>Tutorial 4 — Question Marks (R=3, 3 mines):</strong> Some cells show <strong>?</strong> when revealed. A <strong>?</strong> cell is safe — it is not a mine — but it reveals nothing about how many mines are nearby. Treat a revealed <strong>?</strong> as a safe cell you can eliminate from your deductions, then use the numbered clues to locate all 3 mines.',
  },
};

let thexState = {};
let thexSvgEl = null;
let thexCellSize = 28;

function thexKey(q, r) { return `${q},${r}`; }

function thexBuildCells(R) {
  const out = [];
  for (let r = -(R-1); r <= R-1; r++)
    for (let q = -(R-1); q <= R-1; q++)
      if (Math.abs(q) <= R-1 && Math.abs(r) <= R-1 && Math.abs(q+r) <= R-1)
        out.push([q, r]);
  out.sort((a, b) => a[1] !== b[1] ? a[1]-b[1] : a[0]-b[0]);
  return out;
}

function thexNeighbours(q, r, R) {
  return THEX_DIRS
    .map(([dq,dr]) => [q+dq, r+dr])
    .filter(([nq,nr]) => Math.abs(nq)<=R-1 && Math.abs(nr)<=R-1 && Math.abs(nq+nr)<=R-1);
}

function thexBuildBoard(cells, mines, R, questionCells) {
  const board = new Map();
  for (const [q,r] of cells) {
    const k = thexKey(q,r);
    if (mines.has(k)) { board.set(k,-1); continue; }
    if (questionCells && questionCells.has(k)) { board.set(k, THEX_QUESTION); continue; }
    let count = 0;
    for (const [nq,nr] of thexNeighbours(q,r,R))
      if (mines.has(thexKey(nq,nr))) count++;
    board.set(k, count);
  }
  return board;
}

function thexHexCenter(q, r) {
  return [thexCellSize * THEX_SQRT3 * (q + r/2), thexCellSize * 1.5 * r];
}

function thexHexPoints(cx, cy, s) {
  const pts = [];
  for (let i=0; i<6; i++) {
    const angle = Math.PI/180*(60*i+30);
    pts.push(`${(cx+s*Math.cos(angle)).toFixed(2)},${(cy+s*Math.sin(angle)).toFixed(2)}`);
  }
  return pts.join(' ');
}

function thexChooseSize(R) {
  const maxW = Math.min(window.innerWidth-40, 540);
  const fit = Math.floor(maxW / (THEX_SQRT3 * (2*R-1)));
  return Math.max(16, Math.min(32, fit));
}

function thexBuildSVG() {
  const {R, cells} = thexState;
  thexCellSize = thexChooseSize(R);
  const wrap = document.getElementById('thex-board-wrap');
  if (!wrap) return;
  wrap.innerHTML = '';

  let minX=Infinity, maxX=-Infinity, minY=Infinity, maxY=-Infinity;
  for (const [q,r] of cells) {
    const [cx,cy] = thexHexCenter(q,r);
    minX=Math.min(minX,cx-thexCellSize); maxX=Math.max(maxX,cx+thexCellSize);
    minY=Math.min(minY,cy-thexCellSize); maxY=Math.max(maxY,cy+thexCellSize);
  }
  const pad=4, W=maxX-minX+pad*2, H=maxY-minY+pad*2;
  const ox=-minX+pad, oy=-minY+pad;

  thexSvgEl = document.createElementNS(THEX_SVG_NS,'svg');
  thexSvgEl.setAttribute('width', W.toFixed(0));
  thexSvgEl.setAttribute('height', H.toFixed(0));
  thexSvgEl.setAttribute('viewBox', `0 0 ${W.toFixed(0)} ${H.toFixed(0)}`);
  thexSvgEl.id = 'thex-svg';

  for (const [q,r] of cells) {
    const [cx,cy] = thexHexCenter(q,r);
    const k = thexKey(q,r);
    const isPreRevealed = Object.prototype.hasOwnProperty.call(thexState.startRevealed, k);

    const g = document.createElementNS(THEX_SVG_NS,'g');
    g.dataset.q = q; g.dataset.r = r;
    g.classList.add('hex-cell', isPreRevealed ? 'thex-prerev' : 'hex-hidden');

    const poly = document.createElementNS(THEX_SVG_NS,'polygon');
    poly.setAttribute('points', thexHexPoints(cx+ox, cy+oy, thexCellSize-1.5));
    poly.classList.add('hex-poly');

    const txt = document.createElementNS(THEX_SVG_NS,'text');
    txt.setAttribute('x', (cx+ox).toFixed(2));
    txt.setAttribute('y', (cy+oy).toFixed(2));
    txt.setAttribute('text-anchor','middle');
    txt.setAttribute('dominant-baseline','central');
    txt.classList.add('hex-label');
    txt.style.fontSize = `${Math.round(thexCellSize*0.72)}px`;

    if (isPreRevealed) {
      const val = thexState.startRevealed[k];
      if (val > 0) {
        txt.textContent = val;
        txt.style.fill = THEX_ADJ_COLORS[val] || '#fff';
      }
    } else {
      g.addEventListener('click', e => { e.preventDefault(); thexHandleClick(q,r); });
      g.addEventListener('contextmenu', e => { e.preventDefault(); thexHandleRightClick(q,r); });
      thexAddTouch(g, () => thexHandleClick(q,r), () => thexHandleRightClick(q,r));
    }

    g.appendChild(poly);
    g.appendChild(txt);
    thexSvgEl.appendChild(g);
  }
  wrap.appendChild(thexSvgEl);
}

function thexAddTouch(el, onTap, onLongPress) {
  let timer = null;
  el.addEventListener('touchstart', () => {
    timer = setTimeout(() => { timer=null; onLongPress(); }, 500);
  }, {passive:true});
  el.addEventListener('touchend', () => {
    if (timer) { clearTimeout(timer); timer=null; onTap(); }
  });
  el.addEventListener('touchmove', () => { clearTimeout(timer); timer=null; });
}

function thexCellGroup(q,r) {
  return thexSvgEl ? thexSvgEl.querySelector(`[data-q="${q}"][data-r="${r}"]`) : null;
}

function thexRenderCell(q,r) {
  const g = thexCellGroup(q,r);
  if (!g) return;
  const k = thexKey(q,r);
  const val = thexState.board.get(k);
  g.className.baseVal = 'hex-cell';
  const txt = g.querySelector('.hex-label');
  txt.textContent = '';
  txt.style.fill = '';

  if (thexState.flagged.has(k)) {
    g.classList.add('hex-flagged');
    txt.textContent = '🚩';
    return;
  }
  if (!thexState.revealed.has(k)) {
    g.classList.add('hex-hidden');
    return;
  }
  g.classList.add('hex-revealed');
  if (val === -1) {
    g.classList.add(thexState.explodedKey===k ? 'hex-detonated' : 'hex-mine');
    txt.textContent = '💣';
  } else if (val === THEX_QUESTION) {
    g.classList.add('thex-question');
    txt.textContent = '?';
    txt.style.fill = 'var(--text-dim)';
  } else if (val > 0) {
    txt.textContent = val;
    txt.style.fill = THEX_ADJ_COLORS[val] || '#fff';
  }
}

function thexRevealCell(q,r) {
  const k = thexKey(q,r);
  if (thexState.over || thexState.revealed.has(k) || thexState.flagged.has(k)) return;
  if (thexState.board.get(k) === -1) { thexBoom(q,r); return; }

  const queue = [[q,r]];
  while (queue.length) {
    const [cq,cr] = queue.shift();
    const ck = thexKey(cq,cr);
    if (thexState.revealed.has(ck)) continue;
    thexState.revealed.add(ck);
    thexRenderCell(cq,cr);
    const ckVal = thexState.board.get(ck);
    if (ckVal === 0) {
      for (const [nq,nr] of thexNeighbours(cq,cr,thexState.R)) {
        const nk = thexKey(nq,nr);
        if (!thexState.revealed.has(nk) && !thexState.flagged.has(nk))
          queue.push([nq,nr]);
      }
    }
  }
  thexCheckWin();
}

function thexFlagCell(q,r) {
  if (thexState.over) return;
  const k = thexKey(q,r);
  if (thexState.revealed.has(k)) return;
  if (thexState.flagged.has(k)) thexState.flagged.delete(k);
  else thexState.flagged.add(k);
  thexRenderCell(q,r);
  thexUpdateCounter();
}

function thexBoom(q,r) {
  thexState.over = true;
  thexState.explodedKey = thexKey(q,r);
  for (const mk of thexState.mines) {
    thexState.revealed.add(mk);
    const [mq,mr] = mk.split(',').map(Number);
    thexRenderCell(mq,mr);
  }
  thexShowBanner('💥 Boom! Try again.', false);
}

function thexCheckWin() {
  const allSafe = thexState.cells.every(([q,r]) => {
    const k = thexKey(q,r);
    return thexState.mines.has(k) || thexState.revealed.has(k);
  });
  if (!allSafe) return;
  thexState.over = true;
  thexState.won = true;
  for (const mk of thexState.mines) {
    if (!thexState.flagged.has(mk)) {
      thexState.flagged.add(mk);
      const [mq,mr] = mk.split(',').map(Number);
      thexRenderCell(mq,mr);
    }
  }
  thexShowBanner('🎉 Puzzle complete!', true);
  thexMarkComplete();
}

async function thexMarkComplete() {
  const pid = thexState.puzzleId;
  try {
    const res = await fetch('/api/tametsi-hex/complete', {
      method: 'POST',
      headers: {'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'},
      body: JSON.stringify({puzzle_id: pid}),
    });
    if (res.ok) {
      const btn = document.querySelector(`.thex-puzzle-btn[data-puzzle="${pid}"]`);
      if (btn && !btn.querySelector('.thex-check'))
        btn.insertAdjacentHTML('beforeend', '<span class="thex-check">✓</span>');
    }
  } catch {}
}

function thexShowBanner(msg, won) {
  let el = document.getElementById('thex-banner');
  if (!el) {
    el = document.createElement('div');
    el.id = 'thex-banner';
    const wrap = document.getElementById('thex-board-wrap');
    wrap.insertAdjacentElement('afterend', el);
  }
  el.className = won ? 'thex-banner thex-banner--win' : 'thex-banner thex-banner--loss';
  el.innerHTML = `<span>${msg}</span><button class="thex-reset-btn" onclick="thexReset()">Reset</button>`;
}

function thexHideBanner() {
  const el = document.getElementById('thex-banner');
  if (el) el.textContent = '';
}

function thexHandleClick(q,r) {
  if (thexState.over) return;
  const k = thexKey(q,r);
  if (!thexState.flagged.has(k)) thexRevealCell(q,r);
}

function thexHandleRightClick(q,r) {
  if (thexState.over) return;
  thexFlagCell(q,r);
}

function thexUpdateCounter() {
  const remaining = thexState.mines.size - thexState.flagged.size;
  const left = document.getElementById('thex-mine-counter');
  if (left) left.textContent = '🚩 ' + thexState.flagged.size + ' / ' + thexState.mines.size;
  const right = document.getElementById('thex-mines-left');
  if (right) right.textContent = '💣 ' + remaining;
}

function thexInitPuzzle(puzzleId) {
  const def = THEX_PUZZLES[puzzleId];
  if (!def) return;

  const cells = thexBuildCells(def.R);
  const board = thexBuildBoard(cells, def.mines, def.R, def.questionCells || null);

  thexState = {
    puzzleId,
    R: def.R,
    mines: def.mines,
    startRevealed: def.startRevealed,
    cells,
    board,
    revealed: new Set(Object.keys(def.startRevealed)),
    flagged: new Set(),
    over: false,
    won: false,
    explodedKey: null,
  };

  thexHideBanner();
  thexBuildSVG();
  thexUpdateCounter();

  document.querySelectorAll('.thex-puzzle-btn').forEach(btn => {
    btn.classList.toggle('active', parseInt(btn.dataset.puzzle) === puzzleId);
  });

  const tutEl = document.getElementById('thex-tutorial-text');
  if (tutEl) tutEl.innerHTML = def.tutorialText;
}

window.thexReset = function() { thexInitPuzzle(thexState.puzzleId); };
window.thexSelectPuzzle = function(puzzleId) { thexInitPuzzle(puzzleId); };

document.addEventListener('DOMContentLoaded', () => {
  const wrap = document.getElementById('thex-board-wrap');
  if (!wrap) return;
  const completions = JSON.parse(wrap.dataset.completions || '[]');
  completions.forEach(id => {
    const btn = document.querySelector(`.thex-puzzle-btn[data-puzzle="${id}"]`);
    if (btn && !btn.querySelector('.thex-check'))
      btn.insertAdjacentHTML('beforeend', '<span class="thex-check">✓</span>');
  });
  thexInitPuzzle(1);
});
