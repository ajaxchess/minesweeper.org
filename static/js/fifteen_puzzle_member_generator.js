/**
 * fifteen_puzzle_member_generator.js
 * Member Generator: dual-image 15-puzzle — tile image + reveal image.
 * Posts to /api/fifteen-puzzle/upload-member (no login required).
 */
(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Board hash: base64url encode [width, height, ...tiles]
  // ---------------------------------------------------------------------------
  function boardToHash(cols, rows, tiles) {
    var bytes = new Uint8Array(2 + tiles.length);
    bytes[0] = cols;
    bytes[1] = rows;
    for (var i = 0; i < tiles.length; i++) bytes[i + 2] = tiles[i];
    var bin = String.fromCharCode.apply(null, bytes);
    return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
  }

  // ---------------------------------------------------------------------------
  // PRNG
  // ---------------------------------------------------------------------------
  function randomShuffle(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
    }
    return a;
  }

  function countInversions(tiles) {
    var c = 0;
    for (var i = 0; i < tiles.length; i++) {
      if (tiles[i] === 0) continue;
      for (var j = i + 1; j < tiles.length; j++) {
        if (tiles[j] !== 0 && tiles[i] > tiles[j]) c++;
      }
    }
    return c;
  }

  function isSolvable(tiles, cols) {
    var inv = countInversions(tiles);
    var blankRow = Math.floor(tiles.indexOf(0) / cols);
    var rowFromBottom = cols - blankRow;
    return (inv + rowFromBottom) % 2 === 1;
  }

  function generateScramble(cols, rows) {
    var n = cols * rows;
    var base = [];
    for (var i = 1; i < n; i++) base.push(i);
    base.push(0);

    var tiles;
    var tries = 0;
    do {
      tiles = randomShuffle(base);
      tries++;
    } while (!isSolvable(tiles, cols) && tries < 200);

    if (!isSolvable(tiles, cols)) {
      var a = tiles[0] === 0 ? 1 : 0;
      var b = tiles[a + 1] === 0 ? a + 2 : a + 1;
      var tmp = tiles[a]; tiles[a] = tiles[b]; tiles[b] = tmp;
    }
    return tiles;
  }

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  var COLS = 4, ROWS = 4;
  var tiles = [];
  var tileObjectURL = null;

  // ---------------------------------------------------------------------------
  // Render preview board using tile image
  // ---------------------------------------------------------------------------
  function renderPreview() {
    var board = document.getElementById('gen-board');
    if (!board) return;
    board.innerHTML = '';
    board.style.display = 'grid';
    board.style.gridTemplateColumns = 'repeat(' + COLS + ', 1fr)';

    for (var i = 0; i < tiles.length; i++) {
      var cell = document.createElement('div');
      cell.classList.add('fp-tile');

      if (tiles[i] === 0) {
        cell.classList.add('fp-blank');
      } else if (tileObjectURL) {
        var tileNum = tiles[i] - 1;
        var solvedCol = tileNum % COLS;
        var solvedRow = Math.floor(tileNum / COLS);
        cell.style.backgroundImage    = 'url(' + tileObjectURL + ')';
        cell.style.backgroundSize     = (COLS * 100) + '% ' + (ROWS * 100) + '%';
        cell.style.backgroundPosition =
          (solvedCol / (COLS - 1) * 100) + '% ' + (solvedRow / (ROWS - 1) * 100) + '%';
        cell.style.backgroundRepeat   = 'no-repeat';
        cell.style.border             = '2px solid rgba(255,255,255,0.3)';
        var num = document.createElement('span');
        num.textContent = tiles[i];
        num.style.cssText = 'position:absolute;bottom:3px;right:5px;font-size:0.65rem;opacity:0.7;color:#fff;text-shadow:0 1px 2px #000;';
        cell.style.position = 'relative';
        cell.appendChild(num);
      } else {
        cell.textContent = tiles[i];
      }

      board.appendChild(cell);
    }
  }

  // ---------------------------------------------------------------------------
  // Scramble
  // ---------------------------------------------------------------------------
  function scramble() {
    tiles = generateScramble(COLS, ROWS);
    renderPreview();
  }

  // ---------------------------------------------------------------------------
  // File validation helper
  // ---------------------------------------------------------------------------
  function validateImageFile(file, label) {
    if (!file) return 'Please select a ' + label + ' image.';
    if (!['image/jpeg', 'image/png'].includes(file.type))
      return label + ' image must be JPG or PNG.';
    if (file.size > 2 * 1024 * 1024)
      return label + ' image is too large (max 2 MB).';
    return null;
  }

  // ---------------------------------------------------------------------------
  // File input handlers
  // ---------------------------------------------------------------------------
  function onTileFileChange(e) {
    var file = e.target.files[0];
    var err = validateImageFile(file, 'Tile');
    if (err) { alert(err); e.target.value = ''; return; }
    if (tileObjectURL) URL.revokeObjectURL(tileObjectURL);
    tileObjectURL = URL.createObjectURL(file);
    renderPreview();
  }

  function onRevealFileChange(e) {
    var file = e.target.files[0];
    var err = validateImageFile(file, 'Reveal');
    if (err) { alert(err); e.target.value = ''; return; }
    var preview = document.getElementById('gen-reveal-preview');
    if (preview) {
      preview.src = URL.createObjectURL(file);
      preview.style.display = 'block';
    }
  }

  // ---------------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------------
  function onSubmit(e) {
    e.preventDefault();
    var tileInput   = document.getElementById('gen-tile-file');
    var revealInput = document.getElementById('gen-reveal-file');
    var msgEl       = document.getElementById('gen-msg');
    var submitBtn   = document.getElementById('gen-submit');

    var tileErr   = validateImageFile(tileInput && tileInput.files[0],   'Tile');
    var revealErr = validateImageFile(revealInput && revealInput.files[0], 'Reveal');
    if (tileErr || revealErr) {
      if (msgEl) { msgEl.textContent = tileErr || revealErr; msgEl.style.color = 'var(--danger, #e55)'; }
      return;
    }

    var hash = boardToHash(COLS, ROWS, tiles);
    var hashInput = document.getElementById('gen-hash-hidden');
    if (hashInput) hashInput.value = hash;

    var formData = new FormData(document.getElementById('gen-form'));

    if (submitBtn) submitBtn.disabled = true;
    if (msgEl) { msgEl.textContent = 'Uploading…'; msgEl.style.color = 'var(--text-dim)'; }

    fetch('/api/fifteen-puzzle/upload-member', {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      body: formData,
    })
      .then(function (res) {
        if (!res.ok) return res.json().then(function (d) { throw new Error(d.detail || 'Upload failed'); });
        return res.json();
      })
      .then(function (data) {
        if (submitBtn) submitBtn.disabled = false;
        var fullUrl = window.location.origin + data.url;

        var linkBox   = document.getElementById('gen-link-box');
        var linkUrlEl = document.getElementById('gen-link-url');
        var copyBtn   = document.getElementById('gen-copy-btn');

        if (linkBox && linkUrlEl) {
          linkUrlEl.textContent = fullUrl;
          linkBox.style.display = 'flex';
          linkBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }

        if (copyBtn) {
          copyBtn.onclick = function () {
            navigator.clipboard.writeText(fullUrl).then(function () {
              copyBtn.textContent = 'Copied!';
              copyBtn.classList.add('copied');
              setTimeout(function () {
                copyBtn.textContent = 'Copy';
                copyBtn.classList.remove('copied');
              }, 2000);
            });
          };
        }

        if (msgEl) { msgEl.textContent = ''; }
      })
      .catch(function (err) {
        if (msgEl) { msgEl.textContent = err.message; msgEl.style.color = 'var(--danger, #e55)'; }
        if (submitBtn) submitBtn.disabled = false;
      });
  }

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  function init() {
    scramble();

    var scrambleBtn = document.getElementById('gen-scramble');
    if (scrambleBtn) scrambleBtn.addEventListener('click', scramble);

    var tileInput = document.getElementById('gen-tile-file');
    if (tileInput) tileInput.addEventListener('change', onTileFileChange);

    var revealInput = document.getElementById('gen-reveal-file');
    if (revealInput) revealInput.addEventListener('change', onRevealFileChange);

    var form = document.getElementById('gen-form');
    if (form) form.addEventListener('submit', onSubmit);
  }

  window.addEventListener('DOMContentLoaded', init);
})();
