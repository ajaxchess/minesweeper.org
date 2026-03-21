'use strict';

/**
 * Quest system — localStorage-based daily & seasonal quests.
 * window.questsHook(event) is called by game files on relevant completions.
 *
 * Daily quest: one of three, rotates each UTC day.
 * Seasonal quest: all three active for the calendar month.
 *
 * Reward: complete 20 daily quests in a row (streak) OR 10 daily quests in
 * the current season → ads permanently disabled in localStorage.
 */
(function () {

  const DAILY_DEFS = [
    { id: 'tentaizu_daily', label: 'Clear the daily Tentaizu puzzle', icon: '🔢', link: '/tentaizu' },
    { id: 'easy_win',       label: 'Win Easy Minesweeper',             icon: '💣', link: '/' },
    { id: 'rush_5_mines',   label: 'Clear 5 mines on Rush mode',       icon: '⚡', link: '/rush' },
  ];

  const SEASONAL_DEFS = [
    { id: 'tentaizu_10',      label: 'Clear 10 daily Tentaizu puzzles', icon: '🔢', type: 'count', key: 'tz_count',   target: 10 },
    { id: 'intermediate_win', label: 'Win Intermediate Minesweeper',    icon: '💣', type: 'once',  key: 'int_won' },
    { id: 'rush_100_mines',   label: 'Clear 100 mines on Rush mode',    icon: '⚡', type: 'count', key: 'rush_mines', target: 100 },
  ];

  // ── Helpers ──────────────────────────────────────────────────────────────────

  function todayStr() { return new Date().toISOString().slice(0, 10); }
  function monthStr() { return new Date().toISOString().slice(0, 7); }

  function dailyQuestDef() {
    const dayNum = Math.floor(Date.now() / 86400000); // UTC days since epoch
    return DAILY_DEFS[dayNum % DAILY_DEFS.length];
  }

  function safeGet(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key)) || fallback; }
    catch { return fallback; }
  }

  function safeSet(key, val) {
    try { localStorage.setItem(key, JSON.stringify(val)); } catch {}
  }

  // ── State ────────────────────────────────────────────────────────────────────

  function loadDaily() {
    const today = todayStr();
    const s = safeGet('quests_daily', {});
    if (s.date === today) return s;
    return { date: today, quest: dailyQuestDef().id, completed: false, rush_progress: 0 };
  }

  function loadSeasonal() {
    const month = monthStr();
    const s = safeGet('quests_seasonal', {});
    if (s.month === month) return s;
    return { month, tz_count: 0, int_won: false, rush_mines: 0, daily_days: [] };
  }

  function loadStreak() {
    return safeGet('quests_streak', { count: 0, last_date: '' });
  }

  // ── Streak + season day tracking ─────────────────────────────────────────────

  function recordDailyCompletion(seasonal) {
    // Update streak
    const today     = todayStr();
    const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
    const streak    = loadStreak();
    if (streak.last_date !== today) {
      streak.count    = (streak.last_date === yesterday) ? streak.count + 1 : 1;
      streak.last_date = today;
      safeSet('quests_streak', streak);
    }

    // Track unique days this season with daily quest complete
    if (!(seasonal.daily_days || []).includes(today)) {
      seasonal.daily_days = [...(seasonal.daily_days || []), today];
    }

    return streak;
  }

  // ── Reward ───────────────────────────────────────────────────────────────────

  function checkReward(streak, seasonal) {
    if (localStorage.getItem('quests_ads_disabled') === 'true') return;
    const streakMet = streak.count >= 20;
    const seasonMet = (seasonal.daily_days || []).length >= 10;
    if (streakMet || seasonMet) {
      localStorage.setItem('quests_ads_disabled', 'true');
      const reason = streakMet ? '20-day daily quest streak' : '10 daily quests this season';
      toast(`🎁 Reward unlocked! Ads disabled — ${reason}.`);
    }
  }

  // ── Toast ────────────────────────────────────────────────────────────────────

  function toast(msg) {
    const el    = document.createElement('div');
    el.className = 'quest-toast';
    el.textContent = msg;
    document.body.appendChild(el);
    requestAnimationFrame(() => {
      el.classList.add('quest-toast-show');
      setTimeout(() => {
        el.classList.remove('quest-toast-show');
        el.addEventListener('transitionend', () => el.remove(), { once: true });
      }, 4500);
    });
  }

  // ── Hook ─────────────────────────────────────────────────────────────────────

  window.questsHook = function (event) {
    const daily    = loadDaily();
    const seasonal = loadSeasonal();
    let dirtyD = false, dirtyS = false;
    let streak = null;

    if (event === 'tentaizu_solved') {
      if (daily.quest === 'tentaizu_daily' && !daily.completed) {
        daily.completed = true; dirtyD = true;
        toast('🎯 Daily quest complete! Tentaizu puzzle cleared.');
        streak = recordDailyCompletion(seasonal); dirtyS = true;
      }
      if (seasonal.tz_count < 10) {
        seasonal.tz_count++; dirtyS = true;
        if (seasonal.tz_count >= 10) toast('🏆 Seasonal quest complete! 10 Tentaizu puzzles cleared!');
      }

    } else if (event === 'easy_won') {
      if (daily.quest === 'easy_win' && !daily.completed) {
        daily.completed = true; dirtyD = true;
        toast('🎯 Daily quest complete! Easy Minesweeper won!');
        streak = recordDailyCompletion(seasonal); dirtyS = true;
      }

    } else if (event === 'intermediate_won') {
      if (!seasonal.int_won) {
        seasonal.int_won = true; dirtyS = true;
        toast('🏆 Seasonal quest complete! Intermediate Minesweeper won!');
      }

    } else if (event === 'rush_mine_cleared') {
      if (daily.quest === 'rush_5_mines' && !daily.completed) {
        daily.rush_progress = (daily.rush_progress || 0) + 1; dirtyD = true;
        if (daily.rush_progress >= 5) {
          daily.completed = true;
          toast('🎯 Daily quest complete! 5 Rush mines cleared!');
          streak = recordDailyCompletion(seasonal); dirtyS = true;
        }
      }
      if (seasonal.rush_mines < 100) {
        const prev = seasonal.rush_mines;
        seasonal.rush_mines = Math.min(100, prev + 1); dirtyS = true;
        if (prev < 100 && seasonal.rush_mines >= 100)
          toast('🏆 Seasonal quest complete! 100 Rush mines cleared!');
      }
    }

    if (dirtyD) safeSet('quests_daily', daily);
    if (dirtyS) safeSet('quests_seasonal', seasonal);
    if (dirtyD || dirtyS) checkReward(streak || loadStreak(), seasonal);
    if (typeof window._renderQuests === 'function') window._renderQuests();
  };

  // ── State reader for quests page ─────────────────────────────────────────────

  window.questsGetState = function () {
    const daily    = loadDaily();
    const seasonal = loadSeasonal();
    const streak   = loadStreak();
    const def      = DAILY_DEFS.find(d => d.id === daily.quest) || DAILY_DEFS[0];
    return {
      daily: { def, completed: daily.completed, rush_progress: daily.rush_progress || 0 },
      seasonal: SEASONAL_DEFS.map(d => {
        const val = d.type === 'count' ? (seasonal[d.key] || 0) : !!(seasonal[d.key]);
        return { def: d, value: val, completed: d.type === 'count' ? val >= d.target : val };
      }),
      streak:      streak.count,
      season_days: (seasonal.daily_days || []).length,
      month:       monthStr(),
      ads_disabled: localStorage.getItem('quests_ads_disabled') === 'true',
    };
  };

  window.DAILY_DEFS    = DAILY_DEFS;
  window.SEASONAL_DEFS = SEASONAL_DEFS;

})();
