/* bootcamp_radar.js — Skill Radar page (F-BC-RADAR) */
(function () {
  'use strict';

  const CFG = window.BOOTCAMP_CONFIG || {};
  const apiBase = CFG.apiBase || '/api';
  const copy = CFG.copy || {};

  /* ── DOM refs ────────────────────────────────────────────────────────────── */
  const elLoading  = document.getElementById('br-loading');
  const elEmpty    = document.getElementById('br-empty');
  const elError    = document.getElementById('br-error');
  const elMain     = document.getElementById('br-main');
  const elAxes     = document.getElementById('br-axes');
  const elInsights = document.getElementById('br-insights');
  const elRec      = document.getElementById('br-rec');
  const elGamesMeta = document.getElementById('br-games-meta');
  const elChart    = document.getElementById('br-chart');
  const modeTabs   = document.querySelectorAll('.bc-mode-tab');

  let chartInstance = null;
  let currentMode = CFG.initialMode || 'standard';

  /* ── Axis display names ──────────────────────────────────────────────────── */
  const AXIS_LABELS = {
    speed:               'Speed',
    efficiency:          'Efficiency',
    chord_use:           'Chord Use',
    pattern_recognition: 'Pattern Recognition',
    hierarchy_compliance:'Hierarchy Compliance',
    flag_value:          'Flag Value',
    opening_recognition: 'Opening Recognition',
    guess_avoidance:     'Guess Avoidance',
    consistency:         'Consistency',
  };

  /* axes that belong to Dard Part-2 */
  const DARD2_AXES = new Set([
    'pattern_recognition',
    'hierarchy_compliance',
    'opening_recognition',
    'guess_avoidance',
  ]);

  /* ── Utilities ───────────────────────────────────────────────────────────── */
  function show(el) { el.hidden = false; }
  function hide(el) { el.hidden = true;  }
  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function pillClass(pill) {
    if (pill === 'strong')  return 'br-pill--strong';
    if (pill === 'weak')    return 'br-pill--weak';
    return 'br-pill--average';
  }

  function pillLabel(pill) {
    if (pill === 'strong')  return copy.pillStrong  || 'Strong';
    if (pill === 'weak')    return copy.pillWeak    || 'Weak';
    return copy.pillAverage || 'Average';
  }

  /* ── Fetch ───────────────────────────────────────────────────────────────── */
  function fetchRadar(mode) {
    return fetch(`${apiBase}/radar?mode=${mode}`)
      .then(function (r) {
        if (r.status === 404) return null;
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      });
  }

  /* ── Chart ───────────────────────────────────────────────────────────────── */
  function buildChart(axes) {
    const labels = axes.map(function (a) {
      return AXIS_LABELS[a.axis] || a.axis;
    });
    const playerData    = axes.map(function (a) { return a.player_percentile;    });
    const benchmarkData = axes.map(function (a) { return a.benchmark_percentile; });

    const isDark = document.documentElement.getAttribute('data-theme') === 'dark'
      || (!document.documentElement.getAttribute('data-theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);

    const gridColor  = isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.10)';
    const labelColor = isDark ? '#94a3b8' : '#6b7280';

    if (chartInstance) { chartInstance.destroy(); }

    chartInstance = new Chart(elChart, {
      type: 'radar',
      data: {
        labels: labels,
        datasets: [
          {
            label: copy.legendYou || 'You',
            data: playerData,
            backgroundColor: 'rgba(37,99,235,0.18)',
            borderColor: '#2563eb',
            borderWidth: 2,
            pointBackgroundColor: '#2563eb',
            pointRadius: 3,
          },
          {
            label: copy.legendBenchmark || 'Top 10%',
            data: benchmarkData,
            backgroundColor: 'rgba(16,185,129,0.08)',
            borderColor: '#10b981',
            borderWidth: 2,
            borderDash: [5, 4],
            pointBackgroundColor: '#10b981',
            pointRadius: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        scales: {
          r: {
            min: 0,
            max: 100,
            ticks: {
              stepSize: 25,
              color: labelColor,
              font: { size: 10 },
              backdropColor: 'transparent',
            },
            grid:        { color: gridColor },
            angleLines:  { color: gridColor },
            pointLabels: { color: labelColor, font: { size: 11 } },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                return ctx.dataset.label + ': ' + ctx.raw + 'th %ile';
              },
            },
          },
        },
      },
    });
  }

  /* ── Axis breakdown ──────────────────────────────────────────────────────── */
  function renderAxes(axes) {
    elAxes.innerHTML = axes.map(function (a) {
      const name       = esc(AXIS_LABELS[a.axis] || a.axis);
      const dard2      = DARD2_AXES.has(a.axis);
      const playerPct  = Math.round(a.player_percentile);
      const benchPct   = Math.round(a.benchmark_percentile);
      const pill       = a.pill || 'average';
      const valueLabel = esc(a.player_value_label || (playerPct + 'th %ile'));

      return [
        '<div class="br-axis-item">',
          '<div class="br-axis-header">',
            '<span class="br-axis-name">',
              name,
              dard2 ? ('<span class="br-axis-dard">' + esc(copy.newDardStar || '★ Dard Part-2 skill') + '</span>') : '',
            '</span>',
            '<span class="br-axis-values">' + valueLabel + '</span>',
          '</div>',
          '<div class="br-axis-track">',
            '<div class="br-axis-fill" style="width:' + playerPct + '%"></div>',
            '<div class="br-axis-tick" style="left:' + benchPct + '%"></div>',
          '</div>',
          '<div class="br-axis-meta">',
            '<span>' + playerPct + 'th %ile</span>',
            '<span class="br-pill ' + pillClass(pill) + '">' + esc(pillLabel(pill)) + '</span>',
          '</div>',
        '</div>',
      ].join('');
    }).join('');
  }

  /* ── Insight cards ───────────────────────────────────────────────────────── */
  function renderInsights(insights) {
    if (!insights || insights.length === 0) {
      elInsights.innerHTML = '';
      return;
    }
    const configs = [
      { key: 'top_axis',  label: copy.insightTop      || 'Top axis',        cls: 'br-insight--strength' },
      { key: 'weakness',  label: copy.insightWeakness  || 'Weakest axis',    cls: 'br-insight--weakness'  },
      { key: 'leverage',  label: copy.insightLeverage  || 'Biggest leverage', cls: ''                     },
    ];
    elInsights.innerHTML = configs.map(function (cfg) {
      const item = insights.find(function (i) { return i.type === cfg.key; }) || {};
      const axis   = esc(AXIS_LABELS[item.axis] || item.axis || '—');
      const detail = esc(item.detail || '');
      return [
        '<div class="br-insight ' + cfg.cls + '">',
          '<div class="br-insight-label">' + esc(cfg.label) + '</div>',
          '<div class="br-insight-value">' + axis + '</div>',
          detail ? '<div class="br-insight-detail">' + detail + '</div>' : '',
        '</div>',
      ].join('');
    }).join('');
  }

  /* ── Recommendation block ────────────────────────────────────────────────── */
  function renderRec(data) {
    if (!data.recommendation_title) {
      elRec.innerHTML = '';
      return;
    }
    const title  = esc(data.recommendation_title);
    const body   = esc(data.recommendation_body || '');
    const ctaUrl = esc(data.recommendation_cta_url || '');
    const ctaTxt = esc(data.recommendation_cta_text || 'Start drill');

    elRec.innerHTML = [
      '<div class="br-rec">',
        '<div class="br-rec-icon">🎯</div>',
        '<div>',
          '<div class="br-rec-title">' + title + '</div>',
          body ? '<div class="br-rec-body">' + body + '</div>' : '',
          ctaUrl ? '<a class="br-rec-cta" href="' + ctaUrl + '">' + ctaTxt + '</a>' : '',
        '</div>',
      '</div>',
    ].join('');
  }

  /* ── Games-analyzed footer ───────────────────────────────────────────────── */
  function renderGamesMeta(n) {
    if (!n) { elGamesMeta.textContent = ''; return; }
    const tpl = copy.gamesAnalyzed || 'Based on {n} analyzed games';
    elGamesMeta.textContent = tpl.replace('{n}', n);
  }

  /* ── Full render ─────────────────────────────────────────────────────────── */
  function render(data) {
    buildChart(data.axes);
    renderAxes(data.axes);
    renderInsights(data.insights);
    renderRec(data);
    renderGamesMeta(data.games_analyzed);
  }

  /* ── Load ────────────────────────────────────────────────────────────────── */
  function load(mode) {
    hide(elEmpty);
    hide(elError);
    hide(elMain);
    show(elLoading);

    fetchRadar(mode)
      .then(function (data) {
        hide(elLoading);
        if (!data) { show(elEmpty); return; }
        render(data);
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

  /* ── Init ────────────────────────────────────────────────────────────────── */
  load(currentMode);
}());
