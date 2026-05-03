import { useEffect, useRef, useCallback, useState } from 'react';
import { createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import { getPrefs } from '../services/storage';

const SOURCES = {
  reveal:  require('../../assets/sounds/reveal.wav'),
  flag:    require('../../assets/sounds/flag.wav'),
  explode: require('../../assets/sounds/explode.wav'),
  win:     require('../../assets/sounds/win.wav'),
};

export function useSounds() {
  const playerRefs = useRef({});
  const [muted, setMuted] = useState(false);

  // Initialise from the sound pref — sets the state for this session only.
  // The in-game toggle works within the session but does not save back to prefs.
  useEffect(() => {
    getPrefs().then(prefs => {
      setMuted(prefs.sound === 'off');
    }).catch(() => {});
  }, []);

  useEffect(() => {
    setAudioModeAsync({ playsInSilentModeIOS: false }).catch(() => {});
    for (const [key, source] of Object.entries(SOURCES)) {
      try {
        playerRefs.current[key] = createAudioPlayer(source);
      } catch {}
    }
    return () => {
      for (const player of Object.values(playerRefs.current)) {
        try { player?.remove(); } catch {}
      }
      playerRefs.current = {};
    };
  }, []);

  const mutedRef = useRef(muted);
  mutedRef.current = muted;

  const play = useCallback((name) => {
    if (mutedRef.current) return;
    try {
      const player = playerRefs.current[name];
      if (player) {
        player.seekTo(0);
        player.play();
      }
    } catch {}
  }, []);

  // In-session toggle only — does not persist. Use the Settings screen to
  // change the default sound state for the next app open.
  const toggleMute = useCallback(() => {
    setMuted(prev => !prev);
  }, []);

  return { play, muted, toggleMute };
}
