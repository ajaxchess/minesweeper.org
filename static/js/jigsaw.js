/* jigsaw.js — Jigsaw Puzzle engine for minesweeper.org
 * Canvas-based drag-and-drop interlocking jigsaw puzzle.
 * Config injected via window.JIG_* globals from the template.
 */
(function () {
  'use strict';

  // ── Config ──────────────────────────────────────────────────────────────────
  var DATE       = window.JIG_DATE       || '';
  var IMAGE_NAME = window.JIG_IMAGE_NAME || '';
  var IMAGE_URL  = window.JIG_IMAGE_URL  || '';
  var BOARD_HASH = window.JIG_BOARD_HASH || '';
  var USER_NAME  = window.JIG_USER_NAME  || '';
  var LOGGED_IN  = !!window.JIG_LOGGED_IN;

  // Difficulty grids
  var DIFFS = {
    beginner:     { rows: 10, cols: 10 },
    intermediate: { rows: 20, cols: 25 },
    expert:       { rows: 25, cols: 40 },
  };

  var SNAP_DIST   = 20;   // px — fixed threshold
  var TAB_RATIO   = 0.28; // tab protrusion as fraction of shorter cell dimension

  // ── State ───────────────────────────────────────────────────────────────────
  var img        = null;  // HTMLImageElement
  var difficulty = '';
  var rows = 0, cols = 0;
  var cellW = 0, cellH = 0;
  var tabSz = 0;          // tab protrusion in px
  var pieces = [];        // array of piece objects
  var groups = {};        // groupId -> [pieceIds]
  var nextGroup = 0;

  // Drag state
  var drag = null; // { pids, leadId, offX, offY, areaRect, relPos }

  // Rubber-band selection state
  var selection = []; // pids currently highlighted by rubber-band
  var selDrag   = null; // { startX, startY, curX, curY, rectEl, areaRect }

  // Timer
  var timerInterval = null;
  var elapsedMs     = 0;
  var timerRunning  = false;
  var gameStarted   = false;
  var gameDone      = false;
  var paused        = false;

  // Sound
  var muted     = false;
  var audioCtx  = null;

  // ── DOM refs ─────────────────────────────────────────────────────────────────
  var boardEl       = document.getElementById('jig-board');
  var boardCanvas   = document.getElementById('jig-board-canvas');
  var ctx           = boardCanvas.getContext('2d');
  var stashInner    = document.getElementById('jig-stash-inner');
  var thumbEls      = document.querySelectorAll('.jig-top-img');
  var timerEl       = document.getElementById('jig-timer');
  var pauseBtn      = document.getElementById('jig-pause-btn');
  var restartBtn    = document.getElementById('jig-restart-btn');
  var muteBtn       = document.getElementById('jig-mute-btn');
  var statusEl      = document.getElementById('jig-status');
  var pauseOverlay  = document.getElementById('jig-pause-overlay');
  var winModal      = document.getElementById('jig-win');
  var winTimeEl     = document.getElementById('jig-win-time');
  var winDiffEl     = document.getElementById('jig-win-diff');
  var submitBtn     = document.getElementById('jig-submit-btn');
  var nameInput     = document.getElementById('jig-name');
  var scoreMsgEl    = document.getElementById('jig-score-msg');
  var winRestartBtn = document.getElementById('jig-win-restart');

  // ── LCG PRNG (seeded, for reproducible tab layout) ───────────────────────────
  function makePrng(seed) {
    var s = seed >>> 0;
    return function () {
      s = (Math.imul(1664525, s) + 1013904223) >>> 0;
      return s / 4294967296;
    };
  }

  function seedFromString(str) {
    var h = 0x811c9dc5;
    for (var i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 0x01000193) >>> 0;
    }
    return h;
  }

  // ── Jigsaw edge path helper ───────────────────────────────────────────────────
  // Draws a jigsaw edge from (ax,ay) to (bx,by).
  // tab: +1 = bump toward "outside" (right-hand normal of A→B), -1 = indent, 0 = flat
  function addEdge(ctx, ax, ay, bx, by, tab) {
    if (tab === 0) { ctx.lineTo(bx, by); return; }
    var dx = bx - ax, dy = by - ay;
    // Right-hand normal (perpendicular, pointing outward)
    var nx = -dy, ny = dx;
    var len = Math.hypot(dx, dy);
    nx /= len; ny /= len;
    var bump = tabSz * tab;
    // Key points along edge
    var t0x = ax + dx * 0.35, t0y = ay + dy * 0.35;
    var t1x = ax + dx * 0.65, t1y = ay + dy * 0.65;
    var midx = ax + dx * 0.5  + nx * bump;
    var midy = ay + dy * 0.5  + ny * bump;
    var c0x = ax + dx * 0.3  + nx * bump * 0.5;
    var c0y = ay + dy * 0.3  + ny * bump * 0.5;
    var c1x = ax + dx * 0.4  + nx * bump * 1.1;
    var c1y = ay + dy * 0.4  + ny * bump * 1.1;
    var c2x = ax + dx * 0.6  + nx * bump * 1.1;
    var c2y = ay + dy * 0.6  + ny * bump * 1.1;
    var c3x = ax + dx * 0.7  + nx * bump * 0.5;
    var c3y = ay + dy * 0.7  + ny * bump * 0.5;
    ctx.lineTo(t0x, t0y);
    ctx.bezierCurveTo(c0x, c0y, c1x, c1y, midx, midy);
    ctx.bezierCurveTo(c2x, c2y, c3x, c3y, t1x, t1y);
    ctx.lineTo(bx, by);
  }

  // Build clip path for piece (r,c) with given tabs [top,right,bottom,left]
  // Origin is (ox, oy) on the canvas (piece top-left, excluding tab overhang)
  function buildPiecePath(ctx, ox, oy, tabs) {
    var t = tabs[0], r = tabs[1], b = tabs[2], l = tabs[3];
    ctx.beginPath();
    ctx.moveTo(ox, oy);
    // Top: left→right, normal points UP (−y) = tab value inverted for outward
    addEdge(ctx, ox,        oy,        ox + cellW, oy,        -t);
    // Right: top→bottom, normal points RIGHT (+x)
    addEdge(ctx, ox + cellW, oy,        ox + cellW, oy + cellH, r);
    // Bottom: right→left, normal points DOWN (+y) = -b
    addEdge(ctx, ox + cellW, oy + cellH, ox,        oy + cellH, -b);
    // Left: bottom→top, normal points LEFT (−x) = -l  but right-hand is leftward = l
    addEdge(ctx, ox,        oy + cellH, ox,        oy,        l);
    ctx.closePath();
  }

  // ── Piece canvas rendering ────────────────────────────────────────────────────
  // Returns a small offscreen canvas with the piece drawn (clip + image slice).
  function renderPieceCanvas(p) {
    var pad = tabSz + 2; // extra padding so bezier tips don't clip
    var pw  = cellW + pad * 2;
    var ph  = cellH + pad * 2;
    var oc  = document.createElement('canvas');
    oc.width  = pw;
    oc.height = ph;
    var oc_ = oc.getContext('2d');
    // Clip to piece shape
    buildPiecePath(oc_, pad, pad, p.tabs);
    oc_.save();
    oc_.clip();
    // Draw image slice scaled from the image's intrinsic size to the cell grid.
    var scaleX  = img.naturalWidth  / (cols * cellW);
    var scaleY  = img.naturalHeight / (rows * cellH);
    var srcX    = (p.col * cellW - pad) * scaleX;
    var srcY    = (p.row * cellH - pad) * scaleY;
    var srcW    = pw * scaleX;
    var srcH    = ph * scaleY;
    oc_.drawImage(img, srcX, srcY, srcW, srcH, 0, 0, pw, ph);
    oc_.restore();
    // Outline
    buildPiecePath(oc_, pad, pad, p.tabs);
    oc_.strokeStyle = 'rgba(0,0,0,0.35)';
    oc_.lineWidth   = 1.5;
    oc_.stroke();
    return oc;
  }

  // ── Piece element (DOM canvas) ─────────────────────────────────────────────────
  function createPieceEl(p) {
    var pad = tabSz + 2;
    var pw  = cellW + pad * 2;
    var ph  = cellH + pad * 2;
    var el  = document.createElement('canvas');
    el.className = 'jig-piece';
    el.width     = pw;
    el.height    = ph;
    el.style.cssText = (
      'position:absolute;cursor:grab;touch-action:none;' +
      'width:' + pw + 'px;height:' + ph + 'px;'
    );
    el.dataset.pid = p.id;
    // Draw piece
    var elCtx = el.getContext('2d');
    var oc    = renderPieceCanvas(p);
    elCtx.drawImage(oc, 0, 0);
    return el;
  }

  // ── Initialize game ───────────────────────────────────────────────────────────
  function initGame(diff) {
    clearSelection();
    difficulty   = diff;
    rows         = DIFFS[diff].rows;
    cols         = DIFFS[diff].cols;
    pieces       = [];
    groups       = {};
    nextGroup    = 0;
    drag         = null;
    gameDone     = false;
    paused       = false;
    elapsedMs    = 0;
    gameStarted  = false;
    timerRunning = false;
    clearInterval(timerInterval);
    timerInterval = null;
    timerEl.textContent = '0:00';
    pauseBtn.textContent = '⏸ Pause';
    pauseOverlay.classList.remove('show');
    winModal.classList.remove('show');
    scoreMsgEl.textContent = '';

    // Compute available space from the game area, reserving room for the stash.
    // On mobile (column layout) the stash sits BELOW the board, not beside it.
    var STASH_W       = 260;   // desktop: stash beside the board
    var STASH_H_MOB   = 220;   // mobile: stash height (matches CSS)
    var margin        = 20;
    var isMobile      = window.innerWidth <= 700;
    var areaRect      = gameAreaEl.getBoundingClientRect();
    var availW, availH;
    if (isMobile) {
      availW = Math.max(200, areaRect.width  - 4);
      availH = Math.max(200, areaRect.height - STASH_H_MOB - 4);
    } else {
      availW = Math.max(200, areaRect.width  - STASH_W - 4);
      availH = Math.max(200, areaRect.height || 500);
    }

    // Scale puzzle to fit, preserving the image's natural aspect ratio.
    // cellW and cellH can differ so non-square images aren't distorted.
    var scale = Math.min(
      (availW - margin * 2) / img.naturalWidth,
      (availH - margin * 2) / img.naturalHeight
    );
    cellW = Math.round(Math.max(8, scale * img.naturalWidth  / cols));
    cellH = Math.round(Math.max(8, scale * img.naturalHeight / rows));
    tabSz = Math.round(Math.min(cellW, cellH) * TAB_RATIO);

    // Size the board canvas to exactly the assembled puzzle + margin.
    // The board element is flex: 0 0 auto so it shrinks to match the canvas.
    var boardW = Math.round(cols * cellW) + margin * 2;
    var boardH = Math.round(rows * cellH) + margin * 2;
    boardCanvas.width  = boardW;
    boardCanvas.height = boardH;
    boardCanvas.style.width  = boardW + 'px';
    boardCanvas.style.height = boardH + 'px';
    boardEl.style.width  = boardW + 'px';
    boardEl.style.height = boardH + 'px';

    // Seeded PRNG for tab assignments
    var prng = makePrng(seedFromString(DATE + diff));

    // Horizontal internal edges: between row r and r+1, for each col c
    // hEdge[r][c]: +1 or -1 (what piece at row r sees on its bottom edge)
    var hEdge = [];
    for (var r = 0; r < rows - 1; r++) {
      hEdge[r] = [];
      for (var c = 0; c < cols; c++) {
        hEdge[r][c] = prng() > 0.5 ? 1 : -1;
      }
    }
    // Vertical internal edges: between col c and c+1, for each row r
    // vEdge[r][c]: +1 or -1 (what piece at col c sees on its right edge)
    var vEdge = [];
    for (var r = 0; r < rows; r++) {
      vEdge[r] = [];
      for (var c = 0; c < cols - 1; c++) {
        vEdge[r][c] = prng() > 0.5 ? 1 : -1;
      }
    }

    // Build pieces
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        var topTab    = r === 0           ? 0 : -hEdge[r-1][c];
        var bottomTab = r === rows - 1    ? 0 :  hEdge[r][c];
        var rightTab  = c === cols - 1    ? 0 :  vEdge[r][c];
        var leftTab   = c === 0           ? 0 : -vEdge[r][c-1];
        pieces.push({
          id:      r * cols + c,
          row:     r,
          col:     c,
          tabs:    [topTab, rightTab, bottomTab, leftTab],
          x:       0,   // canvas x of piece origin (pad offset applied in draw)
          y:       0,
          groupId: -1,
          onBoard: false,
          el:      null,
        });
      }
    }

    // Render each piece element
    var pad = tabSz + 2;
    pieces.forEach(function (p) {
      p.el = createPieceEl(p);
    });

    // Set thumbnails — height matches center column so images don't inflate the header
    var topCenterEl = document.querySelector('.jig-top-center');
    var topH = topCenterEl ? topCenterEl.offsetHeight : 0;
    thumbEls.forEach(function(el) {
      el.src = IMAGE_URL;
      if (topH > 0) { el.style.height = topH + 'px'; el.style.width = 'auto'; }
      el.style.display = 'block';
    });
    // Mobile thumbnail (shown below header on narrow screens via CSS)
    var thumbMobile = document.getElementById('jig-thumb-mobile');
    if (thumbMobile) { thumbMobile.src = IMAGE_URL; thumbMobile.classList.add('jig-thumb-ready'); }

    // Set stash inner height to hold all pieces scattered.
    // Use the real stash element's client width so we don't exceed it.
    var stashEl2      = document.getElementById('jig-stash');
    var stashW        = stashEl2.clientWidth  || 260;
    var stashVisible  = stashEl2.clientHeight || (isMobile ? STASH_H_MOB : 500);
    var pieceW        = cellW + pad * 2;
    var pieceH        = cellH + pad * 2;
    var perRow        = Math.max(1, Math.floor(stashW / pieceW));
    // On mobile cap stash scroll depth so pieces stay reachable; desktop keep existing logic.
    var stashH;
    if (isMobile) {
      stashH = Math.max(stashVisible, Math.min(Math.ceil(pieces.length / perRow) * pieceH, stashVisible * 3));
    } else {
      stashH = Math.max(600, Math.min(Math.ceil(pieces.length / perRow) * pieceH, boardH * 3));
    }
    stashInner.style.width  = stashW + 'px';
    stashInner.style.height = stashH + 'px';

    // Clear stash
    stashInner.innerHTML = '';

    // Scatter pieces in stash, clamped so nothing clips under overflow:hidden.
    var stashUsableW = Math.max(0, stashW - pieceW);
    var stashUsableH = Math.max(0, stashH - pieceH);
    pieces.forEach(function (p) {
      p.x      = Math.random() * stashUsableW;
      p.y      = Math.random() * stashUsableH;
      p.onBoard = false;
      p.groupId = -1;
      p.el.style.left = p.x + 'px';
      p.el.style.top  = p.y + 'px';
      p.el.style.zIndex = '1';
      stashInner.appendChild(p.el);
      addPieceListeners(p);
    });

    // Clear board canvas
    ctx.clearRect(0, 0, boardCanvas.width, boardCanvas.height);

    statusEl.textContent = '';
    updateDiffButtons(diff);

    // Check for saved state (authenticated users)
    if (LOGGED_IN) {
      loadSavedState();
    }
  }

  // ── Timer ────────────────────────────────────────────────────────────────────
  function startTimer() {
    if (timerRunning) return;
    timerRunning = true;
    var last = Date.now();
    timerInterval = setInterval(function () {
      var now = Date.now();
      elapsedMs += now - last;
      last = now;
      updateTimerDisplay();
    }, 100);
  }

  function stopTimer() {
    timerRunning = false;
    clearInterval(timerInterval);
    timerInterval = null;
  }

  function updateTimerDisplay() {
    var s = Math.floor(elapsedMs / 1000);
    var m = Math.floor(s / 60);
    timerEl.textContent = m + ':' + String(s % 60).padStart(2, '0');
  }

  function fmtTime(ms) {
    var s = Math.floor(ms / 1000);
    var m = Math.floor(s / 60);
    return m + ':' + String(s % 60).padStart(2, '0');
  }

  // ── Snap sound (Web Audio) ────────────────────────────────────────────────────
  function playSnap() {
    if (muted) return;
    try {
      if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      var osc  = audioCtx.createOscillator();
      var gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.type            = 'sine';
      osc.frequency.value = 880;
      gain.gain.setValueAtTime(0.18, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.08);
      osc.start(audioCtx.currentTime);
      osc.stop(audioCtx.currentTime + 0.08);
    } catch (e) { /* silently fail if audio is unavailable */ }
  }

  // ── Drag & Drop ──────────────────────────────────────────────────────────────

  // Add pointer listeners to a piece element
  function addPieceListeners(p) {
    p.el.addEventListener('pointerdown', function (e) {
      e.preventDefault();
      e.stopPropagation();
      onPieceDown(e, p);
    });
  }

  // The drag layer lives inside .jig-game-area so pieces can't escape it.
  var gameAreaEl = document.querySelector('.jig-game-area');
  var dragLayer  = null;

  function onPieceDown(e, p) {
    if (paused || gameDone) return;
    if (!gameStarted) {
      gameStarted = true;
      startTimer();
    }

    // If the clicked piece is part of the rubber-band selection, drag all selected
    // pieces together. Otherwise clear the selection and drag normally.
    var movePids;
    if (selection.length > 0 && selection.indexOf(p.id) >= 0) {
      movePids = selection.slice();
      clearSelection();
    } else {
      clearSelection();
      var groupId = p.groupId;
      movePids = groupId >= 0 ? groups[groupId].slice() : [p.id];
    }

    var elRect = p.el.getBoundingClientRect();
    var offX   = e.clientX - elRect.left;
    var offY   = e.clientY - elRect.top;

    // Drag layer: positioned to fill the game area, z-index above everything inside it.
    if (!dragLayer) {
      dragLayer = document.createElement('div');
      dragLayer.style.cssText = (
        'position:absolute;inset:0;z-index:5000;pointer-events:none;overflow:hidden;'
      );
      gameAreaEl.appendChild(dragLayer);
    }

    var areaRect = gameAreaEl.getBoundingClientRect();

    // Compute relative offsets using client rects BEFORE lifting (works cross-container).
    var relPos = movePids.reduce(function (acc, pid) {
      var mRect = pieces[pid].el.getBoundingClientRect();
      acc[pid] = { dx: mRect.left - elRect.left, dy: mRect.top - elRect.top };
      return acc;
    }, {});

    // Lift pieces into the drag layer with absolute coords relative to game area.
    movePids.forEach(function (pid) {
      var mp    = pieces[pid];
      var mRect = mp.el.getBoundingClientRect();
      mp.el.style.position = 'absolute';
      mp.el.style.left     = (mRect.left - areaRect.left) + 'px';
      mp.el.style.top      = (mRect.top  - areaRect.top)  + 'px';
      mp.el.style.zIndex   = '6000';
      dragLayer.appendChild(mp.el);
    });

    drag = {
      pids:     movePids,
      leadId:   p.id,
      offX:     offX,
      offY:     offY,
      areaRect: areaRect,
      relPos:   relPos,
    };

    // Capture pointer on the game area so moves outside still register.
    gameAreaEl.setPointerCapture(e.pointerId);

    gameAreaEl.addEventListener('pointermove', onPointerMove);
    gameAreaEl.addEventListener('pointerup',   onPointerUp);
  }

  function onPointerMove(e) {
    if (!drag) return;
    var lp   = pieces[drag.leadId];
    var pad  = tabSz + 2;
    var pw   = cellW + pad * 2;
    var ph   = cellH + pad * 2;
    var area = drag.areaRect;

    // Convert client coords to game-area-relative coords and clamp.
    var rawLeft = e.clientX - drag.offX - area.left;
    var rawTop  = e.clientY - drag.offY - area.top;
    var newLeft = Math.max(0, Math.min(rawLeft, area.width  - pw));
    var newTop  = Math.max(0, Math.min(rawTop,  area.height - ph));

    lp.el.style.left = newLeft + 'px';
    lp.el.style.top  = newTop  + 'px';

    // Move group peers (their relative offsets may extend outside — acceptable).
    drag.pids.forEach(function (pid) {
      if (pid === drag.leadId) return;
      var rel = drag.relPos[pid];
      var mp  = pieces[pid];
      mp.el.style.left = (newLeft + rel.dx) + 'px';
      mp.el.style.top  = (newTop  + rel.dy) + 'px';
    });
  }

  function onPointerUp(e) {
    if (!drag) return;
    gameAreaEl.removeEventListener('pointermove', onPointerMove);
    gameAreaEl.removeEventListener('pointerup',   onPointerUp);

    var boardRect   = boardEl.getBoundingClientRect();
    var stashEl     = document.getElementById('jig-stash');
    var stashRect   = stashEl.getBoundingClientRect();
    var stashScroll = stashEl.scrollTop;
    var areaRect    = drag.areaRect;

    // Determine where the lead piece was dropped (client coords from its current abs position).
    var lp    = pieces[drag.leadId];
    var lpAbsLeft = parseFloat(lp.el.style.left) + areaRect.left;
    var lpAbsTop  = parseFloat(lp.el.style.top)  + areaRect.top;
    var pw    = cellW + (tabSz + 2) * 2;
    var ph    = cellH + (tabSz + 2) * 2;
    var midX  = lpAbsLeft + pw / 2;
    var midY  = lpAbsTop  + ph / 2;
    var onBoard = (midX >= boardRect.left && midX <= boardRect.right &&
                   midY >= boardRect.top  && midY <= boardRect.bottom);

    // For stash drops: compute a single shift from the lead piece so the whole
    // group moves together instead of each piece being clamped independently
    // (independent clamping stacks all left-overhanging pieces at x=0).
    var stashShiftX = 0, stashShiftY = 0;
    if (!onBoard) {
      var pad2  = tabSz + 2;
      var pw2   = cellW + pad2 * 2;
      var lpRawX = lpAbsLeft - stashRect.left;
      var lpRawY = lpAbsTop  - stashRect.top + stashScroll;
      var lpClampX = Math.max(0, Math.min(lpRawX, stashRect.width - pw2));
      var lpClampY = Math.max(0, lpRawY);
      stashShiftX = lpClampX - lpRawX;
      stashShiftY = lpClampY - lpRawY;
    }

    drag.pids.forEach(function (pid) {
      var mp  = pieces[pid];
      // Current absolute client position of this piece.
      var absLeft = parseFloat(mp.el.style.left) + areaRect.left;
      var absTop  = parseFloat(mp.el.style.top)  + areaRect.top;

      if (onBoard) {
        mp.x = absLeft - boardRect.left;
        mp.y = absTop  - boardRect.top;
        mp.onBoard = true;
        boardEl.appendChild(mp.el);
        mp.el.style.position = 'absolute';
        mp.el.style.left     = mp.x + 'px';
        mp.el.style.top      = mp.y + 'px';
        mp.el.style.zIndex   = '2';
      } else {
        var rawX = absLeft - stashRect.left + stashShiftX;
        var rawY = absTop  - stashRect.top + stashScroll + stashShiftY;
        mp.x = rawX;
        mp.y = Math.max(0, rawY);
        mp.onBoard = false;
        stashInner.appendChild(mp.el);
        mp.el.style.position = 'absolute';
        mp.el.style.left     = mp.x + 'px';
        mp.el.style.top      = mp.y + 'px';
        mp.el.style.zIndex   = '1';
      }
    });

    // Snap check (only for pieces on the board)
    if (onBoard) {
      checkSnap(drag.leadId, drag.pids);
    }

    drag = null;
  }

  // ── Rubber-band selection ────────────────────────────────────────────────────

  function clearSelection() {
    selection.forEach(function (pid) {
      var p = pieces[pid];
      if (p && p.el) { p.el.style.outline = ''; }
    });
    selection = [];
  }

  function onSelMove(e) {
    if (!selDrag) return;
    var a    = selDrag.areaRect;
    var curX = Math.max(0, Math.min(e.clientX - a.left, a.width));
    var curY = Math.max(0, Math.min(e.clientY - a.top,  a.height));
    selDrag.curX = curX;
    selDrag.curY = curY;
    var x = Math.min(selDrag.startX, curX);
    var y = Math.min(selDrag.startY, curY);
    var w = Math.abs(curX - selDrag.startX);
    var h = Math.abs(curY - selDrag.startY);
    var r = selDrag.rectEl;
    r.style.left   = x + 'px';
    r.style.top    = y + 'px';
    r.style.width  = w + 'px';
    r.style.height = h + 'px';
  }

  function onSelUp() {
    if (!selDrag) return;
    gameAreaEl.removeEventListener('pointermove', onSelMove);
    gameAreaEl.removeEventListener('pointerup',   onSelUp);
    gameAreaEl.removeChild(selDrag.rectEl);
    var a    = selDrag.areaRect;
    var curX = selDrag.curX !== undefined ? selDrag.curX : selDrag.startX;
    var curY = selDrag.curY !== undefined ? selDrag.curY : selDrag.startY;
    var x1   = Math.min(selDrag.startX, curX);
    var y1   = Math.min(selDrag.startY, curY);
    var x2   = Math.max(selDrag.startX, curX);
    var y2   = Math.max(selDrag.startY, curY);
    selDrag  = null;
    if (x2 - x1 < 8 || y2 - y1 < 8) return; // too small — treat as a click
    // Highlight pieces whose center falls inside the selection rect
    var newSel = [];
    pieces.forEach(function (p) {
      if (!p.el) return;
      var r  = p.el.getBoundingClientRect();
      var cx = r.left + r.width  / 2 - a.left;
      var cy = r.top  + r.height / 2 - a.top;
      if (cx >= x1 && cx <= x2 && cy >= y1 && cy <= y2) { newSel.push(p.id); }
    });
    if (newSel.length > 1) {
      selection = newSel;
      selection.forEach(function (pid) {
        if (pieces[pid] && pieces[pid].el) {
          pieces[pid].el.style.outline = '2px solid rgba(68,170,255,0.9)';
        }
      });
    }
  }

  // Rubber-band starts when the user drags on empty game-area space.
  // Pieces call stopPropagation so they won't trigger this listener.
  gameAreaEl.addEventListener('pointerdown', function (e) {
    if (e.pointerType === 'touch') return; // touch scrolls stash; don't rubber-band
    if (paused || gameDone || !pieces.length) return;
    clearSelection();
    var a      = gameAreaEl.getBoundingClientRect();
    var startX = e.clientX - a.left;
    var startY = e.clientY - a.top;
    var rectEl = document.createElement('div');
    rectEl.style.cssText = (
      'position:absolute;left:' + startX + 'px;top:' + startY + 'px;' +
      'width:0;height:0;border:2px dashed rgba(68,170,255,0.85);' +
      'background:rgba(68,170,255,0.07);pointer-events:none;z-index:8000;'
    );
    gameAreaEl.appendChild(rectEl);
    selDrag = { startX: startX, startY: startY, rectEl: rectEl, areaRect: a };
    gameAreaEl.setPointerCapture(e.pointerId);
    gameAreaEl.addEventListener('pointermove', onSelMove);
    gameAreaEl.addEventListener('pointerup',   onSelUp);
  });

  // ── Snap logic ────────────────────────────────────────────────────────────────
  // Correct board position for piece p: where its top-left should be
  // so the assembled puzzle is centred on the board canvas.
  function solvedPos(p) {
    var pad   = tabSz + 2;
    var totalW = cols * cellW;
    var totalH = rows * cellH;
    var offX  = (boardCanvas.width  - totalW) / 2 - pad;
    var offY  = (boardCanvas.height - totalH) / 2 - pad;
    return {
      x: offX + p.col * cellW,
      y: offY + p.row * cellH,
    };
  }

  function checkSnap(leadId, movedPids) {
    if (!pieces[leadId].onBoard) return;

    var snapped = false;

    // Check every moved piece against every on-board piece not in the drag group.
    // Using a labelled break so we exit both loops as soon as the first snap fires.
    snapSearch: for (var mi = 0; mi < movedPids.length; mi++) {
      var mp = pieces[movedPids[mi]];
      for (var i = 0; i < pieces.length; i++) {
        var op = pieces[i];
        if (!op.onBoard) continue;
        if (movedPids.indexOf(op.id) >= 0) continue; // same drag group

        // Only adjacent grid neighbours can snap together.
        var dr = op.row - mp.row;
        var dc = op.col - mp.col;
        if (Math.abs(dr) + Math.abs(dc) !== 1) continue;

        // Check whether mp is positioned where it belongs relative to op.
        var opSolved = solvedPos(op);
        var mpSolved = solvedPos(mp);
        var expectedRelX = mpSolved.x - opSolved.x;
        var expectedRelY = mpSolved.y - opSolved.y;
        var distX = Math.abs((mp.x - op.x) - expectedRelX);
        var distY = Math.abs((mp.y - op.y) - expectedRelY);

        if (distX <= SNAP_DIST && distY <= SNAP_DIST) {
          // Move all movedPids so mp lands exactly where it belongs next to op.
          var snapDX = (op.x + expectedRelX) - mp.x;
          var snapDY = (op.y + expectedRelY) - mp.y;
          movedPids.forEach(function (pid) {
            var pp = pieces[pid];
            pp.x += snapDX;
            pp.y += snapDY;
            pp.el.style.left = pp.x + 'px';
            pp.el.style.top  = pp.y + 'px';
          });
          mergeGroups(movedPids, op.id);
          playSnap();
          snapped = true;
          break snapSearch;
        }
      }
    }

    // If not snapped to another piece, check if any moved piece is close to its solved position
    if (!snapped) {
      for (var j = 0; j < movedPids.length; j++) {
        var mp  = pieces[movedPids[j]];
        var sp  = solvedPos(mp);
        var dx  = Math.abs(mp.x - sp.x);
        var dy  = Math.abs(mp.y - sp.y);
        if (dx <= SNAP_DIST && dy <= SNAP_DIST) {
          // Snap whole group to solved grid
          var snapDX = sp.x - mp.x;
          var snapDY = sp.y - mp.y;
          movedPids.forEach(function (pid) {
            var pp = pieces[pid];
            pp.x += snapDX;
            pp.y += snapDY;
            pp.el.style.left = pp.x + 'px';
            pp.el.style.top  = pp.y + 'px';
          });
          playSnap();
          break;
        }
      }
      // Check if the newly repositioned pieces now connect with others
      var gid = pieces[leadId].groupId;
      var checkPids = gid >= 0 ? groups[gid].slice() : [leadId];
      for (var k = 0; k < pieces.length; k++) {
        var op2 = pieces[k];
        if (!op2.onBoard) continue;
        if (checkPids.indexOf(op2.id) >= 0) continue;
        for (var l = 0; l < checkPids.length; l++) {
          var mp2 = pieces[checkPids[l]];
          var dr2 = op2.row - mp2.row;
          var dc2 = op2.col - mp2.col;
          if (Math.abs(dr2) + Math.abs(dc2) !== 1) continue;
          var op2Solved  = solvedPos(op2);
          var mp2Solved  = solvedPos(mp2);
          var expRelX2   = mp2Solved.x - op2Solved.x;
          var expRelY2   = mp2Solved.y - op2Solved.y;
          var actRelX2   = mp2.x - op2.x;
          var actRelY2   = mp2.y - op2.y;
          if (Math.abs(actRelX2 - expRelX2) <= SNAP_DIST &&
              Math.abs(actRelY2 - expRelY2) <= SNAP_DIST) {
            mergeGroups(checkPids, op2.id);
            playSnap();
            break;
          }
        }
      }
    }

    checkWin();
  }

  // ── Group management ──────────────────────────────────────────────────────────
  function mergeGroups(pids, otherId) {
    var otherGid = pieces[otherId].groupId;
    var leadGid  = pieces[pids[0]].groupId;

    var newGid = nextGroup++;
    groups[newGid] = [];

    // Collect all pieces that belong to the new group
    var allPids = pids.slice();
    if (otherGid >= 0) {
      groups[otherGid].forEach(function (pid) {
        if (allPids.indexOf(pid) < 0) allPids.push(pid);
      });
      delete groups[otherGid];
    } else {
      if (allPids.indexOf(otherId) < 0) allPids.push(otherId);
    }
    if (leadGid >= 0 && leadGid !== otherGid) {
      groups[leadGid].forEach(function (pid) {
        if (allPids.indexOf(pid) < 0) allPids.push(pid);
      });
      delete groups[leadGid];
    }

    allPids.forEach(function (pid) {
      pieces[pid].groupId = newGid;
    });
    groups[newGid] = allPids;

    // Bring group to front
    allPids.forEach(function (pid) {
      pieces[pid].el.style.zIndex = '3';
    });
  }

  // ── Win detection ─────────────────────────────────────────────────────────────
  function checkWin() {
    if (gameDone) return;
    // All pieces must be on board
    for (var i = 0; i < pieces.length; i++) {
      if (!pieces[i].onBoard) return;
    }
    // All pieces must be in the same group
    var gid0 = pieces[0].groupId;
    if (gid0 < 0) return;
    for (var i = 1; i < pieces.length; i++) {
      if (pieces[i].groupId !== gid0) return;
    }
    gameDone = true;
    stopTimer();
    showWin();
    saveGameState(true);
  }

  function showWin() {
    winTimeEl.textContent  = fmtTime(elapsedMs);
    winDiffEl.textContent  = difficulty.charAt(0).toUpperCase() + difficulty.slice(1) +
                             ' · ' + (rows * cols) + ' pieces';
    winModal.classList.add('show');
  }

  // ── Save / Resume ─────────────────────────────────────────────────────────────
  function buildPieceState() {
    return pieces.map(function (p) {
      return { id: p.id, x: p.x, y: p.y, groupId: p.groupId, onBoard: p.onBoard };
    });
  }

  function saveGameState(final) {
    if (!LOGGED_IN) return;
    if (final) {
      // Puzzle complete — delete the save so returning to the page starts fresh
      fetch('/api/jigsaw/delete-save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
        body: JSON.stringify({ puzzle_date: DATE, difficulty: difficulty }),
      }).catch(function () { /* ignore */ });
      return;
    }
    var payload = {
      puzzle_date: DATE,
      difficulty:  difficulty,
      image_name:  IMAGE_NAME,
      elapsed_ms:  elapsedMs,
      piece_state: buildPieceState(),
    };
    fetch('/api/jigsaw/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify(payload),
    }).catch(function () { /* silently ignore */ });
  }

  function loadSavedState() {
    if (!LOGGED_IN || !difficulty) return;
    fetch('/api/jigsaw/resume?puzzle_date=' + encodeURIComponent(DATE) +
          '&difficulty=' + encodeURIComponent(difficulty))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.saved || !data.piece_state || !data.piece_state.length) return;
        restoreState(data.piece_state, data.elapsed_ms);
      })
      .catch(function () { /* ignore */ });
  }

  function restoreState(pieceState, savedMs) {
    elapsedMs    = savedMs || 0;
    gameStarted  = true;
    var pad       = tabSz + 2;
    var pw        = cellW + pad * 2;
    var ph        = cellH + pad * 2;
    var curStashW = parseInt(stashInner.style.width,  10) || 260;
    var curStashH = parseInt(stashInner.style.height, 10) || 600;

    // Rebuild groups from saved state
    groups   = {};
    nextGroup = 0;
    var groupMap = {};

    pieceState.forEach(function (ps) {
      var p = pieces[ps.id];
      if (!p) return;
      p.x = ps.x; p.y = ps.y;
      p.onBoard = !!ps.onBoard;
      // If saved position is out of the current stash bounds (e.g. from a
      // session with a larger stash), randomize rather than clamping — clamping
      // stacks all out-of-bounds pieces at the same coordinate.
      if (!p.onBoard) {
        var maxX = Math.max(0, curStashW - pw);
        var maxY = Math.max(0, curStashH - ph);
        if (p.x < 0 || p.x > maxX || p.y < 0 || p.y > maxY) {
          p.x = Math.random() * maxX;
          p.y = Math.random() * maxY;
        }
      }
      var gid = ps.groupId;
      if (gid >= 0) {
        if (groupMap[gid] === undefined) { groupMap[gid] = nextGroup++; groups[groupMap[gid]] = []; }
        var newGid = groupMap[gid];
        p.groupId = newGid;
        groups[newGid].push(p.id);
      } else {
        p.groupId = -1;
      }
      // Reposition element
      if (p.onBoard) {
        boardEl.appendChild(p.el);
        p.el.style.position = 'absolute';
      } else {
        stashInner.appendChild(p.el);
        p.el.style.position = 'absolute';
      }
      p.el.style.left = p.x + 'px';
      p.el.style.top  = p.y + 'px';
    });

    updateTimerDisplay();
    // Don't auto-start timer — user must interact
  }

  // ── Pause / Resume ────────────────────────────────────────────────────────────
  function togglePause() {
    if (gameDone || !gameStarted) return;
    paused = !paused;
    if (paused) {
      stopTimer();
      pauseBtn.textContent = '▶ Resume';
      pauseOverlay.classList.add('show');
      saveGameState(false);
    } else {
      startTimer();
      pauseBtn.textContent = '⏸ Pause';
      pauseOverlay.classList.remove('show');
    }
  }

  // ── Controls ──────────────────────────────────────────────────────────────────
  function updateDiffButtons(diff) {
    document.querySelectorAll('.jig-diff-btn').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.diff === diff);
    });
  }

  document.querySelectorAll('.jig-diff-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (!img) {
        statusEl.textContent = 'Loading image…';
        return;
      }
      if (gameStarted && !gameDone) {
        if (!confirm('Start a new puzzle? Your current progress will be lost.')) return;
      }
      stopTimer();
      initGame(btn.dataset.diff);
    });
  });

  pauseBtn.addEventListener('click', togglePause);

  restartBtn.addEventListener('click', function () {
    if (!difficulty) return;
    if (gameStarted && !gameDone) {
      if (!confirm('Restart the puzzle? Your progress will be lost.')) return;
    }
    stopTimer();
    initGame(difficulty);
  });

  muteBtn.addEventListener('click', function () {
    muted = !muted;
    muteBtn.textContent = muted ? '🔇' : '🔊';
  });

  // Score submission
  submitBtn.addEventListener('click', function () {
    var name = nameInput.value.trim();
    if (!name) { scoreMsgEl.textContent = 'Please enter your name.'; return; }
    submitBtn.disabled = true;
    scoreMsgEl.textContent = 'Submitting…';
    fetch('/api/jigsaw-scores', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify({
        name:        name,
        puzzle_date: DATE,
        difficulty:  difficulty,
        image_name:  IMAGE_NAME || 'custom',
        time_ms:     elapsedMs,
      }),
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.ok) {
        scoreMsgEl.textContent = 'Score submitted!';
        document.getElementById('jig-score-form').style.display = 'none';
      } else {
        scoreMsgEl.textContent = 'Submission failed. Try again.';
        submitBtn.disabled = false;
      }
    })
    .catch(function () {
      scoreMsgEl.textContent = 'Submission failed. Try again.';
      submitBtn.disabled = false;
    });
  });

  winRestartBtn.addEventListener('click', function () {
    winModal.classList.remove('show');
    initGame(difficulty);
  });

  // Auto-save on page unload
  window.addEventListener('beforeunload', function () {
    if (LOGGED_IN && gameStarted && !gameDone && difficulty) {
      saveGameState(false);
    }
  });

  // Auto-save every 60 seconds while playing
  setInterval(function () {
    if (LOGGED_IN && gameStarted && !gameDone && !paused && difficulty) {
      saveGameState(false);
    }
  }, 60000);

  // ── Gallery link passes ?img=... and ?diff=... ────────────────────────────────
  function parseQueryParam(name) {
    var params = new URLSearchParams(window.location.search);
    return params.get(name) || '';
  }

  // ── Image loading & boot ─────────────────────────────────────────────────────
  function boot() {
    // Override image from gallery URL param
    var imgParam  = parseQueryParam('img');
    var diffParam = parseQueryParam('diff');

    if (imgParam) {
      IMAGE_NAME = imgParam;
      IMAGE_URL  = '/static/img/puzzle/' + imgParam;
    }
    if (!IMAGE_URL) {
      statusEl.textContent = 'No image available. Please check back tomorrow.';
      return;
    }

    img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = function () {
      statusEl.textContent = '';
      var startDiff = diffParam || window.JIG_DIFFICULTY || 'beginner';
      if (!DIFFS[startDiff]) startDiff = 'beginner';
      initGame(startDiff);
    };
    img.onerror = function () {
      statusEl.textContent = 'Failed to load puzzle image.';
    };
    img.src = IMAGE_URL;
    statusEl.textContent = 'Loading image…';
  }

  boot();

})();
