/**
 * fifteen_puzzle_generator.js
 * Generator page logic: scramble a 4x4 board, preview with uploaded photo,
 * and submit to /api/fifteen-puzzle/upload-photo.
 */
(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Board hash: base64url encode [width, height, ...tiles]
  // For 4x4: 18 bytes — 2 for dimensions + 16 for tiles
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
  // PRNG — crypto random for generator (not seeded by date)
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
    var rowFromBottom = cols - blankRow; // cols == rows for square
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
      // flip parity by swapping first two non-blank tiles
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
  var currentObjectURL = null;
  var currentPhotoMode = 'tiles';

  // ---------------------------------------------------------------------------
  // Render preview board
  // ---------------------------------------------------------------------------
  function renderPreview() {
    var board = document.getElementById('gen-board');
    if (!board) return;
    board.innerHTML = '';
    board.style.display = 'grid';
    board.style.gridTemplateColumns = 'repeat(' + COLS + ', 1fr)';

    var imgSrc = currentObjectURL;

    for (var i = 0; i < tiles.length; i++) {
      var cell = document.createElement('div');
      cell.classList.add('fp-tile');

      if (tiles[i] === 0) {
        cell.classList.add('fp-blank');
      } else if (imgSrc && currentPhotoMode === 'tiles') {
        // show the slice of the image for this tile position
        var tileNum = tiles[i] - 1; // 0-based solved position
        var solvedCol = tileNum % COLS;
        var solvedRow = Math.floor(tileNum / COLS);
        cell.style.backgroundImage = 'url(' + imgSrc + ')';
        cell.style.backgroundSize = (COLS * 100) + '% ' + (ROWS * 100) + '%';
        cell.style.backgroundPosition =
          (solvedCol / (COLS - 1) * 100) + '% ' + (solvedRow / (ROWS - 1) * 100) + '%';
        cell.style.backgroundRepeat = 'no-repeat';
        cell.style.border = '2px solid rgba(255,255,255,0.3)';
        // small number overlay
        var num = document.createElement('span');
        num.textContent = tiles[i];
        num.style.cssText = 'position:absolute;bottom:3px;right:5px;font-size:0.65rem;opacity:0.7;color:#fff;text-shadow:0 1px 2px #000;';
        cell.style.position = 'relative';
        cell.appendChild(num);
      } else if (imgSrc && currentPhotoMode === 'reveal') {
        // solid tiles with number, image hidden until win
        cell.textContent = tiles[i];
        cell.style.background = 'var(--surface)';
      } else {
        cell.textContent = tiles[i];
      }

      board.appendChild(cell);
    }

    // update hash display
    var hash = boardToHash(COLS, ROWS, tiles);
    var hashEl = document.getElementById('gen-hash');
    if (hashEl) hashEl.value = hash;
  }

  // ---------------------------------------------------------------------------
  // Scramble button
  // ---------------------------------------------------------------------------
  function scramble() {
    tiles = generateScramble(COLS, ROWS);
    renderPreview();
  }

  // ---------------------------------------------------------------------------
  // Photo mode toggle
  // ---------------------------------------------------------------------------
  function setPhotoMode(mode) {
    currentPhotoMode = mode;
    document.querySelectorAll('.gen-mode-btn').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.mode === mode);
    });
    renderPreview();
    var modeInput = document.getElementById('gen-photo-mode');
    if (modeInput) modeInput.value = mode;
  }

  // ---------------------------------------------------------------------------
  // File input preview
  // ---------------------------------------------------------------------------
  function onFileChange(e) {
    var file = e.target.files[0];
    if (!file) return;

    // Validate type and size client-side for fast feedback
    if (!['image/jpeg', 'image/png'].includes(file.type)) {
      alert('Please select a JPG or PNG file.');
      e.target.value = '';
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      alert('File is too large. Maximum size is 2MB.');
      e.target.value = '';
      return;
    }

    if (currentObjectURL) URL.revokeObjectURL(currentObjectURL);
    currentObjectURL = URL.createObjectURL(file);
    renderPreview();
  }

  // ---------------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------------
  function onSubmit(e) {
    e.preventDefault();
    var form = document.getElementById('gen-form');
    var fileInput = document.getElementById('gen-file');
    var msgEl = document.getElementById('gen-msg');
    var submitBtn = document.getElementById('gen-submit');

    if (!fileInput || !fileInput.files[0]) {
      if (msgEl) { msgEl.textContent = 'Please select an image first.'; msgEl.style.color = 'var(--danger, #e55)'; }
      return;
    }

    var hash = boardToHash(COLS, ROWS, tiles);
    var hashInput = document.getElementById('gen-hash-hidden');
    if (hashInput) hashInput.value = hash;

    var formData = new FormData(form);

    if (submitBtn) submitBtn.disabled = true;
    if (msgEl) { msgEl.textContent = 'Uploading…'; msgEl.style.color = 'var(--text-dim)'; }

    fetch('/api/fifteen-puzzle/upload-photo', {
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

        var linkBox = document.getElementById('gen-link-box');
        var linkUrlEl = document.getElementById('gen-link-url');
        var copyBtn = document.getElementById('gen-copy-btn');

        if (linkBox && linkUrlEl) {
          linkUrlEl.textContent = fullUrl;
          linkBox.style.display = 'flex';
          // scroll link box into view
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
  // Delete saved puzzle
  // ---------------------------------------------------------------------------
  function onDeletePhoto(boardHash) {
    if (!confirm('Delete this puzzle permanently?')) return;
    fetch('/api/fifteen-puzzle/delete-photo/' + boardHash, {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
      .then(function (res) {
        if (!res.ok) throw new Error('Delete failed');
        window.location.reload();
      })
      .catch(function (err) {
        alert(err.message);
      });
  }
  window.fpDeletePhoto = onDeletePhoto;

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  function init() {
    // Generate initial scramble
    scramble();

    // Scramble button
    var scrambleBtn = document.getElementById('gen-scramble');
    if (scrambleBtn) scrambleBtn.addEventListener('click', scramble);

    // File input
    var fileInput = document.getElementById('gen-file');
    if (fileInput) fileInput.addEventListener('change', onFileChange);

    // Photo mode buttons
    document.querySelectorAll('.gen-mode-btn').forEach(function (btn) {
      btn.addEventListener('click', function () { setPhotoMode(btn.dataset.mode); });
    });
    // Set initial active state
    setPhotoMode('tiles');

    // Form submit
    var form = document.getElementById('gen-form');
    if (form) form.addEventListener('submit', onSubmit);
  }

  window.addEventListener('DOMContentLoaded', init);
})();
