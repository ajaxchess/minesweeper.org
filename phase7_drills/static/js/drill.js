/**
 * static/js/drill.js — client-side drill runner.
 *
 * Flow: load state (resume-aware) → render board → player clicks a cell →
 * POST submit → feedback overlay (with reveal preview of the pick and the
 * optimal pick) → next board → results screen.
 *
 * Drill-type click targets:
 *   l5_opening_recognition  unrevealed cells
 *   l3_strategic_nf         unrevealed cells
 *   l7_fishing              unrevealed cells
 *   l6_flag_value           unrevealed cells (the flag target)
 *   l4_pure_efficiency      revealed number cells (chord targets)
 *   l2_effective_chord      revealed number cells (flag-then-chord targets)
 *   l1_cut_waste            BOTH — chord a number or click a safe cell
 *
 * This is the canonical source. The deployed file is the terser-minified
 * copy at static/js/drill.js — regenerate with:
 *   npx terser phase7_drills/static/js/drill.js -c -m -o static/js/drill.js
 */
(function () {
  'use strict';

  var page = document.querySelector('.dr-page');
  var drillId = page ? parseInt(page.getAttribute('data-drill-id'), 10) : null;

  var state = {
    drill: null,
    currentIndex: 0,
    boardClickAt: null,
    completed: false,
    lastResponse: null,
  };

  var DEFAULT_TYPE = 'l5_opening_recognition';

  // Which drill types make revealed number cells clickable / unrevealed
  // cells clickable. l1_cut_waste appears in both.
  var CLICK_REVEALED = { l4_pure_efficiency: 1, l2_effective_chord: 1, l1_cut_waste: 1 };
  var CLICK_UNREVEALED = {
    l5_opening_recognition: 1, l6_flag_value: 1, l3_strategic_nf: 1,
    l7_fishing: 1, l1_cut_waste: 1,
  };

  // Per-type feedback copy. {n} = pick's score, {m} = optimal score,
  // {q} = pick score as % of optimal.
  var FEEDBACK = {
    l4_pure_efficiency: {
      okTitle: 'Solid chord',
      okBody: 'Chord opens {n} cells ({q}% of the best chord available).',
      badTitle: 'Lower-value chord',
      badBody: 'That chord opens {n} cells. The best chord (highlighted) opens {m}.',
    },
    l6_flag_value: {
      okTitle: 'Great flag',
      okBody: 'That flag enables {n} cells of chord value ({q}% of the best flag available).',
      badTitle: 'Lower-value flag',
      badBody: 'That flag enables {n} cells of chord value. The best flag (highlighted) enables {m}.',
    },
    l1_cut_waste: {
      okTitle: 'Efficient move',
      okBody: 'That move reveals {n} cells ({q}% of the best available move).',
      badTitle: 'Wasted potential',
      badBody: 'That move reveals {n} cells. The best move (highlighted) reveals {m} in a single action.',
    },
    l2_effective_chord: {
      okTitle: 'Right number',
      okBody: 'Flag-then-chord opens {n} cells ({q}% of the best available).',
      badTitle: 'Lower-value chord',
      badBody: 'That flag-then-chord opens {n} cells. The best number (highlighted) opens {m}.',
    },
    l3_strategic_nf: {
      okTitle: 'Provably safe',
      okBody: 'Safe from the raw numbers — no flag needed. Opens {n} cells.',
      badTitle: 'Not provable',
      badBody: 'That cell can’t be proven safe from the numbers alone. The highlighted cell can.',
    },
    l7_fishing: {
      okTitle: 'Good fishing',
      okBody: 'Proved safe by chaining overlapping constraints. Opens {n} cells.',
      badTitle: 'Missed the deduction',
      badBody: 'That cell isn’t provable. The highlighted cell is — compare the overlapping numbers around it.',
    },
    _default: {
      okTitle: 'Nice pick',
      okBody: 'Opens {n} cells ({q}% of the best available).',
      badTitle: 'Small opening',
      badBody: 'That cell only opens {n} cells. The best pick (highlighted) opens {m}.',
    },
  };

  function getJSON(url, opts) {
    return fetch(url, Object.assign({
      method: 'GET',
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    }, opts || {})).then(async function (res) {
      if (!res.ok) {
        var msg = 'HTTP ' + res.status;
        try {
          var body = await res.json();
          if (body && body.detail) msg = body.detail;
        } catch (e) { /* not JSON */ }
        throw new Error(msg);
      }
      return res.json();
    });
  }

  function postJSON(url, body) {
    return getJSON(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body || {}),
    });
  }

  function fillCopy(tpl, result) {
    return tpl
      .replace('{n}', result.opening_size)
      .replace('{m}', result.optimal_opening_size)
      .replace('{q}', Math.round(100 * result.relative_quality));
  }

  // ── Rendering ──────────────────────────────────────────────────────────────

  function showBoard() {
    var idx = state.currentIndex;
    var drill = state.drill;
    var board = drill.boards[idx];
    if (!board) {
      showError('Internal error: missing board ' + idx);
      return;
    }
    setText('dr-progress-label', (idx + 1) + ' / ' + drill.num_boards);
    setText('dr-accuracy-label',
      (drill.attempts || []).filter(function (a) { return a.result && a.result.is_correct; }).length + ' correct');
    var fill = document.getElementById('dr-progress-fill');
    if (fill) fill.style.width = (idx / drill.num_boards * 100) + '%';
    if (board.prompt) setText('dr-prompt', board.prompt);
    renderBoard(board);
    state.boardClickAt = (window.performance && performance.now) ? performance.now() : Date.now();
  }

  function renderBoard(board) {
    var grid = document.getElementById('dr-board');
    if (!grid) return;
    grid.innerHTML = '';
    grid.style.gridTemplateColumns = 'repeat(' + board.width + ', 22px)';

    var revealedSet = new Set((board.revealed || []).map(function (rc) { return rc[0] + ',' + rc[1]; }));
    var flagSet = new Set((board.flags || []).map(function (rc) { return rc[0] + ',' + rc[1]; }));
    var numberMap = new Map((board.numbers || []).map(function (rcn) { return [rcn[0] + ',' + rcn[1], rcn[2]]; }));

    var type = board.drill_type || DEFAULT_TYPE;
    var clickRevealed = !!CLICK_REVEALED[type];
    var clickUnrevealed = !!CLICK_UNREVEALED[type];

    for (var r = 0; r < board.height; r++) {
      for (var c = 0; c < board.width; c++) {
        var cell = document.createElement('div');
        cell.className = 'dr-cell';
        cell.setAttribute('role', 'gridcell');
        cell.dataset.row = r;
        cell.dataset.col = c;
        var key = r + ',' + c;

        if (flagSet.has(key)) {
          cell.classList.add('dr-cell--flagged');
          cell.textContent = '🚩';
        } else if (revealedSet.has(key)) {
          cell.classList.add('dr-cell--revealed');
          var n = numberMap.get(key);
          if (typeof n === 'number') {
            cell.classList.add('dr-cell--n' + n);
            cell.textContent = String(n);
          }
          if (clickRevealed && typeof n === 'number') {
            cell.classList.add('dr-cell--chord-target');
            cell.addEventListener('click', onCellClick);
          }
        } else if (clickUnrevealed) {
          cell.addEventListener('click', onCellClick);
        }
        grid.appendChild(cell);
      }
    }
  }

  // ── Submit ─────────────────────────────────────────────────────────────────

  async function onCellClick(ev) {
    var cell = ev.currentTarget;
    if (!cell) return;
    if (cell.classList.contains('dr-cell--flagged')) return;
    cell.classList.add('dr-cell--picked');

    var grid = document.getElementById('dr-board');
    if (grid) {
      Array.prototype.forEach.call(grid.children, function (el) {
        el.style.pointerEvents = 'none';
      });
    }

    var row = parseInt(cell.dataset.row, 10);
    var col = parseInt(cell.dataset.col, 10);
    var t0 = state.boardClickAt || Date.now();
    var t1 = (window.performance && performance.now) ? performance.now() : Date.now();
    var decisionMs = Math.max(0, Math.round(t1 - t0));

    var resp;
    try {
      resp = await postJSON('/api/drills/' + drillId + '/submit', {
        board_index: state.currentIndex,
        chosen_row: row,
        chosen_col: col,
        decision_ms: decisionMs,
      });
    } catch (e) {
      showError('Submit failed: ' + (e && e.message ? e.message : 'unknown'));
      return;
    }

    var result = resp.result;
    if (result.is_correct) {
      cell.classList.add('dr-cell--correct');
      paintReveal(grid, result.revealed_cells, 'dr-cell--reveal-self');
    } else {
      cell.classList.add('dr-cell--wrong');
      var optimal = grid
        ? grid.querySelector('[data-row="' + result.optimal_row + '"][data-col="' + result.optimal_col + '"]')
        : null;
      if (optimal) optimal.classList.add('dr-cell--optimal');
      paintReveal(grid, result.revealed_cells, 'dr-cell--reveal-self');
      paintReveal(grid, result.optimal_revealed_cells, 'dr-cell--reveal-optimal');
    }

    showFeedback(result, resp);

    if (!state.drill.attempts) state.drill.attempts = [];
    state.drill.attempts.push({
      board_index: state.currentIndex,
      chosen_row: row,
      chosen_col: col,
      decision_ms: decisionMs,
      result: result,
    });
    state.lastResponse = resp;
  }

  function showFeedback(result, resp) {
    var panel = document.getElementById('dr-feedback');
    var icon = document.getElementById('dr-feedback-icon');
    var title = document.getElementById('dr-feedback-title');
    var body = document.getElementById('dr-feedback-body');
    var nextBtn = document.getElementById('dr-next-btn');
    if (!(panel && icon && title && body && nextBtn)) return;

    icon.className = 'dr-feedback-icon';
    var board = (state.drill.boards || [])[state.currentIndex] || {};
    var copy = FEEDBACK[board.drill_type || DEFAULT_TYPE] || FEEDBACK._default;

    if (result.is_mine) {
      icon.classList.add('dr-feedback-icon--mine');
      icon.textContent = '💣';
      title.textContent = 'Mine!';
      body.textContent = 'That cell hides a mine. The best pick (highlighted) opens '
        + result.optimal_opening_size + ' cells.';
    } else if (result.is_correct) {
      icon.classList.add('dr-feedback-icon--correct');
      icon.textContent = '✓';
      title.textContent = copy.okTitle;
      body.textContent = fillCopy(copy.okBody, result);
    } else {
      icon.classList.add('dr-feedback-icon--wrong');
      icon.textContent = '✗';
      title.textContent = copy.badTitle;
      body.textContent = fillCopy(copy.badBody, result);
    }

    var isLast = (resp && resp.completed) || state.currentIndex >= state.drill.num_boards - 1;
    nextBtn.textContent = isLast ? 'See results →' : 'Next board →';
    show('dr-feedback');
  }

  function nextBoard() {
    hide('dr-feedback');
    var resp = state.lastResponse;
    var total = (state.drill && state.drill.num_boards) || 0;
    if ((resp && resp.completed) || state.currentIndex >= total - 1) {
      state.completed = true;
      showResults((resp && resp.summary) || null);
      return;
    }
    state.currentIndex += 1;
    showBoard();
  }

  // ── Results ────────────────────────────────────────────────────────────────

  function showResults(summary) {
    hide('dr-runner');
    show('dr-results');

    if (!summary) {
      // Client-side fallback if the server summary is missing (shouldn't
      // happen, but keeps a refresh on a just-finished drill sane).
      var drill = state.drill || {};
      var attempts = drill.attempts || [];
      var correct = attempts.filter(function (a) { return a.result && a.result.is_correct; }).length;
      var total = drill.num_boards || attempts.length || 0;
      var times = attempts.map(function (a) { return a.decision_ms; }).filter(function (t) { return t > 0; });
      var avg = times.length
        ? Math.round(times.reduce(function (s, t) { return s + t; }, 0) / times.length)
        : 0;
      summary = {
        num_correct: correct,
        num_total: total,
        accuracy_pct: total ? Math.round(1000 * correct / total) / 10 : 0,
        avg_decision_ms: avg,
        mastery_contribution: total ? correct / total : 0,
        counted_toward_mastery: false,
      };
    }

    setText('dr-stat-accuracy',
      summary.num_correct + ' / ' + summary.num_total + '  (' + summary.accuracy_pct.toFixed(0) + '%)');
    setText('dr-stat-avg', (summary.avg_decision_ms / 1000).toFixed(1) + 's');
    setText('dr-stat-mastery', summary.mastery_contribution.toFixed(2));

    var icon = document.getElementById('dr-results-icon');
    var title = document.getElementById('dr-results-title');
    var blurb = document.getElementById('dr-results-blurb');
    if (summary.accuracy_pct >= 80) {
      if (icon) icon.textContent = '🎯';
      if (title) title.textContent = 'Sharp eye';
      if (blurb) blurb.textContent = 'You found the best move on most boards. Keep drilling — this is graduation pace.';
    } else if (summary.accuracy_pct >= 50) {
      if (icon) icon.textContent = '👀';
      if (title) title.textContent = 'Solid';
      if (blurb) blurb.textContent = 'You’re seeing it about half the time. Run this drill daily and watch the score climb.';
    } else {
      if (icon) icon.textContent = '🌱';
      if (title) title.textContent = 'Building the reflex';
      if (blurb) blurb.textContent = 'Review the highlighted optimal cells as you go — the pattern shows up fast on re-runs.';
    }
  }

  async function startAgain() {
    try {
      var drill = state.drill || {};
      var resp = await postJSON('/api/drills/start', {
        drill_type: drill.drill_type || DEFAULT_TYPE,
        level: drill.level || 5,
        difficulty: drill.difficulty || 'expert',
        mode: drill.mode || 'standard',
        num_boards: drill.num_boards || 10,
      });
      window.location.href = '/drill/' + resp.drill_id;
    } catch (e) {
      showError('Could not start a new drill: ' + (e.message || 'unknown'));
    }
  }

  // ── DOM helpers ────────────────────────────────────────────────────────────

  function paintReveal(grid, cells, extraClass) {
    if (!grid || !cells || !cells.length) return;
    cells.forEach(function (rcn) {
      var r = rcn[0], c = rcn[1], n = rcn[2];
      var el = grid.querySelector('[data-row="' + r + '"][data-col="' + c + '"]');
      if (!el) return;
      if (el.classList.contains('dr-cell--revealed')
        || el.classList.contains('dr-cell--correct')
        || el.classList.contains('dr-cell--wrong')
        || el.classList.contains('dr-cell--optimal')) return;
      el.classList.add('dr-cell--reveal');
      if (extraClass) el.classList.add(extraClass);
      if (typeof n === 'number' && n > 0) {
        el.classList.add('dr-cell--n' + n);
        el.textContent = String(n);
      } else {
        el.textContent = '';
      }
    });
  }

  function show(id) { var el = document.getElementById(id); if (el) el.hidden = false; }
  function hide(id) { var el = document.getElementById(id); if (el) el.hidden = true; }
  function setText(id, text) { var el = document.getElementById(id); if (el) el.textContent = text; }

  function showError(detail) {
    hide('dr-loading');
    hide('dr-runner');
    show('dr-error');
    setText('dr-error-detail', detail || '');
  }

  // ── Init (resume-aware) ────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', async function () {
    if (!drillId || Number.isNaN(drillId)) {
      showError('Missing drill id in page URL.');
      return;
    }
    try {
      var drill = await getJSON('/api/drills/' + drillId);
      state.drill = drill;
      if (drill.completed_at) {
        state.completed = true;
        showResults(drill.summary || null);
        return;
      }
      var answered = (drill.attempts || []).length;
      state.currentIndex = Math.min(answered, drill.num_boards - 1);
      show('dr-runner');
      hide('dr-loading');
      var nextBtn = document.getElementById('dr-next-btn');
      var againBtn = document.getElementById('dr-again-btn');
      if (nextBtn) nextBtn.addEventListener('click', nextBoard);
      if (againBtn) againBtn.addEventListener('click', startAgain);
      showBoard();
    } catch (e) {
      showError(e && e.message ? e.message : 'Unknown error');
    }
  });
})();
