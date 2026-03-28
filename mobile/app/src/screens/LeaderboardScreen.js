/**
 * LeaderboardScreen.js
 *
 * Full-screen leaderboard. Accepts optional nav params { mode, noGuess }
 * from GameScreen so it opens pre-filtered to the active game's context.
 * The user can change mode, guess, and period within the screen.
 *
 * Columns: # | Name | Time | 3BV | 3BV/s | Eff | Board
 *
 * 3BV/s and Efficiency are computed client-side:
 *   3BV/s  = bbbv / (time_ms / 1000)
 *   Eff    = bbbv / (left_clicks + right_clicks + chord_clicks)
 *
 * Board = first 8 chars of board_hash.
 */

import React, { useState } from 'react';
import {
  SafeAreaView,
  View,
  Text,
  TouchableOpacity,
  FlatList,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { useTheme }       from '../context/ThemeContext';
import useLeaderboard, { PERIODS } from '../hooks/useLeaderboard';

// ── Helpers ───────────────────────────────────────────────────────────────────

const MODES = ['beginner', 'intermediate', 'expert'];
const MODE_LABELS = { beginner: 'Beginner', intermediate: 'Interm.', expert: 'Expert' };
const PERIOD_LABELS = { daily: 'Daily', season: 'Season', alltime: 'All Time' };
const RANK_MEDALS   = ['🥇', '🥈', '🥉'];

function fmtTime(score) {
  if (score.time_ms != null) {
    const sec = score.time_ms / 1000;
    if (sec >= 60) {
      const m = Math.floor(sec / 60);
      const s = String(Math.round(sec % 60)).padStart(2, '0');
      return `${m}:${s}`;
    }
    return sec.toFixed(3) + 's';
  }
  return score.time_secs != null ? `${score.time_secs}s` : '—';
}

function fmtBbbvs(score) {
  if (score.bbbv == null || !score.time_ms) return '—';
  return (score.bbbv / (score.time_ms / 1000)).toFixed(2);
}

function fmtEff(score) {
  if (score.bbbv == null) return '—';
  const clicks = (score.left_clicks ?? 0) + (score.right_clicks ?? 0) + (score.chord_clicks ?? 0);
  if (clicks === 0) return '—';
  return Math.round((score.bbbv / clicks) * 100) + '%';
}

function fmtBoard(score) {
  return score.board_hash ? score.board_hash.substring(0, 8) : '—';
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SelectorBar({ options, value, onSelect, labelMap, theme }) {
  return (
    <View style={styles.selectorBar}>
      {options.map(opt => {
        const active = opt === value;
        return (
          <TouchableOpacity
            key={opt}
            style={[styles.selectorBtn, active && { backgroundColor: theme.accent }]}
            onPress={() => onSelect(opt)}
          >
            <Text style={[styles.selectorText, { color: active ? theme.accentText : theme.textDim }]}>
              {labelMap ? labelMap[opt] : opt}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

function TableHeader({ theme }) {
  return (
    <View style={[styles.row, styles.headerRow, { borderBottomColor: theme.border }]}>
      <Text style={[styles.rankCell,  styles.headerText, { color: theme.textMuted }]}>#</Text>
      <Text style={[styles.nameCell,  styles.headerText, { color: theme.textMuted }]}>NAME</Text>
      <Text style={[styles.timeCell,  styles.headerText, { color: theme.textMuted }]}>TIME</Text>
      <Text style={[styles.numCell,   styles.headerText, { color: theme.textMuted }]}>3BV</Text>
      <Text style={[styles.bbbvsCell, styles.headerText, { color: theme.textMuted }]}>3BV/S</Text>
      <Text style={[styles.effCell,   styles.headerText, { color: theme.textMuted }]}>EFF</Text>
      <Text style={[styles.boardCell, styles.headerText, { color: theme.textMuted }]}>BOARD</Text>
    </View>
  );
}

function ScoreRow({ score, index, theme }) {
  const isTop3  = index < 3;
  const rankStr = index < 3 ? RANK_MEDALS[index] : String(index + 1);
  const rowBg   = index % 2 === 0 ? 'transparent' : theme.surface;

  return (
    <View style={[styles.row, { backgroundColor: rowBg }]}>
      <Text style={[styles.rankCell,  styles.cellText, { color: theme.textMuted }]}>{rankStr}</Text>
      <Text
        style={[styles.nameCell, styles.cellText, { color: isTop3 ? theme.accent : theme.text, fontWeight: isTop3 ? '600' : '400' }]}
        numberOfLines={1}
      >
        {score.name ?? '—'}
      </Text>
      <Text style={[styles.timeCell,  styles.cellText, { color: isTop3 ? theme.accent : theme.text }]}>
        {fmtTime(score)}
      </Text>
      <Text style={[styles.numCell,   styles.cellText, { color: theme.text }]}>
        {score.bbbv ?? '—'}
      </Text>
      <Text style={[styles.bbbvsCell, styles.cellText, { color: theme.text }]}>
        {fmtBbbvs(score)}
      </Text>
      <Text style={[styles.effCell,   styles.cellText, { color: theme.text }]}>
        {fmtEff(score)}
      </Text>
      <Text style={[styles.boardCell, styles.cellText, { color: theme.textDim }]} numberOfLines={1}>
        {fmtBoard(score)}
      </Text>
    </View>
  );
}

// ── Screen ────────────────────────────────────────────────────────────────────

export default function LeaderboardScreen({ route }) {
  const { theme } = useTheme();

  const initMode    = route?.params?.mode    ?? 'beginner';
  const initNoGuess = route?.params?.noGuess ?? false;

  const [mode,    setMode]    = useState(initMode);
  const [noGuess, setNoGuess] = useState(initNoGuess);

  const { scores, loading, period, setPeriod } = useLeaderboard(mode, noGuess);

  const guessLabel = noGuess ? 'No-Guess' : 'Guess';
  const subtitle   = `${PERIOD_LABELS[period]} · ${MODE_LABELS[mode]} · ${guessLabel}`;

  return (
    <SafeAreaView style={[styles.root, { backgroundColor: theme.background }]}>

      {/* ── Filters ───────────────────────────────────────────────────── */}
      <View style={[styles.filtersBox, { borderBottomColor: theme.border }]}>
        <SelectorBar
          options={MODES}
          value={mode}
          onSelect={setMode}
          labelMap={MODE_LABELS}
          theme={theme}
        />
        <View style={styles.row2}>
          <SelectorBar
            options={['guess', 'noguess']}
            value={noGuess ? 'noguess' : 'guess'}
            onSelect={v => setNoGuess(v === 'noguess')}
            labelMap={{ guess: 'Guess', noguess: 'No-Guess' }}
            theme={theme}
          />
          <SelectorBar
            options={PERIODS}
            value={period}
            onSelect={setPeriod}
            labelMap={PERIOD_LABELS}
            theme={theme}
          />
        </View>
      </View>

      {/* ── Subtitle ──────────────────────────────────────────────────── */}
      <Text style={[styles.subtitle, { color: theme.textDim }]}>{subtitle}</Text>

      {/* ── Table ─────────────────────────────────────────────────────── */}
      {loading ? (
        <ActivityIndicator style={styles.spinner} color={theme.accent} />
      ) : (
        <FlatList
          data={scores}
          keyExtractor={(item, i) => item.id != null ? String(item.id) : `local-${i}`}
          ListHeaderComponent={<TableHeader theme={theme} />}
          renderItem={({ item, index }) => (
            <ScoreRow score={item} index={index} theme={theme} />
          )}
          ListEmptyComponent={
            <Text style={[styles.emptyText, { color: theme.textDim }]}>No scores yet.</Text>
          }
          contentContainerStyle={styles.listContent}
          stickyHeaderIndices={[0]}
        />
      )}

    </SafeAreaView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const CELL_FONT = 12;

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  filtersBox: {
    paddingHorizontal: 8,
    paddingVertical:   6,
    borderBottomWidth: 1,
    gap:               6,
  },
  row2: {
    flexDirection: 'row',
    gap:           6,
  },
  selectorBar: {
    flexDirection: 'row',
    flex:          1,
    gap:           4,
  },
  selectorBtn: {
    flex:            1,
    alignItems:      'center',
    paddingVertical: 5,
    borderRadius:    6,
  },
  selectorText: {
    fontSize:   12,
    fontWeight: '500',
  },
  subtitle: {
    fontSize:          12,
    paddingHorizontal: 12,
    paddingVertical:   6,
  },
  spinner: {
    marginTop: 40,
  },
  listContent: {
    paddingBottom: 24,
  },
  emptyText: {
    textAlign:  'center',
    marginTop:  32,
    fontSize:   14,
  },

  // ── Table rows ─────────────────────────────────────────────────────
  row: {
    flexDirection:     'row',
    alignItems:        'center',
    paddingHorizontal: 8,
    paddingVertical:   7,
  },
  headerRow: {
    borderBottomWidth: 1,
  },
  headerText: {
    fontSize:   10,
    fontWeight: '600',
    letterSpacing: 0.5,
  },
  cellText: {
    fontSize: CELL_FONT,
  },

  // ── Column widths ───────────────────────────────────────────────────
  rankCell:  { width: 24, textAlign: 'center' },
  nameCell:  { flex: 1,   marginRight: 4 },
  timeCell:  { width: 52, textAlign: 'right' },
  numCell:   { width: 28, textAlign: 'right' },
  bbbvsCell: { width: 40, textAlign: 'right' },
  effCell:   { width: 36, textAlign: 'right' },
  boardCell: { width: 62, textAlign: 'right', fontVariant: ['tabular-nums'] },
});
