/**
 * useLeaderboard.js
 *
 * Data hook for the leaderboard panel.
 *
 * Fetches server scores and local scores in parallel, then merges them:
 *   - Deduplicate on (time_ms + board_hash); mode is implicit in the query.
 *   - Prefer the server record when both exist (server record has an `id`).
 *   - Sort merged result by time_ms ascending (fastest first).
 *
 * Exposes a `period` selector ('daily' | 'season' | 'alltime') that the UI
 * can drive with setPeriod. Changing period triggers a fresh fetch.
 *
 * On API failure fetchLeaderboard returns null; the hook falls back to
 * local-only scores without surfacing an error to the caller.
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchLeaderboard } from '../services/apiService';
import { getLocalScores }   from '../services/storage';

export const PERIODS = ['daily', 'season', 'alltime'];

// ── Merge helpers ─────────────────────────────────────────────────────────────

/**
 * Merge server and local score arrays.
 * Server records win on collision (they carry an `id`).
 * Result is sorted by time_ms ascending.
 */
function mergeScores(serverScores, localScores) {
  const map = new Map();

  // Insert server scores first so they take priority on duplicate keys.
  for (const s of serverScores) {
    map.set(`${s.time_ms}:${s.board_hash ?? ''}`, s);
  }

  // Add local scores that have no matching server record.
  for (const s of localScores) {
    const key = `${s.time_ms}:${s.board_hash ?? ''}`;
    if (!map.has(key)) map.set(key, s);
  }

  return [...map.values()].sort((a, b) => (a.time_ms ?? 0) - (b.time_ms ?? 0));
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export default function useLeaderboard(mode, noGuess) {
  const [period,  setPeriod]  = useState('daily');
  const [scores,  setScores]  = useState([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    const guessKey = noGuess ? 'noguess' : 'guess';

    const [serverScores, localScores] = await Promise.all([
      fetchLeaderboard(mode, noGuess, period),
      getLocalScores(mode, guessKey),
    ]);

    setScores(mergeScores(serverScores ?? [], localScores));
    setLoading(false);
  }, [mode, noGuess, period]);

  useEffect(() => { refresh(); }, [refresh]);

  return { scores, loading, period, setPeriod, refresh };
}
