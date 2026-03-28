/**
 * SettingsScreen.js
 *
 * Persisted keys (via storage.js getPrefs / savePrefs):
 *   prefs:player_name    — display name for score submission
 *   prefs:default_mode   — beginner | intermediate | expert
 *   prefs:default_guess  — guess | noguess
 *   prefs:theme          — auto | light | dark (also applied via ThemeContext)
 *
 * All settings save immediately on change — no explicit Save button.
 * Player name saves on blur / return key so we don't thrash AsyncStorage.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  ScrollView,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { useTheme }        from '../context/ThemeContext';
import { getPrefs, savePrefs } from '../services/storage';

// ── Option sets ───────────────────────────────────────────────────────────────

const MODES   = [
  { value: 'beginner',     label: 'Beginner'  },
  { value: 'intermediate', label: 'Interm.'   },
  { value: 'expert',       label: 'Expert'    },
];
const GUESSES = [
  { value: 'guess',   label: 'Guess'    },
  { value: 'noguess', label: 'No-Guess' },
];
const THEMES  = [
  { value: 'auto',  label: 'Auto'  },
  { value: 'light', label: 'Light' },
  { value: 'dark',  label: 'Dark'  },
];

// ── Sub-components ────────────────────────────────────────────────────────────

function Divider({ theme }) {
  return <View style={[styles.divider, { backgroundColor: theme.border }]} />;
}

function SectionLabel({ children, theme }) {
  return (
    <Text style={[styles.sectionLabel, { color: theme.textMuted }]}>{children}</Text>
  );
}

function SegmentedControl({ options, value, onSelect, theme }) {
  return (
    <View style={[styles.segmented, { backgroundColor: theme.surface, borderColor: theme.border }]}>
      {options.map(opt => {
        const active = opt.value === value;
        return (
          <TouchableOpacity
            key={opt.value}
            style={[styles.segment, active && { backgroundColor: theme.accent }]}
            onPress={() => onSelect(opt.value)}
            activeOpacity={0.7}
          >
            <Text style={[styles.segmentText, { color: active ? theme.accentText : theme.textDim }]}>
              {opt.label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

// ── Screen ────────────────────────────────────────────────────────────────────

export default function SettingsScreen() {
  const { theme, themePref, setTheme } = useTheme();

  const [loading,      setLoading]      = useState(true);
  const [playerName,   setPlayerName]   = useState('');
  const [defaultMode,  setDefaultMode]  = useState('beginner');
  const [defaultGuess, setDefaultGuess] = useState('guess');

  // Load persisted prefs once on mount.
  useEffect(() => {
    getPrefs().then(prefs => {
      setPlayerName(prefs.playerName   ?? '');
      setDefaultMode(prefs.defaultMode ?? 'beginner');
      setDefaultGuess(prefs.defaultGuess ?? 'guess');
      setLoading(false);
    });
  }, []);

  // Save player name on blur or return key — not on every keystroke.
  const handleNameSave = useCallback(() => {
    savePrefs({ playerName: playerName.trim() });
  }, [playerName]);

  const handleModeChange = useCallback((value) => {
    setDefaultMode(value);
    savePrefs({ defaultMode: value });
  }, []);

  const handleGuessChange = useCallback((value) => {
    setDefaultGuess(value);
    savePrefs({ defaultGuess: value });
  }, []);

  const handleThemeChange = useCallback((value) => {
    setTheme(value); // ThemeContext saves to prefs and updates UI
  }, [setTheme]);

  if (loading) {
    return (
      <View style={[styles.center, { backgroundColor: theme.background }]}>
        <ActivityIndicator color={theme.accent} />
      </View>
    );
  }

  return (
    <ScrollView
      style={{ backgroundColor: theme.background }}
      contentContainerStyle={styles.container}
      keyboardShouldPersistTaps="handled"
    >

      {/* ── Player ────────────────────────────────────────────────────── */}
      <View style={styles.section}>
        <SectionLabel theme={theme}>PLAYER</SectionLabel>
        <TextInput
          style={[styles.nameInput, {
            borderColor:     theme.border,
            color:           theme.text,
            backgroundColor: theme.surface,
          }]}
          placeholder="Your name (for score submission)"
          placeholderTextColor={theme.textMuted}
          value={playerName}
          onChangeText={setPlayerName}
          onBlur={handleNameSave}
          onSubmitEditing={handleNameSave}
          maxLength={32}
          autoCorrect={false}
          autoCapitalize="words"
          returnKeyType="done"
        />
      </View>

      <Divider theme={theme} />

      {/* ── Game defaults ─────────────────────────────────────────────── */}
      <View style={styles.section}>
        <SectionLabel theme={theme}>GAME DEFAULTS</SectionLabel>

        <View style={styles.row}>
          <Text style={[styles.rowLabel, { color: theme.textDim }]}>Mode</Text>
          <SegmentedControl
            options={MODES}
            value={defaultMode}
            onSelect={handleModeChange}
            theme={theme}
          />
        </View>

        <View style={styles.row}>
          <Text style={[styles.rowLabel, { color: theme.textDim }]}>Board</Text>
          <SegmentedControl
            options={GUESSES}
            value={defaultGuess}
            onSelect={handleGuessChange}
            theme={theme}
          />
        </View>
      </View>

      <Divider theme={theme} />

      {/* ── Theme ─────────────────────────────────────────────────────── */}
      <View style={styles.section}>
        <SectionLabel theme={theme}>THEME</SectionLabel>
        <SegmentedControl
          options={THEMES}
          value={themePref}
          onSelect={handleThemeChange}
          theme={theme}
        />
        <Text style={[styles.themeHint, { color: theme.textMuted }]}>
          Auto follows the iOS system setting.
        </Text>
      </View>

    </ScrollView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  center: {
    flex: 1, justifyContent: 'center', alignItems: 'center',
  },
  container: {
    paddingBottom: 48,
  },
  divider: {
    height: 1,
  },
  section: {
    paddingHorizontal: 24,
    paddingVertical:   20,
    gap:               14,
  },
  sectionLabel: {
    fontSize:      11,
    fontWeight:    '600',
    letterSpacing: 0.8,
  },
  nameInput: {
    borderWidth:       1,
    borderRadius:      8,
    paddingHorizontal: 12,
    paddingVertical:   11,
    fontSize:          15,
  },
  row: {
    flexDirection: 'row',
    alignItems:    'center',
    gap:           12,
  },
  rowLabel: {
    fontSize: 14,
    width:    44,
  },
  segmented: {
    flex:          1,
    flexDirection: 'row',
    borderRadius:  8,
    borderWidth:   1,
    overflow:      'hidden',
  },
  segment: {
    flex:            1,
    alignItems:      'center',
    paddingVertical: 8,
  },
  segmentText: {
    fontSize:   13,
    fontWeight: '500',
  },
  themeHint: {
    fontSize:   12,
    marginTop:  -4,
  },
});
