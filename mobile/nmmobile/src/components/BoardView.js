import React, { memo, useCallback, useMemo } from 'react';
import {
  View, Text, TouchableOpacity, FlatList, StyleSheet, useWindowDimensions,
} from 'react-native';
import { NM_COLS, NM_COLORS } from '../gameEngine';

const CELL_MARGIN = 3; // 1.5px each side

// ── Single cell ────────────────────────────────────────────────────────────────
const Cell = memo(function Cell({ value, idx, isSelected, isHinted, isReachable, theme, size, onPress }) {
  if (value === 0) {
    const bg     = isReachable ? theme.accent + '28' : theme.cellEmpty;
    const border = isReachable ? theme.accent        : theme.border;
    return (
      <View style={[styles.cell, { width: size, height: size, backgroundColor: bg, borderColor: border }]} />
    );
  }

  const bg       = isSelected ? theme.accent2 : isHinted ? '#f9a825' : theme.cellCovered;
  const border   = isSelected ? theme.accent2 : isHinted ? '#f9a825' : isReachable ? theme.accent : theme.border;
  const numColor = (isSelected || isHinted) ? '#000000' : (NM_COLORS[value] || theme.text);

  return (
    <TouchableOpacity
      style={[
        styles.cell,
        { width: size, height: size, backgroundColor: bg, borderColor: border },
        isReachable && !isSelected && !isHinted && styles.reachable,
      ]}
      onPress={() => onPress(idx)}
      activeOpacity={0.7}
      accessibilityRole="button"
      accessibilityLabel={`Number ${value}`}
    >
      <Text style={[styles.cellText, { color: numColor }]}>{value}</Text>
    </TouchableOpacity>
  );
}, (prev, next) =>
  prev.value       === next.value       &&
  prev.isSelected  === next.isSelected  &&
  prev.isHinted    === next.isHinted    &&
  prev.isReachable === next.isReachable &&
  prev.theme       === next.theme       &&
  prev.size        === next.size
);

// ── Board grid ─────────────────────────────────────────────────────────────────
export default function BoardView({ board, selected, hintPair, reachableCells, theme, onPress }) {
  const { width } = useWindowDimensions();
  // Account for paddingHorizontal (32) + cell margins (1.5px each side × NM_COLS)
  const cellSize = Math.floor((width - 32 - NM_COLS * CELL_MARGIN) / NM_COLS);

  const hintSet  = useMemo(() => new Set(hintPair ?? []), [hintPair]);
  const reachSet = useMemo(() => new Set(reachableCells ?? []), [reachableCells]);

  const renderItem = useCallback(({ item, index }) => (
    <Cell
      value={item}
      idx={index}
      isSelected={selected === index}
      isHinted={hintSet.has(index)}
      isReachable={reachSet.has(index)}
      theme={theme}
      size={cellSize}
      onPress={onPress}
    />
  ), [selected, hintSet, reachSet, theme, cellSize, onPress]);

  return (
    <FlatList
      data={board}
      renderItem={renderItem}
      keyExtractor={(_, i) => String(i)}
      numColumns={NM_COLS}
      key={NM_COLS}
      scrollEnabled
      showsVerticalScrollIndicator={false}
      contentContainerStyle={styles.grid}
    />
  );
}

const styles = StyleSheet.create({
  grid: { paddingHorizontal: 16 },
  cell: {
    margin:         1.5,
    borderWidth:    1,
    borderRadius:   5,
    alignItems:     'center',
    justifyContent: 'center',
  },
  cellText: {
    fontSize:   18,
    fontWeight: '800',
  },
  reachable: {
    borderWidth: 2,
    opacity:     0.85,
  },
});
