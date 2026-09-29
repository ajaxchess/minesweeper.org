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

export async function fetchBoard(dateStr) {
  try {
    const res = await fetchWithTimeout(
      `${BASE_URL}/api/numbers-match-board/${dateStr}`,
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
