/* bootcamp_replays.js — Replay list page (F-BC-REPLAY) */
(function () {
  'use strict';

  var CFG  = window.REPLAYS_CONFIG || {};
  var api  = CFG.apiBase || '/api';
  var copy = CFG.copy    || {};

  var elLoading = document.getElementById('brl-loading');
  var elEmpty   = document.getElementById('brl-empty');
  var elError   = document.getElementById('brl-error');
  var elMain    = document.getElementById('brl-main');
  var elTotal   = document.getElementById('brl-total');
  var elTbody   = document.getElementById('brl-tbody');

  function show(el) { if (el) el.hidden = false; }
  function hide(el) { if (el) el.hidden = true;  }
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function fmtDuration(ms) {
    if (!ms) return '—';
    var s = Math.round(ms / 1000);
    var m = Math.floor(s / 60);
    var sec = s % 60;
    return m > 0 ? m + ':' + (sec < 10 ? '0' : '') + sec : sec + 's';
  }

  function fmtDate(iso) {
    if (!iso) return '—';
    var d = new Date(iso);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function outcomeHtml(outcome) {
    var cls = 'brl-outcome--' + (outcome || 'abandon');
    var label = copy[outcome] || outcome || '—';
    return '<span class="brl-outcome ' + cls + '">' + esc(label) + '</span>';
  }

  function renderRow(r) {
    return [
      '<tr>',
        '<td class="brl-num">' + esc(fmtDate(r.created_at)) + '</td>',
        '<td>' + outcomeHtml(r.outcome) + '</td>',
        '<td class="brl-num">' + esc(fmtDuration(r.duration_ms)) + '</td>',
        '<td class="brl-num">' + (r.ioe != null ? r.ioe.toFixed(2) : '—') + '</td>',
        '<td class="brl-num">' + (r.hierarchy_compliance_pct != null ? Math.round(r.hierarchy_compliance_pct) + '%' : '—') + '</td>',
        '<td class="brl-num">' + (r.three_bv != null ? r.three_bv : '—') + '</td>',
        '<td><a class="brl-review-btn" href="/bootcamp/replay/' + r.game_replay_id + '">' + esc(copy.view || 'Review') + '</a></td>',
      '</tr>',
    ].join('');
  }

  fetch(api + '/replays', {
    credentials: 'same-origin',
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
  })
  .then(function (r) {
    if (r.status === 404) return null;
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  })
  .then(function (data) {
    hide(elLoading);
    if (!data || !data.replays || data.replays.length === 0) { show(elEmpty); return; }

    var totalTpl = copy.total || '{n} analyzed games';
    elTotal.textContent = totalTpl.replace('{n}', data.total);
    elTbody.innerHTML = data.replays.map(renderRow).join('');
    show(elMain);
  })
  .catch(function () {
    hide(elLoading);
    show(elError);
  });
}());
