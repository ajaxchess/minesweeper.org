# Speff Championship 2026

**Status:** in-progress
**Feature ID:** F-SPEFF-2026
**Author:** Richard Cross
**Date:** 2026-09-21

---

## Problem / Motivation

Competitive minesweeper players care about two axes: speed (time to clear) and efficiency (click ratio = bbbv / clicks). "Speff" (Speed + Efficiency) championships filter for only 100%-efficiency games, then rank by time. Minesweeper.online runs a similar competition. We want to offer our own 2026 Speff Championship for logged-in minesweeper.org users, covering Beginner, Intermediate, Expert, and a Combined category.

---

## Success Criteria

- [ ] `/speff/2026` renders four leaderboards (Beginner, Intermediate, Expert, Combined) in tabs
- [ ] Only games where `bbbv == left_clicks + coalesce(chord_clicks, 0)` qualify (100% click efficiency)
- [ ] Only logged-in users, only standard board sizes (B 9×9/10, I 16×16/40, E 30×16/99), only 2026
- [ ] Combined tab requires qualifying times in all three modes; ranked by total time
- [ ] Player names link to their `/u/{public_id}` profile page
- [ ] Logged-in user's own row is visually highlighted
- [ ] `/speff/2026` is in sitemap.xml

---

## Scope

**In this feature:**
- `speff_routes.py` — route handler, SQL queries
- `templates/speff.html` — four-tab leaderboard page
- `main.py` — router registration
- `templates/sitemap.xml` — sitemap entry

**Out of scope:**
- Real-time updates (leaderboard is page-load snapshot)
- Historical years (2026 only for now)
- Email notifications when a player's rank changes

---

## Data Model

Source: `GameHistory` (permanent, never pruned)

Efficiency filter: `bbbv = left_clicks + COALESCE(chord_clicks, 0)`

Standard board sizes:
- Beginner: rows=9, cols=9, mines=10
- Intermediate: rows=16, cols=16, mines=40
- Expert: rows=30, cols=16, mines=99

Year scope: `created_at >= 2026-01-01` and `< 2027-01-01` (UTC)

---

## Implementation Notes

_To be filled in after shipping._
