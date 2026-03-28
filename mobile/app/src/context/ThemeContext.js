import React, { createContext, useContext, useEffect, useState } from 'react';
import { useColorScheme } from 'react-native';
import { getPrefs, savePrefs } from '../services/storage';

// ── Colour palettes ───────────────────────────────────────────────────────────

export const THEMES = {
  light: {
    background:   '#ffffff',
    surface:      '#f4f4f4',
    border:       '#d0d0d0',
    text:         '#111111',
    textDim:      '#555555',
    textMuted:    '#888888',
    accent:       '#2563eb',
    accentText:   '#ffffff',
    cellCovered:  '#c0c0c0',
    cellRevealed: '#e8e8e8',
    cellHover:    '#b0b0b0',
    mine:         '#cc0000',
    flag:         '#e67e00',
    numberColors: ['', '#0000ff', '#007b00', '#ff0000', '#00007b', '#7b0000', '#007b7b', '#000000', '#7b7b7b'],
  },
  dark: {
    background:   '#1a1a1a',
    surface:      '#2a2a2a',
    border:       '#444444',
    text:         '#eeeeee',
    textDim:      '#aaaaaa',
    textMuted:    '#666666',
    accent:       '#3b82f6',
    accentText:   '#ffffff',
    cellCovered:  '#4a4a4a',
    cellRevealed: '#2e2e2e',
    cellHover:    '#5a5a5a',
    mine:         '#ff4444',
    flag:         '#f59e0b',
    numberColors: ['', '#6eb5ff', '#6fcf7c', '#ff6b6b', '#a78bfa', '#f87171', '#34d399', '#eeeeee', '#aaaaaa'],
  },
};

// ── Context ───────────────────────────────────────────────────────────────────

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const systemScheme = useColorScheme(); // 'light' | 'dark' | null
  const [themePref, setThemePref] = useState('auto'); // 'auto' | 'light' | 'dark'

  // Load persisted preference on mount
  useEffect(() => {
    getPrefs().then(prefs => {
      if (prefs.theme) setThemePref(prefs.theme);
    });
  }, []);

  // Resolve actual scheme: pref overrides OS, 'auto' follows OS
  const resolvedScheme = themePref === 'auto'
    ? (systemScheme === 'dark' ? 'dark' : 'light')
    : themePref;

  const theme = THEMES[resolvedScheme];

  async function setTheme(value) {
    setThemePref(value);
    await savePrefs({ theme: value });
  }

  return (
    <ThemeContext.Provider value={{ theme, themePref, setTheme, resolvedScheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
