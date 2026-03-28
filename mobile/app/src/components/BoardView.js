/**
 * BoardView.js
 *
 * Renders the full minesweeper board.
 *
 * Layout: nested ScrollViews — outer scrolls vertically, inner scrolls
 * horizontally. A PanResponder wrapper captures 2-finger touches for
 * pinch-to-zoom, disabling ScrollView scroll during the pinch gesture.
 *
 * zoomScale is managed in GameScreen and passed down. BoardView calls
 * onZoomChange(newScale) as the user pinches; GameScreen stores the value.
 *
 * Cell size = baseCellSize * zoomScale, clamped [MIN_CELL_SIZE, MAX_CELL_SIZE].
 * baseCellSize fills the available screen width for the column count (capped
 * at 44 so large screens don't produce oversized cells at 1×zoom).
 */

import React, { useMemo, useState, useRef } from 'react';
import {
  ScrollView,
  View,
  StyleSheet,
  useWindowDimensions,
  PanResponder,
} from 'react-native';
import Cell from './Cell';

const BASE_MIN  = 28;   // natural size floor
const BASE_MAX  = 44;   // natural size ceiling
const ZOOM_MIN  = 20;   // absolute floor after zoom-out
const ZOOM_MAX  = 88;   // absolute ceiling after zoom-in (2× BASE_MAX)
const BOARD_PADDING = 8;

export default function BoardView({
  rows,
  cols,
  board,
  mineSet,
  revealed,
  flagged,
  explodedIdx,
  gameOver,
  gameWon,
  theme,
  zoomScale    = 1.0,   // controlled by GameScreen
  onZoomChange,         // (newScale: number) => void
  onPressCell,
  onLongPressCell,
}) {
  const { width: screenWidth } = useWindowDimensions();
  const [isPinching, setIsPinching] = useState(false);

  // ── Cell size ──────────────────────────────────────────────────────────────
  const baseCellSize = useMemo(() => {
    const available = screenWidth - BOARD_PADDING * 2;
    const natural   = Math.floor(available / cols);
    return Math.max(BASE_MIN, Math.min(BASE_MAX, natural));
  }, [screenWidth, cols]);

  const cellSize = Math.max(
    ZOOM_MIN,
    Math.min(ZOOM_MAX, Math.round(baseCellSize * zoomScale))
  );

  const boardWidth  = cellSize * cols;
  const boardHeight = cellSize * rows;

  // ── Pinch-to-zoom via PanResponder ────────────────────────────────────────
  //
  // Refs keep the PanResponder closure stable while still reading the latest
  // values on each gesture event.
  //
  const onZoomChangeRef = useRef(onZoomChange);
  onZoomChangeRef.current = onZoomChange;

  const zoomScaleRef = useRef(zoomScale);
  zoomScaleRef.current = zoomScale;

  // Mutable pinch state — not React state, no re-render needed mid-gesture
  const pinch = useRef({ startDist: 0, startScale: 1 });

  const panResponder = useRef(
    PanResponder.create({
      // Capture 2-finger touches before ScrollView or Cell can claim them
      onStartShouldSetPanResponderCapture: (evt) =>
        evt.nativeEvent.touches.length >= 2,
      onMoveShouldSetPanResponderCapture: (evt) =>
        evt.nativeEvent.touches.length >= 2,

      onPanResponderGrant: (evt) => {
        const t = evt.nativeEvent.touches;
        if (t.length < 2) return;
        const dx = t[0].pageX - t[1].pageX;
        const dy = t[0].pageY - t[1].pageY;
        pinch.current.startDist  = Math.sqrt(dx * dx + dy * dy) || 1;
        pinch.current.startScale = zoomScaleRef.current;
        setIsPinching(true);
      },

      onPanResponderMove: (evt) => {
        const t = evt.nativeEvent.touches;
        if (t.length < 2 || pinch.current.startDist === 0) return;
        const dx   = t[0].pageX - t[1].pageX;
        const dy   = t[0].pageY - t[1].pageY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const raw  = pinch.current.startScale * (dist / pinch.current.startDist);
        onZoomChangeRef.current?.(Math.max(0.5, Math.min(3.0, raw)));
      },

      onPanResponderRelease: () => {
        setIsPinching(false);
        pinch.current.startDist = 0;
      },
      onPanResponderTerminate: () => {
        setIsPinching(false);
        pinch.current.startDist = 0;
      },
    })
  ).current;

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
            onPress={onPressCell      ? () => onPressCell(idx)      : undefined}
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
  }, [
    rows, cols, board, revealed, flagged, explodedIdx,
    gameOver, gameWon, cellSize, theme, onPressCell, onLongPressCell,
  ]);

  return (
    // gestureContainer receives panHandlers so 2-finger touches go to
    // the PanResponder rather than the nested ScrollViews.
    <View style={styles.gestureContainer} {...panResponder.panHandlers}>
      <ScrollView
        style={styles.outerScroll}
        contentContainerStyle={styles.outerContent}
        showsVerticalScrollIndicator={false}
        bounces={false}
        scrollEnabled={!isPinching}
      >
        <ScrollView
          horizontal
          style={styles.innerScroll}
          contentContainerStyle={[
            styles.innerContent,
            { width: Math.max(boardWidth, screenWidth - BOARD_PADDING * 2) },
          ]}
          showsHorizontalScrollIndicator={false}
          bounces={false}
          scrollEnabled={!isPinching}
        >
          <View
            style={[
              styles.board,
              {
                width:           boardWidth,
                height:          boardHeight,
                borderColor:     theme.border,
                backgroundColor: theme.surface,
              },
            ]}
          >
            {rowElements}
          </View>
        </ScrollView>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  gestureContainer: {
    flex: 1,
  },
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
    borderWidth: 1,
    overflow:    'hidden',
  },
  row: {
    flexDirection: 'row',
  },
});
