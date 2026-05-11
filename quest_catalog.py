"""Shared quest definitions and UI copy for the browser quest system."""

from __future__ import annotations


DAILY_QUESTS: list[dict[str, object]] = [
    {
        "id": "tentaizu_daily",
        "label_key": "quest_daily_tentaizu",
        "icon": "TZ",
        "link": "/tentaizu",
        "target": 1,
    },
    {
        "id": "easy_win",
        "label_key": "quest_daily_easy_win",
        "icon": "MS",
        "link": "/",
        "target": 1,
    },
    {
        "id": "rush_5_mines",
        "label_key": "quest_daily_rush_5",
        "icon": "RS",
        "link": "/rush",
        "target": 5,
    },
]


SEASONAL_QUESTS: list[dict[str, object]] = [
    {
        "id": "tentaizu_10",
        "label_key": "quest_season_tentaizu_10",
        "icon": "TZ",
        "type": "count",
        "key": "tz_count",
        "target": 10,
    },
    {
        "id": "intermediate_win",
        "label_key": "quest_season_intermediate_win",
        "icon": "MS",
        "type": "once",
        "key": "int_won",
    },
    {
        "id": "rush_100_mines",
        "label_key": "quest_season_rush_100",
        "icon": "RS",
        "type": "count",
        "key": "rush_mines",
        "target": 100,
    },
]


def _t(t: dict, key: str) -> str:
    return str(t[key])


def quest_config(t: dict) -> dict[str, object]:
    """Return the localized quest config consumed by static quest JavaScript."""
    def localize(items: list[dict[str, object]]) -> list[dict[str, object]]:
        localized = []
        for item in items:
            entry = dict(item)
            entry["label"] = _t(t, str(entry.pop("label_key")))
            localized.append(entry)
        return localized

    return {
        "daily": localize(DAILY_QUESTS),
        "seasonal": localize(SEASONAL_QUESTS),
        "rewards": {
            "streakTarget": 20,
            "seasonTarget": 10,
        },
        "copy": {
            "play": _t(t, "quest_play"),
            "complete": _t(t, "quest_complete"),
            "notComplete": _t(t, "quest_not_complete"),
            "unlocked": _t(t, "quest_unlocked"),
            "days": _t(t, "quest_days"),
            "rewardReasonStreak": _t(t, "quest_reward_reason_streak"),
            "rewardReasonSeason": _t(t, "quest_reward_reason_season"),
            "rewardUnlockedToast": _t(t, "quest_toast_reward_unlocked"),
            "toastDailyTentaizu": _t(t, "quest_toast_daily_tentaizu"),
            "toastDailyEasy": _t(t, "quest_toast_daily_easy"),
            "toastDailyRush": _t(t, "quest_toast_daily_rush"),
            "toastSeasonTentaizu": _t(t, "quest_toast_season_tentaizu"),
            "toastSeasonIntermediate": _t(t, "quest_toast_season_intermediate"),
            "toastSeasonRush": _t(t, "quest_toast_season_rush"),
        },
    }
