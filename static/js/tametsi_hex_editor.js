"use strict";

/* ─── Tametsi Hex Board Editor — E1 slot ──────────────────────────────────── */

const THEX_ED_CELLS = thexBuildCells(3);
const THEX_ED_SET   = new Set(THEX_ED_CELLS.map(([q, r]) => `${q},${r}`));

let thexEd = {
  tool:   'mine',   // 'mine' | 'reveal'
  mines:  new Set(),
  prerev: new Set(),
};

/* ─── Encoding ────────────────────────────────────────────────────────────── */

function thexEdEncode(mines, prerev) {
  let m = 0, rv = 0;
  THEX_ED_CELLS.forEach(([q, r], i) => {
    const k = `${q},${r}`;
    if (mines.has(k))       m  |= 1 << i;
    else if (prerev.has(k)) rv |= 1 << i;
  });
  return `${m.toString(36)}-${rv.toString(36)}`;
}

function thexEdDecode(hash) {
  if (!hash) return null;
  const dash = hash.indexOf('-');
  if (dash < 0) return null;
  const m  = parseInt(hash.slice(0, dash), 36);
  const rv = parseInt(hash.slice(dash + 1), 36);
  if (isNaN(m) || isNaN(rv)) return null;
  const mines  = new Set();
  const prerev = new Set();
  THEX_ED_CELLS.forEach(([q, r], i) => {
    const k = `${q},${r}`;
    if (m  & (1 << i)) mines.add(k);
    else if (rv & (1 << i)) prerev.add(k);
  });
  return { mines, prerev };
}

/* ─── Solver (constraint propagation only, no guessing) ──────────────────── */

function thexEdSolve(mines, prerev) {
  const board    = thexBuildBoard(THEX_ED_CELLS, mines, THEX_ED_SET, null);
  const revealed = new Set();
  const flagged  = new Set();

  function cascade(k) {
    if (revealed.has(k)) return;
    revealed.add(k);
    if (board.get(k) === 0) {
      const [q, r] = k.split(',').map(Number);
      for (const [nq, nr] of thexNeighbours(q, r, THEX_ED_SET)) {
        const nk = `${nq},${nr}`;
        if (!mines.has(nk)) cascade(nk);
      }
    }
  }

  for (const k of prerev) if (!mines.has(k)) cascade(k);

  let changed = true;
  while (changed) {
    changed = false;
    for (const k of [...revealed]) {
      const v = board.get(k);
      if (!v || v < 0) continue;  // skip 0-cells (handled by cascade) and edge cases
      const [q, r]   = k.split(',').map(Number);
      const nbrs     = thexNeighbours(q, r, THEX_ED_SET);
      const nFlagged = nbrs.filter(([a, b]) => flagged.has(`${a},${b}`)).length;
      const hidden   = nbrs.filter(([a, b]) => {
        const nk = `${a},${b}`;
        return !revealed.has(nk) && !flagged.has(nk);
      });
      const rem = v - nFlagged;
      if (rem > 0 && rem === hidden.length) {
        hidden.forEach(([a, b]) => { flagged.add(`${a},${b}`); changed = true; });
      }
      if (rem === 0 && hidden.length > 0) {
        hidden.forEach(([a, b]) => {
          if (!mines.has(`${a},${b}`)) { cascade(`${a},${b}`); changed = true; }
        });
      }
    }
  }

  return THEX_ED_CELLS.every(([q, r]) => {
    const k = `${q},${r}`;
    return mines.has(k) || revealed.has(k);
  });
}

/* ─── Board render ────────────────────────────────────────────────────────── */

