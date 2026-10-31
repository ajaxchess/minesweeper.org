import React, { createContext, useContext, useEffect, useState } from 'react';
import { useColorScheme } from 'react-native';
import { getPrefs, savePrefs } from '../services/storage';

export const THEMES = {
  light: {
    background:  '#ffffff',
    surface:     '#f4f4f4',
    border:      '#d0d0d0',
    text:        '#111111',
    textDim:     '#555555',
    textMuted:   '#888888',
    accent:      '#2563eb',
    accent2:     '#00bcd4',
    accentText:  '#ffffff',
    cellCovered: '#c8c8c8',
    cellEmpty:   '#e8e8e8',
    cellHover:   '#b0b0b0',
    // Colour of numbers 1-9 (index 0 unused); same values as style.css.
    numbers: ['', '#8e1010', '#0b3d91', '#0f5a1c', '#7a3a00', '#5e1190', '#574a00', '#00545c', '#93105a', '#141414'],
  },
  dark: {
    background:  '#1a1a1a',
    surface:     '#2a2a2a',
    border:      '#444444',
    text:        '#eeeeee',
    textDim:     '#aaaaaa',
    textMuted:   '#666666',
    accent:      '#3b82f6',
    accent2:     '#00bcd4',
    accentText:  '#ffffff',
    cellCovered: '#3a3a3a',
    cellEmpty:   '#252525',
    cellHover:   '#5a5a5a',
    numbers: ['', '#ff8080', '#64b5f6', '#66d96b', '#ffa726', '#c4a6ff', '#ffee58', '#26e0d0', '#ff7fc4', '#f0f0f0'],
  },
};

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const systemScheme = useColorScheme();
  const [themePref, setThemePref] = useState('auto');

  useEffect(() => {
    getPrefs().then(prefs => { if (prefs.theme) setThemePref(prefs.theme); });
  }, []);

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
