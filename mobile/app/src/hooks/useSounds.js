import { useEffect, useRef, useCallback, useState } from 'react';
import { createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = 'sound_muted';

const SOURCES = {
  reveal:  require('../../assets/sounds/reveal.wav'),
  flag:    require('../../assets/sounds/flag.wav'),
  explode: require('../../assets/sounds/explode.wav'),
  win:     require('../../assets/sounds/win.wav'),
};

export function useSounds() {
  const playerRefs = useRef({});
  const [muted, setMuted] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY).then(val => {
      if (val === 'true') setMuted(true);
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

  const toggleMute = useCallback(() => {
    setMuted(prev => {
      const next = !prev;
      AsyncStorage.setItem(STORAGE_KEY, String(next)).catch(() => {});
      return next;
    });
  }, []);

  return { play, muted, toggleMute };
}
