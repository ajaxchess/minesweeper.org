import { useEffect, useRef, useCallback, useState } from 'react';
import { Audio } from 'expo-av';
import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = 'sound_muted';

const SOURCES = {
  reveal:  require('../../assets/sounds/reveal.wav'),
  flag:    require('../../assets/sounds/flag.wav'),
  explode: require('../../assets/sounds/explode.wav'),
  win:     require('../../assets/sounds/win.wav'),
};

export function useSounds() {
  const soundRefs = useRef({});
  const [muted, setMuted] = useState(false); // on by default

  // Load saved mute preference
  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY).then(val => {
      if (val === 'true') setMuted(true);
    }).catch(() => {});
  }, []);

  // Load audio files
  useEffect(() => {
    let mounted = true;

    Audio.setAudioModeAsync({ playsInSilentModeIOS: false }).catch(() => {});

    (async () => {
      for (const [key, source] of Object.entries(SOURCES)) {
        try {
          const { sound } = await Audio.Sound.createAsync(source, { shouldPlay: false });
          if (mounted) soundRefs.current[key] = sound;
        } catch {}
      }
    })();

    return () => {
      mounted = false;
      for (const sound of Object.values(soundRefs.current)) {
        sound?.unloadAsync().catch(() => {});
      }
      soundRefs.current = {};
    };
  }, []);

  const mutedRef = useRef(muted);
  mutedRef.current = muted;

  const play = useCallback(async (name) => {
    if (mutedRef.current) return;
    try {
      await soundRefs.current[name]?.replayAsync();
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
