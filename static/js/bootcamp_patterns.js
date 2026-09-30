/* bootcamp_patterns.js — Pattern Fluency page (F-BC-FLUENCY) */
(function () {
  'use strict';

  const CFG  = window.FLUENCY_CONFIG || {};
  const api  = CFG.apiBase || '/api';
  const copy = CFG.copy    || {};

  const elLoading   = document.getElementById('bp-loading');
  const elEmpty     = document.getElementById('bp-empty');
  const elError     = document.getElementById('bp-error');
  const elMain      = document.getElementById('bp-main');
  const elSummary   = document.getElementById('bp-summary');
  const elList      = document.getElementById('bp-list');
  const elPlan      = document.getElementById('bp-plan');
  const elGamesMeta = document.getElementById('bp-games-meta');
  const modeTabs    = document.querySelectorAll('.bc-mode-tab');

  let currentMode = CFG.initialMode || 'standard';

  /* ── Mini-board cell layout by pattern_key ───────────────────────────────── */
  /*
   * Cell types:  F=flag  S=safe(highlighted)  N=number  O=open/blank  U=unknown
   * n: number value for N cells
   */
  var BOARDS = {
    pattern_121: {
      cols: 3,
      cells: [{t:'F'},{t:'S'},{t:'F'},{t:'N',n:1},{t:'N',n:2},{t:'N',n:1}]
    },
    pattern_1221: {
      cols: 4,
      cells: [{t:'F'},{t:'S'},{t:'S'},{t:'F'},{t:'N',n:1},{t:'N',n:2},{t:'N',n:2},{t:'N',n:1}]
    },
    pattern_232: {
      cols: 3,
      cells: [
        {t:'F'},{t:'S'},{t:'F'},
        {t:'N',n:2},{t:'N',n:3},{t:'N',n:2},
        {t:'F'},{t:'O'},{t:'F'}
      ]
    },
    pattern_11_corner: {
      cols: 2,
      cells: [{t:'N',n:1},{t:'N',n:1},{t:'S'},{t:'F'}]
    },
    pattern_21_edge: {
      cols: 2,
      cells: [{t:'F'},{t:'S'},{t:'N',n:2},{t:'N',n:1}]
    },
    opening_l_shape_edge: {
      cols: 3,
      cells: [{t:'U'},{t:'F'},{t:'S'},{t:'N',n:1},{t:'N',n:1},{t:'O'}]
    },
    opening_2_satisfied: {
      cols: 3,
      cells: [{t:'F'},{t:'F'},{t:'S'},{t:'N',n:2},{t:'O'},{t:'O'}]
    },
    opening_potential_2cell: {
      cols: 3,
      cells: [{t:'O'},{t:'U'},{t:'O'},{t:'O'},{t:'U'},{t:'O'}]
    },
    fishing_for_1: {
      cols: 3,
      cells: [{t:'N',n:1},{t:'F'},{t:'O'},{t:'S'},{t:'U'},{t:'S'}]
    },
    fishing_for_2: {
      cols: 3,
      cells: [{t:'F'},{t:'N',n:2},{t:'O'},{t:'S'},{t:'U'},{t:'O'}]
    },
  };

  var NUM_COLOR = {1:'#0000ff', 2:'#008200', 3:'#ff0000', 4:'#000084'};

  /* ── Utilities ───────────────────────────────────────────────────────────── */
  function show(el) { if (el) el.hidden = false; }
  function hide(el) { if (el) el.hidden = true;  }
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;');
  }

  /* ── Mini-board renderer ─────────────────────────────────────────────────── */
  function buildMiniBoard(key) {
    var spec = BOARDS[key];
    if (!spec) return '<div class="bp-mini" style="grid-template-columns:repeat(2,17px)"><div class="bp-cell bp-cell--u"></div><div class="bp-cell bp-cell--u"></div><div class="bp-cell bp-cell--u"></div><div class="bp-cell bp-cell--u"></div></div>';

    var cells = spec.cells.map(function (c) {
      if (c.t === 'F') {
        return '<div class="bp-cell bp-cell--F" title="Flag" aria-label="flagged mine">🚩</div>';
      }
      if (c.t === 'S') {
        return '<div class="bp-cell bp-cell--S" title="Safe cell" aria-label="safe"></div>';
      }
      if (c.t === 'N') {
        var col = NUM_COLOR[c.n] || '#000';
        return '<div class="bp-cell bp-cell--N" style="color:' + col + '" aria-label="' + c.n + '">' + c.n + '</div>';
      }
      if (c.t === 'O') {
        return '<div class="bp-cell bp-cell--O" aria-label="open"></div>';
      }
      return '<div class="bp-cell bp-cell--u" aria-label="unknown">?</div>';
    }).join('');

    return '<div class="bp-mini" style="grid-template-columns:repeat(' + spec.cols + ',17px)" role="img" aria-label="Pattern diagram">' + cells + '</div>';
  }

  /* ── Summary card ────────────────────────────────────────────────────────── */
  function renderSummary(data) {
    var drilledTotal = data.layer_12_total + data.layer_4_total;
    var drilledDone  = data.layer_12_drilled + data.layer_4_drilled;
    var gainStr      = data.predicted_gain_seconds > 0
      ? '−' + data.predicted_gain_seconds.toFixed(1) + 's'
      : '—';

    elSummary.innerHTML = [
      '<div class="bp-summary">',
        '<div>',
          '<div class="bp-summary-eyebrow">' + esc(copy.overallLabel || 'Overall pattern fluency') + '</div>',
          '<div class="bp-summary-score">' + esc(data.overall_score) + '<span style="font-size:24px;font-weight:400">/100</span></div>',
          '<div class="bp-summary-detail">' + esc(data.headline_message || '') + '</div>',
        '</div>',
        '<div class="bp-summary-stats">',
          '<div class="bp-summary-stat">',
            '<div class="bp-summary-stat-label">' + esc(copy.drilledLabel || 'Patterns drilled') + '</div>',
            '<div class="bp-summary-stat-value">' + drilledDone + ' / ' + drilledTotal + '</div>',
          '</div>',
          '<div class="bp-summary-stat">',
            '<div class="bp-summary-stat-label">' + esc(copy.gainLabel || 'Predicted gain') + '</div>',
            '<div class="bp-summary-stat-value">' + gainStr + '</div>',
          '</div>',
        '</div>',
      '</div>',
    ].join('');
  }

  /* ── Pattern list ────────────────────────────────────────────────────────── */
  function renderPatternList(patterns) {
    if (!patterns || patterns.length === 0) { elList.innerHTML = ''; return; }

    var maxBench = Math.max.apply(null, patterns.map(function (p) { return p.benchmark_value || 0; }));

    elList.innerHTML = patterns.map(function (p) {
      var tierCls  = 'bp-row--' + (p.leverage_tier || 'low');
      var miniHtml = buildMiniBoard(p.pattern_key);

      /* Reaction-time / take-rate bar */
      var barHtml = '';
      if (p.category === 'patterns' || p.category === 'reductions') {
        var ref     = maxBench || p.benchmark_value || 1;
        var yourPct = Math.min(100, Math.round((p.your_value / ref) * 100));
        var benchPct= Math.min(100, Math.round((p.benchmark_value / ref) * 100));
        barHtml = [
          '<div class="bp-rt-track">',
            '<div class="bp-rt-fill" style="width:' + yourPct + '%"></div>',
            '<div class="bp-rt-bench" style="left:' + benchPct + '%"></div>',
          '</div>',
          '<div class="bp-rt-meta">',
            '<span>You: <strong>' + esc(p.your_value_label) + '</strong></span>',
            '<span>Top: <strong>' + esc(p.benchmark_value_label) + '</strong></span>',
          '</div>',
        ].join('');
      } else {
        /* openings / fishing: show take-rate as a progress bar */
        var yourRatePct  = Math.round((p.your_value  || 0) * 100);
        var benchRatePct = Math.round((p.benchmark_value || 0) * 100);
        barHtml = [
          '<div class="bp-rt-track">',
            '<div class="bp-rt-fill" style="width:' + yourRatePct + '%"></div>',
            '<div class="bp-rt-bench" style="left:' + benchRatePct + '%"></div>',
          '</div>',
          '<div class="bp-rt-meta">',
            '<span>You: <strong>' + esc(p.your_value_label) + '</strong></span>',
            '<span>Top: <strong>' + esc(p.benchmark_value_label) + '</strong></span>',
          '</div>',
        ].join('');
      }

      /* Leverage */
      var levCls  = 'bp-lev-value--' + (p.leverage_tier || 'low');
      var levStr  = p.leverage_seconds > 0
        ? '−' + p.leverage_seconds.toFixed(1) + 's'
        : '≈0s';

      /* Drill button */
      var btnHtml;
      if (p.mastered) {
        btnHtml = '<div class="bp-drill-btn bp-drill-btn--mastered">' + esc(copy.masteredLabel || 'Mastered ✓') + '</div>';
      } else if (p.drill_id) {
        var mins = p.drill_estimated_minutes ? ' (' + p.drill_estimated_minutes + ' min)' : '';
        btnHtml = '<button class="bp-drill-btn bp-drill-btn--primary" data-drill-id="' + esc(p.drill_id) + '">▶ ' + esc(copy.drillBtn || 'Drill') + mins + '</button>';
      } else {
        btnHtml = '<div class="bp-drill-btn bp-drill-btn--none">No drill</div>';
      }

      var dardTag = p.is_new_dard ? '<span class="bp-dard-tag">' + esc(copy.dardLabel || '★ Dard Part-2') + '</span>' : '';

      return [
        '<div class="bp-row ' + tierCls + '">',
          miniHtml,
          '<div>',
            '<div class="bp-pattern-name">' + esc(p.display_name) + dardTag + '</div>',
            '<div class="bp-pattern-desc">' + esc(p.description) + '</div>',
            '<div class="bp-pattern-freq">~' + (p.frequency_per_board || '?') + '× per expert board</div>',
          '</div>',
          '<div>' + barHtml + '</div>',
          '<div class="bp-leverage">',
            '<div class="bp-lev-value ' + levCls + '">' + levStr + '</div>',
            '<div class="bp-lev-label">' + esc(copy.leverageLabel || 'per game') + '</div>',
          '</div>',
          '<div>' + btnHtml + '</div>',
        '</div>',
      ].join('');
    }).join('');
  }

  /* ── Weekly plan ─────────────────────────────────────────────────────────── */
  function renderWeeklyPlan(weekly, planNote) {
    if (!weekly || weekly.length === 0) { elPlan.innerHTML = ''; return; }

    var dayCards = weekly.map(function (d) {
      return [
        '<div class="bp-plan-day">',
          '<div class="bp-plan-day-label">' + esc(d.days_label) + '</div>',
          '<div class="bp-plan-day-pattern">' + esc(d.pattern_name) + '</div>',
          '<div class="bp-plan-day-meta">' + d.board_count + ' boards · <strong>' + d.minutes + ' min</strong><br>' + esc(d.target) + '</div>',
        '</div>',
      ].join('');
    }).join('');

    var noteHtml = planNote
      ? '<div class="bp-plan-note">' + esc(planNote) + '</div>'
      : '';

    elPlan.innerHTML = [
      '<div class="bp-plan">',
        '<div class="bp-plan-title">🎯 ' + esc(copy.planTitle || "This week's drill plan") + '</div>',
        '<div class="bp-plan-grid">' + dayCards + '</div>',
        noteHtml,
      '</div>',
    ].join('');
  }

  /* ── Games-analyzed footer ───────────────────────────────────────────────── */
  function renderGamesMeta(n) {
    if (!n) { elGamesMeta.textContent = ''; return; }
    var tpl = copy.gamesAnalyzed || 'Based on {n} analyzed games';
    elGamesMeta.textContent = tpl.replace('{n}', n);
  }

  /* ── Fetch ───────────────────────────────────────────────────────────────── */
  function fetchFluency(mode) {
    return fetch(api + '/patterns/fluency?mode=' + mode, {
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    }).then(function (r) {
      if (r.status === 404) return null;
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  /* ── Drill start ─────────────────────────────────────────────────────────── */
  function startDrill(drillId) {
    var level = 1;
    var m = /^(pat|fish|opening)_/.exec(drillId);
    if (m) level = (drillId.startsWith('opening') || drillId.startsWith('fish')) ? 5 : 2;

    fetch('/api/drills/start', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({ drill_type: drillId, level: level,
                              difficulty: 'expert', mode: currentMode, num_boards: 10 }),
    })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (d) { window.location.href = '/drill/' + d.drill_id; })
    .catch(function (e) { console.error('[patterns] drill start failed', e); });
  }

  /* ── Load ────────────────────────────────────────────────────────────────── */
  function load(mode) {
    hide(elEmpty); hide(elError); hide(elMain); show(elLoading);

    fetchFluency(mode)
      .then(function (data) {
        hide(elLoading);
        if (!data) { show(elEmpty); return; }
        renderSummary(data);
        renderPatternList(data.patterns);
        renderWeeklyPlan(data.weekly_plan, data.plan_note);
        renderGamesMeta(data.games_analyzed);
        show(elMain);
      })
      .catch(function () {
        hide(elLoading);
        show(elError);
      });
  }

  /* ── Mode toggle ─────────────────────────────────────────────────────────── */
  modeTabs.forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (btn.dataset.mode === currentMode) return;
      modeTabs.forEach(function (b) {
        b.classList.remove('bc-mode-tab--active');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('bc-mode-tab--active');
      btn.setAttribute('aria-selected', 'true');
      currentMode = btn.dataset.mode;
      load(currentMode);
    });
  });

  /* ── Drill button delegation ─────────────────────────────────────────────── */
  elList && elList.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-drill-id]');
    if (btn) startDrill(btn.dataset.drillId);
  });

  /* ── Init ────────────────────────────────────────────────────────────────── */
  load(currentMode);
}());
