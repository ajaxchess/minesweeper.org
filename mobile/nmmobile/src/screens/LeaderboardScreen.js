import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet, SafeAreaView, ActivityIndicator,
} from 'react-native';
import { useTheme }           from '../context/ThemeContext';
import { fetchNMLeaderboard } from '../services/apiService';
import { fmtTime, getTodayString } from '../gameEngine';

const MEDALS = ['🥇', '🥈', '🥉'];

function countryFlag(code) {
  if (!code || code.length !== 2) return '';
  const c = code.toUpperCase();
  return String.fromCodePoint(0x1F1E6 + c.charCodeAt(0) - 65) +
         String.fromCodePoint(0x1F1E6 + c.charCodeAt(1) - 65);
}

function puzzleLabel(puzzleDate) {
  const m = puzzleDate.match(/^(\d{4}-\d{2}-\d{2})-?(easy|medium|hard|expert)?$/i);
  if (!m) return puzzleDate;
  const diff = m[2] ? m[2].charAt(0).toUpperCase() + m[2].slice(1) : null;
  return diff ? `${diff} · ${m[1]}` : `Daily · ${m[1]}`;
}

export default function LeaderboardScreen({ route }) {
  const { theme } = useTheme();
  const puzzleDate = route?.params?.puzzleDate ?? getTodayString();

  const [scores,  setScores]  = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    const data = await fetchNMLeaderboard(puzzleDate);
    if (data) {
      setScores(data);
    } else {
      setError(true);
    }
    setLoading(false);
  }, [puzzleDate]);

  useEffect(() => { load(); }, [load]);

  function renderRow({ item, index }) {
    const rank = index < 3 ? MEDALS[index] : String(index + 1);
    return (
      <View style={[styles.row, index % 2 === 0 && { backgroundColor: theme.surface }]}>
        <Text style={[styles.rank, { color: theme.text }]}>{rank}</Text>
        <Text style={[styles.name, { color: theme.text }]} numberOfLines={1}>
          {countryFlag(item.country)}{item.country ? ' ' : ''}{item.name}
        </Text>
        <Text style={[styles.score, { color: theme.accent }]}>{item.score}</Text>
        <Text style={[styles.time,  { color: theme.textDim }]}>{fmtTime(item.time_secs)}</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={[styles.root, { backgroundColor: theme.background }]}>
      <Text style={[styles.subtitle, { color: theme.textDim }]}>
        {puzzleLabel(puzzleDate)}
      </Text>

      {/* Header */}
      <View style={[styles.header, { borderBottomColor: theme.border }]}>
        <Text style={[styles.hRank,  { color: theme.textMuted }]}>#</Text>
        <Text style={[styles.hName,  { color: theme.textMuted }]}>Name</Text>
        <Text style={[styles.hScore, { color: theme.textMuted }]}>Score</Text>
        <Text style={[styles.hTime,  { color: theme.textMuted }]}>Time</Text>
      </View>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 40 }} color={theme.accent} />
      ) : error ? (
        <View style={styles.center}>
          <Text style={{ color: theme.textDim }}>⚠️ Could not load scores.</Text>
          <TouchableOpacity onPress={load} style={[styles.retryBtn, { backgroundColor: theme.accent }]}>
            <Text style={{ color: theme.accentText, fontWeight: '600' }}>Retry</Text>
          </TouchableOpacity>
        </View>
      ) : !scores?.length ? (
        <Text style={[styles.empty, { color: theme.textDim }]}>No scores yet — be the first!</Text>
      ) : (
        <FlatList
          data={scores}
          keyExtractor={item => String(item.id ?? item.name + item.score)}
          renderItem={renderRow}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root:     { flex: 1 },
  subtitle: { textAlign: 'center', fontSize: 13, paddingVertical: 8 },
  header:   { flexDirection: 'row', paddingHorizontal: 16, paddingVertical: 6, borderBottomWidth: 1 },
  hRank:    { width: 36, fontSize: 12, fontWeight: '600' },
  hName:    { flex: 1,   fontSize: 12, fontWeight: '600' },
  hScore:   { width: 54, fontSize: 12, fontWeight: '600', textAlign: 'right' },
  hTime:    { width: 54, fontSize: 12, fontWeight: '600', textAlign: 'right' },
  row:      { flexDirection: 'row', paddingHorizontal: 16, paddingVertical: 10, alignItems: 'center' },
  rank:     { width: 36, fontSize: 14 },
  name:     { flex: 1,   fontSize: 14 },
  score:    { width: 54, fontSize: 14, fontWeight: '700', textAlign: 'right' },
  time:     { width: 54, fontSize: 13, textAlign: 'right' },
  empty:    { textAlign: 'center', marginTop: 40, fontSize: 15 },
  center:   { alignItems: 'center', marginTop: 40, gap: 16 },
  retryBtn: { paddingHorizontal: 24, paddingVertical: 10, borderRadius: 8 },
});
