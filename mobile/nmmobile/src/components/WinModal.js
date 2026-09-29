import React, { useState, useEffect, useCallback } from 'react';
import {
  Modal, View, Text, TextInput, TouchableOpacity,
  ActivityIndicator, StyleSheet,
} from 'react-native';
import { getPrefs, savePrefs } from '../services/storage';
import { submitNMScore }       from '../services/apiService';
import { fmtTime }             from '../gameEngine';

function StatRow({ label, value, theme }) {
  return (
    <View style={styles.statRow}>
      <Text style={[styles.statLabel, { color: theme.textDim }]}>{label}</Text>
      <Text style={[styles.statValue, { color: theme.text }]}>{value}</Text>
    </View>
  );
}

export default function WinModal({ visible, score, timeSecs, linesAdded, isPOTD, puzzleId, theme, onNewDaily, onRandom, onClose }) {
  const [name,         setName]         = useState('');
  const [submitting,   setSubmitting]   = useState(false);
  const [submitted,    setSubmitted]    = useState(false);
  const [submitResult, setSubmitResult] = useState(null); // 'ok' | 'error'

  const doSubmit = useCallback(async (nameToSave, persist = true) => {
    const trimmed = nameToSave.trim();
    if (!trimmed || submitting) return;
    setSubmitting(true);
    if (persist) await savePrefs({ playerName: trimmed });
    const result = await submitNMScore({
      name:        trimmed,
      puzzle_date: puzzleId,
      score,
      time_secs:   Math.max(1, timeSecs),
      lines_added: linesAdded,
    });
    setSubmitting(false);
    setSubmitted(true);
    setSubmitResult(result ? 'ok' : 'error');
  }, [submitting, puzzleId, score, timeSecs, linesAdded]);

  // Auto-save when modal opens if a name is already stored
  useEffect(() => {
    if (!visible || !isPOTD) return;
    setSubmitted(false);
    setSubmitResult(null);
    setSubmitting(false);

    getPrefs().then(prefs => {
      const stored = (prefs.playerName ?? '').trim();
      setName(stored);
      if (stored) doSubmit(stored, false);
    });
  }, [visible, isPOTD]);

  if (!visible) return null;

  return (
    <Modal visible={visible} transparent animationType="fade">
      <View style={styles.overlay}>
        <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>

          <View style={styles.titleRow}>
            <Text style={[styles.title, { color: theme.text }]}>🎉 Board Cleared!</Text>
            <TouchableOpacity onPress={onClose} hitSlop={{ top: 8, right: 8, bottom: 8, left: 8 }}>
              <Text style={[styles.closeBtn, { color: theme.textDim }]}>✕</Text>
            </TouchableOpacity>
          </View>

          {/* Stats */}
          <View style={[styles.statsBox, { borderColor: theme.border }]}>
            <StatRow label="Score"       value={String(score)}      theme={theme} />
            <StatRow label="Time"        value={fmtTime(timeSecs)}   theme={theme} />
            <StatRow label="Lines Added" value={String(linesAdded)} theme={theme} />
          </View>

          {/* Score submission */}
          {isPOTD && (
            submitting ? (
              <ActivityIndicator color={theme.accent} />
            ) : submitted ? (
              <Text style={[styles.resultText, {
                color: submitResult === 'ok' ? theme.accent : theme.textDim,
              }]}>
                {submitResult === 'ok' ? '✅ Score saved!' : '⚠️ Could not save score.'}
              </Text>
            ) : (
              <>
                <TextInput
                  style={[styles.nameInput, {
                    borderColor: theme.border, color: theme.text,
                    backgroundColor: theme.background,
                  }]}
                  placeholder="Your name"
                  placeholderTextColor={theme.textMuted}
                  value={name}
                  onChangeText={setName}
                  maxLength={32}
                  autoCorrect={false}
                  autoCapitalize="words"
                  returnKeyType="done"
                  onSubmitEditing={() => doSubmit(name)}
                />
                <TouchableOpacity
                  style={[styles.submitBtn, { backgroundColor: theme.accent },
                    !name.trim() && styles.disabled]}
                  onPress={() => doSubmit(name)}
                  disabled={!name.trim()}
                >
                  <Text style={[styles.btnText, { color: theme.accentText }]}>Save Score</Text>
                </TouchableOpacity>
              </>
            )
          )}

          {/* Navigation buttons */}
          <View style={styles.btnRow}>
            <TouchableOpacity
              style={[styles.navBtn, { borderColor: theme.border }]}
              onPress={onNewDaily}
            >
              <Text style={[styles.btnText, { color: theme.accent }]}>📅 Daily</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.navBtn, { borderColor: theme.border }]}
              onPress={onRandom}
            >
              <Text style={[styles.btnText, { color: theme.accent }]}>🎲 Play Again</Text>
            </TouchableOpacity>
          </View>

        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex:            1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent:  'center',
    alignItems:      'center',
    padding:         24,
  },
  card: {
    width:        '100%',
    maxWidth:     360,
    borderRadius: 12,
    borderWidth:  1,
    padding:      24,
    gap:          16,
  },
  titleRow:  { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  title:     { fontSize: 22, fontWeight: '700', flex: 1 },
  closeBtn:  { fontSize: 18, paddingLeft: 8 },
  statsBox:  { borderWidth: 1, borderRadius: 8, overflow: 'hidden' },
  statRow:   { flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 12, paddingVertical: 8 },
  statLabel: { fontSize: 14 },
  statValue: { fontSize: 14, fontWeight: '600' },
  nameInput: {
    borderWidth:       1,
    borderRadius:      8,
    paddingHorizontal: 12,
    paddingVertical:   10,
    fontSize:          15,
  },
  submitBtn:  { borderRadius: 8, paddingVertical: 12, alignItems: 'center' },
  disabled:   { opacity: 0.4 },
  btnRow:     { flexDirection: 'row', gap: 10 },
  navBtn:     { flex: 1, borderWidth: 1, borderRadius: 8, paddingVertical: 12, alignItems: 'center' },
  btnText:    { fontSize: 15, fontWeight: '600' },
  resultText: { textAlign: 'center', fontSize: 14, fontWeight: '500' },
});
