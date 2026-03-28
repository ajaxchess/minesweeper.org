/**
 * GameScreen.js
 *
 * Main game screen. Manages mode/no-guess selection and renders the board.
 *
 * Phase 3b additions:
 *   - flagMode toggle: tapping a cell flags/unflags instead of revealing
 *   - chord routing: tapping a revealed numbered cell dispatches CHORD
 *   - zoomScale state passed down to BoardView for pinch-to-zoom
 *
 * Phase 3c adds: timer display.
 * Phase 4  adds: win modal, score submission.
 */

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
} from 'react-native';

import { useTheme } from '../context/ThemeContext';
import useGameState  from '../hooks/useGameState';
import BoardView     from '../components/BoardView';

const MODES = ['beginner', 'intermediate', 'expert'];

export default function GameScreen({ navigation }) {
  const { theme } = useTheme();
  const {
    state,
    newGame,
    setMode,
    setNoGuess,
    revealCell,
    toggleFlag,
    chordCell,
  } = useGameState('beginner', false);

  const {
    rows, cols, mines, board, mineSet, revealed, flagged,
    explodedIdx, over, won, mode, noGuess, started,
  } = state;

  // ── Local UI state ────────────────────────────────────────────────────────
  const [flagMode,  setFlagMode]  = useState(false);
  const [zoomScale, setZoomScale] = useState(1.0);

  // ── Press routing ─────────────────────────────────────────────────────────
  //
  // Priority:
  //   1. Flag mode active   → always flag/unflag
  //   2. Tap revealed cell with value > 0 and game started → chord
  //   3. Default            → reveal
  //
  const handlePressCell = useCallback((idx) => {
    if (flagMode) {
      toggleFlag(idx);
      return;
    }
    if (started && revealed[idx] === 1 && board !== null) {
      const r = Math.floor(idx / cols);
      const c = idx % cols;
      if (board[r][c] > 0) {
        chordCell(idx);
        return;
      }
    }
    revealCell(idx);
  }, [flagMode, started, revealed, board, cols, toggleFlag, chordCell, revealCell]);

  // Long-press always flags regardless of flagMode
  const handleLongPressCell = useCallback((idx) => {
    toggleFlag(idx);
  }, [toggleFlag]);

  // Reset flag mode when switching mode (new board context)
  const handleSetMode = useCallback((m) => {
    setFlagMode(false);
    setMode(m);
  }, [setMode]);

  // Reset flag mode on explicit new game
  const handleNewGame = useCallback(() => {
    setFlagMode(false);
    newGame(mode, noGuess);
  }, [mode, noGuess, newGame]);

  // ── Status text ───────────────────────────────────────────────────────────
  let statusText = `${mines} mines`;
  if (won)          statusText = '🎉 You win!';
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
            onPress={() => handleSetMode(m)}
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

        <TouchableOpacity style={styles.optionBtn} onPress={handleNewGame}>
          <Text style={{ color: theme.accent, fontSize: 13, fontWeight: '600' }}>
            New Game
          </Text>
        </TouchableOpacity>
      </View>

      {/* ── Tool row: flag mode + zoom reset ──────────────────────────── */}
      <View style={[styles.toolRow, { borderBottomColor: theme.border }]}>
        <TouchableOpacity
          style={[styles.toolBtn, flagMode && { backgroundColor: theme.accent }]}
          onPress={() => setFlagMode(f => !f)}
          accessibilityLabel="Toggle flag mode"
          accessibilityRole="button"
        >
          <Text style={{ fontSize: 18 }}>🚩</Text>
        </TouchableOpacity>

        {zoomScale !== 1.0 && (
          <TouchableOpacity
            style={styles.toolBtn}
            onPress={() => setZoomScale(1.0)}
          >
            <Text style={{ color: theme.textDim, fontSize: 12 }}>Reset Zoom</Text>
          </TouchableOpacity>
        )}
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
        zoomScale={zoomScale}
        onZoomChange={setZoomScale}
        onPressCell={handlePressCell}
        onLongPressCell={handleLongPressCell}
      />

    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  modeBar: {
    flexDirection:     'row',
    justifyContent:    'center',
    paddingVertical:   6,
    paddingHorizontal: 8,
    gap:               6,
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
  toolRow: {
    flexDirection:     'row',
    alignItems:        'center',
    paddingHorizontal: 12,
    paddingVertical:   4,
    borderBottomWidth: 1,
    gap:               8,
  },
  toolBtn: {
    paddingHorizontal: 12,
    paddingVertical:   4,
    borderRadius:      6,
  },
});
