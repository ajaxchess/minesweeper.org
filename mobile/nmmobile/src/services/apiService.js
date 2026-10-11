import { Platform } from 'react-native';

const BASE_URL   = 'https://minesweeper.org';
const TIMEOUT_MS = 10_000;

const XHR_HEADERS = {
  'X-Requested-With': 'XMLHttpRequest',
  'X-Client-Type':    Platform.OS === 'ios' ? 'ios_app' : 'android_app',
};

async function fetchWithTimeout(url, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

// Today's puzzle date (America/New_York) and the current board revision, so the
// app plays the same boards as the website and the server can verify them.
export async function fetchToday() {
  try {
    const res = await fetchWithTimeout(`${BASE_URL}/api/numbers-match-today`, { headers: XHR_HEADERS });
    if (!res.ok) return null;
    const data = await res.json();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(data.today) || !/^v\d+$/.test(data.revision)) return null;
    return { today: data.today, revision: data.revision };
  } catch {
    return null;
  }
}

// Signed one-time token for a leaderboard game; required to submit its score.
export async function startGame(puzzleId) {
  try {
    const res = await fetchWithTimeout(`${BASE_URL}/api/numbers-match-start`, {
      method:  'POST',
      headers: { ...XHR_HEADERS, 'Content-Type': 'application/json' },
      body:    JSON.stringify({ puzzle_id: puzzleId }),
    });
    if (!res.ok) return null;
    return (await res.json()).token ?? null;
  } catch {
    return null;
  }
}

export async function fetchBoard(dateStr, revision) {
  try {
    const res = await fetchWithTimeout(
      `${BASE_URL}/api/numbers-match-board/${dateStr}?rev=${encodeURIComponent(revision)}`,
      { headers: XHR_HEADERS },
    );
    if (res.ok) return await res.json();
    return null;
  } catch {
    return null;
  }
}

export async function submitNMScore(payload) {
  try {
    const res = await fetchWithTimeout(`${BASE_URL}/api/numbers-match-scores`, {
      method:  'POST',
      headers: { ...XHR_HEADERS, 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });
    if (res.ok) return await res.json();
    return null;
  } catch {
    return null;
  }
}

export async function fetchNMLeaderboard(dateStr) {
  try {
    const res = await fetchWithTimeout(
      `${BASE_URL}/api/numbers-match-scores/${dateStr}`,
      { headers: XHR_HEADERS },
    );
    if (res.ok) return await res.json();
    return null;
  } catch {
    return null;
  }
}
