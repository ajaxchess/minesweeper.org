# Board Hash Specification

The board hash uniquely identifies a mine layout. It is submitted with every
score and displayed (truncated) on leaderboards so players can compare times
on the same board.

## Source of truth

The canonical implementation lives in `static/js/minesweeper.js`:

```js
function calcBoardHash(rows, cols, mineSet) {
  const bytes = new Uint8Array(Math.ceil(rows * cols / 8));
  for (const idx of mineSet) bytes[idx >> 3] |= (1 << (idx & 7));
  let bin = '';
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin);
}
```

## Step-by-step

### 1. Cell index encoding

Cells are numbered in **row-major order**, 0-based:

```
idx = row * cols + col
```

For a 9×9 beginner board, the top-left cell is index 0 and the
bottom-right cell is index 80.

### 2. Bit array

Allocate `ceil(rows * cols / 8)` bytes, all zero.

For each mine at cell index `idx`, set one bit:

```
byte position : idx / 8   (integer division, i.e. idx >> 3)
bit position  : idx % 8   (i.e. idx & 7)
```

Bit 0 is the **least-significant bit** of the byte (LSB-first / little-endian
bit order within each byte).

Example: mine at idx=0 → byte[0] bit 0 → byte[0] = 0x01
Example: mine at idx=9 → byte[1] bit 1 → byte[1] = 0x02

### 3. Padding

If `rows * cols` is not a multiple of 8, the last byte is zero-padded in the
unused high bits. No length prefix or other framing is added.

### 4. Base64 encoding

Encode the raw byte array using **standard RFC 4648 base64**:

- Alphabet: `A–Z a–z 0–9 + /`
- Padding character: `=`
- **Not** URL-safe base64 (do not substitute `-` for `+` or `_` for `/`)

## React Native implementation

`btoa` is not available in the React Native JS engine. Use `Buffer` instead —
the output is identical:

```js
import { Buffer } from 'buffer'; // or: global.Buffer = require('buffer').Buffer

function calcBoardHash(rows, cols, mineSet) {
  const bytes = new Uint8Array(Math.ceil(rows * cols / 8));
  for (const idx of mineSet) bytes[idx >> 3] |= (1 << (idx & 7));
  return Buffer.from(bytes).toString('base64');
}
```

`mineSet` must be an iterable of integer cell indices (`row * cols + col`).

## Validation test vectors

Use these to confirm your implementation matches the server before shipping.

### 9×9 beginner — mine only at cell 0

```
rows=9, cols=9, mineSet={0}
bytes (hex): 01 00 00 00 00 00 00 00 00 00 00 (11 bytes)
expected hash: AQAAAAAAAAAAAAA=
```

### 9×9 beginner — mine only at cell 9

```
rows=9, cols=9, mineSet={9}
bytes (hex): 00 02 00 00 00 00 00 00 00 00 00 (11 bytes)
expected hash: AAIAAAAAAAAAAAA=
```

### 9×9 beginner — mines at cells 0 and 80 (corners)

```
rows=9, cols=9, mineSet={0, 80}
cell 0  → byte[0]  bit 0 → 0x01
cell 80 → byte[10] bit 0 → 0x01
bytes (hex): 01 00 00 00 00 00 00 00 00 00 01 (11 bytes)
expected hash: AQAAAAAAAAAAAAE=
```

> **Tip:** To cross-check against the live server, win a game in the web
> client, open DevTools → Network, find the score submission request, and
> compare the `board_hash` field to what your JS function produces for the
> same `mineSet`.

## Leaderboard display

The leaderboard shows a **truncated** hash. Truncation is done in the
frontend (first N characters of the base64 string). The full hash is stored
in the database and used for deduplication matching.
