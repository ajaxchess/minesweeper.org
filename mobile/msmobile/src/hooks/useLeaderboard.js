/**
 * useLeaderboard.js
 *
 * Data hook for the global leaderboard panel.
 * Fetches server scores only — local device scores live in MyScoresScreen.
 *
 * Exposes a `period` selector ('daily' | 'season' | 'alltime') that the UI
 * can drive with setPeriod. Changing period triggers a fresh fetch.
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchLeaderboard } from '../services/apiService';

export const PERIODS = ['daily', 'season', 'alltime'];

export default function useLeaderboard(mode, noGuess) {
  const [period,  setPeriod]  = useState('daily');
  const [scores,  setScores]  = useState([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    const serverScores = await fetchLeaderboard(mode, noGuess, period);
    setScores(serverScores ?? []);
    setLoading(false);
  }, [mode, noGuess, period]);

  useEffect(() => { refresh(); }, [refresh]);

  return { scores, loading, period, setPeriod, refresh };
}
