/**
 * moveLog.test.js — the move log the server replays (F-MS-VERIFY-APP), the start
 * token helper, and the client type header.
 */
import { reducer, makeInitialState } from '../hooks/useGameState';

const T0 = 1_700_000_000_000;

function play(actions, state = makeInitialState('beginner', false)) {
  return actions.reduce((s, [type, idx, now]) => reducer(s, { type, idx, now }), state);
}

describe('move log', () => {
  test('a new game has an empty log and its own id', () => {
    const a = makeInitialState('beginner', false);
    const b = makeInitialState('beginner', false);
    expect(a.log).toEqual([]);
    expect(b.gameId).not.toBe(a.gameId);
  });

  test('records [t_ms, type, row, col] from the first reveal', () => {
    const s = play([
      ['TOGGLE_FLAG', 0, T0 - 500],      // before the first reveal: t = 0
      ['REVEAL', 40, T0],                // (4, 4)
    ]);
    expect(s.log[0]).toEqual([0, 'r', 0, 0]);
    expect(s.log[1]).toEqual([0, 'l', 4, 4]);
    expect(s.startTime).toBe(T0);
  });

  test('later moves are timed from the first reveal and never go backwards', () => {
    let s = play([['REVEAL', 40, T0]]);
    const closed = [...Array(81).keys()].find(i => !s.revealed[i]);
    s = play([['TOGGLE_FLAG', closed, T0 + 1234], ['TOGGLE_FLAG', closed, T0 + 1000]], s);
    expect(s.log.slice(1).map(e => e[0])).toEqual([1234, 1234]);
  });

  test('moves the app ignores are not logged', () => {
    let s = play([['REVEAL', 40, T0]]);
    const before = s.log.length;
    s = play([['REVEAL', 40, T0 + 100]], s);           // already open
    const open = [...Array(81).keys()].find(i => s.revealed[i]);
    s = play([['TOGGLE_FLAG', open, T0 + 200]], s);    // cannot flag an open cell
    expect(s.log.length).toBe(before);
  });

  test('the log matches the click counts the app shows', () => {
    let s = play([['REVEAL', 40, T0]]);
    const closed = [...Array(81).keys()].filter(i => !s.revealed[i]);
    s = play([['TOGGLE_FLAG', closed[0], T0 + 300], ['TOGGLE_FLAG', closed[0], T0 + 600]], s);
    const count = type => s.log.filter(e => e[1] === type).length;
    expect(count('l')).toBe(s.leftClicks);
    expect(count('r')).toBe(s.rightClicks);
    expect(count('c')).toBe(s.chordClicks);
  });
});

describe('apiService', () => {
  beforeEach(() => jest.resetModules());

  test('Android reports android_app', () => {
    jest.doMock('react-native', () => ({ Platform: { OS: 'android' } }));
    const { CLIENT_TYPE } = require('../services/apiService');
    expect(CLIENT_TYPE).toBe('android_app');
  });

  test('iOS reports ios_app', () => {
    jest.doMock('react-native', () => ({ Platform: { OS: 'ios' } }));
    const { CLIENT_TYPE } = require('../services/apiService');
    expect(CLIENT_TYPE).toBe('ios_app');
  });

  test('withMoveLog adds the log, the app rules and the token', async () => {
    const { withMoveLog } = require('../services/apiService');
    const body = await withMoveLog({ name: 'A' }, [[0, 'l', 4, 4]], Promise.resolve('tok'));
    expect(body).toEqual({ name: 'A', log: [[0, 'l', 4, 4]], rules: 'msmobile', chording: true, game_token: 'tok' });
  });

  test('withMoveLog sends the score without a token when none arrives in time', async () => {
    const { withMoveLog } = require('../services/apiService');
    const never = new Promise(() => {});
    const body = await withMoveLog({ name: 'A' }, [[0, 'l', 4, 4]], never, 20);
    expect(body.game_token).toBeUndefined();
    expect(body.rules).toBe('msmobile');
  });

  test('withMoveLog leaves a score without moves unchanged', async () => {
    const { withMoveLog } = require('../services/apiService');
    expect(await withMoveLog({ name: 'A' }, [], Promise.resolve('tok'))).toEqual({ name: 'A' });
  });
});
