# Classic Score Verification — Statistics Page

**Status:** in-progress
**Feature ID:** F-MS-VERIFY-STATS
**Author:** Richard Cross
**Date:** 2026-11-26

---

## Problem / Motivation

F-MS-VERIFY replays classic Minesweeper scores that could reach a high score list
and records the outcome in `scores.verification`. The site runs in `observe` mode so
that false failures can be found on real traffic before switching to `enforce`. Today
the only way to see how verification is going is to read the server log (`score not
listed (...)` lines) or query the database by hand, and the reason a score failed is
not stored anywhere but the log.

To decide when it is safe to switch to `enforce`, admins need to see, at a glance, how
many submitted scores pass and fail verification, and why the failures fail.

---

## Success Criteria

- [ ] Every classic score whose verification fails (or that has no token or move log)
      stores the reason in the database, not only in the log.
- [ ] `/admin/score-verification` shows, for the last 1, 7, 30 or 90 days: counts per
      verification status, the pass rate of replayed scores, a per-day breakdown, a
      breakdown by game mode and by client (browser, iOS app, Android app), the top
      failure reasons, and the most recent failed scores.
- [ ] The page shows the current `SCORE_VERIFICATION_MODE` and whether the app grace
      rule is on, so the reader knows whether failures are hidden or only recorded.
- [ ] Only admins can open the page; it is linked from the admin dashboard.

---

## Scope

**In this feature:**
- A nullable `scores.verification_reason` column (VARCHAR(64)), filled by
  `POST /api/scores` from `score_verification.verify()`.
- The admin page and its link on `/admin`.

**Out of scope (future):**
- Numbers Match verification statistics (F-NM-VERIFY).
- Charts; alerts when the failure rate jumps.
- Backfilling reasons for scores saved before this feature (their reason shows as
  "not recorded").

---

## Key Design Decisions

- Statistics are computed from `scores` (one row per submission), so there is no new
  table and no extra writes. Duplicate board submissions are not saved and are not
  counted.
- Reasons are the fixed `ReplayError` messages in `score_verification.py` and
  `minesweeper_engine.py`, so they group cleanly. They are trimmed to 64 characters.
- Additive schema change only (works with the previous release, F-ZERO-DOWNTIME).
- "Pass rate" = verified ÷ (verified + failed + unverified). `unchecked` scores (not
  fast enough to reach a list) and `app` scores (grace rule) are counted but not
  part of the rate.
