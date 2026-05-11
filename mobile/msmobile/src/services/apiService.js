/**
 * apiService.js
 *
 * HTTP client for the minesweeper.org API.
 *
 *   submitScore(payload)              — POST /api/scores
 *   fetchLeaderboard(mode, ...)       — GET  /api/scores/{mode}
 *
 * Both return null on any network error, timeout, or non-success HTTP
 * status so callers can treat all failures identically (offline = null).
 * The spec forbids retry logic — do not add it here.
 */

const BASE_URL    = 'https://minesweeper.org';
const TIMEOUT_MS  = 10_000;

// Required on every request per APISpec.md csrf_xhr_check middleware.
const XHR_HEADERS = {
  'X-Requested-With': 'XMLHttpRequest',
  'X-Client-Type':    'ios_app',
};

async function fetchWithTimeout(url, options) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

// ── Score submission ───────────────────────────────────────────────────────────

/**
 * POST /api/scores
 *
 * Submits a completed game. Fields per APISpec.md:
 *   name, mode, time_secs, time_ms, rows, cols, mines,
 *   no_guess, board_hash, bbbv, left_clicks, right_clicks, chord_clicks
 *
 * @param {object} payload
 * @returns {{ ok: boolean, id: number } | null}
 *   Server response on HTTP 201, or null on any failure (network, 4xx, 5xx).
 */
export async function submitScore(payload) {
  try {
    const res = await fetchWithTimeout(`${BASE_URL}/api/scores`, {
      method:  'POST',
      headers: { ...XHR_HEADERS, 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });
    if (res.status === 201) return await res.json();
    // 403 = missing header (bug), 422 = bad payload, 429 = rate limit — none retriable
    return null;
  } catch {
    return null;
  }
}

// ── Leaderboard fetch ──────────────────────────────────────────────────────────

/**
 * GET /api/scores/{mode}
 *
 * @param {'beginner'|'intermediate'|'expert'} mode
 * @param {boolean} noGuess
 * @param {'daily'|'season'|'alltime'} [period='daily']
 * @param {{ date?: string, season_num?: number }} [opts={}]
 * @returns {Array | null} Score array (up to 15, fastest first), or null on failure.
 */
export async function fetchLeaderboard(mode, noGuess, period = 'daily', opts = {}) {
  const params = new URLSearchParams({
    no_guess: noGuess ? 'true' : 'false',
    period,
  });
  if (period === 'daily'  && opts.date       != null) params.set('date',       opts.date);
  if (period === 'season' && opts.season_num != null) params.set('season_num', String(opts.season_num));

  try {
    const res = await fetchWithTimeout(
      `${BASE_URL}/api/scores/${mode}?${params}`,
      { headers: XHR_HEADERS },
    );
    if (res.ok) return await res.json();
    return null;
  } catch {
    return null;
  }
}
