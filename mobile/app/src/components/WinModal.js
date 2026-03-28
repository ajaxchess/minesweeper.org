/**
 * WinModal.js
 *
 * Shown automatically when the player wins.
 *
 * Responsibilities:
 *   - Compute bbbv, board_hash, efficiency, 3BV/s from props
 *   - Load stored player name; allow editing before submit
 *   - POST to /api/scores via submitScore; fall back to local on failure
 *   - saveLocalScore always — with server id on success, without on failure
 *   - Persist player name to prefs after first successful entry
 *
 * Dismissed only via the "New Game" button, which calls onNewGame() in
 * GameScreen. That resets game state (won → false), which hides the modal.
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  Modal,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';

import { calc3BV, calcBoardHash } from '../gameEngine';
import { getPrefs, savePrefs, saveLocalScore } from '../services/storage';
import { submitScore } from '../services/apiService';

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatTime(ms) {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${s}s`;
}

function StatRow({ label, value, theme }) {
  return (
    <View style={styles.statRow}>
      <Text style={[styles.statLabel, { color: theme.textDim }]}>{label}</Text>
      <Text style={[styles.statValue, { color: theme.text }]}>{value}</Text>
    </View>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function WinModal({
  visible,
  mode,
  noGuess,
  rows,
  cols,
  mines,
  board,
  mineSet,
  elapsedMs,
  leftClicks,
  rightClicks,
  chordClicks,
  theme,
  onNewGame,
}) {
  const [playerName, setPlayerName] = useState('');
  const [submitting,  setSubmitting]  = useState(false);
  const [submitted,   setSubmitted]   = useState(false);
  const [submitResult, setSubmitResult] = useState(null); // 'ok' | 'offline'

  // Reset submit state and load stored name each time the modal appears.
  useEffect(() => {
    if (!visible) return;
    setSubmitted(false);
    setSubmitResult(null);
    getPrefs().then(prefs => {
      if (prefs.playerName) setPlayerName(prefs.playerName);
    });
  }, [visible]);

  // Computed once per win — board/mineSet are stable after the game ends.
  const stats = useMemo(() => {
    if (!board || !mineSet) return null;
    const bbbv      = calc3BV(board, rows, cols, mineSet);
    const boardHash = calcBoardHash(rows, cols, mineSet);
    const total     = leftClicks + rightClicks + chordClicks;
    const efficiency  = total > 0    ? bbbv / total               : 0;
    const bbbvPerSec  = elapsedMs > 0 ? bbbv / (elapsedMs / 1000) : 0;
    return { bbbv, boardHash, efficiency, bbbvPerSec };
  }, [board, mineSet, rows, cols, elapsedMs, leftClicks, rightClicks, chordClicks]);

  async function handleSubmit() {
    if (!playerName.trim() || !stats || submitting) return;
    setSubmitting(true);

    const name     = playerName.trim();
    const guessKey = noGuess ? 'noguess' : 'guess';

    await savePrefs({ playerName: name });

    const payload = {
      name,
      mode,
      time_secs:    Math.floor(elapsedMs / 1000),
      time_ms:      elapsedMs,
      rows,
      cols,
      mines,
      no_guess:     noGuess,
      board_hash:   stats.boardHash,
      bbbv:         stats.bbbv,
      left_clicks:  leftClicks,
      right_clicks: rightClicks,
      chord_clicks: chordClicks,
    };

    const result = await submitScore(payload);

    // Always persist locally; attach server id when available.
    await saveLocalScore(mode, guessKey, {
      ...payload,
      ...(result?.id != null ? { id: result.id } : {}),
    });

    setSubmitting(false);
    setSubmitted(true);
    setSubmitResult(result ? 'ok' : 'offline');
  }

  if (!visible || !stats) return null;

  const canSubmit = playerName.trim().length > 0 && !submitting;

  return (
    <Modal visible={visible} transparent animationType="fade">
      <View style={styles.overlay}>
        <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>

          <Text style={[styles.title, { color: theme.text }]}>You Win! 🎉</Text>

          {/* ── Stats ─────────────────────────────────────────────────── */}
          <View style={[styles.statsBox, { borderColor: theme.border }]}>
            <StatRow label="Time"       value={formatTime(elapsedMs)}                theme={theme} />
            <StatRow label="3BV"        value={String(stats.bbbv)}                   theme={theme} />
            <StatRow label="3BV/s"      value={stats.bbbvPerSec.toFixed(2)}          theme={theme} />
            <StatRow label="Efficiency" value={(stats.efficiency * 100).toFixed(1) + '%'} theme={theme} />
          </View>

          {/* ── Name + submit ──────────────────────────────────────────── */}
          {submitted ? (
            <Text style={[
              styles.resultText,
              { color: submitResult === 'ok' ? theme.accent : theme.textDim },
            ]}>
              {submitResult === 'ok' ? 'Score submitted!' : 'Saved locally (offline)'}
            </Text>
          ) : (
            <>
              <TextInput
                style={[styles.nameInput, {
                  borderColor:     theme.border,
                  color:           theme.text,
                  backgroundColor: theme.background,
                }]}
                placeholder="Your name"
                placeholderTextColor={theme.textMuted}
                value={playerName}
                onChangeText={setPlayerName}
                maxLength={32}
                autoCorrect={false}
                autoCapitalize="words"
                returnKeyType="done"
                onSubmitEditing={handleSubmit}
              />
              <TouchableOpacity
                style={[
                  styles.submitBtn,
                  { backgroundColor: theme.accent },
                  !canSubmit && styles.disabledBtn,
                ]}
                onPress={handleSubmit}
                disabled={!canSubmit}
              >
                {submitting
                  ? <ActivityIndicator color={theme.accentText} />
                  : <Text style={[styles.btnText, { color: theme.accentText }]}>Submit Score</Text>
                }
              </TouchableOpacity>
            </>
          )}

          {/* ── New Game ───────────────────────────────────────────────── */}
          <TouchableOpacity
            style={[styles.newGameBtn, { borderColor: theme.border }]}
            onPress={onNewGame}
          >
            <Text style={[styles.btnText, { color: theme.accent }]}>New Game</Text>
          </TouchableOpacity>

        </View>
      </View>
    </Modal>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  overlay: {
    flex:            1,
    backgroundColor: 'rgba(0,0,0,0.55)',
    justifyContent:  'center',
    alignItems:      'center',
    padding:         24,
  },
  card: {
    width:         '100%',
    maxWidth:      360,
    borderRadius:  12,
    borderWidth:   1,
    padding:       24,
    gap:           16,
  },
  title: {
    fontSize:   22,
    fontWeight: '700',
    textAlign:  'center',
  },
  statsBox: {
    borderWidth:  1,
    borderRadius: 8,
    overflow:     'hidden',
  },
  statRow: {
    flexDirection:     'row',
    justifyContent:    'space-between',
    paddingHorizontal: 12,
    paddingVertical:   8,
  },
  statLabel: {
    fontSize: 14,
  },
  statValue: {
    fontSize:   14,
    fontWeight: '600',
  },
  nameInput: {
    borderWidth:   1,
    borderRadius:  8,
    paddingHorizontal: 12,
    paddingVertical:   10,
    fontSize:      15,
  },
  submitBtn: {
    borderRadius:    8,
    paddingVertical: 12,
    alignItems:      'center',
  },
  disabledBtn: {
    opacity: 0.4,
  },
  newGameBtn: {
    borderWidth:   1,
    borderRadius:  8,
    paddingVertical: 12,
    alignItems:    'center',
  },
  btnText: {
    fontSize:   15,
    fontWeight: '600',
  },
  resultText: {
    textAlign:  'center',
    fontSize:   14,
    fontWeight: '500',
  },
});
