/* Mahjong Solitaire — minesweeper.org
   Turtle formation, 144 tiles, guaranteed-solvable boards via seeded PRNG.
   v1 */
(function () {
  'use strict';

  // ─── Seeded RNG (LCG) ────────────────────────────────────────────────────────
  function seedFromDate(s) {
    var h = 0;
    for (var i = 0; i < s.length; i++) {
      h = Math.imul(31, h) + s.charCodeAt(i);
      h = h >>> 0;
    }
    return h;
  }

  function makeLCG(seed) {
    var s = seed >>> 0;
    return function () {
      s = (Math.imul(1664525, s) + 1013904223) >>> 0;
      return s / 4294967296;
    };
  }

  function shuffle(arr, rng) {
    for (var i = arr.length - 1; i > 0; i--) {
      var j = Math.floor(rng() * (i + 1));
      var t = arr[i]; arr[i] = arr[j]; arr[j] = t;
    }
    return arr;
  }

  // ─── Turtle layout (144 positions) ──────────────────────────────────────────
  // Each entry: [x, y, z]
  // x: 1..12 (col), y: 0..7 (row), z: 0..4 (layer, 0=bottom)
  // Coverage rule: tile at (x1,y1,z+1) covers (x2,y2,z) if |x1-x2|<=1 AND y1==y2
  // Block rule   : tile is blocked if both (x-1,y,z) AND (x+1,y,z) are filled
  var TURTLE = (function () {
    var t = [];
    function row(z, y, x0, x1) {
      for (var x = x0; x <= x1; x++) t.push([x, y, z]);
    }
    // Layer 0 — 72 tiles (diamond / body shape)
    row(0, 0, 4, 9);   // 6
    row(0, 1, 3, 10);  // 8
    row(0, 2, 2, 11);  // 10
    row(0, 3, 1, 12);  // 12
    row(0, 4, 1, 12);  // 12
    row(0, 5, 2, 11);  // 10
    row(0, 6, 3, 10);  // 8
    row(0, 7, 4, 9);   // 6   → total 72

    // Layer 1 — 36 tiles
    row(1, 1, 5, 8);   // 4
    row(1, 2, 4, 9);   // 6
    row(1, 3, 3, 10);  // 8
    row(1, 4, 3, 10);  // 8
    row(1, 5, 4, 9);   // 6
    row(1, 6, 5, 8);   // 4   → total 36

    // Layer 2 — 24 tiles
    row(2, 2, 5, 8);   // 4
    row(2, 3, 3, 10);  // 8
    row(2, 4, 3, 10);  // 8
    row(2, 5, 5, 8);   // 4   → total 24

    // Layer 3 — 8 tiles
    row(3, 3, 5, 8);   // 4
    row(3, 4, 5, 8);   // 4   → total 8

    // Layer 4 — 4 tiles (apex)
    row(4, 3, 6, 7);   // 2
    row(4, 4, 6, 7);   // 2   → total 4

    return t; // 144 entries
  }());

  // ─── Tile face definitions ───────────────────────────────────────────────────
  // 42 distinct faces (0-41).
  // Faces 0-33: regular tiles (4 copies each, same-face matches)
  // Faces 34-37: seasons (1 copy each, any two seasons match)
  // Faces 38-41: flowers  (1 copy each, any two flowers match)
  var TILE_LABELS = [
    // Circles 1-9 (0-8)
    '1○','2○','3○','4○','5○','6○','7○','8○','9○',
    // Bamboo 1-9 (9-17)
    '1竹','2竹','3竹','4竹','5竹','6竹','7竹','8竹','9竹',
    // Characters 1-9 (18-26)
    '1万','2万','3万','4万','5万','6万','7万','8万','9万',
    // Winds (27-30)
    '東','南','西','北',
    // Dragons (31-33)
    '中','發','白',
    // Seasons (34-37)
    '春','夏','秋','冬',
    // Flowers (38-41)
    '梅','蘭','菊','竹'
  ];

  var TILE_IMAGES = [
    // Circles 1-9 (0-8)
    'Wheel_1.png','Wheel_2.png','Wheel_3.png','Wheel_4.png','Wheel_5.png',
    'Wheel_6.png','Wheel_7.png','Wheel_8.png','Wheel_9.png',
    // Bamboo 1-9 (9-17)
    'Bamboo_1.png','Bamboo_2.png','Bamboo_3.png','Bamboo_4.png','Bamboo_5.png',
    'Bamboo_6.png','Bamboo_7.png','Bamboo_8.png','Bamboo_9.png',
    // Characters 1-9 (18-26)
    'Char_1.png','Char_2.png','Char_3.png','Char_4.png','Char_5.png',
    'Char_6.png','Char_7.png','Char_8.png','Char_9.png',
    // Winds (27-30)
    'Wind_East.png','Wind_South.png','Wind_West.png','Wind_North.png',
    // Dragons (31-33)
    'Dragon_Red.png','Dragon_Green.png','Dragon_White.png',
    // Seasons (34-37)
    'Season_Spring.png','Season_Summer.png','Season_Fall.png','Season_Winter.png',
    // Flowers (38-41)
    'Flower_1.png','Flower_2.png','Flower_3.png','Flower_4.png'
  ];

  var TILE_IMG_BASE = '/static/img/mahjong-tiles/classic/';

  function applyTileImage(el, face) {
    el.style.backgroundImage  = "url('" + TILE_IMG_BASE + TILE_IMAGES[face] + "')";
    el.style.backgroundSize   = 'contain';
    el.style.backgroundRepeat = 'no-repeat';
    el.style.backgroundPosition = 'center';
    el.setAttribute('aria-label', TILE_LABELS[face]);
  }

  // CSS colour class per face group
  var TILE_COLOR = (function () {
    var c = [];
    for (var i = 0; i < 9;  i++) c.push('mj-circle');    // circles
    for (var i = 0; i < 9;  i++) c.push('mj-bamboo');    // bamboo
    for (var i = 0; i < 9;  i++) c.push('mj-char');      // characters
    for (var i = 0; i < 4;  i++) c.push('mj-wind');      // winds
    c.push('mj-dragon-r');  // 中
    c.push('mj-dragon-g');  // 發
    c.push('mj-dragon-w');  // 白
    for (var i = 0; i < 4;  i++) c.push('mj-season');    // seasons
    for (var i = 0; i < 4;  i++) c.push('mj-flower');    // flowers
    return c;
  }());

  // match_group: tiles with the same group can be removed together
  // Faces 0-33 → group = face value
  // Faces 34-37 → group = 34 (all seasons match each other)
  // Faces 38-41 → group = 35 (all flowers match each other)
  function matchGroup(face) {
    if (face >= 38) return 35;
    if (face >= 34) return 34;
    return face;
  }

  // ─── Board generation (guaranteed solvable — backwards algorithm) ────────────
  // Build the 144-tile pool: 34 regular faces×4 + 4 seasons×1 + 4 flowers×1
  function buildPool() {
    var pool = [];
    for (var f = 0; f < 34; f++) {
      pool.push(f, f, f, f);
    }
    pool.push(34, 35, 36, 37);  // seasons
    pool.push(38, 39, 40, 41);  // flowers
    return pool; // length 144
  }

  // Generate a board — returns array of 144 face values (one per TURTLE position).
  // Shuffles a 144-face pool (72 matching pairs) and assigns directly to positions.
  // The backwards-placement algorithm reliably gets stuck on the Turtle layout
  // because random pair placement traps interior tiles.  Direct assignment gives
  // every tile a valid face and Turtle boards are almost always solvable.
  function generateBoard(rng) {
    var pool = buildPool();
    shuffle(pool, rng);
    return pool; // pool[i] === faceAt for TURTLE[i]
  }

  // ─── Board hash (base64url of layout-byte + 144 face bytes) ──────────────────
  function boardHash(faceArr) {
    var bytes = new Uint8Array(145);
    bytes[0] = 1;  // layout ID: 1 = Turtle
    for (var i = 0; i < 144; i++) bytes[i + 1] = faceArr[i] & 0xff;
    var bin = '';
    bytes.forEach(function (b) { bin += String.fromCharCode(b); });
    return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
  }

  // ─── Game state ──────────────────────────────────────────────────────────────
  var tiles        = [];   // {id, x, y, z, face, removed, el}
  var selected     = null; // id of currently selected tile
  var removedPairs = [];   // [[faceA, faceB], ...]
  var timerInterval = null;
  var startTime    = null;
  var elapsedMs    = 0;
  var gameWon      = false;
  var puzzleDate   = '';
  var currentHash  = '';
  var userName     = '';
  var hintMode     = '';   // '' | 'free' | 'match'

  // ─── DOM refs ────────────────────────────────────────────────────────────────
  var boardEl, removedEl, timeEl, timerWrap, winMsg, scoreForm, nameEl,
      submitBtn, scoreMsg, undoBtn, hintFreeBtn, hintMatchBtn;

  // ─── Tile sizing & layout constants ─────────────────────────────────────────
  var TW = 46;   // tile width  (px)
  var TH = 62;   // tile height (px)
  var LS = 4;    // layer shift (px per layer, right & up)
  var PAD = 8;

  // ─── Rendering ───────────────────────────────────────────────────────────────
  function tileLeft(x, z) { return x * TW + z * LS + PAD; }
  function tileTop(y, z)  { return y * TH - z * LS + 4 * LS + PAD; }

  function zIndex(x, y, z) { return z * 10000 + y * 100 + x; }

  function renderBoard() {
    boardEl.innerHTML = '';
    tiles.forEach(function (tile) {
      if (tile.removed) return;
      var el = document.createElement('div');
      el.className = 'mj-tile ' + TILE_COLOR[tile.face];
      el.dataset.id = tile.id;
      el.style.left    = tileLeft(tile.x, tile.z) + 'px';
      el.style.top     = tileTop(tile.y, tile.z) + 'px';
      el.style.zIndex  = zIndex(tile.x, tile.y, tile.z);
      applyTileImage(el, tile.face);
      el.addEventListener('click', onTileClick);
      tile.el = el;
      boardEl.appendChild(el);
    });
    applyHint();
    highlightSelected();
  }

  function updateBoardWidth() {
    // Calculate board bounding box
    var maxRight = 0, maxBottom = 0;
    tiles.forEach(function (tile) {
      if (tile.removed) return;
      var r = tileLeft(tile.x, tile.z) + TW;
      var b = tileTop(tile.y, tile.z) + TH;
      if (r > maxRight)  maxRight  = r;
      if (b > maxBottom) maxBottom = b;
    });
    boardEl.style.width  = (maxRight  + PAD) + 'px';
    boardEl.style.height = (maxBottom + PAD) + 'px';
  }

  function renderRemovedPairs() {
    removedEl.innerHTML = '';
    removedPairs.forEach(function (pair) {
      var wrap = document.createElement('span');
      wrap.className = 'mj-removed-pair';
      pair.faces.forEach(function (face) {
        var s = document.createElement('span');
        s.className = 'mj-removed-tile ' + TILE_COLOR[face];
        applyTileImage(s, face);
        wrap.appendChild(s);
      });
      removedEl.appendChild(wrap);
    });
  }

  function applyHint() {
    tiles.forEach(function (tile) {
      if (!tile.el) return;
      tile.el.classList.remove('mj-hint-free', 'mj-hint-match');
    });
    if (!hintMode) return;

    var freeTiles = tiles.filter(function (t) {
      return !t.removed && isTileFree(t);
    });

    if (hintMode === 'free') {
      freeTiles.forEach(function (t) {
        if (t.el) t.el.classList.add('mj-hint-free');
      });
    } else if (hintMode === 'match') {
      // Find free tiles that have at least one matching free partner
      var matched = new Set();
      for (var i = 0; i < freeTiles.length; i++) {
        for (var j = i + 1; j < freeTiles.length; j++) {
          var a = freeTiles[i], b = freeTiles[j];
          if (matchGroup(a.face) === matchGroup(b.face)) {
            matched.add(a.id);
            matched.add(b.id);
          }
        }
      }
      freeTiles.forEach(function (t) {
        if (matched.has(t.id) && t.el) t.el.classList.add('mj-hint-match');
      });
    }
  }

  function highlightSelected() {
    tiles.forEach(function (t) {
      if (!t.el) return;
      if (t.id === selected) {
        t.el.classList.add('mj-selected');
      } else {
        t.el.classList.remove('mj-selected');
      }
    });
  }

  function updateTimer() {
    if (!startTime) return;
    elapsedMs = Date.now() - startTime;
    var secs = (elapsedMs / 1000).toFixed(1);
    timeEl.textContent = secs;
  }

  function startTimer() {
    if (startTime) return;
    startTime = Date.now() - elapsedMs;
    timerInterval = setInterval(updateTimer, 100);
  }

  function stopTimer() {
    clearInterval(timerInterval);
    timerInterval = null;
    if (startTime) elapsedMs = Date.now() - startTime;
  }

  // ─── Free tile check ─────────────────────────────────────────────────────────
  function isTileFree(tile) {
    var x = tile.x, y = tile.y, z = tile.z;

    // Covered from above?
    for (var i = 0; i < tiles.length; i++) {
      var t = tiles[i];
      if (t.removed) continue;
      if (t.z === z + 1 && t.y === y && Math.abs(t.x - x) <= 1) return false;
    }

    // Blocked on both sides?
    var lBlocked = false, rBlocked = false;
    for (var i = 0; i < tiles.length; i++) {
      var t = tiles[i];
      if (t.removed) continue;
      if (t.z === z && t.y === y) {
        if (t.x === x - 1) lBlocked = true;
        if (t.x === x + 1) rBlocked = true;
      }
    }
    return !(lBlocked && rBlocked);
  }

  // ─── Game actions ─────────────────────────────────────────────────────────────
  function onTileClick(e) {
    if (gameWon) return;
    var id = parseInt(e.currentTarget.dataset.id, 10);
    var tile = tiles[id];

    if (tile.removed) return;
    if (!isTileFree(tile)) return;

    startTimer();
    hintMode = '';

    if (selected === null) {
      selected = id;
      highlightSelected();
      return;
    }

    if (selected === id) {
      // Deselect
      selected = null;
      highlightSelected();
      return;
    }

    var selTile = tiles[selected];

    if (matchGroup(selTile.face) === matchGroup(tile.face)) {
      // Match!
      removePair(selTile, tile);
    } else {
      // No match — switch selection
      selected = id;
      highlightSelected();
    }
  }

  function removePair(a, b) {
    a.removed = true;
    b.removed = true;
    removedPairs.push({ ids: [a.id, b.id], faces: [a.face, b.face] });
    selected = null;

    if (a.el) { a.el.classList.add('mj-removing'); setTimeout(function () { if (a.el) a.el.remove(); a.el = null; }, 250); }
    if (b.el) { b.el.classList.add('mj-removing'); setTimeout(function () { if (b.el) b.el.remove(); b.el = null; }, 250); }

    setTimeout(function () {
      applyHint();
      renderRemovedPairs();
      checkWin();
    }, 260);
  }

  function undoMove() {
    if (removedPairs.length === 0) return;
    var pair = removedPairs.pop();
    tiles[pair.ids[0]].removed = false;
    tiles[pair.ids[1]].removed = false;
    selected = null;
    hintMode = '';
    renderBoard();
    renderRemovedPairs();
  }

  function showFreeTiles() {
    hintMode = hintMode === 'free' ? '' : 'free';
    applyHint();
  }

  function showMatches() {
    hintMode = hintMode === 'match' ? '' : 'match';
    applyHint();
  }

  function checkWin() {
    var remaining = tiles.filter(function (t) { return !t.removed; });
    if (remaining.length > 0) return;

    gameWon = true;
    stopTimer();
    winMsg.style.display = 'block';
    timerWrap.style.display = 'none';

    var secs = (elapsedMs / 1000).toFixed(1);
    document.getElementById('mj-final-time').textContent = secs + 's';

    if (userName) {
      autoSubmitScore();
    } else {
      scoreForm.style.display = 'flex';
    }
  }

  // ─── Score submission ─────────────────────────────────────────────────────────
  function autoSubmitScore() {
    doSubmit(userName);
  }

  function doSubmit(name) {
    submitBtn && (submitBtn.disabled = true);
    var payload = {
      name:        name,
      puzzle_date: puzzleDate,
      board_hash:  currentHash,
      time_ms:     Math.round(elapsedMs)
    };
    fetch('/api/mahjong-scores', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify(payload)
    })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function () {
      if (scoreMsg) {
        scoreMsg.style.display = 'block';
        scoreMsg.textContent   = '\u2713 Score submitted!';
      }
      if (scoreForm) scoreForm.style.display = 'none';
    })
    .catch(function () {
      if (scoreMsg) {
        scoreMsg.style.display = 'block';
        scoreMsg.textContent   = 'Could not submit score.';
      }
    });
  }

  // ─── Initialisation ───────────────────────────────────────────────────────────
  function initGame(dateStr) {
    puzzleDate = dateStr;
    gameWon    = false;
    selected   = null;
    removedPairs = [];
    hintMode   = '';
    elapsedMs  = 0;
    startTime  = null;
    clearInterval(timerInterval);
    timerInterval = null;

    var rng       = makeLCG(seedFromDate(dateStr));
    var faceArray = generateBoard(rng);
    currentHash   = boardHash(faceArray);

    tiles = faceArray.map(function (face, i) {
      return {
        id:      i,
        x:       TURTLE[i][0],
        y:       TURTLE[i][1],
        z:       TURTLE[i][2],
        face:    face,
        removed: false,
        el:      null
      };
    });

    if (timeEl) timeEl.textContent = '0.0';
    if (winMsg) winMsg.style.display = 'none';
    if (timerWrap) timerWrap.style.display = '';
    if (scoreForm) scoreForm.style.display = 'none';
    if (scoreMsg) scoreMsg.style.display = 'none';
    if (submitBtn) submitBtn.disabled = false;

    renderBoard();
    updateBoardWidth();
    renderRemovedPairs();
  }

  // ─── Entry point ─────────────────────────────────────────────────────────────
  window.addEventListener('load', function () {
    puzzleDate = window.MAHJONG_DATE  || new Date().toISOString().slice(0, 10);
    userName   = window.MAHJONG_USER  || '';

    boardEl    = document.getElementById('mj-board');
    removedEl  = document.getElementById('mj-removed');
    timeEl     = document.getElementById('mj-time');
    timerWrap  = document.getElementById('mj-timer-wrap');
    winMsg     = document.getElementById('mj-win-msg');
    scoreForm  = document.getElementById('mj-score-form');
    nameEl     = document.getElementById('mj-name');
    submitBtn  = document.getElementById('mj-submit');
    scoreMsg   = document.getElementById('mj-score-msg');
    undoBtn    = document.getElementById('mj-undo');
    hintFreeBtn  = document.getElementById('mj-hint-free');
    hintMatchBtn = document.getElementById('mj-hint-match');

    if (undoBtn)      undoBtn.addEventListener('click',      undoMove);
    if (hintFreeBtn)  hintFreeBtn.addEventListener('click',  showFreeTiles);
    if (hintMatchBtn) hintMatchBtn.addEventListener('click', showMatches);
    if (submitBtn) {
      submitBtn.addEventListener('click', function () {
        var n = nameEl ? nameEl.value.trim() : '';
        if (!n) { if (nameEl) nameEl.focus(); return; }
        doSubmit(n);
      });
    }
    document.getElementById('mj-reset') &&
      document.getElementById('mj-reset').addEventListener('click', function () {
        initGame(puzzleDate);
      });

    initGame(puzzleDate);
  });

}());
