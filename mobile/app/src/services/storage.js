import AsyncStorage from '@react-native-async-storage/async-storage';

// ── Keys ──────────────────────────────────────────────────────────────────────
// Preferences:  prefs:player_name | prefs:default_mode | prefs:default_guess |
//               prefs:theme | prefs:sound | prefs:autosubmit | prefs:on_win | prefs:on_lose
// Scores:       scores:{mode}:{guess}  e.g. scores:beginner:guess, scores:expert:noguess

const PREFS_KEYS = {
  playerName:   'prefs:player_name',
  defaultMode:  'prefs:default_mode',
  defaultGuess: 'prefs:default_guess',
  theme:        'prefs:theme',
  sound:        'prefs:sound',       // 'on' | 'off'
  autoSubmit:   'prefs:autosubmit',  // 'yes' | 'no'
  onWin:        'prefs:on_win',      // 'summary' | 'newgame'
  onLose:       'prefs:on_lose',     // 'summary' | 'newgame'
};

const MODES   = ['beginner', 'intermediate', 'expert'];
const GUESSES = ['guess', 'noguess'];
const MAX_LOCAL_SCORES = 20;

function scoresKey(mode, guess) {
  return `scores:${mode}:${guess}`;
}

// ── Preferences ───────────────────────────────────────────────────────────────

export async function getPrefs() {
  const pairs = await AsyncStorage.multiGet(Object.values(PREFS_KEYS));
  return {
    playerName:   pairs[0][1] ?? null,
    defaultMode:  pairs[1][1] ?? 'beginner',
    defaultGuess: pairs[2][1] ?? 'noguess',   // default changed to no-guess
    theme:        pairs[3][1] ?? 'auto',
    sound:        pairs[4][1] ?? 'on',
    autoSubmit:   (pairs[5][1] ?? 'no') === 'yes',
    onWin:        pairs[6][1] ?? 'summary',
    onLose:       pairs[7][1] ?? 'summary',
  };
}

export async function savePrefs(updates) {
  const pairs = [];
  if (updates.playerName   !== undefined) pairs.push([PREFS_KEYS.playerName,   updates.playerName]);
  if (updates.defaultMode  !== undefined) pairs.push([PREFS_KEYS.defaultMode,  updates.defaultMode]);
  if (updates.defaultGuess !== undefined) pairs.push([PREFS_KEYS.defaultGuess, updates.defaultGuess]);
  if (updates.theme        !== undefined) pairs.push([PREFS_KEYS.theme,        updates.theme]);
  if (updates.sound        !== undefined) pairs.push([PREFS_KEYS.sound,        updates.sound]);
  if (updates.autoSubmit   !== undefined) pairs.push([PREFS_KEYS.autoSubmit,   updates.autoSubmit ? 'yes' : 'no']);
  if (updates.onWin        !== undefined) pairs.push([PREFS_KEYS.onWin,        updates.onWin]);
  if (updates.onLose       !== undefined) pairs.push([PREFS_KEYS.onLose,       updates.onLose]);
  if (pairs.length) await AsyncStorage.multiSet(pairs);
}

// ── Local scores ──────────────────────────────────────────────────────────────

/**
 * Load the local top-20 scores for a given mode + guess combination.
 * Returns an array sorted by time_ms ascending (fastest first).
 */
export async function getLocalScores(mode, guess) {
  const raw = await AsyncStorage.getItem(scoresKey(mode, guess));
  return raw ? JSON.parse(raw) : [];
}

/**
 * Insert a new score into local storage.
 * - Deduplicates on (mode + time_ms + board_hash)
 * - Keeps top MAX_LOCAL_SCORES by time_ms (fastest)
 * - Persists the server id if the submission succeeded
 */
export async function saveLocalScore(mode, guess, score) {
  const existing = await getLocalScores(mode, guess);

  // Deduplicate: if a matching record exists, update it with server id if now available
  const dupIdx = existing.findIndex(s =>
    s.time_ms === score.time_ms && s.board_hash === score.board_hash
  );
  if (dupIdx >= 0) {
    if (score.id && !existing[dupIdx].id) {
      existing[dupIdx].id = score.id;
      await AsyncStorage.setItem(scoresKey(mode, guess), JSON.stringify(existing));
    }
    return;
  }

  const updated = [...existing, score]
    .sort((a, b) => a.time_ms - b.time_ms)
    .slice(0, MAX_LOCAL_SCORES);

  await AsyncStorage.setItem(scoresKey(mode, guess), JSON.stringify(updated));
}

/**
 * Load local scores for all 6 mode/guess combinations.
 * Returns a flat array.
 */
export async function getAllLocalScores() {
  const keys = MODES.flatMap(m => GUESSES.map(g => scoresKey(m, g)));
  const pairs = await AsyncStorage.multiGet(keys);
  return pairs.flatMap(([, raw]) => (raw ? JSON.parse(raw) : []));
}