function thexEdBuildSVG() {
  const wrap = document.getElementById('thex-board-wrap');
  if (!wrap) return;
  wrap.innerHTML = '';

  const mines  = thexEd.mines;
  const prerev = thexEd.prerev;
  const board  = thexBuildBoard(THEX_ED_CELLS, mines, THEX_ED_SET, null);

  thexCellSize = thexChooseSize(THEX_ED_CELLS, 0);

  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const [q, r] of THEX_ED_CELLS) {
    const [cx, cy] = thexHexCenter(q, r);
    x0 = Math.min(x0, cx - thexCellSize); x1 = Math.max(x1, cx + thexCellSize);
    y0 = Math.min(y0, cy - thexCellSize); y1 = Math.max(y1, cy + thexCellSize);
  }
  const W = x1 - x0 + 8, H = y1 - y0 + 8;
  const ox = 4 - x0,     oy = 4 - y0;

  const svg = document.createElementNS(THEX_SVG_NS, 'svg');
  svg.setAttribute('width',   W.toFixed(0));
  svg.setAttribute('height',  H.toFixed(0));
  svg.setAttribute('viewBox', `0 0 ${W.toFixed(0)} ${H.toFixed(0)}`);
  svg.id = 'thex-svg';

  for (const [q, r] of THEX_ED_CELLS) {
    const k      = `${q},${r}`;
    const isMine = mines.has(k);
    const isRev  = prerev.has(k) && !isMine;
    const [cx, cy] = thexHexCenter(q, r);

    const g = document.createElementNS(THEX_SVG_NS, 'g');
    g.dataset.q = q; g.dataset.r = r;

    const poly = document.createElementNS(THEX_SVG_NS, 'polygon');
    poly.setAttribute('points', thexHexPoints(cx + ox, cy + oy, thexCellSize - 1.5));
    poly.classList.add('hex-poly');

    const lbl = document.createElementNS(THEX_SVG_NS, 'text');
    lbl.setAttribute('x', (cx + ox).toFixed(2));
    lbl.setAttribute('y', (cy + oy).toFixed(2));
    lbl.setAttribute('text-anchor', 'middle');
    lbl.setAttribute('dominant-baseline', 'central');
    lbl.classList.add('hex-label');
    lbl.style.fontSize = `${Math.round(0.72 * thexCellSize)}px`;

    if (isMine) {
      g.classList.add('hex-cell', 'thex-editor-mine');
      lbl.textContent = '💣';
    } else if (isRev) {
      const cnt = board.get(k) ?? 0;
      g.classList.add('hex-cell', 'thex-prerev');
      if (cnt > 0) {
        lbl.textContent = cnt;
        lbl.style.fill  = THEX_ADJ_COLORS[cnt] || '#fff';
      }
    } else {
      g.classList.add('hex-cell', 'hex-hidden');
    }

    g.addEventListener('click',       e => { e.preventDefault(); thexEdToggle(q, r); });
    g.addEventListener('contextmenu', e => { e.preventDefault(); thexEdClear(q, r); });
    thexAddTouch(g, () => thexEdToggle(q, r), () => thexEdClear(q, r));

    g.appendChild(poly);
    g.appendChild(lbl);
    svg.appendChild(g);
  }

  wrap.appendChild(svg);
}

/* ─── Cell interaction ────────────────────────────────────────────────────── */

function thexEdToggle(q, r) {
  const k = `${q},${r}`;
  if (thexEd.tool === 'mine') {
    if (thexEd.mines.has(k)) thexEd.mines.delete(k);
    else { thexEd.mines.add(k); thexEd.prerev.delete(k); }
  } else {
    if (thexEd.prerev.has(k)) thexEd.prerev.delete(k);
    else if (!thexEd.mines.has(k)) thexEd.prerev.add(k);
  }
  thexEdBuildSVG();
  thexEdUpdateCounter();
}

function thexEdClear(q, r) {
  const k = `${q},${r}`;
  thexEd.mines.delete(k);
  thexEd.prerev.delete(k);
  thexEdBuildSVG();
  thexEdUpdateCounter();
}

/* ─── Counter ──────────────────────────────────────────────────────────────── */

function thexEdUpdateCounter() {
  const mc = document.getElementById('thex-mine-counter');
  if (mc) mc.textContent = `💣 ${thexEd.mines.size} mines`;
  const ml = document.getElementById('thex-mines-left');
  if (ml) ml.textContent = `👁 ${thexEd.prerev.size} revealed`;
  const cc = document.getElementById('thex-color-counts');
  if (cc) { cc.style.display = 'none'; cc.innerHTML = ''; }
}

/* ─── Save & Check ────────────────────────────────────────────────────────── */

window.thexEditorSave = function () {
  const { mines, prerev } = thexEd;
  const rd = document.getElementById('thex-editor-result');
  if (!rd) return;

  if (mines.size === 0) {
    rd.className = 'thex-editor-result thex-editor-result--fail';
    rd.innerHTML = 'Place at least one mine before saving.';
    return;
  }
  if (prerev.size === 0) {
    rd.className = 'thex-editor-result thex-editor-result--fail';
    rd.innerHTML = 'Mark at least one revealed cell — the player needs a starting clue.';
    return;
  }

  const ok = thexEdSolve(mines, prerev);
  if (!ok) {
    rd.className = 'thex-editor-result thex-editor-result--fail';
    rd.innerHTML = '⚠️ This puzzle requires guessing. Add more revealed cells or rearrange mines until the solver can deduce every cell.';
    return;
  }

  const hash = thexEdEncode(mines, prerev);
  const url  = `${location.origin}${location.pathname}?board=${hash}`;
  history.replaceState(null, '', `?board=${hash}`);

  const isAuthed = !!document.querySelector('[data-thex-authed]');
  const signNote = isAuthed
    ? '<span style="color:var(--accent2)">✓ Board saved to your profile.</span>'
    : `<a href="/auth/login?next=${encodeURIComponent('/tametsi/hex?board=' + hash)}">Sign in</a> to keep this board in your profile.`;

  rd.className = 'thex-editor-result thex-editor-result--ok';
  rd.innerHTML =
    `✅ Solvable — no guessing needed!<br>` +
    `<span class="thex-editor-share-url">${url}</span> ` +
    `<button class="thex-reset-btn" style="margin-left:0.4rem" ` +
      `onclick="navigator.clipboard&&navigator.clipboard.writeText(${JSON.stringify(url)})">Copy link</button><br>` +
    `<small style="color:var(--text-dim);margin-top:0.3rem;display:block">${signNote}</small>`;

  // Save board server-side for logged-in users (silent if not authenticated)
  fetch('/api/tametsi-hex/editor/save', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
    body:    JSON.stringify({ board_hash: hash }),
  }).catch(() => {});

  thexEdShowPlay(mines, prerev);
};

