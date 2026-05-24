/*
 * static/js/drill.js — Bootcamp drill runner.
 *
 * Loaded by templates/drill.html. Reads the drill_id off the .dr-page
 * data-attribute, fetches state via /api/drills/{id}, renders one board at
 * a time, handles the click → submit → feedback flow, then renders results.
 *
 * No frameworks; mirrors the bootcamp.js style (delegated events,
 * defensive null checks, escapeHtml everywhere).
 */
(function () {
  'use strict';

  // ── State ────────────────────────────────────────────────────────────────
  const pageEl   = document.querySelector('.dr-page');
  const drillId  = pageEl ? parseInt(pageEl.getAttribute('data-drill-id'), 10) : null;

  let state = {
    drill: null,                  // server response from /api/drills/{id}
    currentIndex: 0,              // which board the player is on
    boardClickAt: null,           // performance.now() when board rendered
    completed: false,
  };

  // ── Lifecycle ────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', init);

  async function init() {
    if (!drillId || Number.isNaN(drillId)) {
      showError('Missing drill id in page URL.');
      return;
    }

    try {
      const drill = await fetchJSON('/api/drills/' + drillId);
      state.drill = drill;

      // If the drill is already complete, jump straight to results.
      if (drill.completed_at) {
        state.completed = true;
        renderResults(drill.summary || null);
        return;
      }

      // Otherwise, advance to the first unanswered board.
      const answered = (drill.attempts || []).length;
      state.currentIndex = Math.min(answered, drill.num_boards - 1);

      show('dr-runner');
      hide('dr-loading');
      bindButtons();
      renderCurrentBoard();
    } catch (err) {
      showError(err && err.message ? err.message : 'Unknown error');
    }
  }

  // ── Networking ───────────────────────────────────────────────────────────
  async function fetchJSON(url, opts) {
    const resp = await fetch(url, Object.assign({
      method: 'GET',
      credentials: 'same-origin',
      headers: { 'Accept': 'application/json' },
    }, opts || {}));
    if (!resp.ok) {
      let msg = 'HTTP ' + resp.status;
      try {
        const j = await resp.json();
        if (j && j.detail) msg = j.detail;
      } catch (_) { /* ignore */ }
      throw new Error(msg);
    }
    return resp.json();
  }

  function postJSON(url, body) {
    return fetchJSON(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body || {}),
    });
  }

  // ── Rendering ────────────────────────────────────────────────────────────
  function renderCurrentBoard() {
    const idx   = state.currentIndex;
    const drill = state.drill;
    const board = drill.boards[idx];
    if (!board) {
      showError('Internal error: missing board ' + idx);
      return;
    }

    // Header counters
    setText('dr-progress-label', (idx + 1) + ' / ' + drill.num_boards);
    const correctSoFar = (drill.attempts || []).filter(
      (a) => a.result && a.result.is_correct
    ).length;
    setText('dr-accuracy-label', correctSoFar + ' correct');
    const fill = (idx / drill.num_boards) * 100;
    setStyle('dr-progress-fill', 'width', fill + '%');

    renderBoardGrid(board);

    state.boardClickAt = (window.performance && performance.now) ? performance.now() : Date.now();
  }

  function renderBoardGrid(board) {
    const boardEl = document.getElementById('dr-board');
    if (!boardEl) return;
    boardEl.innerHTML = '';
    boardEl.style.gridTemplateColumns = 'repeat(' + board.width + ', 22px)';

    // Map revealed cells + numbers for fast lookup.
    const revealedSet = new Set(board.revealed.map(rc => rc[0] + ',' + rc[1]));
    const numbersMap  = new Map(board.numbers.map(rcn => [rcn[0] + ',' + rcn[1], rcn[2]]));

    for (let r = 0; r < board.height; r++) {
      for (let c = 0; c < board.width; c++) {
        const cell = document.createElement('div');
        cell.className = 'dr-cell';
        cell.setAttribute('role', 'gridcell');
        cell.dataset.row = r;
        cell.dataset.col = c;
        const key = r + ',' + c;
        if (revealedSet.has(key)) {
          cell.classList.add('dr-cell--revealed');
          const n = numbersMap.get(key);
          if (typeof n === 'number') {
            cell.classList.add('dr-cell--n' + n);
            cell.textContent = String(n);
          }
        } else {
          cell.addEventListener('click', onCellClick);
        }
        boardEl.appendChild(cell);
      }
    }
  }

  // ── Click flow ───────────────────────────────────────────────────────────
  async function onCellClick(ev) {
    const cell = ev.currentTarget;
    if (!cell || cell.classList.contains('dr-cell--revealed')) return;

    // Disable further clicks for this board.
    cell.classList.add('dr-cell--picked');
    const boardEl = document.getElementById('dr-board');
    if (boardEl) {
      Array.prototype.forEach.call(boardEl.children, (c) => {
        c.style.pointerEvents = 'none';
      });
    }

    const r = parseInt(cell.dataset.row, 10);
    const c = parseInt(cell.dataset.col, 10);

    const startedAt = state.boardClickAt || Date.now();
    const nowFn = (window.performance && performance.now) ? performance.now() : Date.now();
    const decisionMs = Math.max(0, Math.round(nowFn - startedAt));

    let resp;
    try {
      resp = await postJSON('/api/drills/' + drillId + '/submit', {
        board_index: state.currentIndex,
        chosen_row: r,
        chosen_col: c,
        decision_ms: decisionMs,
      });
    } catch (err) {
      showError('Submit failed: ' + (err && err.message ? err.message : 'unknown'));
      return;
    }

    // Mark the cell with the verdict, highlight the optimal cell if missed.
    const verdict = resp.result;
    if (verdict.is_correct) {
      cell.classList.add('dr-cell--correct');
    } else {
      cell.classList.add('dr-cell--wrong');
      const optKey = verdict.optimal_row + ',' + verdict.optimal_col;
      const optEl = boardEl ? boardEl.querySelector(
        '[data-row="' + verdict.optimal_row + '"][data-col="' + verdict.optimal_col + '"]'
      ) : null;
      if (optEl) optEl.classList.add('dr-cell--optimal');
    }

    showFeedback(verdict, resp);
    // Stash the new state so re-renders use up-to-date attempts list.
    if (!state.drill.attempts) state.drill.attempts = [];
    state.drill.attempts.push({
      board_index: state.currentIndex,
      chosen_row: r, chosen_col: c, decision_ms: decisionMs,
      result: verdict,
    });
    state.lastResponse = resp;
  }

  function showFeedback(verdict, resp) {
    const fb       = document.getElementById('dr-feedback');
    const iconEl   = document.getElementById('dr-feedback-icon');
    const titleEl  = document.getElementById('dr-feedback-title');
    const bodyEl   = document.getElementById('dr-feedback-body');
    const nextBtn  = document.getElementById('dr-next-btn');

    if (!fb || !iconEl || !titleEl || !bodyEl || !nextBtn) return;

    iconEl.className = 'dr-feedback-icon';
    if (verdict.is_mine) {
      iconEl.classList.add('dr-feedback-icon--mine');
      iconEl.textContent = '💣';
      titleEl.textContent = 'Mine!';
      bodyEl.textContent =
        'That cell hides a mine. The best pick (highlighted) opens ' +
        verdict.optimal_opening_size + ' cells.';
    } else if (verdict.is_correct) {
      iconEl.classList.add('dr-feedback-icon--correct');
      iconEl.textContent = '✓';
      titleEl.textContent = 'Nice pick';
      bodyEl.textContent =
        'Opens ' + verdict.opening_size +
        ' cells (' + Math.round(verdict.relative_quality * 100) +
        '% of the best available).';
    } else {
      iconEl.classList.add('dr-feedback-icon--wrong');
      iconEl.textContent = '✗';
      titleEl.textContent = 'Small opening';
      bodyEl.textContent =
        'That cell only opens ' + verdict.opening_size +
        ' cells. The best pick (highlighted) opens ' +
        verdict.optimal_opening_size + '.';
    }

    // Last board → "See results"; otherwise → "Next board"
    if (resp && resp.completed) {
      nextBtn.textContent = 'See results →';
    } else {
      nextBtn.textContent = 'Next board →';
    }

    show('dr-feedback');
  }

  function onNextClick() {
    hide('dr-feedback');
    const resp = state.lastResponse;
    if (resp && resp.completed) {
      state.completed = true;
      renderResults(resp.summary || null);
      return;
    }
    state.currentIndex += 1;
    renderCurrentBoard();
  }

  // ── Results ──────────────────────────────────────────────────────────────
  function renderResults(summary) {
    hide('dr-runner');
    show('dr-results');

    if (!summary) {
      // Fall back to recomputing from state.
      const drill = state.drill || {};
      const attempts = drill.attempts || [];
      const correct = attempts.filter((a) => a.result && a.result.is_correct).length;
      const total = drill.num_boards || attempts.length || 0;
      const decisions = attempts.map((a) => a.decision_ms).filter((n) => n > 0);
      const avg = decisions.length
        ? Math.round(decisions.reduce((s, n) => s + n, 0) / decisions.length)
        : 0;
      summary = {
        num_correct: correct,
        num_total: total,
        accuracy_pct: total ? Math.round((1000 * correct) / total) / 10 : 0,
        avg_decision_ms: avg,
        mastery_contribution: total ? correct / total : 0,
        counted_toward_mastery: false,
      };
    }

    setText('dr-stat-accuracy',
      summary.num_correct + ' / ' + summary.num_total +
      '  (' + summary.accuracy_pct.toFixed(0) + '%)'
    );
    setText('dr-stat-avg', (summary.avg_decision_ms / 1000).toFixed(1) + 's');
    setText('dr-stat-mastery', summary.mastery_contribution.toFixed(2));

    const iconEl = document.getElementById('dr-results-icon');
    const titleEl = document.getElementById('dr-results-title');
    const blurbEl = document.getElementById('dr-results-blurb');
    if (summary.accuracy_pct >= 80) {
      if (iconEl)  iconEl.textContent  = '🎯';
      if (titleEl) titleEl.textContent = 'Sharp eye';
      if (blurbEl) blurbEl.textContent =
        'You spotted the best opening on most boards. Keep drilling — this is what graduating L5 looks like.';
    } else if (summary.accuracy_pct >= 50) {
      if (iconEl)  iconEl.textContent  = '👀';
      if (titleEl) titleEl.textContent = 'Solid';
      if (blurbEl) blurbEl.textContent =
        'You’re seeing the openings about half the time. Run this drill daily and watch the score climb.';
    } else {
      if (iconEl)  iconEl.textContent  = '🌱';
      if (titleEl) titleEl.textContent = 'Building the reflex';
      if (blurbEl) blurbEl.textContent =
        'Look for cells far from existing numbers — corners and edges of unrevealed areas.';
    }
  }

  // ── Buttons ──────────────────────────────────────────────────────────────
  function bindButtons() {
    const next  = document.getElementById('dr-next-btn');
    const again = document.getElementById('dr-again-btn');
    if (next)  next.addEventListener('click', onNextClick);
    if (again) again.addEventListener('click', onAgainClick);
  }

  async function onAgainClick() {
    try {
      const drill = state.drill || {};
      const created = await postJSON('/api/drills/start', {
        drill_type: drill.drill_type || 'l5_opening_recognition',
        level: drill.level || 5,
        difficulty: drill.difficulty || 'expert',
        mode: drill.mode || 'standard',
        num_boards: drill.num_boards || 10,
      });
      window.location.href = '/drill/' + created.drill_id;
    } catch (err) {
      showError('Could not start a new drill: ' + (err.message || 'unknown'));
    }
  }

  // ── DOM helpers ──────────────────────────────────────────────────────────
  function show(id) { const el = document.getElementById(id); if (el) el.hidden = false; }
  function hide(id) { const el = document.getElementById(id); if (el) el.hidden = true; }
  function setText(id, txt) {
    const el = document.getElementById(id);
    if (el) el.textContent = txt;
  }
  function setStyle(id, prop, val) {
    const el = document.getElementById(id);
    if (el) el.style[prop] = val;
  }
  function showError(detail) {
    hide('dr-loading');
    hide('dr-runner');
    show('dr-error');
    setText('dr-error-detail', detail || '');
  }

}());
