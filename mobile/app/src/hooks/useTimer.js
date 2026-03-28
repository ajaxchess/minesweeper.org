/**
 * useTimer.js
 *
 * Returns elapsed time in milliseconds for a minesweeper game.
 *
 * - Starts (and records startTime) the moment `started` becomes true.
 * - Freezes when `over` becomes true — the interval is cleared and
 *   elapsedMs holds the final value.
 * - Resets to 0 when `started` returns to false (new game).
 *
 * Ticks every 100 ms, which is fine for a seconds display. Phase 4 reads
 * the frozen elapsedMs for score submission so millisecond precision is
 * preserved in the returned value.
 */

import { useState, useEffect, useRef } from 'react';

export default function useTimer(started, over) {
  const [elapsedMs, setElapsedMs] = useState(0);
  const startTimeRef = useRef(null);

  // Start interval when the game begins; freeze (via cleanup) when it ends.
  useEffect(() => {
    if (!started || over) return;
    startTimeRef.current = Date.now();
    const id = setInterval(() => {
      setElapsedMs(Date.now() - startTimeRef.current);
    }, 100);
    return () => clearInterval(id);
  }, [started, over]);

  // Reset display when a new game begins.
  useEffect(() => {
    if (!started) setElapsedMs(0);
  }, [started]);

  return elapsedMs;
}
