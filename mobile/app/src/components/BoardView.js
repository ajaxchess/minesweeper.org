/**
 * BoardView.js
 *
 * Renders the full minesweeper board.
 *
 * Layout: nested ScrollViews — outer scrolls vertically, inner scrolls
 * horizontally — allowing the board to be larger than the screen in
 * either dimension. Pinch-to-zoom is added in Phase 3b.
 *
 * Cell size is calculated to fill the available width for the board's column
 * count, capped at MAX_CELL_SIZE so large screens don't produce giant cells,
 * and floored at MIN_CELL_SIZE so expert boards remain usable.
 */

import React, { useMemo } from 'react';
import { ScrollView, View, StyleSheet, useWindowDimensions } from 'react-native';
import Cell from './Cell';

const MIN_CELL_SIZE = 28;
const MAX_CELL_SIZE = 44;
const BOARD_PADDING = 8; // horizontal padding on each side

export default function BoardView({
  rows,
  cols,
  board,        // number[][] | null (null = pre-first-click, all covered)
  mineSet,      // Set<idx> | null
  revealed,     // Uint8Array
  flagged,      // Uint8Array
  explodedIdx,  // number (-1 if none)
  gameOver,
  gameWon,
  theme,
  onPressCell,      // (idx) => void  — wired in Phase 3b
  onLongPressCell,  // (idx) => void  — wired in Phase 3b
}) {
  const { width: screenWidth } = useWindowDimensions();

  // ── Cell size ──────────────────────────────────────────────────────────────
  const cellSize = useMemo(() => {
    const available = screenWidth - BOARD_PADDING * 2;
    const natural   = Math.floor(available / cols);
    return Math.max(MIN_CELL_SIZE, Math.min(MAX_CELL_SIZE, natural));
  }, [screenWidth, cols]);

  const boardWidth  = cellSize * cols;
  const boardHeight = cellSize * rows;

  // ── Row rendering ─────────────────────────────────────────────────────────
  const rowElements = useMemo(() => {
    const rowArr = [];
    for (let r = 0; r < rows; r++) {
      const cells = [];
      for (let c = 0; c < cols; c++) {
        const idx   = r * cols + c;
        const value = board ? board[r][c] : 0;
        cells.push(
          <Cell
            key={idx}
            idx={idx}
            value={value}
            isRevealed={revealed[idx] === 1}
            isFlagged={flagged[idx] === 1}
            isExploded={idx === explodedIdx}
            gameOver={gameOver}
            gameWon={gameWon}
            cellSize={cellSize}
            theme={theme}
            onPress={onPressCell     ? () => onPressCell(idx)     : undefined}
            onLongPress={onLongPressCell ? () => onLongPressCell(idx) : undefined}
          />
        );
      }
      rowArr.push(
        <View key={r} style={styles.row}>
          {cells}
        </View>
      );
    }
    return rowArr;
  }, [rows, cols, board, revealed, flagged, explodedIdx, gameOver, gameWon, cellSize, theme, onPressCell, onLongPressCell]);

  return (
    <ScrollView
      style={styles.outerScroll}
      contentContainerStyle={styles.outerContent}
      showsVerticalScrollIndicator={false}
      bounces={false}
    >
      <ScrollView
        horizontal
        style={styles.innerScroll}
        contentContainerStyle={[styles.innerContent, { width: Math.max(boardWidth, screenWidth - BOARD_PADDING * 2) }]}
        showsHorizontalScrollIndicator={false}
        bounces={false}
      >
        <View
          style={[
            styles.board,
            {
              width:            boardWidth,
              height:           boardHeight,
              borderColor:      theme.border,
              backgroundColor:  theme.surface,
            },
          ]}
        >
          {rowElements}
        </View>
      </ScrollView>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  outerScroll: {
    flex: 1,
  },
  outerContent: {
    padding: BOARD_PADDING,
  },
  innerScroll: {
    flex: 1,
  },
  innerContent: {
    alignItems: 'flex-start',
  },
  board: {
    borderWidth:  1,
    overflow:     'hidden',
  },
  row: {
    flexDirection: 'row',
  },
});
