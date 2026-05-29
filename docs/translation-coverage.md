# Translation Coverage Report

Generated: 2026-05-29  
English baseline: **1,761 keys**

---

## Coverage by Language

| Language | Keys | Missing | Coverage |
|---|---|---|---|
| 🇳🇱 `nl` Dutch | 1,615 | 146 | **91.7%** |
| 🇩🇪 `de` German | 1,401 | 360 | **79.6%** |
| 🇮🇹 `it` Italian | 1,367 | 394 | **77.6%** |
| 🇯🇵 `ja` Japanese | 1,300 | 461 | **73.8%** |
| 🇨🇳 `zh` Simplified Chinese | 1,293 | 468 | **73.4%** |
| 🇫🇷 `fr` French | 1,288 | 473 | **73.1%** |
| 🇪🇸 `es` Spanish | 1,290 | 471 | **73.3%** |
| 🇰🇷 `ko` Korean | 1,264 | 497 | **71.8%** |
| 🇺🇦 `uk` Ukrainian | 1,264 | 497 | **71.8%** |
| 🇷🇺 `ru` Russian | 1,264 | 497 | **71.8%** |
| 🇧🇷 `pt` Portuguese | 1,264 | 497 | **71.8%** |
| 🇹🇭 `th` Thai | 1,259 | 502 | **71.5%** |
| `eo` Esperanto | 1,249 | 512 | **70.9%** |
| 🇹🇼 `zh-hant` Traditional Chinese | 1,158 | 603 | **65.8%** |
| 🇵🇱 `pl` Polish | 1,170 | 591 | **66.4%** |
| 🇵🇭 `tl` Tagalog | 1,179 | 582 | **67.0%** |
| `pgl` Pig Latin | 1,083 | 678 | **61.5%** |

> `tlh` Klingon inherits from `en` automatically and is excluded from this report.

---

## Gaps by Feature Area

The table below shows which feature groups have untranslated keys and how many languages are affected. Groups marked **All 17** affect every non-English language.

| Feature group | Key prefix | EN keys | Langs missing any |
|---|---|---|---|
| SEO meta tags — Sudoku, Worldsweeper, Cylinder, Toroid, PvP, Board Generator | `meta_*` | 127 | **All 17** |
| 15 Puzzle game + how-to + generator | `fp_*` | 72 | **All 17** |
| Mahjong Solitaire UI + how-to | `mj_*` | 42 | **All 17** |
| 2048 game UI + how-to | `t2k_*` | 43 | **All 17** |
| Quests / achievements system | `quest_*`, `quests_*` | 38 | **All 17** |
| Worldsweeper game | `ws_*` | 37 | **All 17** |
| Numbers Match game | `nn_*` | 29 | **All 17** |
| Seasonal banners | `banner_*` | 5 | **All 17** |
| Profile / game history | `profile_*` | 10 | **All 17** |
| Other games descriptions | `other_*` | 10 | **All 17** |
| 2048 Hexagon variant UI | `t2kh_*` | 21 | 16 of 17 *(th has it)* |
| 2048 Hexagon how-to | `t2khex_*` | 27 | 16 of 17 *(th has it)* |
| Tentaizu strategy guide | `tz_strategy_*` | 52 | 16 of 17 *(it has it)* |
| Tentaizu landing / SEO sections | `tz_landing_*` | 24 | 10 of 17 |
| Rush mode how-to guide | `rush_*` | 157 | pgl, zh-hant only |
| Minesweeper how-to guide | `ms_*` | 114 | eo, th, pgl, zh-hant, pl, tl |
| Jigsaw puzzle generator | `jgen_*` | 26 | th, pgl, zh-hant, pl, tl |
| Links page | `links_*` | 39 | 15 of 17 *(de, ja have it)* |
| Board generator UI | `bg_*` | 17 | 15 of 17 |
| Error pages (403, 404) | `err403_*`, `err404_*` | 6 | 15 of 17 |

---

## Priority Recommendations

### P1 — Affects every language, high player-facing impact
- **`mj_*`** — Mahjong Solitaire UI strings (game currently shows English fallback in all non-English locales)
- **`t2k_*`** — 2048 game UI
- **`nn_*`** — Numbers Match game
- **`quest_*` / `quests_*`** — Quests/achievements system
- **`game_*` gaps** — Stats labels (3BV, efficiency, share link) shown in-game

### P2 — Content/SEO, affects all languages
- **`fp_*`** — 15 Puzzle full how-to and generator (72 keys)
- **`ws_*`** — Worldsweeper game (37 keys)
- **`banner_*`** — Seasonal banners (5 keys, simple)
- **`meta_*` gaps** — SEO tags for Sudoku, PvP, Cylinder/Toroid/Worldsweeper, Board Generator

### P3 — Affects a subset of languages
- **`tz_strategy_*`** — Tentaizu strategy guide (52 keys; missing from 16 langs)
- **`t2kh_*` / `t2khex_*`** — 2048 Hexagon (48 keys combined; missing from 16 langs)
- **`ms_*`** — Minesweeper how-to (114 keys; missing from eo, th, pgl, zh-hant, pl, tl)
- **`tz_landing_*`** — Tentaizu landing content (24 keys; missing from 10 langs)

### P4 — Lower traffic / niche
- `rush_*` how-to guide (missing only from pgl, zh-hant)
- `jgen_*` jigsaw generator (missing from th, pgl, zh-hant, pl, tl)
- `links_*` links page
- `err403_*` / `err404_*` error pages

---

## Notes

- **Dutch (`nl`)** is the most complete language at 91.7% — it was written most recently and captures features the other languages predate.
- **Pig Latin (`pgl`)** and **Traditional Chinese (`zh-hant`)** have the largest gaps, also missing `rush_*` and several older feature groups.
- The **`tmt_*`** keys (Tametsi page) were added to all 18 languages on 2026-05-29 and are not reflected as gaps.
- Re-run `scripts/coverage_report.py` after any translation batch to refresh this data.
