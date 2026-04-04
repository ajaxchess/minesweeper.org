/**
 * 2048hex.js — 2048 on a hexagonal grid
 *
 * Hex grid: size 2 (3 cells per edge, 19 cells total).
 * Center cell (0,0) is a fixed stone — blocks movement, cannot merge.
 * 18 playable cells.
 *
 * Six move directions: E, W, NE, SW, NW, SE
 * Keyboard: Q=NW, E=NE, A=W, D=E(right), Z=SW, X=SE  ← also ArrowLeft/Right
 * Mobile:   6-direction swipe (60° sectors)
 * Buttons:  clickable hex directional pad
 *
 * Daily seed: window.H2K_DATE (YYYY-MM-DD) — same tile sequence for every
 * player on the same day.
 */
(function () {
  'use strict';

  // ── Constants ───────────────────────────────────────────────────────────────
  const GRID_SIZE = 2;
  const SQRT3     = Math.sqrt(3);
  const HEX_SIZE  = 44;   // axial scale factor; adjacent center distance = HEX_SIZE * sqrt(3)
  const CIRCLE_R  = 34;   // SVG circle radius (px)

  // Tile colour palette (2048 classic)
  function tileStyle(v) {
    var MAP = {
      0:    { bg: '#cdc1b4', fg: 'transparent' },
      2:    { bg: '#eee4da', fg: '#776e65' },
      4:    { bg: '#ede0c8', fg: '#776e65' },
      8:    { bg: '#f2b179', fg: '#f9f6f2' },
      16:   { bg: '#f59563', fg: '#f9f6f2' },
      32:   { bg: '#f67c5f', fg: '#f9f6f2' },
      64:   { bg: '#f65e3b', fg: '#f9f6f2' },
      128:  { bg: '#edcf72', fg: '#f9f6f2' },
      256:  { bg: '#edcc61', fg: '#f9f6f2' },
      512:  { bg: '#edc850', fg: '#f9f6f2' },
      1024: { bg: '#edc53f', fg: '#f9f6f2' },
      2048: { bg: '#edc22e', fg: '#f9f6f2' },
    };
    return MAP[v] || { bg: '#3c3a32', fg: '#f9f6f2' };
  }
  function tileFontSize(v) {
    if (!v || v < 100)   return CIRCLE_R * 0.70;
    if (v < 1000)        return CIRCLE_R * 0.55;
    if (v < 10000)       return CIRCLE_R * 0.44;
    return CIRCLE_R * 0.36;
  }

  // ── Grid helpers ────────────────────────────────────────────────────────────
  function inBounds(q, r) {
    return Math.abs(q) <= GRID_SIZE
        && Math.abs(r) <= GRID_SIZE
        && Math.abs(q + r) <= GRID_SIZE;
  }
  function isStone(q, r) { return q === 0 && r === 0; }
  function key(q, r)     { return q + ',' + r; }

  // Build cell lists once at load time
  var ALL_CELLS = [], PLAYABLE = [];
  for (var _q = -GRID_SIZE; _q <= GRID_SIZE; _q++) {
    for (var _r = -GRID_SIZE; _r <= GRID_SIZE; _r++) {
      if (inBounds(_q, _r)) {
        ALL_CELLS.push({ q: _q, r: _r });
        if (!isStone(_q, _r)) PLAYABLE.push({ q: _q, r: _r });
      }
    }
  }

  // Pixel position of a cell center (pointy-top hex, axial coords)
  function hexPx(q, r) {
    return {
      x: HEX_SIZE * SQRT3 * (q + r / 2),
      y: HEX_SIZE * 1.5   * r,
    };
  }

  // ── Directions ──────────────────────────────────────────────────────────────
  // lineKey : invariant for grouping ALL_CELLS into slide-lines
  // sortKey : sort ascending → tiles pile toward the HIGH end (last index = wall)
  var DIRS = {
    E:  { dq: +1, dr:  0, lineKey: function (q, r) { return  r;     }, sortKey: function (q, r) { return  q;  } },
    W:  { dq: -1, dr:  0, lineKey: function (q, r) { return  r;     }, sortKey: function (q, r) { return -q;  } },
    NE: { dq: +1, dr: -1, lineKey: function (q, r) { return  q + r; }, sortKey: function (q, r) { return  q;  } },
    SW: { dq: -1, dr: +1, lineKey: function (q, r) { return  q + r; }, sortKey: function (q, r) { return -q;  } },
    SE: { dq:  0, dr: +1, lineKey: function (q, r) { return  q;     }, sortKey: function (q, r) { return  r;  } },
    NW: { dq:  0, dr: -1, lineKey: function (q, r) { return  q;     }, sortKey: function (q, r) { return -r;  } },
  };

  // ── PRNG (LCG, same params as 2048.js) ─────────────────────────────────────
  function makeLCG(seed) {
    var s = seed >>> 0;
    return {
      next: function () {
        s = (Math.imul(1664525, s) + 1013904223) >>> 0;
        return s / 4294967296;
      },
    };
  }
  function seedFromDate(str) {
    var seed = 0;
    for (var i = 0; i < str.length; i++)
      seed = (Math.imul(31, seed) + str.charCodeAt(i)) >>> 0;
    return seed;
  }

  // ── Game state ──────────────────────────────────────────────────────────────
  var tiles     = {};   // key(q,r) -> tile value; absent / 0 = empty
  var score     = 0;
  var moveCount = 0;
  var won       = false;
  var over      = false;
  var continued = false;
  var rng       = null;

  function getEmpties() {
    return PLAYABLE.filter(function (c) { return !tiles[key(c.q, c.r)]; });
  }

  function spawnTile() {
    var pool = getEmpties();
    if (!pool.length) return;
    var c = pool[Math.floor(rng.next() * pool.length)];
    tiles[key(c.q, c.r)] = rng.next() < 0.9 ? 2 : 4;
  }

  // ── Slide logic ─────────────────────────────────────────────────────────────
  // Merge non-zero values, tiles pile toward end of array.
  function slideValues(nonZero) {
    var r = nonZero.slice();
    var gained = 0;
    for (var i = r.length - 1; i > 0; i--) {
      if (r[i] === r[i - 1]) {
        r[i] *= 2;
        gained += r[i];
        r.splice(i - 1, 1);
      }
    }
    return { merged: r, gained: gained };
  }

  // Compute the result of a move without applying it.
  // Returns { newTiles, totalGained, anyChanged }.
  function computeMove(dirName) {
    var dir = DIRS[dirName];

    // Group ALL_CELLS (including stone) into lines by the direction's invariant
    var lineMap = {};
    for (var ci = 0; ci < ALL_CELLS.length; ci++) {
      var c  = ALL_CELLS[ci];
      var lk = dir.lineKey(c.q, c.r);
      if (!lineMap[lk]) lineMap[lk] = [];
      lineMap[lk].push({ q: c.q, r: c.r });
    }

    var totalGained = 0;
    var anyChanged  = false;
    var newTiles    = Object.assign({}, tiles);

    var lineKeys = Object.keys(lineMap);
    for (var li = 0; li < lineKeys.length; li++) {
      var line = lineMap[lineKeys[li]];

      // Sort: low sortKey first; tiles pile toward HIGH end
      line.sort(function (a, b) {
        return dir.sortKey(a.q, a.r) - dir.sortKey(b.q, b.r);
      });

      // Split at the stone
      var si = -1;
      for (var i = 0; i < line.length; i++) {
        if (isStone(line[i].q, line[i].r)) { si = i; break; }
      }
      var segs = si === -1 ? [line] : [line.slice(0, si), line.slice(si + 1)];

      for (var si2 = 0; si2 < segs.length; si2++) {
        var seg = segs[si2];
        if (!seg.length) continue;

        var oldVals = seg.map(function (c) { return tiles[key(c.q, c.r)] || 0; });
        var nonZero = oldVals.filter(function (v) { return v > 0; });
        if (!nonZero.length) continue;

        var res    = slideValues(nonZero);
        totalGained += res.gained;

        // Pad with leading zeros to restore segment length
        var newVals = [];
        for (var z = 0; z < seg.length - res.merged.length; z++) newVals.push(0);
        newVals = newVals.concat(res.merged);

        for (var j = 0; j < seg.length; j++) {
          if (oldVals[j] !== newVals[j]) anyChanged = true;
          var k = key(seg[j].q, seg[j].r);
          if (newVals[j]) { newTiles[k] = newVals[j]; }
          else            { delete newTiles[k]; }
        }
      }
    }

    return { newTiles: newTiles, totalGained: totalGained, anyChanged: anyChanged };
  }

  function applyMove(dirName) {
    if (over || (won && !continued)) return;

    var result = computeMove(dirName);
    if (!result.anyChanged) return;

    tiles      = result.newTiles;
    score     += result.totalGained;
    moveCount++;

    // Check win
    if (!won && !continued) {
      var vals = Object.values(tiles);
      for (var i = 0; i < vals.length; i++) {
        if (vals[i] >= 2048) { won = true; break; }
      }
    }

    spawnTile();

    // Game over: board full and no direction produces a change
    if (!getEmpties().length) {
      var stuck = Object.keys(DIRS).every(function (d) {
        return !computeMove(d).anyChanged;
      });
      if (stuck) over = true;
    }

    render();
    if      (won && !continued) showWin();
    else if (over)              showOver();
  }

  // ── SVG board ───────────────────────────────────────────────────────────────
  var svgEls = {};   // key(q,r) -> { circle, text }

  function buildBoard() {
    var container = document.getElementById('hex2k-board');
    if (!container) return;

    var NS = 'http://www.w3.org/2000/svg';

    // Compute bounds
    var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (var i = 0; i < ALL_CELLS.length; i++) {
      var c = ALL_CELLS[i], p = hexPx(c.q, c.r);
      if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x;
      if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y;
    }
    var pad = CIRCLE_R + 8;
    var W   = maxX - minX + 2 * pad;
    var H   = maxY - minY + 2 * pad;
    var ox  = -minX + pad;
    var oy  = -minY + pad;

    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    svg.setAttribute('width',   W);
    svg.setAttribute('height',  H);
    svg.style.maxWidth = '100%';
    svg.style.display  = 'block';
    svg.style.margin   = '0 auto';

    // Board background
    var bgRect = document.createElementNS(NS, 'rect');
    bgRect.setAttribute('x', 0); bgRect.setAttribute('y', 0);
    bgRect.setAttribute('width', W); bgRect.setAttribute('height', H);
    bgRect.setAttribute('rx', 12); bgRect.setAttribute('fill', '#bbada0');
    svg.appendChild(bgRect);

    for (var ci = 0; ci < ALL_CELLS.length; ci++) {
      var c  = ALL_CELLS[ci];
      var p  = hexPx(c.q, c.r);
      var px = p.x + ox, py = p.y + oy;

      var circle = document.createElementNS(NS, 'circle');
      circle.setAttribute('cx', px);
      circle.setAttribute('cy', py);
      circle.setAttribute('r',  CIRCLE_R);

      if (isStone(c.q, c.r)) {
        circle.setAttribute('fill', '#7a6a5e');
        svg.appendChild(circle);
      } else {
        circle.setAttribute('fill', '#cdc1b4');
        var text = document.createElementNS(NS, 'text');
        text.setAttribute('x',                  px);
        text.setAttribute('y',                  py);
        text.setAttribute('text-anchor',         'middle');
        text.setAttribute('dominant-baseline',   'central');
        text.setAttribute('font-weight',         '800');
        text.setAttribute('font-family',         'Arial, Helvetica, sans-serif');
        text.setAttribute('font-size',           tileFontSize(0));
        text.setAttribute('fill',                'transparent');
        svg.appendChild(circle);
        svg.appendChild(text);
        svgEls[key(c.q, c.r)] = { circle: circle, text: text };
      }
    }

    container.appendChild(svg);
  }

  function render() {
    for (var i = 0; i < PLAYABLE.length; i++) {
      var c  = PLAYABLE[i];
      var k  = key(c.q, c.r);
      var el = svgEls[k];
      if (!el) continue;
      var v = tiles[k] || 0;
      var s = tileStyle(v);
      el.circle.setAttribute('fill', s.bg);
      el.text.textContent = v || '';
      el.text.setAttribute('fill',      v ? s.fg : 'transparent');
      el.text.setAttribute('font-size', tileFontSize(v));
    }
    var scoreEl = document.getElementById('hex2k-score');
    if (scoreEl) scoreEl.textContent = score;
    var movesEl = document.getElementById('hex2k-moves');
    if (movesEl) movesEl.textContent = moveCount;
  }

  // ── Win / game-over UI ──────────────────────────────────────────────────────
  function showWin() {
    var el = document.getElementById('hex2k-win-msg');
    if (el) el.style.display = 'block';
  }
  function showOver() {
    var el = document.getElementById('hex2k-over-msg');
    if (el) el.style.display = 'block';
  }
  function continueGame() {
    continued = true;
    var el = document.getElementById('hex2k-win-msg');
    if (el) el.style.display = 'none';
  }

  // ── Keyboard ────────────────────────────────────────────────────────────────
  var KEY_MAP = {
    'q': 'NW', 'Q': 'NW',
    'e': 'NE', 'E': 'NE',
    'a': 'W',  'A': 'W',
    'd': 'E',  'D': 'E',
    'z': 'SW', 'Z': 'SW',
    'x': 'SE', 'X': 'SE',
    'ArrowLeft':  'W',
    'ArrowRight': 'E',
  };
  document.addEventListener('keydown', function (ev) {
    var dir = KEY_MAP[ev.key];
    if (dir) { ev.preventDefault(); applyMove(dir); }
  });

  // ── 6-direction swipe ───────────────────────────────────────────────────────
  // Map swipe angle to 60° sector: 0°=E, 60°=SE, 120°=SW, 180°=W, 240°=NW, 300°=NE
  // (screen coords: y+ = down)
  var DIR_ORDER = ['E', 'SE', 'SW', 'W', 'NW', 'NE'];
  var _tx = 0, _ty = 0;
  document.addEventListener('touchstart', function (ev) {
    _tx = ev.touches[0].clientX;
    _ty = ev.touches[0].clientY;
  }, { passive: true });
  document.addEventListener('touchend', function (ev) {
    var dx = ev.changedTouches[0].clientX - _tx;
    var dy = ev.changedTouches[0].clientY - _ty;
    if (Math.abs(dx) < 20 && Math.abs(dy) < 20) return;
    var angle   = Math.atan2(dy, dx) * 180 / Math.PI;
    var a       = ((angle % 360) + 360) % 360;
    var sector  = Math.floor(((a + 30) % 360) / 60);
    applyMove(DIR_ORDER[sector]);
  }, { passive: true });

  // ── Reset / init ────────────────────────────────────────────────────────────
  function resetGame() {
    var dateStr = window.H2K_DATE || new Date().toISOString().slice(0, 10);
    rng       = makeLCG(seedFromDate(dateStr));
    tiles     = {};
    score     = 0;
    moveCount = 0;
    won       = false;
    over      = false;
    continued = false;
    ['hex2k-win-msg', 'hex2k-over-msg'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.style.display = 'none';
    });
    spawnTile();
    spawnTile();
    render();
  }

  function init() {
    buildBoard();

    var resetBtn    = document.getElementById('hex2k-reset');
    var continueBtn = document.getElementById('hex2k-continue');
    if (resetBtn)    resetBtn.addEventListener('click', resetGame);
    if (continueBtn) continueBtn.addEventListener('click', continueGame);

    document.querySelectorAll('[data-dir]').forEach(function (btn) {
      btn.addEventListener('click', function () { applyMove(this.dataset.dir); });
    });

    resetGame();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
