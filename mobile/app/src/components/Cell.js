/**
 * Cell.js
 *
 * Renders a single minesweeper cell.
 * All interaction callbacks are passed in from BoardView — this component
 * is purely presentational.
 */

import React, { memo } from 'react';
import { TouchableOpacity, View, Text, StyleSheet } from 'react-native';

// Raised 3-D border effect for covered cells (classic minesweeper look)
const BORDER_WIDTH = 1;

function Cell({
  idx,
  value,          // board[r][c]: -1 (mine) | 0-8
  isRevealed,
  isFlagged,
  isExploded,     // true only for the specific mine the player clicked
  gameOver,
  gameWon,
  cellSize,
  theme,
  onPress,
  onLongPress,
}) {
  // ── Determine visual state ─────────────────────────────────────────────────

  const isMine = value === -1;

  // After game over: an incorrectly flagged non-mine cell
  const isWrongFlag = gameOver && isFlagged && !isMine;

  let bgColor   = theme.cellCovered;
  let label     = null;
  let labelColor = theme.text;

  if (isRevealed) {
    if (isMine) {
      bgColor = isExploded ? theme.mine : theme.cellCovered;
      label   = '💣';
    } else {
      bgColor = theme.cellRevealed;
      if (value > 0) {
        label      = String(value);
        labelColor = theme.numberColors[value];
      }
    }
  } else if (isWrongFlag) {
    bgColor = theme.cellCovered;
    label   = '❌';
  } else if (isFlagged) {
    label = '🚩';
  }

  // ── Raised border for covered cells ───────────────────────────────────────
  const isCovered = !isRevealed;
  const borderStyle = isCovered ? {
    borderTopColor:    '#ffffff88',
    borderLeftColor:   '#ffffff88',
    borderBottomColor: '#00000044',
    borderRightColor:  '#00000044',
    borderWidth:       BORDER_WIDTH,
  } : {
    borderColor: theme.border,
    borderWidth: 0.5,
  };

  const fontSize = cellSize * 0.52;

  return (
    <TouchableOpacity
      activeOpacity={0.7}
      onPress={onPress}
      onLongPress={onLongPress}
      delayLongPress={350}
      style={[
        styles.cell,
        { width: cellSize, height: cellSize, backgroundColor: bgColor },
        borderStyle,
      ]}
    >
      {label !== null && (
        <Text
          style={[styles.label, { fontSize, color: labelColor }]}
          allowFontScaling={false}
        >
          {label}
        </Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  cell: {
    alignItems:     'center',
    justifyContent: 'center',
    overflow:       'hidden',
  },
  label: {
    fontWeight: '700',
    textAlign:  'center',
    lineHeight: undefined,   // let it be natural
  },
});

// memo prevents re-rendering cells whose state hasn't changed
export default memo(Cell, (prev, next) => {
  return (
    prev.isRevealed  === next.isRevealed  &&
    prev.isFlagged   === next.isFlagged   &&
    prev.isExploded  === next.isExploded  &&
    prev.gameOver    === next.gameOver    &&
    prev.gameWon     === next.gameWon     &&
    prev.cellSize    === next.cellSize    &&
    prev.theme       === next.theme       &&
    prev.value       === next.value
  );
});
