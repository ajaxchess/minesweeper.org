/**
 * WinToast.js
 *
 * Bottom-anchored win notification shown when autoSubmit + onWin = 'newgame'.
 * Displays time, 3BV, and efficiency, then fades out after 5 seconds.
 * GameScreen triggers the new game when the toast disappears.
 */

import React, { useEffect, useRef } from 'react';
import { Animated, StyleSheet, Text, View } from 'react-native';

function formatTime(ms) {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${s}s`;
}

export default function WinToast({ visible, elapsedMs, bbbv, efficiency, theme, bottomOffset = 80 }) {
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!visible) {
      opacity.setValue(0);
      return;
    }
    opacity.setValue(1);
    // Start fading at 4.2 s so the animation completes at ~5 s
    const timer = setTimeout(() => {
      Animated.timing(opacity, {
        toValue:         0,
        duration:        800,
        useNativeDriver: true,
      }).start();
    }, 4200);
    return () => clearTimeout(timer);
  }, [visible, opacity]);

  if (!visible) return null;

  return (
    <Animated.View style={[styles.toast, {
      backgroundColor: theme.surface,
      borderColor:     theme.border,
      opacity,
      bottom:          bottomOffset,
    }]}>
      <Text style={[styles.winText, { color: theme.accent }]}>🎉 You Win!</Text>
      <View style={styles.statsRow}>
        <Text style={[styles.stat, { color: theme.text }]}>{formatTime(elapsedMs)}</Text>
        <Text style={[styles.dot,  { color: theme.textMuted }]}>·</Text>
        <Text style={[styles.stat, { color: theme.text }]}>3BV {bbbv}</Text>
        <Text style={[styles.dot,  { color: theme.textMuted }]}>·</Text>
        <Text style={[styles.stat, { color: theme.text }]}>{efficiency}% eff</Text>
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  toast: {
    position:          'absolute',
    left:              16,
    right:             16,
    borderRadius:      10,
    borderWidth:       1,
    paddingVertical:   10,
    paddingHorizontal: 16,
    alignItems:        'center',
    gap:               4,
    shadowColor:       '#000',
    shadowOffset:      { width: 0, height: 2 },
    shadowOpacity:     0.18,
    shadowRadius:      4,
    elevation:         4,
  },
  winText: {
    fontSize:   15,
    fontWeight: '700',
  },
  statsRow: {
    flexDirection: 'row',
    gap:           8,
    alignItems:    'center',
  },
  stat: {
    fontSize:   13,
    fontWeight: '500',
  },
  dot: {
    fontSize: 13,
  },
});
