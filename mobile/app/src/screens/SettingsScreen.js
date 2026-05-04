/**
 * SettingsScreen.js
 *
 * Persisted keys (via storage.js getPrefs / savePrefs):
 *   prefs:default_mode    — beginner | intermediate | expert
 *   prefs:default_guess   — guess | noguess  (default: noguess)
 *   prefs:sound           — on | off          (default: on)
 *   prefs:player_name     — display name for score submission
 *   prefs:autosubmit      — yes | no          (only settable when name is set)
 *   prefs:on_win          — summary | newgame (only settable when autosubmit = yes)
 *   prefs:on_lose         — summary | newgame (settable when name is set)
 *   prefs:theme           — auto | light | dark
 *
 * All settings save immediately on change. Player name saves on blur / return.
 * Sound pref sets the initial mute state on next app open — the in-game 🔇
 * toggle still works within the current session independently.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  ScrollView,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  Linking,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { useTheme }            from '../context/ThemeContext';
import { getPrefs, savePrefs } from '../services/storage';

// ── Data ──────────────────────────────────────────────────────────────────────

const GAME_MODES = [
  { mode: 'beginner',     noGuess: false, label: 'Beginner'              },
  { mode: 'beginner',     noGuess: true,  label: 'Beginner No-Guess'     },
  { mode: 'intermediate', noGuess: false, label: 'Intermediate'          },
  { mode: 'intermediate', noGuess: true,  label: 'Intermediate No-Guess' },
  { mode: 'expert',       noGuess: false, label: 'Expert'                },
  { mode: 'expert',       noGuess: true,  label: 'Expert No-Guess'       },
];

const SOUNDS  = [{ value: 'on',  label: 'On'  }, { value: 'off', label: 'Off' }];
const THEMES  = [{ value: 'auto', label: 'Auto' }, { value: 'light', label: 'Light' }, { value: 'dark', label: 'Dark' }];
const ON_WINS  = [{ value: 'summary', label: 'Summary' }, { value: 'newgame', label: 'New Game' }];
const ON_LOSES = [{ value: 'summary', label: 'Summary' }, { value: 'newgame', label: 'New Game' }];

// ── Sub-components ────────────────────────────────────────────────────────────

function Divider({ theme }) {
  return <View style={[styles.divider, { backgroundColor: theme.border }]} />;
}

function SectionLabel({ children, theme }) {
  return <Text style={[styles.sectionLabel, { color: theme.textMuted }]}>{children}</Text>;
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

function RadioRow({ label, selected, onPress, theme, last }) {
  return (
    <TouchableOpacity
      style={[
        styles.radioRow,
        !last && { borderBottomWidth: 1, borderBottomColor: theme.border },
      ]}
      onPress={onPress}
      activeOpacity={0.6}
    >
      <Text style={[styles.radioLabel, { color: theme.text }]}>{label}</Text>
      {selected && <Text style={[styles.radioCheck, { color: theme.accent }]}>✓</Text>}
    </TouchableOpacity>
  );
}

// ── Screen ────────────────────────────────────────────────────────────────────

export default function SettingsScreen() {
  const { theme, themePref, setTheme } = useTheme();

  const [loading,      setLoading]      = useState(true);
  const [defaultMode,  setDefaultMode]  = useState('beginner');
  const [defaultGuess, setDefaultGuess] = useState('noguess');
  const [sound,        setSound]        = useState('on');
  const [playerName,   setPlayerName]   = useState('');
  const [autoSubmit,   setAutoSubmit]   = useState(false);
  const [onWin,        setOnWin]        = useState('summary');
  const [onLose,       setOnLose]       = useState('summary');

  useEffect(() => {
    getPrefs().then(prefs => {
      setDefaultMode(prefs.defaultMode   ?? 'beginner');
      setDefaultGuess(prefs.defaultGuess ?? 'noguess');
      setSound(prefs.sound               ?? 'on');
      setPlayerName(prefs.playerName     ?? '');
      setAutoSubmit(prefs.autoSubmit     ?? false);
      setOnWin(prefs.onWin               ?? 'summary');
      setOnLose(prefs.onLose             ?? 'summary');
      setLoading(false);
    });
  }, []);

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleModeSelect = useCallback((item) => {
    const guess = item.noGuess ? 'noguess' : 'guess';
    setDefaultMode(item.mode);
    setDefaultGuess(guess);
    savePrefs({ defaultMode: item.mode, defaultGuess: guess });
  }, []);

  const handleSoundChange = useCallback((val) => {
    setSound(val);
    savePrefs({ sound: val });
  }, []);

  const handleNameSave = useCallback(() => {
    const trimmed = playerName.trim();
    savePrefs({ playerName: trimmed });
    if (!trimmed) {
      setAutoSubmit(false);
      savePrefs({ autoSubmit: false });
    }
  }, [playerName]);

  const handleAutoSubmitChange = useCallback((val) => {
    const next = val === 'yes';
    setAutoSubmit(next);
    savePrefs({ autoSubmit: next });
    if (!next) {
      setOnWin('summary');
      savePrefs({ onWin: 'summary' });
    }
  }, []);

  const handleOnWinChange = useCallback((val) => {
    setOnWin(val);
    savePrefs({ onWin: val });
  }, []);

  const handleOnLoseChange = useCallback((val) => {
    setOnLose(val);
    savePrefs({ onLose: val });
  }, []);

  const handleThemeChange = useCallback((val) => {
    setTheme(val);
  }, [setTheme]);

  if (loading) {
    return (
      <View style={[styles.center, { backgroundColor: theme.background }]}>
        <ActivityIndicator color={theme.accent} />
      </View>
    );
  }

  const hasName       = playerName.trim().length > 0;
  const autoSubmitVal = autoSubmit ? 'yes' : 'no';

  return (
    <ScrollView
      style={{ backgroundColor: theme.background }}
      contentContainerStyle={styles.container}
      keyboardShouldPersistTaps="handled"
    >

      {/* ── Default game ──────────────────────────────────────────────── */}
      <View style={styles.section}>
        <SectionLabel theme={theme}>DEFAULT GAME</SectionLabel>
        <View style={[styles.radioList, { borderColor: theme.border }]}>
          {GAME_MODES.map((item, idx) => {
            const selected =
              item.mode === defaultMode &&
              (item.noGuess ? defaultGuess === 'noguess' : defaultGuess === 'guess');
            return (
              <RadioRow
                key={item.label}
                label={item.label}
                selected={selected}
                onPress={() => handleModeSelect(item)}
                theme={theme}
                last={idx === GAME_MODES.length - 1}
              />
            );
          })}
        </View>
      </View>

      <Divider theme={theme} />

      {/* ── Sound ─────────────────────────────────────────────────────── */}
      <View style={styles.section}>
        <SectionLabel theme={theme}>SOUND</SectionLabel>
        <View style={styles.row}>
          <Text style={[styles.rowLabel, { color: theme.textDim, width: 58 }]}>Default</Text>
          <SegmentedControl
            options={SOUNDS}
            value={sound}
            onSelect={handleSoundChange}
            theme={theme}
          />
        </View>
        <Text style={[styles.hint, { color: theme.textMuted }]}>
          Sets the sound state when you open the app. Use 🔇 in-game to toggle for the current session.
        </Text>
      </View>

      <Divider theme={theme} />

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

        {hasName && (
          <>
            <View style={styles.row}>
              <Text style={[styles.rowLabel, { color: theme.textDim, width: 84 }]}>Auto-submit</Text>
              <SegmentedControl
                options={[{ value: 'yes', label: 'Yes' }, { value: 'no', label: 'No' }]}
                value={autoSubmitVal}
                onSelect={handleAutoSubmitChange}
                theme={theme}
              />
            </View>
            <Text style={[styles.hint, { color: theme.textMuted }]}>
              Submits your score automatically on every win.
            </Text>
          </>
        )}

        {hasName && autoSubmit && (
          <>
            <View style={styles.row}>
              <Text style={[styles.rowLabel, { color: theme.textDim, width: 84 }]}>On win</Text>
              <SegmentedControl
                options={ON_WINS}
                value={onWin}
                onSelect={handleOnWinChange}
                theme={theme}
              />
            </View>
            <Text style={[styles.hint, { color: theme.textMuted }]}>
              Summary: show your stats until you tap New Game.{'\n'}
              New Game: show a brief stats banner, then start the next game automatically.
            </Text>
          </>
        )}

        {hasName && (
          <>
            <View style={styles.row}>
              <Text style={[styles.rowLabel, { color: theme.textDim, width: 84 }]}>On lose</Text>
              <SegmentedControl
                options={ON_LOSES}
                value={onLose}
                onSelect={handleOnLoseChange}
                theme={theme}
              />
            </View>
            <Text style={[styles.hint, { color: theme.textMuted }]}>
              Summary: board stays on screen until you tap New Game.{'\n'}
              New Game: automatically start a new game after half a second.
            </Text>
          </>
        )}
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
        <Text style={[styles.hint, { color: theme.textMuted }]}>
          Auto follows the iOS system setting.
        </Text>
      </View>

      <Divider theme={theme} />

      {/* ── About ─────────────────────────────────────────────────────── */}
      <View style={styles.section}>
        <SectionLabel theme={theme}>ABOUT</SectionLabel>
        <Text style={[styles.aboutText, { color: theme.textDim }]}>
          This game is dedicated to Diana, Princess of Wales. Her dream to ban
          landmines lives on at{' '}
          <Text
            style={[styles.aboutLink, { color: theme.accent }]}
            onPress={() => Linking.openURL('https://minesweeper.org/about')}
          >
            minesweeper.org
          </Text>
          .
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
    gap:               12,
  },
  sectionLabel: {
    fontSize:      11,
    fontWeight:    '600',
    letterSpacing: 0.8,
  },
  radioList: {
    borderWidth:  1,
    borderRadius: 10,
    overflow:     'hidden',
  },
  radioRow: {
    flexDirection:     'row',
    alignItems:        'center',
    justifyContent:    'space-between',
    paddingHorizontal: 16,
    paddingVertical:   13,
  },
  radioLabel: {
    fontSize: 15,
  },
  radioCheck: {
    fontSize:   17,
    fontWeight: '700',
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
  nameInput: {
    borderWidth:       1,
    borderRadius:      8,
    paddingHorizontal: 12,
    paddingVertical:   11,
    fontSize:          15,
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
    paddingVertical: 6,
  },
  segmentText: {
    fontSize:   13,
    fontWeight: '500',
  },
  hint: {
    fontSize:   12,
    marginTop:  -4,
    lineHeight: 17,
  },
  aboutText: {
    fontSize:   14,
    lineHeight: 22,
  },
  aboutLink: {
    fontWeight:         '600',
    textDecorationLine: 'underline',
  },
});
