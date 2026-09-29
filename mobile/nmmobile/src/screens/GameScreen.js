import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, SafeAreaView, ActivityIndicator, Animated,
} from 'react-native';

import { useTheme }           from '../context/ThemeContext';
import useGameState           from '../hooks/useGameState';
import useTimer               from '../hooks/useTimer';
import BoardView              from '../components/BoardView';
import WinModal               from '../components/WinModal';
import AdBanner               from '../components/AdBanner';
import { fetchBoard }         from '../services/apiService';
import {
  generateBoardClient, fmtTime, getTodayString, getAxisCells,
} from '../gameEngine';

export default function GameScreen({ navigation }) {
  const { theme } = useTheme();
  const { state, initGame, pressCell, undo, hint, addLines, clearFlash, toggleConnections, dismissWin } = useGameState();
  const { board, rows, score, selected, hintPair, undosLeft, hintsLeft, addLinesLeft, won, started, isPOTD, puzzleId, linesAdded, addLinesFlash, showConnections } = state;

  const axisCells = useMemo(
    () => (showConnections && selected !== null) ? getAxisCells(board, selected) : [],
    [showConnections, selected, board],
  );

  const addLinesScale = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    if (!addLinesFlash) return;
    Animated.sequence([
      Animated.timing(addLinesScale, { toValue: 1.12, duration: 150, useNativeDriver: true }),
      Animated.timing(addLinesScale, { toValue: 1,    duration: 400, useNativeDriver: true }),
    ]).start(() => clearFlash());
  }, [addLinesFlash]);

  const elapsed = useTimer(started, won);

  const DIFFICULTIES = [
    { label: 'Easy',   rows: 4,  key: 'easy'   },
    { label: 'Medium', rows: 8,  key: 'medium' },
    { label: 'Hard',   rows: 16, key: 'hard'   },
    { label: 'Expert', rows: 32, key: 'expert' },
  ];

  const [loading,  setLoading]  = useState(false);
  const [loadErr,  setLoadErr]  = useState(false);
  const [mode,     setMode]     = useState('daily');   // 'daily' | 'random'
  const [diffRows, setDiffRows] = useState(4);

  // ── Load daily board ─────────────────────────────────────────────────────────
  const loadDaily = useCallback(async () => {
    setLoadErr(false);
    setLoading(true);
    const today = getTodayString();
    const data  = await fetchBoard(today);
    if (data) {
      initGame(data.board_data, data.rows, today, true);
      setMode('daily');
    } else {
      setLoadErr(true);
    }
    setLoading(false);
  }, [initGame]);

  // ── Generate random board ────────────────────────────────────────────────────
  const loadRandom = useCallback((rows = diffRows) => {
    const seed       = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    const diffEntry  = DIFFICULTIES.find(d => d.rows === rows);
    const puzzleId   = diffEntry ? `${getTodayString()}-${diffEntry.key}` : seed;
    const scored     = !!diffEntry;
    initGame(generateBoardClient(seed, rows), rows, puzzleId, scored);
    setDiffRows(rows);
    setMode('random');
  }, [initGame, diffRows]);

  // Start with daily on mount
  useEffect(() => { loadDaily(); }, []);

  // Win modal callbacks
  const handleNewDaily = useCallback(() => { loadDaily(); }, [loadDaily]);
  const handleRandom   = useCallback(() => { loadRandom(diffRows); }, [loadRandom, diffRows]);

  return (
    <SafeAreaView style={[styles.root, { backgroundColor: theme.background }]}>

      {/* ── Mode bar ─────────────────────────────────────────────────────── */}
      <View style={[styles.modeBar, { borderBottomColor: theme.border }]}>
        <TouchableOpacity
          style={[styles.modeBtn, mode === 'daily' && { backgroundColor: theme.accent }]}
          onPress={loadDaily}
        >
          <Text style={[styles.modeTxt, { color: mode === 'daily' ? theme.accentText : theme.textDim }]}>
            📅 Daily
          </Text>
        </TouchableOpacity>
        {DIFFICULTIES.map(({ label, rows }) => {
          const active = mode === 'random' && diffRows === rows;
          return (
            <TouchableOpacity
              key={rows}
              style={[styles.modeBtn, active && { backgroundColor: theme.accent }]}
              onPress={() => loadRandom(rows)}
            >
              <Text style={[styles.modeTxt, { color: active ? theme.accentText : theme.textDim }]}>
                {label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* ── Stats row ────────────────────────────────────────────────────── */}
      <View style={[styles.statsRow, { borderBottomColor: theme.border }]}>
        <Text style={[styles.stat, { color: theme.text }]}>⭐ {score}</Text>
        <Text style={[styles.stat, { color: theme.text }]}>⏱ {fmtTime(elapsed)}</Text>
        <TouchableOpacity onPress={() => navigation.navigate('Leaderboard', { puzzleDate: isPOTD ? puzzleId : null })}>
          <Text style={[styles.lbLink, { color: theme.accent }]}>🏆 Scores</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => navigation.navigate('Settings')}>
          <Text style={{ fontSize: 18 }}>⚙️</Text>
        </TouchableOpacity>
      </View>

      {/* ── Tool bar ─────────────────────────────────────────────────────── */}
      <View style={[styles.toolBar, { borderBottomColor: theme.border }]}>
        <TouchableOpacity
          style={[styles.toolBtn, { borderColor: theme.border, backgroundColor: theme.surface },
            (undosLeft <= 0 || !state.history.length) && styles.toolDisabled]}
          onPress={undo}
          disabled={undosLeft <= 0 || !state.history.length}
        >
          <Text style={[styles.toolTxt, { color: theme.text }]}>↩ {undosLeft}</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.toolBtn, { borderColor: theme.border, backgroundColor: theme.surface },
            hintsLeft <= 0 && styles.toolDisabled]}
          onPress={hint}
          disabled={hintsLeft <= 0}
        >
          <Text style={[styles.toolTxt, { color: theme.text }]}>💡 {hintsLeft}</Text>
        </TouchableOpacity>

        <Animated.View style={{ flex: 1.4, transform: [{ scale: addLinesScale }] }}>
          <TouchableOpacity
            style={[styles.toolBtn, styles.addBtn,
              { borderColor: addLinesFlash ? theme.text : theme.accent },
              addLinesLeft <= 0 && styles.toolDisabled]}
            onPress={addLines}
            disabled={addLinesLeft <= 0}
          >
            <Text style={[styles.toolTxt, { color: addLinesFlash ? theme.text : theme.accent }]}>
              + Add ({addLinesLeft})
            </Text>
          </TouchableOpacity>
        </Animated.View>

        <TouchableOpacity
          style={[styles.toolBtn, { borderColor: showConnections ? theme.accent : theme.border,
            backgroundColor: showConnections ? theme.surface : theme.surface }]}
          onPress={toggleConnections}
        >
          <Text style={[styles.toolTxt, { color: showConnections ? theme.accent : theme.textDim }]}>🔗 Paths</Text>
        </TouchableOpacity>
      </View>

      {/* ── Board ────────────────────────────────────────────────────────── */}
      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={theme.accent} />
          <Text style={[styles.loadTxt, { color: theme.textDim }]}>Loading puzzle…</Text>
        </View>
      ) : loadErr ? (
        <View style={styles.center}>
          <Text style={[styles.errTxt, { color: theme.textDim }]}>⚠️ Could not load today's puzzle.</Text>
          <TouchableOpacity onPress={loadDaily} style={[styles.retryBtn, { backgroundColor: theme.accent }]}>
            <Text style={{ color: theme.accentText, fontWeight: '600' }}>Retry</Text>
          </TouchableOpacity>
        </View>
      ) : board.length > 0 ? (
        <BoardView
          board={board}
          selected={selected}
          hintPair={hintPair}
          reachableCells={axisCells}
          theme={theme}
          onPress={pressCell}
        />
      ) : null}

      {/* ── Win modal ────────────────────────────────────────────────────── */}
      <WinModal
        visible={won}
        score={score}
        timeSecs={elapsed}
        linesAdded={linesAdded}
        isPOTD={isPOTD}
        puzzleId={puzzleId}
        theme={theme}
        onNewDaily={handleNewDaily}
        onRandom={handleRandom}
        onClose={dismissWin}
      />

      {/* ── AdMob banner ─────────────────────────────────────────────────── */}
      <AdBanner />

    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root:         { flex: 1 },
  modeBar:      { flexDirection: 'row', gap: 6, paddingHorizontal: 12, paddingVertical: 6, borderBottomWidth: 1 },
  modeBtn:      { flex: 1, alignItems: 'center', paddingVertical: 7, borderRadius: 6 },
  modeTxt:      { fontSize: 13, fontWeight: '600' },
  statsRow:     { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 8, borderBottomWidth: 1 },
  stat:         { fontSize: 15, fontWeight: '700' },
  lbLink:       { fontSize: 13, fontWeight: '600' },
  toolBar:      { flexDirection: 'row', gap: 8, paddingHorizontal: 12, paddingVertical: 6, borderBottomWidth: 1 },
  toolBtn:      { flex: 1, alignItems: 'center', paddingVertical: 7, borderRadius: 6, borderWidth: 1 },
  toolTxt:      { fontSize: 13, fontWeight: '600' },
  addBtn:       { flex: 1 },
  toolDisabled: { opacity: 0.35 },
  center:       { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16 },
  loadTxt:      { fontSize: 15, marginTop: 8 },
  errTxt:       { fontSize: 15, textAlign: 'center', paddingHorizontal: 24 },
  retryBtn:     { paddingHorizontal: 24, paddingVertical: 10, borderRadius: 8 },
});
