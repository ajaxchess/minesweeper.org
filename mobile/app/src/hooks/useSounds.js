import { useEffect, useRef, useCallback } from 'react';
import { Audio } from 'expo-av';

const SOURCES = {
  reveal:  require('../../assets/sounds/reveal.wav'),
  flag:    require('../../assets/sounds/flag.wav'),
  explode: require('../../assets/sounds/explode.wav'),
  win:     require('../../assets/sounds/win.wav'),
};

export function useSounds() {
  const soundRefs = useRef({});

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

  return useCallback(async (name) => {
    try {
      await soundRefs.current[name]?.replayAsync();
    } catch {}
  }, []);
}
