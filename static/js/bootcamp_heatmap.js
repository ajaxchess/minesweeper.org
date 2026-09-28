(function () {
  'use strict';

  const CFG = window.HM_CONFIG || {};
  const API = CFG.apiBase || '/api';
  const COPY = CFG.copy || {};

  // ── State ─────────────────────────────────────────────────────────────────
  let difficulty = 'expert';
  let timeRange  = 90;
  let mode       = 'standard';

  // ── DOM refs ──────────────────────────────────────────────────────────────
  const elLoading    = document.getElementById('hm-loading');
  const elLoggedOut  = document.getElementById('hm-logged-out');
  const elEmpty      = document.getElementById('hm-empty');
  const elError      = document.getElementById('hm-error');
  const elMain       = document.getElementById('hm-main');
  const elBoard      = document.getElementById('hm-board');
  const elBoardTitle = document.getElementById('hm-board-title');
  const elTooltip    = document.getElementById('hm-tooltip');
  const elLegendMax  = document.getElementById('hm-legend-max');
  const elCauseList  = document.getElementById('hm-cause-list');
  const elCauseSubtitle = document.getElementById('hm-cause-subtitle');
  const elRegionGrid = document.getElementById('hm-region-grid');
  const elInsights   = document.getElementById('hm-insights');
  const elStatGames  = document.getElementById('hm-stat-games');
  const elStatGamesMeta = document.getElementById('hm-stat-games-meta');
  const elStatCause  = document.getElementById('hm-stat-cause');
  const elStatCauseMeta = document.getElementById('hm-stat-cause-meta');
  const elStatRegion = document.getElementById('hm-stat-region');
  const elStatRegionMeta = document.getElementById('hm-stat-region-meta');
  const elStatSurvival = document.getElementById('hm-stat-survival');
  const elTrend      = document.getElementById('hm-trend');
  const elDrill      = document.getElementById('hm-drill');
  const elDrillTitle = document.getElementById('hm-drill-title');
  const elDrillList  = document.getElementById('hm-drill-list');
  const elDrillClose = document.getElementById('hm-drill-close');

  // ── Helpers ───────────────────────────────────────────────────────────────
  function show(el) { if (el) el.hidden = false; }
  function hide(el) { if (el) el.hidden = true; }

  function escH(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function regionLabel(r) {
    return {
      center:       COPY.region_center || 'Center',
      edge:         COPY.region_edge   || 'Edge',
      corner:       COPY.region_corner || 'Corner',
      denseCluster: COPY.region_dense  || 'Dense cluster',
    }[r] || r;
  }

  // Heat colour: transparent → yellow → amber → red → dark red
  function heatColor(count, maxCount) {
    if (count <= 0 || maxCount <= 0) return null;
    const t = Math.min(count / maxCount, 1);
    if (t < 0.25) {
      const r = t / 0.25;
      return `rgba(252,211,77,${(0.25 + r * 0.45).toFixed(2)})`;
    }
    if (t < 0.55) {
      const r = (t - 0.25) / 0.30;
      return `rgba(245,158,11,${(0.70 + r * 0.20).toFixed(2)})`;
    }
    if (t < 0.80) {
      const r = (t - 0.55) / 0.25;
      return `rgba(239,68,68,${(0.85 + r * 0.10).toFixed(2)})`;
    }
    const r = (t - 0.80) / 0.20;
    const g = Math.round(68 - r * 41);
    return `rgba(${Math.round(239 - r * 86)},${g},${g},1)`;
  }

  // ── Board rendering ───────────────────────────────────────────────────────
  function renderBoard(data) {
    const w = data.board_width;
    const h = data.board_height;

    const cellMap = {};
    let maxCount = 0;
    (data.cells || []).forEach(function (c) {
      cellMap[c.x + ',' + c.y] = c.death_count;
      if (c.death_count > maxCount) maxCount = c.death_count;
    });

    elBoard.style.gridTemplateColumns = 'repeat(' + w + ', 20px)';
    elBoard.innerHTML = '';

    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const count = cellMap[x + ',' + y] || 0;
        const cell  = document.createElement('div');
        cell.className = 'hm-cell' + (count > 0 ? ' has-deaths' : '');
        cell.dataset.x = x;
        cell.dataset.y = y;
        cell.dataset.count = count;

        const overlay = document.createElement('div');
        overlay.className = 'hm-cell-heat';
        const color = heatColor(count, maxCount);
        if (color) overlay.style.background = color;
        cell.appendChild(overlay);
        elBoard.appendChild(cell);
      }
    }

    const diff = difficulty[0].toUpperCase() + difficulty.slice(1);
    elBoardTitle.textContent = 'Death heatmap (' + diff + ' · ' + w + '×' + h + ')';
    if (elLegendMax) {
      elLegendMax.textContent = maxCount + (maxCount >= 12 ? '+ deaths' : ' deaths');
    }
  }

  // ── Stat strip ────────────────────────────────────────────────────────────
  function renderStats(data) {
    const losses = data.losses || 0;
    const wins   = data.wins   || 0;
    const total  = data.games_analyzed || 0;
    const wr     = total > 0 ? Math.round(100 * wins / total) : 0;

    elStatGames.textContent     = total;
    elStatGamesMeta.textContent = losses + ' losses · ' + wins + ' wins · ' + wr + '% win rate';

    const topCause = (data.cause_breakdown || [])[0];
    if (topCause) {
      elStatCause.textContent    = topCause.display_name || topCause.cause;
      elStatCauseMeta.textContent = Math.round(topCause.pct * 100) + '% of deaths · ' + topCause.count + ' games';
    }

    const topRegion = (data.region_breakdown || [])[0];
    if (topRegion) {
      elStatRegion.textContent    = regionLabel(topRegion.region);
      elStatRegionMeta.textContent = Math.round(topRegion.pct * 100) + '% of deaths';
    }

    const surv = data.avg_survival_pct;
    elStatSurvival.textContent = (surv != null) ? Math.round(surv) + '%' : '—';
  }

  // ── Cause breakdown list ──────────────────────────────────────────────────
  function renderCauses(data) {
    const losses = data.losses || 0;
    elCauseSubtitle.textContent = losses + ' lost games classified.';

    elCauseList.innerHTML = '';
    (data.cause_breakdown || []).forEach(function (c) {
      const pct   = Math.round(c.pct * 100);
      const color = c.color || '#6b7280';
      const name  = escH(c.display_name || c.cause);

      const row = document.createElement('li');
      row.className = 'hm-breakdown-row';
      row.innerHTML =
        '<span class="hm-swatch" style="background:' + escH(color) + '"></span>' +
        '<span class="hm-breakdown-name">' + name + '</span>' +
        '<span class="hm-breakdown-pct">' + pct + '%</span>' +
        '<span class="hm-breakdown-count">' + c.count + '</span>';
      elCauseList.appendChild(row);

      const barWrap = document.createElement('li');
      barWrap.className = 'hm-breakdown-bar-wrap';
      barWrap.innerHTML =
        '<div class="hm-breakdown-bar">' +
        '<div class="hm-breakdown-bar-fill" style="width:' + pct + '%;background:' + escH(color) + '"></div>' +
        '</div>';
      elCauseList.appendChild(barWrap);
    });
  }

  // ── Region grid ───────────────────────────────────────────────────────────
  const REGION_COLORS = {
    center:       { bg: '#fee2e2', pctColor: '#b91c1c' },
    edge:         { bg: '#fef3c7', pctColor: '#b45309' },
    corner:       { bg: '#ede9fe', pctColor: '#7c3aed' },
    denseCluster: { bg: '#d1fae5', pctColor: '#065f46' },
  };

  function renderRegions(data) {
    elRegionGrid.innerHTML = '';
    (data.region_breakdown || []).forEach(function (r) {
      const pct    = Math.round(r.pct * 100);
      const colors = REGION_COLORS[r.region] || {};
      const tile   = document.createElement('div');
      tile.className = 'hm-region-tile';
      if (colors.bg) tile.style.background = colors.bg;
      tile.innerHTML =
        '<div class="hm-region-name">' + escH(regionLabel(r.region)) + '</div>' +
        '<div class="hm-region-pct"' + (colors.pctColor ? ' style="color:' + colors.pctColor + '"' : '') + '>' + pct + '%</div>' +
        '<div class="hm-region-count">' + r.count + ' deaths</div>';
      elRegionGrid.appendChild(tile);
    });
  }

  // ── Insights ──────────────────────────────────────────────────────────────
  function renderInsights(data) {
    elInsights.innerHTML = '';

    const avoidPct = data.avoidable_pct;
    const sitePct  = data.site_avoidable_pct;
    if (avoidPct != null) {
      const isHigh = sitePct != null && avoidPct > sitePct;
      const body   = (COPY.insight_avoidable_body || '{pct}% of your losses were classified as avoidable. Site average is {site_pct}%.')
        .replace('{pct}', avoidPct)
        .replace('{site_pct}', sitePct != null ? sitePct : '—');
      elInsights.appendChild(makeInsight(
        COPY.insight_avoidable_title || 'Avoidable deaths',
        body,
        isHigh ? 'warn' : ''
      ));
    }

    const edgePct = data.edge_pct;
    if (edgePct != null && edgePct > 0) {
      const body = (COPY.insight_edge_body || '{pct}% of your deaths happen on the edge.')
        .replace('{pct}', edgePct);
      const level = edgePct >= 35 ? 'warn' : edgePct <= 20 ? 'good' : '';
      elInsights.appendChild(makeInsight(
        COPY.insight_edge_title || 'Edge clustering',
        body,
        level
      ));
    }

    (data.anomalies || []).forEach(function (a) {
      elInsights.appendChild(makeInsight(a.type.replace(/_/g, ' '), escH(a.detail), 'warn'));
    });
  }

  function makeInsight(title, bodyHtml, level) {
    const div = document.createElement('div');
    div.className = 'hm-insight' + (level ? ' ' + level : '');
    div.innerHTML =
      '<div class="hm-insight-title">' + escH(title) + '</div>' +
      '<div class="hm-insight-body">' + bodyHtml + '</div>';
    return div;
  }

  // ── Trend bar chart ───────────────────────────────────────────────────────
  function renderTrend(data) {
    if (!elTrend) return;
    const trend = data.trend || [];
    if (trend.length === 0) {
      hide(elTrend);
      return;
    }

    const maxRate = Math.max.apply(null, trend.map(function (t) {
      return t.standard_avoidable_per_game || 0;
    }));

    let barsHtml = '';
    trend.forEach(function (t) {
      const rate = t.standard_avoidable_per_game || 0;
      const pct  = maxRate > 0 ? Math.round((rate / maxRate) * 100) : 0;
      const pctDisp = Math.round(rate * 100);
      const label = t.week_label.replace(/^\d{4}-/, '');  // e.g. "W32"
      barsHtml +=
        '<div class="hm-trend-col">' +
        '<div class="hm-trend-bar-wrap">' +
        '<div class="hm-trend-bar" style="height:' + pct + '%" title="' + escH(t.week_label) + ': ' + pctDisp + '% avoidable"></div>' +
        '</div>' +
        '<div class="hm-trend-label">' + escH(label) + '</div>' +
        '</div>';
    });

    elTrend.innerHTML =
      '<div class="hm-trend-heading">Avoidable-death rate by week</div>' +
      '<div class="hm-trend-chart">' + barsHtml + '</div>' +
      '<div class="hm-trend-caption">Each bar = % of that week\'s losses classified as avoidable</div>';

    show(elTrend);
  }

  // ── Cell drill-down ───────────────────────────────────────────────────────
  function openDrillDown(x, y) {
    if (!elDrill) return;
    if (elDrillTitle) elDrillTitle.textContent = 'Games that died at (' + x + ', ' + y + ')';
    if (elDrillList) elDrillList.innerHTML = '<li class="hm-drill-loading">Loading…</li>';
    show(elDrill);

    const url = API + '/heatmap/cell?x=' + x + '&y=' + y +
      '&difficulty=' + encodeURIComponent(difficulty) +
      '&mode=' + encodeURIComponent(mode) +
      '&time_range_days=' + encodeURIComponent(timeRange);

    fetch(url, {
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
    .then(function (res) { return res.json(); })
    .then(function (games) {
      if (!elDrillList) return;
      if (!games || games.length === 0) {
        elDrillList.innerHTML = '<li class="hm-drill-empty">No replay data for this cell.</li>';
        return;
      }
      elDrillList.innerHTML = '';
      games.forEach(function (g) {
        const secs = g.time_ms > 0 ? (g.time_ms / 1000).toFixed(1) + 's' : '—';
        const cause = g.death_cause ? g.death_cause.replace(/([A-Z])/g, ' $1').trim() : 'unknown';
        const li = document.createElement('li');
        li.className = 'hm-drill-item';
        li.innerHTML =
          '<a href="/game/' + escH(g.game_replay_id) + '" class="hm-drill-link">' +
          '<span class="hm-drill-date">' + escH(g.date) + '</span>' +
          '<span class="hm-drill-time">' + escH(secs) + '</span>' +
          '<span class="hm-drill-cause">' + escH(cause) + '</span>' +
          '<span class="hm-drill-arrow">→</span>' +
          '</a>';
        elDrillList.appendChild(li);
      });
    })
    .catch(function () {
      if (elDrillList) elDrillList.innerHTML = '<li class="hm-drill-empty">Failed to load games.</li>';
    });
  }

  // ── Tooltip ───────────────────────────────────────────────────────────────
  function attachTooltip() {
    elBoard.addEventListener('mouseover', function (e) {
      const cell = e.target.closest('.hm-cell');
      if (!cell) return;
      const count = parseInt(cell.dataset.count, 10) || 0;
      if (count === 0) {
        hide(elTooltip);
        return;
      }
      elTooltip.textContent = count + (count === 1 ? ' death' : ' deaths') +
        ' — (' + cell.dataset.x + ', ' + cell.dataset.y + ')';
      show(elTooltip);
    });

    elBoard.addEventListener('mousemove', function (e) {
      elTooltip.style.left = (e.clientX + 12) + 'px';
      elTooltip.style.top  = (e.clientY - 28) + 'px';
    });

    elBoard.addEventListener('mouseleave', function () {
      hide(elTooltip);
    });

    elBoard.addEventListener('click', function (e) {
      const cell = e.target.closest('.hm-cell.has-deaths');
      if (!cell) return;
      openDrillDown(parseInt(cell.dataset.x, 10), parseInt(cell.dataset.y, 10));
    });
  }

  // ── Fetch and render ──────────────────────────────────────────────────────
  function render(data) {
    renderStats(data);
    renderBoard(data);
    renderCauses(data);
    renderRegions(data);
    renderInsights(data);
    renderTrend(data);
    if (elDrill) hide(elDrill);
  }

  async function load() {
    hide(elMain);
    hide(elLoggedOut);
    hide(elEmpty);
    hide(elError);
    show(elLoading);

    const url = API + '/heatmap?difficulty=' + encodeURIComponent(difficulty) +
      '&mode=' + encodeURIComponent(mode) +
      '&time_range_days=' + encodeURIComponent(timeRange);

    try {
      const res = await fetch(url, {
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });

      hide(elLoading);

      if (res.status === 401) {
        show(elLoggedOut);
        return;
      }
      if (!res.ok) throw new Error('HTTP ' + res.status);

      const data = await res.json();

      if (!data.losses || data.losses === 0) {
        show(elEmpty);
        return;
      }

      render(data);
      show(elMain);
    } catch (err) {
      hide(elLoading);
      show(elError);
      console.error('[heatmap] load failed:', err);
    }
  }

  // ── Filter chip interactions ──────────────────────────────────────────────
  function initFilters() {
    document.querySelectorAll('.hm-chip[data-filter]').forEach(function (chip) {
      chip.addEventListener('click', function () {
        const group = chip.dataset.filter;
        const value = chip.dataset.value;

        document.querySelectorAll('.hm-chip[data-filter="' + group + '"]').forEach(function (c) {
          c.classList.remove('active');
        });
        chip.classList.add('active');

        if (group === 'difficulty') difficulty = value;
        if (group === 'time')       timeRange  = parseInt(value, 10);
        if (group === 'mode')       mode       = value;

        load();
      });
    });
  }

  // ── Drill-down close button ────────────────────────────────────────────────
  function initDrill() {
    if (elDrillClose) {
      elDrillClose.addEventListener('click', function () {
        hide(elDrill);
      });
    }
  }

  // ── Bootstrap ─────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    initFilters();
    initDrill();
    attachTooltip();
    load();
  });
}());
