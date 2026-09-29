import { useState, useEffect, useRef } from 'react';

export default function useTimer(started, over) {
  const [secs, setSecs] = useState(0);
  const startRef    = useRef(null);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (started && !over) {
      if (!startRef.current) startRef.current = Date.now();
      clearInterval(intervalRef.current);
      intervalRef.current = setInterval(() => {
        setSecs(Math.floor((Date.now() - startRef.current) / 1000));
      }, 500);
    } else {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    return () => clearInterval(intervalRef.current);
  }, [started, over]);

  // Reset when a new game starts
  useEffect(() => {
    if (!started) {
      setSecs(0);
      startRef.current = null;
    }
  }, [started]);

  return secs;
}
