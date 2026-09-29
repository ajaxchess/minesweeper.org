import AsyncStorage from '@react-native-async-storage/async-storage';

const KEYS = {
  playerName: 'nm:player_name',
  theme:      'nm:theme',
};

export async function getPrefs() {
  const pairs = await AsyncStorage.multiGet(Object.values(KEYS));
  return {
    playerName: pairs[0][1] ?? null,
    theme:      pairs[1][1] ?? 'auto',
  };
}

export async function savePrefs(updates) {
  const pairs = [];
  if (updates.playerName !== undefined) pairs.push([KEYS.playerName, updates.playerName]);
  if (updates.theme      !== undefined) pairs.push([KEYS.theme,      updates.theme]);
  if (pairs.length) await AsyncStorage.multiSet(pairs);
}