/* ─── Show playable board ─────────────────────────────────────────────────── */

function thexEdShowPlay(mines, prerev) {
  const board = thexBuildBoard(THEX_ED_CELLS, mines, THEX_ED_SET, null);
  const startRevealed = {};
  for (const k of prerev) {
    if (!mines.has(k)) startRevealed[k] = board.get(k) ?? 0;
  }
  THEX_PUZZLES['e1'] = {
    R:    3,
    mines: new Set([...mines]),
    startRevealed,
    tutorialText: '<strong>Your Puzzle — Play Test:</strong> Left-click to reveal, right-click to flag mines. Can you solve it with pure logic?',
  };
  thexInitPuzzle('e1');
  // Keep editor panel visible above the board
  const panel = document.getElementById('thex-editor-panel');
  if (panel) panel.style.display = '';
  // Manually mark E1 active (thexInitPuzzle uses parseInt which doesn't match 'e1')
  document.querySelectorAll('.thex-puzzle-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.puzzle === 'e1'));
}

/* ─── Show editor ─────────────────────────────────────────────────────────── */

window.thexShowEditor = function (preload) {
  thexEd.tool   = 'mine';
  thexEd.mines  = preload ? new Set([...preload.mines])  : new Set();
  thexEd.prerev = preload ? new Set([...preload.prerev]) : new Set();

  document.querySelectorAll('.thex-puzzle-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.puzzle === 'e1'));

  const tutDiv = document.getElementById('thex-tutorial-text');
  if (tutDiv) tutDiv.innerHTML =
    '<strong>E1 — Create a Puzzle:</strong> ' +
    'Click in <strong>💣 Mine</strong> mode to place mines (click again to remove). ' +
    'Switch to <strong>👁 Reveal</strong> to mark which cells appear at the start. ' +
    'Hit <strong>Save &amp; Check</strong> — the solver verifies the board is solvable without guessing and generates a shareable link. ' +
    '<em>Sign in to keep your boards in your profile.</em>';

  const panel = document.getElementById('thex-editor-panel');
  if (panel) panel.style.display = '';

  document.getElementById('thex-editor-result').innerHTML = '';
  document.querySelectorAll('.thex-editor-tool-btn[data-tool]').forEach(b =>
    b.classList.toggle('active', b.dataset.tool === 'mine'));

  const timer = document.getElementById('thex-timer');
  if (timer) { timer.textContent = ''; timer.style.display = 'none'; }

  thexHideBanner();
  thexEdBuildSVG();
  thexEdUpdateCounter();
};

/* ─── Tool controls ───────────────────────────────────────────────────────── */

window.thexEditorSetTool = function (tool) {
  thexEd.tool = tool;
  document.querySelectorAll('.thex-editor-tool-btn[data-tool]').forEach(b =>
    b.classList.toggle('active', b.dataset.tool === tool));
};

window.thexEditorClear = function () {
  thexEd.mines.clear();
  thexEd.prerev.clear();
  delete THEX_PUZZLES['e1'];
  document.getElementById('thex-editor-result').innerHTML = '';
  history.replaceState(null, '', location.pathname);
  thexEdBuildSVG();
  thexEdUpdateCounter();
};

/* ─── Override thexSelectPuzzle to intercept E1 ──────────────────────────── */

(function () {
  const _orig = window.thexSelectPuzzle;
  window.thexSelectPuzzle = function (id) {
    const panel = document.getElementById('thex-editor-panel');
    if (id === 'e1') {
      if (panel) panel.style.display = '';
      thexShowEditor();
    } else {
      if (panel) panel.style.display = 'none';
      _orig(id);
    }
  };
})();

/* ─── URL boot — load shared board on page load ───────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {
  const hash = new URLSearchParams(location.search).get('board');
  if (!hash) return;
  const decoded = thexEdDecode(hash);
  if (!decoded) return;

  // Pre-fill editor with the shared board
  thexShowEditor(decoded);
  // Auto-render the playable board below the editor
  thexEdShowPlay(decoded.mines, decoded.prerev);

  const url = `${location.origin}${location.pathname}?board=${hash}`;
  const rd  = document.getElementById('thex-editor-result');
  if (rd) {
    rd.className = 'thex-editor-result thex-editor-result--ok';
    rd.innerHTML =
      `✅ Shared puzzle loaded!<br>` +
      `<span class="thex-editor-share-url">${url}</span> ` +
      `<button class="thex-reset-btn" style="margin-left:0.4rem" ` +
        `onclick="navigator.clipboard&&navigator.clipboard.writeText(${JSON.stringify(url)})">Copy link</button>`;
  }
});
