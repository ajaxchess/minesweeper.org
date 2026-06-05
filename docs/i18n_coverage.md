# i18n Coverage Report
_Generated 2026-06-05 · Baseline: 1,936 English non-empty keys_

## Summary table

| Lang | Keys present | Missing | Empty | % done |
|------|-------------|---------|-------|--------|
| nl   | 1,993 | 0   | 1 | ✅ 100% |
| el   | 1,993 | 0   | 1 | ✅ 100% |
| hi   | 1,850 | 143 | 1 | 93% |
| sv   | 1,830 | 163 | 1 | 92% |
| id   | 1,830 | 163 | 1 | 92% |
| ms   | 1,830 | 163 | 1 | 92% |
| it   | 1,679 | 312 | 1 | 84% |
| de   | 1,651 | 340 | 1 | 82% |
| ja   | 1,616 | 376 | 1 | 81% |
| es   | 1,606 | 385 | 1 | 80% |
| fr   | 1,604 | 387 | 1 | 80% |
| zh   | 1,582 | 409 | 1 | 79% |
| ko   | 1,580 | 411 | 2 | 79% |
| uk   | 1,580 | 411 | 1 | 79% |
| ru   | 1,580 | 411 | 1 | 79% |
| pt   | 1,580 | 411 | 1 | 79% |
| th   | 1,554 | 436 | 0 | 78% |
| eo   | 1,529 | 460 | 1 | 76% |
| pl   | 1,487 | 503 | 0 | 74% |
| tl   | 1,487 | 503 | 0 | 74% |
| pgl  | 1,363 | 625 | 0 | 68% |

> The 1 "empty" key present in most languages (`ms_howto_inter_p_cascade2`) is also empty in
> English — intentionally blank in the source.

---

## Missing key waves

Missing keys fall into three distinct tiers corresponding to when features were added to the site.

### Wave 1 — Missing from all languages except nl/el (~100 keys)

These are the highest-priority gaps: live UI that every user sees.

| Prefix | Count | Feature |
|--------|-------|---------|
| `lb_*` | 47 | New leaderboard UI (period labels, empty states, personal scores, showcase) |
| `jig_*` | 43 | Jigsaw puzzle (daily, how-to-play, leaderboard, controls) |
| `pvprk_*` | 11 | PvP Rankings page |
| `pvplb_*` | 7 | PvP Leaderboard page |
| `pvp_*` | 6 | PvP shared UI |
| `aria_*` | 6 | Accessibility labels (directional moves) |
| `mswchess_*` | 5 | Minesweeper Chess variant |
| `puzzles_*` | 3 | Puzzles hub (subtitle, section labels) |
| `duel_chat_*` | 2 | Duel chat header/placeholder |

### Wave 2 — Missing from ~15 languages (adds ~160–220 more keys)

Languages below `hi`/`sv`/`id`/`ms` also lack these.

| Prefix | Count | Feature |
|--------|-------|---------|
| `links_*` | 19–57 | Links page (videos, images, community; full set for lower tiers) |
| `tz_strategy_*` | 58 | Tentaizu Strategy Guide |
| `tz_landing_*` | 24 | Tentaizu landing page (history, diff, tips) |
| `ws_*` | 31–37 | Worldsweeper |
| `t2khex_*` | 25 | Hex-2048 how-to-play |
| `t2kh_*` | 20 | Hex-2048 game UI |
| `bg_*` | 17 | Board Generator |
| `nav_*` | 10 | Nav theme descriptions + Tametsi nav entries |
| `other_*` | 5–10 | Other games hub descriptions |
| `meta_*` | 12–23 | Page titles/descriptions for newer games |
| `err404_*` / `err403_*` | 4 | Error page copy |
| `profile_*` | 1 | Game history label |
| `blog_*` | 1 | Blog subtitle |

### Wave 3 — Missing from the lowest-coverage languages (adds ~100+ more)

Languages below `it` (and some above) also lack these.

| Prefix | Count | Feature |
|--------|-------|---------|
| `ms_*` | 39–106 | Mosaic puzzle (partial or full) |
| `meta_kw_*` | 2 | Meta keywords |
| `meta_title_*` | ~11 | Additional page titles |

---

## Recommended priority order

1. **Wave 1 universals** (~100 keys) — add to all 19 incomplete languages. These cover the
   leaderboard, Jigsaw, and PvP pages that every visitor encounters regardless of game mode.

2. **`tz_*` content** (58–82 keys depending on language) — Tentaizu is a flagship daily puzzle;
   Strategy Guide and landing page copy is missing from most languages.

3. **`ws_*` + `t2kh/t2khex_*`** (~60 keys combined) — Worldsweeper and Hex-2048 UI.

4. **`ms_*` backfill** for `th`, `pl`, `tl`, `pgl`, `eo` — Mosaic is partially or fully untranslated
   in the lowest-coverage languages.

5. **`links_*` full set** for lower-tier languages — lower urgency (static page, not game UI).

---

## Notes

- `nl` is the only language besides `el` kept fully up to date, likely as the primary
  non-English development language.
- `th`, `pl`, `tl` report 0 empty keys despite being incomplete — all gaps are *missing* keys
  (the key/value pair is absent entirely), not present-but-blank entries.
- `ko` is the only language with 2 empty keys rather than 1.
- `pgl` (Pirate/novelty language) is the least complete at 68% and lowest priority for gaps.
