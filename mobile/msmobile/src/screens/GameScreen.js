/**
 * GameScreen.js
 *
 * Main game screen. Manages mode/no-guess selection and renders the board.
 *
 * On mount, loads prefs to set the default mode, no-guess, autoSubmit, and
 * onWin settings.  autoSubmit + onWin prefs are re-read on every focus so
 * changes made in SettingsScreen take effect immediately on return.
 *
 * Win behaviour:
 *   autoSubmit=false           — WinModal shown; user enters name + submits manually
 *   autoSubmit=true, summary   — WinModal shown; submission fires automatically
 *   autoSubmit=true, newgame   — WinModal hidden; WinToast shown for 5 s, then new game
 *
 * Ad refresh: banner reloads (via refreshKey) on every win when autoSubmit is on.
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
} from 'react-native';

import { useTheme }                              from '../context/ThemeContext';
import useGameState                              from '../hooks/useGameState';
import { useSounds }                             from '../hooks/useSounds';
import useTimer                                  from '../hooks/useTimer';
import BoardView                                 from '../components/BoardView';
import WinModal                                  from '../components/WinModal';
import WinToast                                  from '../components/WinToast';
import AdBanner                                  from '../components/AdBanner';
import { getPrefs, saveLocalScore }              from '../services/storage';
import { submitScore }                           from '../services/apiService';
import { calc3BV, calcBoardHash }                from '../gameEngine';

function formatTime(ms) {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${s}s`;
}

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
  } = useGameState('beginner', true); // default noGuess=true; overridden by prefs on mount

  const {
    rows, cols, mines, board, mineSet, revealed, flagged,
    explodedIdx, over, won, mode, noGuess, started,
    leftClicks, rightClicks, chordClicks,
  } = state;

  // ── Local UI state ────────────────────────────────────────────────────────
  const [flagMode,      setFlagMode]      = useState(false);
  const [zoomScale,     setZoomScale]     = useState(1.0);
  const [autoSubmit,    setAutoSubmit]    = useState(false);
  const [onWin,         setOnWin]         = useState('summary');
  const [onLose,        setOnLose]        = useState('summary');
  const [adRefreshKey,  setAdRefreshKey]  = useState(0);
  const [adHeight,      setAdHeight]      = useState(0);
  const [toastVisible,  setToastVisible]  = useState(false);
  const [toastStats,    setToastStats]    = useState(null);

  // ── Timer ─────────────────────────────────────────────────────────────────
  const elapsedMs = useTimer(started, over);

  // ── Sound effects ─────────────────────────────────────────────────────────
  const { play, muted, toggleMute } = useSounds();

  // ── Load prefs on mount (mode + guess defaults) ───────────────────────────
  useEffect(() => {
    getPrefs().then(prefs => {
      setMode(prefs.defaultMode ?? 'beginner');
      setNoGuess((prefs.defaultGuess ?? 'noguess') === 'noguess');
      setAutoSubmit(prefs.autoSubmit ?? false);
      setOnWin(prefs.onWin ?? 'summary');
      setOnLose(prefs.onLose ?? 'summary');
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // intentionally runs once

  // Re-read autoSubmit + onWin when returning from Settings
  useEffect(() => {
    const unsubscribe = navigation.addListener('focus', () => {
      getPrefs().then(prefs => {
        setAutoSubmit(prefs.autoSubmit ?? false);
        setOnWin(prefs.onWin ?? 'summary');
        setOnLose(prefs.onLose ?? 'summary');
      });
    });
    return unsubscribe;
  }, [navigation]);

  // ── Sound + win detection ─────────────────────────────────────────────────
  const prevOver    = useRef(false);
  const prevWon     = useRef(false);
  const prevRevealed = useRef(0);
  const prevFlagged  = useRef(0);

  useEffect(() => {
    const revCount  = revealed ? revealed.reduce((a, v) => a + v, 0) : 0;
    const flagCount = flagged  ? flagged.reduce((a, v) => a + v, 0)  : 0;

    if (won && !prevWon.current) {
      play('win');
      if (autoSubmit) {
        setAdRefreshKey(k => k + 1); // refresh ad on every autosubmit win
        if (onWin === 'newgame') {
          handleAutoNewGame();
        }
      }
    } else if (over && !prevOver.current) {
      play('explode');
      if (onLose === 'newgame') {
        setTimeout(() => {
          setFlagMode(false);
          newGame(mode, noGuess);
        }, 500);
      }
    } else if (revCount > prevRevealed.current) {
      play('reveal');
    }

    if (!over && !won && flagCount > prevFlagged.current) {
      play('flag');
    }

    prevOver.current     = over;
    prevWon.current      = won;
    prevRevealed.current = revCount;
    prevFlagged.current  = flagCount;
  // handleAutoNewGame intentionally excluded — it's stable via useCallback
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [over, won, revealed, flagged, play, autoSubmit, onWin, onLose]);

  // ── Auto-new-game: submit score, show toast, reset after 5 s ─────────────
  const handleAutoNewGame = useCallback(async () => {
    if (!board || !mineSet) return;

    const bbbv       = calc3BV(board, rows, cols, mineSet);
    const boardHash  = calcBoardHash(rows, cols, mineSet);
    const total      = leftClicks + rightClicks + chordClicks;
    const efficiency = total > 0     ? (bbbv / total) * 100              : 0;
    const bbbvPerSec = elapsedMs > 0 ? bbbv / (elapsedMs / 1000)         : 0;

    setToastStats({ bbbv, efficiency: efficiency.toFixed(1), elapsedMs, bbbvPerSec });
    setToastVisible(true);

    // Submit in background
    const prefs = await getPrefs();
    const name  = prefs.playerName?.trim();
    if (name) {
      const guessKey = noGuess ? 'noguess' : 'guess';
      const payload  = {
        name,
        mode,
        time_secs:    Math.floor(elapsedMs / 1000),
        time_ms:      elapsedMs,
        rows,
        cols,
        mines,
        no_guess:     noGuess,
        board_hash:   boardHash,
        bbbv,
        left_clicks:  leftClicks,
        right_clicks: rightClicks,
        chord_clicks: chordClicks,
      };
      const result = await submitScore(payload).catch(() => null);
      await saveLocalScore(mode, guessKey, {
        ...payload,
        ...(result?.id != null ? { id: result.id } : {}),
      });
    }

    // Start new game after 0.5 s so the player can play again immediately
    setTimeout(() => {
      setFlagMode(false);
      newGame(mode, noGuess);
    }, 500);

    // Clear toast after 5 s (matches WinToast fade duration)
    setTimeout(() => {
      setToastVisible(false);
      setToastStats(null);
    }, 5000);
  // Board/game values are stable after won=true; newGame is stable
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [board, mineSet, rows, cols, elapsedMs, leftClicks, rightClicks, chordClicks, mode, noGuess, mines, newGame]);

  // ── Press routing ─────────────────────────────────────────────────────────
  const handlePressCell = useCallback((idx) => {
    if (flagMode) { toggleFlag(idx); return; }
    if (started && revealed[idx] === 1 && board !== null) {
      const r = Math.floor(idx / cols);
      const c = idx % cols;
      if (board[r][c] > 0) { chordCell(idx); return; }
    }
    revealCell(idx);
  }, [flagMode, started, revealed, board, cols, toggleFlag, chordCell, revealCell]);

  const handleLongPressCell = useCallback((idx) => {
    toggleFlag(idx);
  }, [toggleFlag]);

  const handleSetMode = useCallback((m) => {
    setFlagMode(false);
    setMode(m);
  }, [setMode]);

  const handleNewGame = useCallback(() => {
    setFlagMode(false);
    newGame(mode, noGuess);
  }, [mode, noGuess, newGame]);

  // ── Derived display values ────────────────────────────────────────────────
  const flagCount = flagged ? flagged.reduce((sum, v) => sum + v, 0) : 0;
  const minesLeft = mines - flagCount;

  const smileyFace = won ? '😎' : over ? '😵' : started ? '😮' : '🙂';

  let statusText;
  if (won)          statusText = '🎉 You win!';
  else if (over)    statusText = '💥 Game over';
  else if (started) statusText = formatTime(elapsedMs);
  else              statusText = null;

  // WinModal is shown unless we're in autoSubmit+newgame mode (toast handles that)
  const showModal = won && !(autoSubmit && onWin === 'newgame');

  return (
    <SafeAreaView style={[styles.root, { backgroundColor: theme.background }]}>

      {/* ── Mode selector ──────────────────────────────────────────────── */}
      <View style={[styles.modeBar, { borderBottomColor: theme.border }]}>
        {MODES.map(m => (
          <TouchableOpacity
            key={m}
            style={[styles.modeBtn, mode === m && { backgroundColor: theme.accent }]}
            onPress={() => handleSetMode(m)}
          >
            <Text style={[styles.modeBtnText, { color: mode === m ? theme.accentText : theme.textDim }]}>
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

        <View style={styles.statusCenter}>
          <Text style={[styles.mineCount, { color: theme.text }]}>💣 {minesLeft}</Text>
          {statusText !== null && (
            <Text style={[styles.statusText, { color: theme.textDim }]}>{statusText}</Text>
          )}
        </View>

        <TouchableOpacity style={[styles.optionBtn, styles.newGameBtn]} onPress={handleNewGame}>
          <Text style={{ fontSize: 16 }}>{smileyFace}</Text>
          <Text style={{ color: theme.accent, fontSize: 13, fontWeight: '600' }}>New Game</Text>
        </TouchableOpacity>
      </View>

      {/* ── Tool row ───────────────────────────────────────────────────── */}
      <View style={[styles.toolRow, { borderBottomColor: theme.border }]}>
        <TouchableOpacity
          style={[styles.toolBtn, flagMode && { backgroundColor: theme.accent }]}
          onPress={() => setFlagMode(f => !f)}
          accessibilityLabel="Toggle flag mode"
          accessibilityRole="button"
        >
          <Text style={{ fontSize: 18 }}>🚩</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.toolBtn}
          onPress={toggleMute}
          accessibilityLabel={muted ? 'Unmute sounds' : 'Mute sounds'}
          accessibilityRole="button"
        >
          <Text style={{ fontSize: 18 }}>{muted ? '🔇' : '🔊'}</Text>
        </TouchableOpacity>

        {zoomScale !== 1.0 && (
          <TouchableOpacity style={styles.toolBtn} onPress={() => setZoomScale(1.0)}>
            <Text style={{ color: theme.textDim, fontSize: 12 }}>Reset Zoom</Text>
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={[styles.toolBtn, styles.scoresBtn]}
          onPress={() => navigation.navigate('Leaderboard', { mode, noGuess })}
        >
          <Text style={{ color: theme.accent, fontSize: 12, fontWeight: '600' }}>Scores</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.toolBtn}
          onPress={() => navigation.navigate('Settings')}
          accessibilityLabel="Open preferences"
          accessibilityRole="button"
        >
          <Text style={{ fontSize: 18 }}>⚙️</Text>
        </TouchableOpacity>
      </View>

      {/* ── Board ──────────────────────────────────────────────────────── */}
      <BoardView
        rows={rows} cols={cols} board={board} mineSet={mineSet}
        revealed={revealed} flagged={flagged} explodedIdx={explodedIdx}
        gameOver={over} gameWon={won} theme={theme}
        zoomScale={zoomScale} onZoomChange={setZoomScale}
        onPressCell={handlePressCell} onLongPressCell={handleLongPressCell}
      />

      {/* ── Win modal ──────────────────────────────────────────────────── */}
      <WinModal
        visible={showModal}
        mode={mode} noGuess={noGuess} rows={rows} cols={cols} mines={mines}
        board={board} mineSet={mineSet} elapsedMs={elapsedMs}
        leftClicks={leftClicks} rightClicks={rightClicks} chordClicks={chordClicks}
        theme={theme} onNewGame={handleNewGame}
        autoSubmit={autoSubmit}
      />

      {/* ── AdMob banner ───────────────────────────────────────────────── */}
      <View onLayout={e => setAdHeight(e.nativeEvent.layout.height)}>
        <AdBanner refreshKey={adRefreshKey} />
      </View>

      {/* ── Win toast (autoSubmit + newgame mode) ──────────────────────── */}
      {/* Rendered after AdBanner so it sits on top in z-order */}
      {toastStats && (
        <WinToast
          visible={toastVisible}
          elapsedMs={toastStats.elapsedMs}
          bbbv={toastStats.bbbv}
          efficiency={toastStats.efficiency}
          theme={theme}
          bottomOffset={Math.max(adHeight + 16, 80)}
        />
      )}

    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root:       { flex: 1 },
  modeBar: {
    flexDirection: 'row', justifyContent: 'center',
    paddingVertical: 6, paddingHorizontal: 8, gap: 6, borderBottomWidth: 1,
  },
  modeBtn: {
    flex: 1, alignItems: 'center', paddingVertical: 6, borderRadius: 6,
  },
  modeBtnText: { fontSize: 13, fontWeight: '600' },
  optionsRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 12, paddingVertical: 6, borderBottomWidth: 1,
  },
  optionBtn:   { paddingHorizontal: 10, paddingVertical: 5, borderRadius: 6 },
  newGameBtn:  { flexDirection: 'row', alignItems: 'center', gap: 5 },
  statusCenter: { alignItems: 'center', gap: 2 },
  mineCount:    { fontSize: 15, fontWeight: '700' },
  statusText:   { fontSize: 12 },
  toolRow: {
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: 12, paddingVertical: 4, borderBottomWidth: 1, gap: 8,
  },
  toolBtn:   { paddingHorizontal: 12, paddingVertical: 4, borderRadius: 6 },
  scoresBtn: { marginLeft: 'auto' },
});
