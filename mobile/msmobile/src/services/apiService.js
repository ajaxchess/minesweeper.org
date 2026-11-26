/**
 * apiService.js
 *
 * HTTP client for the minesweeper.org API.
 *
 *   fetchGameToken()                  — POST /api/scores/start
 *   withMoveLog(payload, log, tokenP) — add the F-MS-VERIFY-APP fields
 *   submitScore(payload)              — POST /api/scores
 *   fetchLeaderboard(mode, ...)       — GET  /api/scores/{mode}
 *
 * Both return null on any network error, timeout, or non-success HTTP
 * status so callers can treat all failures identically (offline = null).
 * The spec forbids retry logic — do not add it here.
 */

import { Platform } from 'react-native';

const BASE_URL    = 'https://minesweeper.org';
const TIMEOUT_MS  = 10_000;

// Required on every request per APISpec.md csrf_xhr_check middleware.
// X-Client-Type tells the server which app sent a score (it was 'ios_app' on Android too).
export const CLIENT_TYPE = Platform.OS === 'android' ? 'android_app' : 'ios_app';
const XHR_HEADERS = {
  'X-Requested-With': 'XMLHttpRequest',
  'X-Client-Type':    CLIENT_TYPE,
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

// ── Verified scores (F-MS-VERIFY-APP) ─────────────────────────────────────────

/**
 * POST /api/scores/start — the signed start token for one game.
 * Fetched when a game is set up; resolves to null when offline.
 * @returns {Promise<string|null>}
 */
export async function fetchGameToken() {
  try {
    const res = await fetchWithTimeout(`${BASE_URL}/api/scores/start`, {
      method:  'POST',
      headers: { ...XHR_HEADERS, 'Content-Type': 'application/json' },
      body:    '{}',
    });
    if (!res.ok) return null;
    const data = await res.json();
    return typeof data?.token === 'string' ? data.token : null;
  } catch {
    return null;
  }
}

/**
 * Add the start token and move log to a score, so the server can replay the game
 * with the app's rules. Waits up to `waitMs` for a token still on its way; a score
 * without one is still saved, just not verified.
 */
export async function withMoveLog(payload, log, tokenP, waitMs = 3000) {
  if (!Array.isArray(log) || log.length === 0) return payload;
  const token = await Promise.race([
    Promise.resolve(tokenP).catch(() => null),
    new Promise(resolve => setTimeout(() => resolve(null), waitMs)),
  ]);
  return {
    ...payload,
    log,
    rules:    'msmobile',
    chording: true,
    ...(token ? { game_token: token } : {}),
  };
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
