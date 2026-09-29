import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, SafeAreaView, ScrollView,
} from 'react-native';
import { useTheme } from '../context/ThemeContext';
import { getPrefs, savePrefs } from '../services/storage';

const THEME_OPTIONS = [
  { value: 'auto',  label: 'Auto (follows system)' },
  { value: 'light', label: 'Light' },
  { value: 'dark',  label: 'Dark' },
];

export default function SettingsScreen() {
  const { theme, themePref, setTheme } = useTheme();
  const [playerName, setPlayerName] = useState('');
  const [saved,      setSaved]      = useState(false);

  useEffect(() => {
    getPrefs().then(prefs => setPlayerName(prefs.playerName ?? ''));
  }, []);

  async function handleSaveName() {
    await savePrefs({ playerName: playerName.trim() });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  function Row({ children }) {
    return <View style={[styles.row, { borderBottomColor: theme.border }]}>{children}</View>;
  }

  return (
    <SafeAreaView style={[styles.root, { backgroundColor: theme.background }]}>
      <ScrollView contentContainerStyle={styles.content}>

        {/* Player name */}
        <Text style={[styles.label, { color: theme.textDim }]}>PLAYER NAME</Text>
        <View style={styles.nameRow}>
          <TextInput
            style={[styles.nameInput, {
              borderColor:     theme.border,
              color:           theme.text,
              backgroundColor: theme.surface,
            }]}
            placeholder="Enter your name"
            placeholderTextColor={theme.textMuted}
            value={playerName}
            onChangeText={t => { setPlayerName(t); setSaved(false); }}
            maxLength={32}
            autoCorrect={false}
            autoCapitalize="words"
            returnKeyType="done"
            onSubmitEditing={handleSaveName}
          />
          <TouchableOpacity
            style={[styles.saveBtn, { backgroundColor: theme.accent }]}
            onPress={handleSaveName}
          >
            <Text style={{ color: theme.accentText, fontWeight: '600', fontSize: 14 }}>
              {saved ? '✓' : 'Save'}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Theme picker */}
        <Text style={[styles.label, { color: theme.textDim, marginTop: 24 }]}>THEME</Text>
        <View style={[styles.card, { borderColor: theme.border, backgroundColor: theme.surface }]}>
          {THEME_OPTIONS.map((opt, i) => (
            <TouchableOpacity
              key={opt.value}
              style={[
                styles.themeRow,
                i < THEME_OPTIONS.length - 1 && { borderBottomWidth: 1, borderBottomColor: theme.border },
              ]}
              onPress={() => setTheme(opt.value)}
            >
              <Text style={[styles.themeLabel, { color: theme.text }]}>{opt.label}</Text>
              <View style={[styles.radio, { borderColor: theme.accent }]}>
                {themePref === opt.value && (
                  <View style={[styles.radioDot, { backgroundColor: theme.accent }]} />
                )}
              </View>
            </TouchableOpacity>
          ))}
        </View>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root:       { flex: 1 },
  content:    { padding: 20 },
  label:      { fontSize: 12, fontWeight: '600', letterSpacing: 0.5, marginBottom: 8 },
  nameRow:    { flexDirection: 'row', gap: 8 },
  nameInput:  { flex: 1, borderWidth: 1, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, fontSize: 15 },
  saveBtn:    { paddingHorizontal: 20, paddingVertical: 10, borderRadius: 8, justifyContent: 'center' },
  card:       { borderWidth: 1, borderRadius: 10, overflow: 'hidden' },
  themeRow:   { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 14 },
  themeLabel: { fontSize: 15 },
  radio:      { width: 20, height: 20, borderRadius: 10, borderWidth: 2, alignItems: 'center', justifyContent: 'center' },
  radioDot:   { width: 10, height: 10, borderRadius: 5 },
});
