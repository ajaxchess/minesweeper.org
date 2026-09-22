# Bootcamp: Onboarding, Continuity and the Retention Loop

**Status:** idea
**Feature ID:** F-BC-FUNNEL
**Author:** Richard Cross
**Date:** 2026-09-21

---

## Problem / Motivation

The bootcamp is built and reachable, and almost nothing pulls a player into it or
brings them back. Four gaps, all small individually, compound into the difference
between a feature that exists and a feature that gets used:

**Nothing announces it.** A player accumulates analyzed games and is never told a
diagnosis is waiting. The nav link is the only invitation, and a nav link is not an
invitation — it is a thing you notice if you were already looking.

**Guest progress is lost at signup.** Diagnosis and drills both work for anonymous
players via `guest_token` — `phase7_drills/routes.py` resolves a player as email or
guest token. Nothing migrates those rows when the guest creates an account. A player
who drills as a guest, likes it enough to sign up, and finds an empty bootcamp has
been actively punished for converting.

**There is no reason to come back tomorrow.** `drill_sessions.started_at` is indexed
by player and nothing reads it for streaks. The habit loop the bootcamp depends on
has no mechanic behind it.

**We cannot see whether any of it works.** `/admin/bootcamp` exists but carries no
funnel: diagnosis views → drill starts → completions → mastery change. Every field
needed is already in `drill_sessions` and `game_analyses`. Without it there is no
way to know whether the 0.85 mastery threshold or the 0.3× drill weight are anywhere
near correctly calibrated — they are currently guesses that nobody can check.

---

## Success Criteria

- [ ] A player who crosses the analyzed-game threshold sees a dismissible prompt that
      their diagnosis is ready, linking to `/bootcamp`
- [ ] Guest analyses and drill sessions migrate to the account on signup, with no
      loss of level or mastery
- [ ] A drill streak is tracked and displayed, and breaking it is visible
- [ ] The recommended next drill comes from the player's weakest habit rather than
      always the current level's default drill
- [ ] `/admin/bootcamp` shows the funnel: diagnosis views, drill starts, completion
      rate, mastery delta, all filterable by date
- [ ] `/admin/bootcamp` shows cohorts by entry level and median time-to-graduate per
      level

---

## Scope

**In this feature:**
- Diagnosis-ready prompt on the game summary, with a seen/dismissed state
- Guest→account migration for `game_analyses` and `drill_sessions` on signup
- Streak computation from `drill_sessions.started_at`, surfaced on `/bootcamp`
- Weakest-habit drill recommendation (no `weakest_habit` consumer exists today)
- Admin funnel and cohort charts

**Out of scope:**
- Email or push notifications of any kind
- Badges, points or any broader gamification system beyond the streak
- Recalibrating the mastery threshold or drill weight — this feature builds the
  instrument that would let someone make that call, deliberately not the call itself

---

## Key Design Decisions

**Guest migration is a correctness bug, not a feature.** It should be treated as the
highest priority item here. The migration key is `guest_token`, which already lives
on `game_replays` and is used as `player_id` in `drill_sessions`; signup needs to
rewrite those rows to the new account identity inside one transaction, and it needs
to be idempotent because signup can be retried.

**The prompt must not nag.** One dismissible prompt at the threshold, remembered,
not re-shown. The bootcamp's entire premise is that we are helping rather than
harassing, and a re-appearing banner contradicts that before the player has read a
word of it.

**Streaks measured in drills, not logins.** A streak that rewards opening a page is
a streak that teaches nothing. Count days on which a drill session was completed.

**The admin funnel is the point, not a nice-to-have.** Two of the bootcamp's central
constants — the 0.85 mastery threshold and the 0.3× drill blend weight — were chosen
by judgement and have never been validated against behaviour. Until the funnel and
cohort views exist, nobody can tell whether players are graduating too easily, too
slowly, or dropping out at a particular level. Build this before tuning anything.

---

## Effort Sizing

| Item | Est. |
|---|---|
| Guest→account migration | 3 days |
| Diagnosis-ready prompt | 2 days |
| Streaks | 2 days |
| Weakest-habit recommendation | 2 days |
| Admin funnel + cohort charts | 1 wk |

**~2.5 weeks total.** Each item ships independently; the migration should go first.

---

## Implementation Notes

_To be filled in after shipping._
