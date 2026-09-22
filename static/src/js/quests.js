'use strict';

/**
 * LocalStorage-based daily and seasonal quests.
 * Quest definitions and UI copy are rendered into window.QUEST_CONFIG by Jinja.
 */
(function () {
  const CONFIG = window.QUEST_CONFIG || {};
  const DAILY_DEFS = CONFIG.daily || [];
  const SEASONAL_DEFS = CONFIG.seasonal || [];
  const REWARDS = CONFIG.rewards || { streakTarget: 20, seasonTarget: 10 };
  const COPY = CONFIG.copy || {};

  function todayStr() { return new Date().toISOString().slice(0, 10); }
  function monthStr() { return new Date().toISOString().slice(0, 7); }

  function dailyQuestDef() {
    const dayNum = Math.floor(Date.now() / 86400000);
    return DAILY_DEFS[dayNum % DAILY_DEFS.length] || {};
  }

  function safeGet(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key)) || fallback; }
    catch { return fallback; }
  }

  function safeSet(key, val) {
    try { localStorage.setItem(key, JSON.stringify(val)); } catch {}
  }

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

  function recordDailyCompletion(seasonal) {
    const today = todayStr();
    const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
    const streak = loadStreak();
    if (streak.last_date !== today) {
      streak.count = (streak.last_date === yesterday) ? streak.count + 1 : 1;
      streak.last_date = today;
      safeSet('quests_streak', streak);
    }

    if (!(seasonal.daily_days || []).includes(today)) {
      seasonal.daily_days = [...(seasonal.daily_days || []), today];
    }

    return streak;
  }

  function checkReward(streak, seasonal) {
    if (localStorage.getItem('quests_ads_disabled') === 'true') return;
    const streakMet = streak.count >= REWARDS.streakTarget;
    const seasonMet = (seasonal.daily_days || []).length >= REWARDS.seasonTarget;
    if (streakMet || seasonMet) {
      localStorage.setItem('quests_ads_disabled', 'true');
      const reason = streakMet ? COPY.rewardReasonStreak : COPY.rewardReasonSeason;
      if (COPY.rewardUnlockedToast) toast(COPY.rewardUnlockedToast.replace('{reason}', reason || ''));
    }
  }

  function toast(msg) {
    if (!msg) return;
    const el = document.createElement('div');
    el.className = 'quest-toast';
    el.textContent = msg;
    document.body.appendChild(el);
    requestAnimationFrame(function() {
      el.classList.add('quest-toast-show');
      setTimeout(function() {
        el.classList.remove('quest-toast-show');
        el.addEventListener('transitionend', function() { el.remove(); }, { once: true });
      }, 4500);
    });
  }

  window.questsHook = function(event) {
    const daily = loadDaily();
    const seasonal = loadSeasonal();
    let dirtyD = false;
    let dirtyS = false;
    let streak = null;

    if (event === 'tentaizu_solved') {
      if (daily.quest === 'tentaizu_daily' && !daily.completed) {
        daily.completed = true; dirtyD = true;
        toast(COPY.toastDailyTentaizu);
        streak = recordDailyCompletion(seasonal); dirtyS = true;
      }
      if (seasonal.tz_count < 10) {
        seasonal.tz_count++; dirtyS = true;
        if (seasonal.tz_count >= 10) toast(COPY.toastSeasonTentaizu);
      }
    } else if (event === 'easy_won') {
      if (daily.quest === 'easy_win' && !daily.completed) {
        daily.completed = true; dirtyD = true;
        toast(COPY.toastDailyEasy);
        streak = recordDailyCompletion(seasonal); dirtyS = true;
      }
    } else if (event === 'intermediate_won') {
      if (!seasonal.int_won) {
        seasonal.int_won = true; dirtyS = true;
        toast(COPY.toastSeasonIntermediate);
      }
    } else if (event === 'rush_mine_cleared') {
      if (daily.quest === 'rush_5_mines' && !daily.completed) {
        daily.rush_progress = (daily.rush_progress || 0) + 1; dirtyD = true;
        if (daily.rush_progress >= 5) {
          daily.completed = true;
          toast(COPY.toastDailyRush);
          streak = recordDailyCompletion(seasonal); dirtyS = true;
        }
      }
      if (seasonal.rush_mines < 100) {
        const prev = seasonal.rush_mines;
        seasonal.rush_mines = Math.min(100, prev + 1); dirtyS = true;
        if (prev < 100 && seasonal.rush_mines >= 100) toast(COPY.toastSeasonRush);
      }
    }

    if (dirtyD) safeSet('quests_daily', daily);
    if (dirtyS) safeSet('quests_seasonal', seasonal);
    if (dirtyD || dirtyS) checkReward(streak || loadStreak(), seasonal);
    if (typeof window._renderQuests === 'function') window._renderQuests();
  };

  window.questsGetState = function() {
    const daily = loadDaily();
    const seasonal = loadSeasonal();
    const streak = loadStreak();
    const def = DAILY_DEFS.find(function(d) { return d.id === daily.quest; }) || DAILY_DEFS[0] || {};
    return {
      daily: { def, completed: daily.completed, rush_progress: daily.rush_progress || 0 },
      seasonal: SEASONAL_DEFS.map(function(d) {
        const val = d.type === 'count' ? (seasonal[d.key] || 0) : !!(seasonal[d.key]);
        return { def: d, value: val, completed: d.type === 'count' ? val >= d.target : val };
      }),
      streak: streak.count,
      season_days: (seasonal.daily_days || []).length,
      month: monthStr(),
      ads_disabled: localStorage.getItem('quests_ads_disabled') === 'true',
    };
  };

  window.DAILY_DEFS = DAILY_DEFS;
  window.SEASONAL_DEFS = SEASONAL_DEFS;
})();
