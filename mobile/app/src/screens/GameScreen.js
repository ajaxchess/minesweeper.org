/**
 * GameScreen.js
 *
 * Main game screen. Manages mode/no-guess selection and renders the board.
 * Touch callbacks (onPressCell, onLongPressCell) are wired here but the
 * actual reveal/flag/chord logic lives in useGameState.
 *
 * Phase 3b adds: flag mode button, pinch-to-zoom, chord handling.
 * Phase 3c adds: timer display.
 * Phase 4  adds: win modal, score submission.
 */

import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
} from 'react-native';

import { useTheme } from '../context/ThemeContext';
import useGameState from '../hooks/useGameState';
import BoardView    from '../components/BoardView';

const MODES = ['beginner', 'intermediate', 'expert'];

export default function GameScreen({ navigation }) {
  const { theme }  = useTheme();
  const {
    state,
    newGame,
    setMode,
    setNoGuess,
    revealCell,
    toggleFlag,
  } = useGameState('beginner', false);

  const { rows, cols, mines, board, mineSet, revealed, flagged,
          explodedIdx, over, won, mode, noGuess } = state;

  // ── Status text ───────────────────────────────────────────────────────────
  let statusText = `${mines} mines`;
  if (won)  statusText = '🎉 You win!';
  if (over && !won) statusText = '💥 Game over';

  return (
    <SafeAreaView style={[styles.root, { backgroundColor: theme.background }]}>

      {/* ── Mode selector ──────────────────────────────────────────────── */}
      <View style={[styles.modeBar, { borderBottomColor: theme.border }]}>
        {MODES.map(m => (
          <TouchableOpacity
            key={m}
            style={[
              styles.modeBtn,
              mode === m && { backgroundColor: theme.accent },
            ]}
            onPress={() => setMode(m)}
          >
            <Text
              style={[
                styles.modeBtnText,
                { color: mode === m ? theme.accentText : theme.textDim },
              ]}
            >
              {m.charAt(0).toUpperCase() + m.slice(1)}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* ── Options row ────────────────────────────────────────────────── */}
      <View style={[styles.optionsRow, { borderBottomColor: theme.border }]}>
        <TouchableOpacity
          style={[styles.optionBtn, noGuess && { backgroundColor: theme.accent }]}
          onPress={() => setNoGuess(!noGuess)}
        >
          <Text style={{ color: noGuess ? theme.accentText : theme.textDim, fontSize: 13 }}>
            No-Guess
          </Text>
        </TouchableOpacity>

        <Text style={[styles.statusText, { color: theme.text }]}>
          {statusText}
        </Text>

        <TouchableOpacity
          style={styles.optionBtn}
          onPress={() => newGame(mode, noGuess)}
        >
          <Text style={{ color: theme.accent, fontSize: 13, fontWeight: '600' }}>
            New Game
          </Text>
        </TouchableOpacity>
      </View>

      {/* ── Board ──────────────────────────────────────────────────────── */}
      <BoardView
        rows={rows}
        cols={cols}
        board={board}
        mineSet={mineSet}
        revealed={revealed}
        flagged={flagged}
        explodedIdx={explodedIdx}
        gameOver={over}
        gameWon={won}
        theme={theme}
        onPressCell={revealCell}
        onLongPressCell={toggleFlag}
      />

    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  modeBar: {
    flexDirection:    'row',
    justifyContent:   'center',
    paddingVertical:  6,
    paddingHorizontal: 8,
    gap:              6,
    borderBottomWidth: 1,
  },
  modeBtn: {
    flex:            1,
    alignItems:      'center',
    paddingVertical: 6,
    borderRadius:    6,
  },
  modeBtnText: {
    fontSize:   13,
    fontWeight: '600',
  },
  optionsRow: {
    flexDirection:     'row',
    alignItems:        'center',
    justifyContent:    'space-between',
    paddingHorizontal: 12,
    paddingVertical:   6,
    borderBottomWidth: 1,
  },
  optionBtn: {
    paddingHorizontal: 10,
    paddingVertical:   5,
    borderRadius:      6,
  },
  statusText: {
    fontSize:   14,
    fontWeight: '600',
  },
});
