/* bootcamp_replay.js — Annotated replay playback (F-BC-REPLAY)
 *
 * Module layout (reusable for F-EMBED Phase 6):
 *   MinesweeperReplayBoard  — board state tracker + DOM renderer
 *   ReplayPlayback          — play/pause/step/scrub clock
 *   AnnotationRail          — filtering + per-insight DOM management
 *   page glue               — fetch, wire up, render stat strip
 */
(function () {
  'use strict';

  var CFG  = window.REPLAY_CONFIG || {};
  var api  = CFG.apiBase || '/api';
  var copy = CFG.copy    || {};
  var replayId = CFG.gameReplayId;

  /* ── Utilities ───────────────────────────────────────────── */
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function fmtDuration(ms) {
    if (ms == null) return '—';
    var s = Math.round(ms / 1000);
    var m = Math.floor(s / 60);
    var sec = s % 60;
    return m > 0 ? m + ':' + (sec < 10 ? '0' : '') + sec : sec + 's';
  }
  function fmtSec(ms) {
    return ms != null ? (ms / 1000).toFixed(1) + 's' : '—';
  }
  function pct(v) { return v != null ? Math.round(v) + '%' : '—'; }
  function fix2(v) { return v != null ? v.toFixed(2) : '—'; }

  /* ── Badge color map ─────────────────────────────────────── */
  var BADGE_COLOR = {
    wasted:    '#f59e0b',
    shortcut:  '#8b5cf6',
    opening:   '#2563eb',
    fish:      '#06b6d4',
    flagval:   '#f97316',
    hierarchy: '#6366f1',
    death:     '#ef4444',
  };

  /* ────────────────────────────────────────────────────────────
   * MinesweeperReplayBoard
   * Tracks cell state (unrevealed / revealed / flagged / mine)
   * and renders a Win95-style board grid.
   * ─────────────────────────────────────────────────────────── */
  function MinesweeperReplayBoard(containerEl, width, height) {
    this.w = width;
    this.h = height;
    this.container = containerEl;
    /* state[y][x]: 'u'=unrevealed, 'r'=revealed, 'f'=flagged, 'm'=mine */
    this.state = [];
    this.cellEls = [];
    this._init();
  }

  MinesweeperReplayBoard.prototype._init = function () {
    var w = this.w, h = this.h;
    for (var y = 0; y < h; y++) {
      this.state[y] = [];
      this.cellEls[y] = [];
      for (var x = 0; x < w; x++) {
        this.state[y][x] = 'u';
        this.cellEls[y][x] = null;
      }
    }
    this.container.style.gridTemplateColumns = 'repeat(' + w + ', 28px)';

    for (var yi = 0; yi < h; yi++) {
      for (var xi = 0; xi < w; xi++) {
        var el = document.createElement('div');
        el.className = 'br-cell br-cell--unrevealed';
        el.dataset.x = xi;
        el.dataset.y = yi;
        this.container.appendChild(el);
        this.cellEls[yi][xi] = el;
      }
    }
  };

  MinesweeperReplayBoard.prototype.reset = function () {
    for (var y = 0; y < this.h; y++) {
      for (var x = 0; x < this.w; x++) {
        this.state[y][x] = 'u';
        var el = this.cellEls[y][x];
        el.className = 'br-cell br-cell--unrevealed';
        el.textContent = '';
      }
    }
  };

  MinesweeperReplayBoard.prototype.applyMove = function (move) {
    var x = move.x, y = move.y, action = move.action;
    if (x < 0 || x >= this.w || y < 0 || y >= this.h) return;

    var st = this.state[y][x];
    if (action === 'l' || action === 'c') {
      if (st !== 'f') {
        this.state[y][x] = 'r';
        var el = this.cellEls[y][x];
        el.className = 'br-cell br-cell--revealed';
        el.textContent = '';
      }
    } else if (action === 'r') {
      if (st === 'u') {
        this.state[y][x] = 'f';
        var fe = this.cellEls[y][x];
        fe.className = 'br-cell br-cell--flagged';
        fe.textContent = '🚩';
      } else if (st === 'f') {
        this.state[y][x] = 'u';
        var ue = this.cellEls[y][x];
        ue.className = 'br-cell br-cell--unrevealed';
        ue.textContent = '';
      }
    }
  };

  MinesweeperReplayBoard.prototype.setCursor = function (x, y, prevX, prevY) {
    if (prevX != null && prevX >= 0 && prevX < this.w && prevY >= 0 && prevY < this.h) {
      var prevEl = this.cellEls[prevY][prevX];
      prevEl.classList.remove('br-cell--cursor');
    }
    if (x >= 0 && x < this.w && y >= 0 && y < this.h) {
      this.cellEls[y][x].classList.add('br-cell--cursor');
    }
  };

  MinesweeperReplayBoard.prototype.clearAnnotDots = function () {
    var dots = this.container.querySelectorAll('.br-annot-dot');
    for (var i = 0; i < dots.length; i++) { dots[i].remove(); }
  };

  MinesweeperReplayBoard.prototype.showAnnotDots = function (annotations, upToMove) {
    this.clearAnnotDots();
    for (var i = 0; i < annotations.length; i++) {
      var a = annotations[i];
      if (a.move_index > upToMove) continue;
      var x = a.cell_x, y = a.cell_y;
      if (x < 0 || x >= this.w || y < 0 || y >= this.h) continue;
      var dot = document.createElement('div');
      dot.className = 'br-annot-dot br-annot-dot--' + a.badge;
      dot.textContent = a.annotation_number;
      this.cellEls[y][x].appendChild(dot);
    }
  };

  /* ────────────────────────────────────────────────────────────
   * ReplayPlayback
   * Controls play/pause/step and emits onMove(moveIndex) callbacks.
   * ─────────────────────────────────────────────────────────── */
  function ReplayPlayback(moveLog, onMove) {
    this.moves = moveLog;
    this.onMove = onMove;
    this.current = 0;
    this.playing = false;
    this._timer = null;
    this.speed = 1.0;
  }

  ReplayPlayback.prototype.play = function () {
    if (this.playing) return;
    if (this.current >= this.moves.length - 1) { this.current = 0; this.onMove(0); }
    this.playing = true;
    this._tick();
  };

  ReplayPlayback.prototype._tick = function () {
    var self = this;
    if (!self.playing || self.current >= self.moves.length - 1) {
      self.playing = false;
      return;
    }
    var curr = self.moves[self.current];
    var next = self.moves[self.current + 1];
    var delay = next ? Math.max(30, (next.t_ms - curr.t_ms) / self.speed) : 300;
    delay = Math.min(delay, 1000); /* cap inter-move gap at 1 s regardless of real time */
    self._timer = setTimeout(function () {
      self.current += 1;
      self.onMove(self.current);
      self._tick();
    }, delay);
  };

  ReplayPlayback.prototype.pause = function () {
    this.playing = false;
    clearTimeout(this._timer);
  };

  ReplayPlayback.prototype.stepBack = function () {
    this.pause();
    if (this.current > 0) { this.current -= 1; this.onMove(this.current); }
  };

  ReplayPlayback.prototype.stepFwd = function () {
    this.pause();
    if (this.current < this.moves.length - 1) { this.current += 1; this.onMove(this.current); }
  };

  ReplayPlayback.prototype.seekTo = function (idx) {
    this.pause();
    this.current = Math.max(0, Math.min(idx, this.moves.length - 1));
    this.onMove(this.current);
  };

  ReplayPlayback.prototype.restart = function () {
    this.pause();
    this.current = 0;
    this.onMove(0);
  };

  /* ────────────────────────────────────────────────────────────
   * AnnotationRail
   * Renders the insight list and tracks the active filter.
   * ─────────────────────────────────────────────────────────── */
  function AnnotationRail(listEl, insights, annotations, onSeek) {
    this.listEl = listEl;
    this.insights = insights;
    this.annotations = annotations; /* ReplayAnnotation[] — for move_index lookup */
    this.onSeek = onSeek;
    this.filter = 'all';
    this.activeNum = null;
  }

  AnnotationRail.prototype.setFilter = function (badge) {
    this.filter = badge;
    this._render();
  };

  AnnotationRail.prototype._render = function () {
    var self = this;
    var visible = this.insights.filter(function (i) {
      return self.filter === 'all' || i.severity === self.filter;
    });

    if (visible.length === 0) {
      this.listEl.innerHTML = '<li class="br-rail-none">' + esc(copy.noAnnotations || 'No annotations match this filter.') + '</li>';
      return;
    }

    var annByNum = {};
    for (var i = 0; i < this.annotations.length; i++) {
      annByNum[this.annotations[i].annotation_number] = this.annotations[i];
    }

    this.listEl.innerHTML = visible.map(function (ins) {
      var ann = annByNum[ins.annotation_number] || {};
      var badge = ann.badge || ins.severity;
      var numCls = 'br-rail-num--' + badge;
      var activeCls = self.activeNum === ins.annotation_number ? ' active' : '';

      var linksHtml = '';
      if (ins.drill_id) {
        linksHtml += '<a class="br-rail-item-link" href="/drill/start?drill_type=' + esc(ins.drill_id) + '" data-drill-id="' + esc(ins.drill_id) + '">' + esc(copy.drillCta || 'Drill this →') + '</a>';
      }
      if (ins.citation_url) {
        linksHtml += '<a class="br-rail-item-link" href="' + esc(ins.citation_url) + '" target="_blank" rel="noopener">' + esc(copy.learnMore || 'Learn more →') + '</a>';
      }

      return [
        '<li class="br-rail-item' + activeCls + '" data-annot-num="' + ins.annotation_number + '" data-move-index="' + (ann.move_index != null ? ann.move_index : 0) + '">',
          '<div class="br-rail-num ' + numCls + '">' + ins.annotation_number + '</div>',
          '<div class="br-rail-body">',
            '<div class="br-rail-item-title">' + esc(ins.title) + '</div>',
            '<div class="br-rail-item-body">' + esc(ins.body) + '</div>',
            linksHtml ? '<div class="br-rail-item-links">' + linksHtml + '</div>' : '',
          '</div>',
        '</li>',
      ].join('');
    }).join('');

    /* Bind click-to-seek */
    var items = this.listEl.querySelectorAll('.br-rail-item[data-move-index]');
    for (var j = 0; j < items.length; j++) {
      items[j].addEventListener('click', function (e) {
        /* Don't intercept link clicks */
        if (e.target.tagName === 'A') return;
        var mi = parseInt(this.dataset.moveIndex, 10);
        if (!isNaN(mi)) self.onSeek(mi);
      });
    }
  };

  AnnotationRail.prototype.highlightMove = function (moveIndex) {
    /* Find the annotation number(s) at this move */
    var num = null;
    for (var i = 0; i < this.annotations.length; i++) {
      if (this.annotations[i].move_index === moveIndex) {
        num = this.annotations[i].annotation_number; break;
      }
    }
    if (num === this.activeNum) return;
    this.activeNum = num;

    var items = this.listEl.querySelectorAll('.br-rail-item');
    for (var j = 0; j < items.length; j++) {
      var annotNum = parseInt(items[j].dataset.annotNum, 10);
      if (annotNum === num) {
        items[j].classList.add('active');
        items[j].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      } else {
        items[j].classList.remove('active');
      }
    }
  };

  /* ────────────────────────────────────────────────────────────
   * Page glue
   * ─────────────────────────────────────────────────────────── */

  var elLoading   = document.getElementById('br-loading');
  var elContainer = document.getElementById('br-container');

  function showLoading() { if (elLoading) elLoading.hidden = false; }
  function hideLoading() { if (elLoading) elLoading.hidden = true; }

  function showError(title, body) {
    hideLoading();
    elContainer.innerHTML = [
      '<div class="br-state-box">',
        '<h2>' + esc(title) + '</h2>',
        '<p>' + esc(body) + '</p>',
      '</div>',
    ].join('');
  }

  function fmtDate(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    return d.toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' });
  }

  function buildStatStrip(data) {
    var stats = [
      { label: 'Time',       value: fmtDuration(data.duration_ms),                meta: data.difficulty + ' · ' + data.mode },
      { label: '3BV/s',      value: fix2(data.three_bv_per_sec),                  meta: data.three_bv + ' 3BV' },
      { label: 'IOE',        value: fix2(data.ioe),                               meta: 'target 0.85+' },
      { label: 'Correctness',value: pct(data.correctness != null ? data.correctness * 100 : null), meta: '' },
      { label: 'Hierarchy',  value: pct(data.hierarchy_compliance_pct),           meta: 'target 88%+' },
      { label: 'Openings',   value: data.openings_taken + '/' + (data.openings_taken + data.openings_missed), meta: 'taken/available' },
      { label: 'Wasted',     value: data.wasted_clicks,                           meta: 'zero-progress clicks' },
    ];
    return '<div class="br-stats">' + stats.map(function (s) {
      return [
        '<div class="br-stat">',
          '<div class="br-stat-label">' + esc(s.label) + '</div>',
          '<div class="br-stat-value">' + esc(s.value) + '</div>',
          s.meta ? '<div class="br-stat-meta">' + esc(s.meta) + '</div>' : '',
        '</div>',
      ].join('');
    }).join('') + '</div>';
  }

  function buildFilterBar() {
    var filters = [
      { key: 'all',       label: copy.filterAll       || 'All' },
      { key: 'wasted',    label: copy.filterWasted     || 'Wasted' },
      { key: 'shortcut',  label: copy.filterShortcut   || 'Shortcuts' },
      { key: 'opening',   label: copy.filterOpening    || 'Openings' },
      { key: 'fish',      label: copy.filterFish       || 'Fishing' },
      { key: 'flagval',   label: copy.filterFlagval    || 'Flag value' },
      { key: 'hierarchy', label: copy.filterHierarchy  || 'Hierarchy' },
    ];
    return '<div class="br-filters">' + filters.map(function (f) {
      var dot = f.key !== 'all' && BADGE_COLOR[f.key]
        ? '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:' + BADGE_COLOR[f.key] + ';margin-right:4px;vertical-align:middle"></span>'
        : '';
      return '<button class="br-filter-chip' + (f.key === 'all' ? ' active' : '') + '" data-filter="' + f.key + '">' + dot + esc(f.label) + '</button>';
    }).join('') + '</div>';
  }

  function buildPage(data) {
    hideLoading();

    var outcomeCls = 'br-outcome-pill--' + (data.outcome || 'abandon');
    var outcomeLabel = copy[data.outcome] || data.outcome || '—';
    var modeLabel = data.mode === 'no_guess' ? 'No-Guess' : 'Standard';

    /* Inject layout HTML */
    elContainer.innerHTML = [
      '<div class="br-title-row">',
        '<h1>' + esc(data.difficulty || 'Expert') + ' · ' + esc(modeLabel) + ' · Replay #' + esc(data.game_replay_id) + '</h1>',
        '<span class="br-outcome-pill ' + outcomeCls + '">' + esc(outcomeLabel) + '</span>',
      '</div>',
      buildStatStrip(data),
      '<div class="br-grid">',
        /* Board column */
        '<div class="br-board-card">',
          '<div class="br-board-wrap"><div id="br-board"></div></div>',
          '<div class="br-playback" id="br-playback">',
            '<button id="br-btn-restart" class="br-step-btn" title="' + esc(copy.restart || 'Restart') + '">⟵</button>',
            '<button id="br-btn-back"    class="br-step-btn">' + esc(copy.stepBack || '◀ Step') + '</button>',
            '<button id="br-btn-play"    class="br-play-btn">▶</button>',
            '<button id="br-btn-fwd"     class="br-step-btn">' + esc(copy.stepFwd || 'Step ▶') + '</button>',
            '<div class="br-scrub-wrap">',
              '<div id="br-scrub-track" class="br-scrub-track">',
                '<div id="br-scrub-fill"  class="br-scrub-fill"></div>',
                '<div id="br-scrub-thumb" class="br-scrub-thumb"></div>',
              '</div>',
            '</div>',
            '<span id="br-move-counter" class="br-move-counter">—</span>',
            '<select id="br-speed-sel" class="br-speed-sel">',
              '<option value="0.25">0.25×</option>',
              '<option value="0.5">0.5×</option>',
              '<option value="1" selected>1×</option>',
              '<option value="2">2×</option>',
              '<option value="4">4×</option>',
            '</select>',
          '</div>',
        '</div>',
        /* Rail column */
        '<div class="br-rail-card">',
          '<div class="br-rail-header">',
            '<div class="br-rail-title">' + esc(copy.annotTitle || 'Coaching notes') + '</div>',
            buildFilterBar(),
          '</div>',
          '<ul id="br-rail-list" class="br-rail-list"></ul>',
        '</div>',
      '</div>',
    ].join('');

    /* ── Wire up board ─────────────────────────────────────── */
    var boardEl = document.getElementById('br-board');
    var board   = new MinesweeperReplayBoard(boardEl, data.board_width, data.board_height);

    /* Place annotation markers on scrub track */
    var trackEl  = document.getElementById('br-scrub-track');
    var fillEl   = document.getElementById('br-scrub-fill');
    var thumbEl  = document.getElementById('br-scrub-thumb');
    var total    = data.move_log.length;

    data.annotations.forEach(function (a) {
      var pctPos = total > 1 ? (a.move_index / (total - 1)) * 100 : 0;
      var mark = document.createElement('div');
      mark.className = 'br-scrub-mark br-scrub-mark--' + a.badge;
      mark.style.left = pctPos + '%';
      trackEl.appendChild(mark);
    });

    /* Board state rebuild (replay up to index) — we keep a snapshot array */
    var snapshots = []; /* snapshots[i] = state after move i applied */
    /* We rebuild incrementally during playback; on seek we replay from 0 */

    var prevCursorX = null, prevCursorY = null;

    function applyMoveIndex(idx) {
      /* Rebuild board from move 0..idx */
      board.reset();
      prevCursorX = null; prevCursorY = null;
      for (var m = 0; m <= idx && m < data.move_log.length; m++) {
        board.applyMove(data.move_log[m]);
      }
      var move = data.move_log[idx] || {};
      board.setCursor(move.x, move.y, null, null);
      board.showAnnotDots(data.annotations, idx);

      /* Update scrub bar */
      var p = total > 1 ? (idx / (total - 1)) * 100 : 0;
      fillEl.style.width  = p + '%';
      thumbEl.style.left  = p + '%';

      /* Update counter */
      var counterEl = document.getElementById('br-move-counter');
      if (counterEl) {
        var tpl = copy.moveOf || 'Move {current} of {total}';
        counterEl.innerHTML = tpl
          .replace('{current}', '<strong>' + (idx + 1) + '</strong>')
          .replace('{total}',   total);
      }

      /* Update play button */
      var playBtn = document.getElementById('br-btn-play');
      if (playBtn) playBtn.textContent = playback.playing ? '⏸' : '▶';

      /* Highlight rail */
      rail.highlightMove(idx);
    }

    /* ── Wire up annotation rail ────────────────────────────── */
    var railListEl = document.getElementById('br-rail-list');
    var rail = new AnnotationRail(railListEl, data.insights, data.annotations, function (moveIdx) {
      playback.seekTo(moveIdx);
    });
    rail._render();

    /* ── Wire up playback ───────────────────────────────────── */
    var playback = new ReplayPlayback(data.move_log, function (idx) {
      applyMoveIndex(idx);
      /* Update play btn */
      var playBtn = document.getElementById('br-btn-play');
      if (playBtn) playBtn.textContent = playback.playing ? '⏸' : '▶';
    });

    /* Init board at move 0 */
    applyMoveIndex(0);

    /* Play/Pause */
    document.getElementById('br-btn-play').addEventListener('click', function () {
      if (playback.playing) { playback.pause(); this.textContent = '▶'; }
      else                  { playback.play();  this.textContent = '⏸'; }
    });
    document.getElementById('br-btn-back').addEventListener('click', function () {
      playback.stepBack();
    });
    document.getElementById('br-btn-fwd').addEventListener('click', function () {
      playback.stepFwd();
    });
    document.getElementById('br-btn-restart').addEventListener('click', function () {
      playback.restart();
      var playBtn = document.getElementById('br-btn-play');
      if (playBtn) playBtn.textContent = '▶';
    });
    document.getElementById('br-speed-sel').addEventListener('change', function () {
      playback.speed = parseFloat(this.value) || 1;
    });

    /* Scrub bar click/drag */
    (function () {
      function seekFromEvent(e) {
        var rect = trackEl.getBoundingClientRect();
        var x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
        var ratio = Math.max(0, Math.min(1, x / rect.width));
        var idx = Math.round(ratio * (total - 1));
        playback.seekTo(idx);
      }
      var dragging = false;
      trackEl.addEventListener('mousedown',  function (e) { dragging = true; seekFromEvent(e); });
      trackEl.addEventListener('touchstart', function (e) { dragging = true; seekFromEvent(e); }, { passive: true });
      document.addEventListener('mousemove',  function (e) { if (dragging) seekFromEvent(e); });
      document.addEventListener('touchmove',  function (e) { if (dragging) seekFromEvent(e); }, { passive: true });
      document.addEventListener('mouseup',   function () { dragging = false; });
      document.addEventListener('touchend',  function () { dragging = false; });
    }());

    /* Filter chips */
    var chips = elContainer.querySelectorAll('.br-filter-chip');
    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        chips.forEach(function (c) { c.classList.remove('active'); });
        chip.classList.add('active');
        rail.setFilter(chip.dataset.filter);
      });
    });
  }

  /* ── Fetch ───────────────────────────────────────────────── */
  fetch(api + '/replays/' + replayId, {
    credentials: 'same-origin',
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
  })
  .then(function (r) {
    if (r.status === 404 || r.status === 403) {
      showError(copy.errorTitle || 'Couldn\'t load this replay', copy.errorBody || 'The replay may not exist or you may not have access.');
      return null;
    }
    if (r.status === 425) {
      showError(copy.pendingTitle || 'Analysis in progress', copy.pendingBody || 'This game is queued for analysis. Check back in a few minutes.');
      return null;
    }
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  })
  .then(function (data) {
    if (!data) return;
    buildPage(data);
  })
  .catch(function (err) {
    console.error('[replay]', err);
    showError(copy.errorTitle || 'Couldn\'t load this replay', copy.errorBody || 'Something went wrong.');
  });

}());
