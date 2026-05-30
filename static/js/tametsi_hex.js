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
    mines: new Set(['3,-1','3,-2','3,-3','-3,1','-3,2','-3,3']),
    startRevealed: {'0,0':0,'3,0':1,'-3,0':1},
    tutorialText: '<strong>Tutorial 3 — Cascade (R=4, 6 mines):</strong> A <strong>0</strong> cell has no adjacent mines. When you reveal one, every neighbour is uncovered automatically — and if any neighbour is also 0, the cascade keeps spreading. Click any cell next to the centre <strong>0</strong> to trigger a cascade that opens most of the board. Then use the boundary numbers to flag all 6 mines.',
  },
  4: {
    R: 3,
    mines: new Set(['0,-1','2,-1','2,0']),
    startRevealed: {'0,-2':1,'1,-2':1,'-1,-1':1},
    questionCells: new Set(['-1,0','0,0','1,0']),
    tutorialText: '<strong>Tutorial 4 — Question Marks (R=3, 3 mines):</strong> Some cells show <strong>?</strong> when revealed. A <strong>?</strong> cell is safe — it is not a mine — but it reveals nothing about how many mines are nearby. Treat a revealed <strong>?</strong> as a safe cell you can eliminate from your deductions, then use the numbered clues to locate all 3 mines.',
  },
  5: {
    customCells: [
      // Row 1 — main cells (r=0, q=0..6)
      [0,0],[1,0],[2,0],[3,0],[4,0],[5,0],[6,0],
      // Row 1 — indicator cells (r=1, q=0..5) — pre-revealed, each shows 1
      [0,1],[1,1],[2,1],[3,1],[4,1],[5,1],
      // Row 2 — main cells (r=3, q=-2..4)
      [-2,3],[-1,3],[0,3],[1,3],[2,3],[3,3],[4,3],
      // Row 2 — indicator cells (r=4, q=-2..3) — pre-revealed, each shows 1
      [-2,4],[-1,4],[0,4],[1,4],[2,4],[3,4],
      // Row 3 — main cells (r=6, q=-4..2)
      [-4,6],[-3,6],[-2,6],[-1,6],[0,6],[1,6],[2,6],
      // Row 3 — indicator cells (r=7, q=-4..1) — pre-revealed, each shows 1
      [-4,7],[-3,7],[-2,7],[-1,7],[0,7],[1,7],
    ],
    mines: new Set([
      '1,0','3,0','5,0',          // row 1: positions 2,4,6 → count 3
      '-2,3','0,3','2,3','4,3',   // row 2: positions 1,3,5,7 → count 4
      '-3,6','-1,6','1,6',        // row 3: positions 2,4,6 → count 3 (deduced from total)
    ]),
    startRevealed: {
      '0,1':1,'1,1':1,'2,1':1,'3,1':1,'4,1':1,'5,1':1,
      '-2,4':1,'-1,4':1,'0,4':1,'1,4':1,'2,4':1,'3,4':1,
      '-4,7':1,'-3,7':1,'-2,7':1,'-1,7':1,'0,7':1,'1,7':1,
    },
    rowHints: [
      {r: 0, count: 3},
      {r: 3, count: 4},
    ],
    tutorialText: '<strong>Tutorial 5 — Row Hints (10 mines):</strong> The <strong style="color:#ffd700">yellow numbers</strong> to the left of each row show the total mine count for that row. Combined with the indicator cells below (each showing how many mines are in the two cells above it), you can deduce the exact mine positions in rows 1 and 2. For row 3, use the <strong>💣 mines left</strong> counter — with 10 mines total and rows 1 and 2 solved, you can work out how many remain in row 3.',
  },
  6: {
    R: 3,
    mines: new Set(['1,-2','1,-1','0,0','1,0','2,0','-1,1','0,1','1,1','0,2']),
    cellColors: {
      '0,-2':'red', '0,-1':'red', '0,0':'red', '1,0':'red', '2,0':'red',
      '1,-2':'blue', '2,-2':'blue', '1,-1':'blue', '2,-1':'blue',
    },
    startRevealed: {'-2,1':1, '-2,2':1, '-1,2':3},
    tutorialText: '<strong>Tutorial 6 — Coloured Cells (R=3, 9 mines):</strong> '
      + 'Red and blue cells form colour groups — each group has its own mine count shown in the counter bar as '
      + '<span style="color:#e74c3c"><strong>🔴 3:3</strong></span> and <span style="color:#5b9cf6"><strong>🔵 2:2</strong></span>. '
      + 'The format is <em>total&thinsp;:&thinsp;still to flag</em> — flag a red cell and it becomes <span style="color:#e74c3c"><strong>🔴 3:2</strong></span>. '
      + 'Numbers on any cell still count <strong>all</strong> adjacent mines regardless of colour. '
      + 'The overall total (9) includes mines hidden under coloured tiles.',
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

function thexNeighbours(q, r, cellSet) {
  return THEX_DIRS
    .map(([dq,dr]) => [q+dq, r+dr])
    .filter(([nq,nr]) => cellSet.has(thexKey(nq,nr)));
}

function thexBuildBoard(cells, mines, cellSet, questionCells) {
  const board = new Map();
  for (const [q,r] of cells) {
    const k = thexKey(q,r);
    if (mines.has(k)) { board.set(k,-1); continue; }
    if (questionCells && questionCells.has(k)) { board.set(k, THEX_QUESTION); continue; }
    let count = 0;
    for (const [nq,nr] of thexNeighbours(q,r,cellSet))
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

function thexChooseSize(cells, extraLeftPx) {
  const maxW = Math.min(window.innerWidth - 40, 540) - (extraLeftPx || 0);
  let minX = Infinity, maxX = -Infinity;
  for (const [q,r] of cells) {
    const x = THEX_SQRT3 * (q + r/2);
    minX = Math.min(minX, x - 1); maxX = Math.max(maxX, x + 1);
  }
  const span = maxX - minX;
  return Math.max(16, Math.min(32, Math.floor(maxW / span)));
}

function thexBuildSVG() {
  const {cells, rowHints} = thexState;
  const wrap = document.getElementById('thex-board-wrap');
  if (!wrap) return;
  wrap.innerHTML = '';

  const hasHints = rowHints && rowHints.length > 0;
  // Estimate hint label width as 2 cell-widths; compute size with that reserved
  const hintReservePx = hasHints ? 50 : 0;
  thexCellSize = thexChooseSize(cells, hintReservePx);

  let minX=Infinity, maxX=-Infinity, minY=Infinity, maxY=-Infinity;
  for (const [q,r] of cells) {
    const [cx,cy] = thexHexCenter(q,r);
    minX=Math.min(minX,cx-thexCellSize); maxX=Math.max(maxX,cx+thexCellSize);
    minY=Math.min(minY,cy-thexCellSize); maxY=Math.max(maxY,cy+thexCellSize);
  }
  const pad = 4;
  // Add left room for row hint labels
  const leftExtra = hasHints ? Math.round(thexCellSize * 2.2) : 0;
  const W = maxX - minX + pad * 2 + leftExtra;
  const H = maxY - minY + pad * 2;
  const ox = -minX + pad + leftExtra;
  const oy = -minY + pad;

  thexSvgEl = document.createElementNS(THEX_SVG_NS,'svg');
  thexSvgEl.setAttribute('width', W.toFixed(0));
  thexSvgEl.setAttribute('height', H.toFixed(0));
  thexSvgEl.setAttribute('viewBox', `0 0 ${W.toFixed(0)} ${H.toFixed(0)}`);
  thexSvgEl.id = 'thex-svg';

  for (const [q,r] of cells) {
    const [cx,cy] = thexHexCenter(q,r);
    const k = thexKey(q,r);
    const isPreRevealed = Object.prototype.hasOwnProperty.call(thexState.startRevealed, k);

    const color = thexState.cellColors ? thexState.cellColors[k] : null;

    const g = document.createElementNS(THEX_SVG_NS,'g');
    g.dataset.q = q; g.dataset.r = r;
    g.classList.add('hex-cell', isPreRevealed ? 'thex-prerev' : 'hex-hidden');
    if (!isPreRevealed && color) g.classList.add(`thex-color-${color}`);

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

  // Row hint labels — yellow number to the left of each hinted row
  if (hasHints) {
    for (const hint of rowHints) {
      const rowCells = cells.filter(([,cr]) => cr === hint.r);
      if (!rowCells.length) continue;
      // Leftmost cell in this row
      const [lq, lr] = rowCells.reduce((a, b) => (a[0]+a[1]/2 < b[0]+b[1]/2 ? a : b));
      const [lcx, lcy] = thexHexCenter(lq, lr);
      const lbl = document.createElementNS(THEX_SVG_NS,'text');
      lbl.setAttribute('x', (lcx + ox - thexCellSize * 1.6).toFixed(2));
      lbl.setAttribute('y', (lcy + oy).toFixed(2));
      lbl.setAttribute('text-anchor', 'middle');
      lbl.setAttribute('dominant-baseline', 'central');
      lbl.style.fill = '#ffd700';
      lbl.style.fontSize = `${Math.round(thexCellSize * 0.85)}px`;
      lbl.style.fontWeight = 'bold';
      lbl.textContent = hint.count;
      thexSvgEl.appendChild(lbl);
    }
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
  const color = thexState.cellColors ? thexState.cellColors[k] : null;
  g.className.baseVal = 'hex-cell';
  const txt = g.querySelector('.hex-label');
  txt.textContent = '';
  txt.style.fill = '';

  if (thexState.flagged.has(k)) {
    g.classList.add('hex-flagged');
    if (color) g.classList.add(`thex-color-${color}`); // keep hue on flagged cells
    txt.textContent = '🚩';
    return;
  }
  if (!thexState.revealed.has(k)) {
    g.classList.add('hex-hidden');
    if (color) g.classList.add(`thex-color-${color}`);
    return;
  }
  g.classList.add('hex-revealed');
  // Revealed safe cells lose colour (show as standard dark); mines keep it for clarity
  if (val === -1) {
    g.classList.add(thexState.explodedKey===k ? 'hex-detonated' : 'hex-mine');
    if (color) g.classList.add(`thex-color-${color}`);
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
      for (const [nq,nr] of thexNeighbours(cq,cr,thexState.cellSet)) {
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

  const colorEl = document.getElementById('thex-color-counts');
  if (!colorEl) return;
  if (thexState.colorMines) {
    const EMOJI  = {red:'🔴', blue:'🔵'};
    const CLS    = {red:'thex-ccount-red', blue:'thex-ccount-blue'};
    colorEl.style.display = 'flex';
    colorEl.innerHTML = Object.entries(thexState.colorMines).map(([color, total]) => {
      const flaggedOnColor = [...thexState.flagged]
        .filter(k => thexState.cellColors && thexState.cellColors[k] === color).length;
      return `<span class="${CLS[color]}">${EMOJI[color]}&thinsp;${total}:${total - flaggedOnColor}</span>`;
    }).join('');
  } else {
    colorEl.style.display = 'none';
    colorEl.innerHTML = '';
  }
}

function thexInitPuzzle(puzzleId) {
  const def = THEX_PUZZLES[puzzleId];
  if (!def) return;

  const cells = def.customCells ? def.customCells.slice() : thexBuildCells(def.R);
  const cellSet = new Set(cells.map(([q,r]) => thexKey(q,r)));
  const board = thexBuildBoard(cells, def.mines, cellSet, def.questionCells || null);

  // Tally mines per colour group
  let colorMines = null;
  if (def.cellColors) {
    const cm = {};
    for (const [k, col] of Object.entries(def.cellColors))
      if (def.mines.has(k)) cm[col] = (cm[col] || 0) + 1;
    if (Object.keys(cm).length) colorMines = cm;
  }

  thexState = {
    puzzleId,
    mines: def.mines,
    startRevealed: def.startRevealed,
    cells,
    cellSet,
    board,
    rowHints: def.rowHints || [],
    cellColors: def.cellColors || null,
    colorMines,
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
