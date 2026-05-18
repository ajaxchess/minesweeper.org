/**
 * static/js/bootcamp.js — Bootcamp page client.
 *
 * Reads window.BOOTCAMP_CONFIG (set inline by templates/bootcamp.html), fetches
 * /api/bootcamp/diagnosis, and renders the diagnosis panel, ladder, and 7
 * level cards. Mode toggle re-fetches with the selected mode.
 *
 * Pure vanilla JS, no framework. Mirrors the existing style of quests.js.
 */

(function () {
  'use strict';

  // ── Config + helpers ──────────────────────────────────────────────────────
  const cfg = window.BOOTCAMP_CONFIG || {};
  const copy = cfg.copy || {};
  const apiBase = cfg.apiBase || '/api';
  const difficulty = cfg.difficulty || 'expert';

  // Page-level state
  let currentMode = cfg.initialMode || 'standard';

  // ── DOM refs ──────────────────────────────────────────────────────────────
  const $loading   = document.getElementById('bc-loading');
  const $empty     = document.getElementById('bc-empty');
  const $error     = document.getElementById('bc-error');
  const $main      = document.getElementById('bc-main');
  const $modeTabs  = document.querySelectorAll('.bc-mode-tab');

  // ── Utility ───────────────────────────────────────────────────────────────
  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (ch) {
      return ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
      })[ch];
    });
  }

  function fmtTimeMs(ms) {
    if (ms == null) return '—';
    return (ms / 1000).toFixed(1) + 's';
  }

  function fmtPct(v) {
    if (v == null) return '—';
    return Math.round(v * 100) + '%';
  }

  function fmtNum(v, decimals) {
    if (v == null) return '—';
    return Number(v).toFixed(decimals == null ? 2 : decimals);
  }

  function show(el)  { if (el) el.hidden = false; }
  function hide(el)  { if (el) el.hidden = true; }

  // ── Data fetch ────────────────────────────────────────────────────────────
  async function fetchDiagnosis(mode) {
    const url = apiBase + '/bootcamp/diagnosis?difficulty=' +
                encodeURIComponent(difficulty) + '&mode=' + encodeURIComponent(mode);
    const resp = await fetch(url, {
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    });
    if (resp.status === 404 || resp.status === 425) {
      return { empty: true, status: resp.status };
    }
    if (!resp.ok) {
      throw new Error('HTTP ' + resp.status);
    }
    return await resp.json();
  }

  // ── Renderers ─────────────────────────────────────────────────────────────
  function renderDiagnosis(d) {
    document.getElementById('bc-current-level-name').textContent =
      'Level ' + d.current_level + ' — ' + d.current_level_name;
    document.getElementById('bc-current-level-tagline').textContent =
      d.current_level_tagline || '';
    document.getElementById('bc-profile-name').textContent =
      cfg.username + ' · ' + (d.difficulty[0].toUpperCase() + d.difficulty.slice(1));

    const remaining = Math.max(0, 7 - d.current_level);
    document.getElementById('bc-levels-to-master').textContent =
      remaining + ' ' + copy.levelsToMaster;

    document.getElementById('bc-stat-best').textContent       = fmtTimeMs(d.best_time_ms);
    document.getElementById('bc-stat-median').textContent     = 'Median ' + fmtTimeMs(d.median_time_ms);
    document.getElementById('bc-stat-bvs').textContent        = fmtNum(d.three_bv_per_sec);
    document.getElementById('bc-stat-ioe').textContent        = fmtNum(d.ioe);
    document.getElementById('bc-stat-correctness').textContent = fmtNum(d.correctness);
    document.getElementById('bc-stat-hierarchy').textContent  = fmtPct(d.hierarchy_compliance_pct);
    document.getElementById('bc-stat-throughput').textContent = fmtNum(d.throughput);

    const pct = Math.round((d.progress_pct_to_next || 0) * 100);
    document.getElementById('bc-progress-fill').style.width = pct + '%';
    document.getElementById('bc-progress-text').textContent =
      copy.progressToLevel + ' ' + Math.min(7, d.current_level + 1);
    document.getElementById('bc-progress-pct').textContent = pct + '%';
  }

  function renderLadder(levels) {
    const track = document.getElementById('bc-ladder-track');
    track.innerHTML = '';

    levels.forEach(function (lv) {
      const step = document.createElement('div');
      step.className = 'bc-ladder-step';

      const circle = document.createElement('div');
      circle.className = 'bc-step-circle bc-step-circle--' + lv.status;
      circle.textContent = lv.status === 'complete' ? '✓' : String(lv.level);

      const label = document.createElement('div');
      label.className = 'bc-step-label';
      label.textContent = 'L' + lv.level;

      const sub = document.createElement('div');
      sub.className = 'bc-step-sublabel';
      sub.textContent = shortLevelName(lv.name);

      step.appendChild(circle);
      step.appendChild(label);
      step.appendChild(sub);
      track.appendChild(step);
    });

    // Position the cumulative-progress overlay
    const completeCount = levels.filter(l => l.status === 'complete').length;
    track.dataset.complete = String(completeCount);
  }

  function shortLevelName(name) {
    // Compact ladder labels — fit small spaces
    return name
      .replace('Cut Wasted Clicks', 'Cut Waste')
      .replace('Effective Chording', 'Eff. Chording')
      .replace('Strategic No-Flag', 'Strategic NF')
      .replace('Pure Efficiency', 'Pure Efficiency')
      .replace('Opening Recognition', 'Openings')
      .replace('Flag Value', 'Flag Value')
      .replace('Fishing & Decision Hierarchy', 'Hierarchy');
  }

  function renderLevels(levels) {
    const container = document.getElementById('bc-levels');
    container.innerHTML = '';

    levels.forEach(function (lv, idx) {
      // Section divider before L5 (the Part 2 / Layer 4 transition)
      if (lv.level === 5) {
        const divider = document.createElement('div');
        divider.className = 'bc-section-divider';
        divider.textContent = '── Grand-Master Decision-Making (Part 2) ──';
        container.appendChild(divider);
      }

      container.appendChild(buildLevelCard(lv));
    });
  }

  function buildLevelCard(lv) {
    const card = document.createElement('div');
    card.className = 'bc-level-card bc-level-card--' + lv.status;

    // Summary row (always visible)
    const summary = document.createElement('div');
    summary.className = 'bc-level-summary';
    summary.innerHTML =
      '<div class="bc-level-summary-left">' +
        '<div class="bc-level-num bc-level-num--l' + lv.level + '">' + lv.level + '</div>' +
        '<div>' +
          '<div class="bc-level-name">' + escapeHtml(lv.name) + '</div>' +
          '<div class="bc-level-tagline">' + escapeHtml(lv.tagline) + '</div>' +
        '</div>' +
      '</div>' +
      '<div class="bc-level-summary-right">' +
        statusPill(lv) +
        (lv.status === 'current' ? '<span class="bc-level-expand">▾</span>' : '') +
      '</div>';
    card.appendChild(summary);

    // Body — fully expanded only for current level; locked levels get a preview
    if (lv.status === 'current') {
      card.appendChild(buildLevelBody(lv));
    } else if (lv.status === 'locked') {
      const preview = document.createElement('div');
      preview.className = 'bc-locked-preview';
      preview.textContent = copy.preview + ': ' + lv.tagline;
      card.appendChild(preview);
    }

    return card;
  }

  function statusPill(lv) {
    if (lv.status === 'complete')
      return '<span class="bc-level-status bc-level-status--complete">' + copy.completeTag + '</span>';
    if (lv.status === 'current')
      return '<span class="bc-level-status bc-level-status--current">' +
             copy.currentTag + ' · ' + Math.round(lv.mastery * 100) + '%</span>';
    if (lv.level === 7)
      return '<span class="bc-level-status bc-level-status--locked">' + copy.grandMasterTag + '</span>';
    return '<span class="bc-level-status bc-level-status--locked">' + copy.lockedTag + '</span>';
  }

  function buildLevelBody(lv) {
    const body = document.createElement('div');
    body.className = 'bc-level-body';
    body.innerHTML = '<div class="bc-level-loading">Loading level details…</div>';

    // Lazy-fetch the level detail
    fetch(apiBase + '/bootcamp/level/' + lv.level +
          '?difficulty=' + encodeURIComponent(difficulty) +
          '&mode=' + encodeURIComponent(currentMode), {
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
      .then(function (r) { return r.json(); })
      .then(function (detail) {
        body.innerHTML = renderLevelBody(detail);
      })
      .catch(function () {
        body.innerHTML = '<div class="bc-level-loading">Couldn’t load level details.</div>';
      });
    return body;
  }

  function renderLevelBody(detail) {
    const habitsHTML = (detail.habits || []).map(function (h) {
      const check = h.state === 'done'
        ? '<span class="bc-habit-check bc-habit-check--done">✓</span>'
        : h.state === 'partial'
          ? '<span class="bc-habit-check bc-habit-check--partial">◐</span>'
          : '<span class="bc-habit-check"></span>';
      return '<li class="bc-habit">' + check +
        '<span>' + escapeHtml(h.name) + '</span>' +
        '<span class="bc-habit-progress">' + Math.round(h.progress_pct * 100) + '%</span>' +
      '</li>';
    }).join('');

    const drillsHTML = (detail.drills || []).map(function (d, i) {
      const cls = i === 0 ? 'bc-btn bc-btn--primary' : 'bc-btn bc-btn--secondary';
      return '<div class="bc-drill">' +
        '<div>' +
          '<div class="bc-drill-name">' + escapeHtml(d.name) + '</div>' +
          '<div class="bc-drill-meta">' + d.board_count + ' boards · ' +
            '~' + d.estimated_minutes + ' min · ' + escapeHtml(d.target) +
          '</div>' +
        '</div>' +
        '<button class="' + cls + '" data-drill-id="' + escapeHtml(d.drill_id) + '">' +
          copy.startDrill +
        '</button>' +
      '</div>';
    }).join('');

    const grad = detail.graduation;
    const gradHTML = grad ? '<div class="bc-graduation">' +
      '<strong>' + copy.graduationLabel + ':</strong> ' + escapeHtml(grad.description) +
      '<div class="bc-graduation-progress">' +
        'Currently <strong>' + fmtNum(grad.current_value) + '</strong> · ' +
        'target ' + fmtNum(grad.target_value) +
      '</div>' +
    '</div>' : '';

    const citationHTML = detail.citation_url
      ? '<div class="bc-citation">From Dard’s ' +
        '<a href="' + escapeHtml(detail.citation_url) + '" target="_blank" rel="noopener">video</a>' +
        '</div>'
      : '';

    return '<div>' +
      '<div class="bc-section-label">' + copy.habitsLabel + '</div>' +
      '<ul class="bc-habits">' + habitsHTML + '</ul>' +
    '</div>' +
    '<div>' +
      '<div class="bc-section-label">' + copy.drillsLabel + '</div>' +
      '<div class="bc-drills">' + drillsHTML + '</div>' +
    '</div>' +
    gradHTML + citationHTML +
    '<div class="bc-level-actions">' +
      '<button class="bc-btn bc-btn--primary">' + copy.startDrill + ' today’s drill</button>' +
      '<button class="bc-btn bc-btn--secondary">' + copy.viewProgress + '</button>' +
    '</div>';
  }

  // ── Mode toggle ───────────────────────────────────────────────────────────
  function bindModeToggle() {
    $modeTabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        const mode = tab.dataset.mode;
        if (mode === currentMode) return;
        currentMode = mode;

        $modeTabs.forEach(function (t) {
          const active = t.dataset.mode === currentMode;
          t.classList.toggle('bc-mode-tab--active', active);
          t.setAttribute('aria-selected', active ? 'true' : 'false');
        });
        load();
      });
    });
  }

  // ── Footer meta ───────────────────────────────────────────────────────────
  function renderFooter(d) {
    const tpl = (copy.analyzedFromLast || 'Diagnosis based on your last {n} expert games');
    document.getElementById('bc-footer-meta').textContent = tpl.replace('{n}', '50');
  }

  // ── Boot ──────────────────────────────────────────────────────────────────
  async function load() {
    hide($main); hide($empty); hide($error);
    show($loading);

    try {
      const data = await fetchDiagnosis(currentMode);
      hide($loading);

      if (data.empty) {
        show($empty);
        return;
      }

      renderDiagnosis(data);
      renderLadder(data.levels || []);
      renderLevels(data.levels || []);
      renderFooter(data);
      show($main);
    } catch (err) {
      hide($loading);
      show($error);
      console.error('[bootcamp] load failed:', err);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    bindModeToggle();
    load();
  });
})();
