# Greek (`el`) Translation Plan — minesweeper.org

The routing pattern (`/de`, `/fr`, `/el`…), language switcher, flag image system, FastAPI backend,
and sitemap generation all already exist for 18 languages. The work is mostly **content translation
+ registering the new locale in one place**.

---

## Step 1 — Register the new locale in the codebase (~1 hour)

- Add `el` (display name `Ελληνικά`) to wherever the supported language list is defined (likely a
  single config dict or constant in the FastAPI app)
- Add `/static/img/flags/el.png` — the Greek flag image for the switcher

---

## Step 2 — Create the Greek translation file (~30 min setup)

- Copy the English source translation file (`.po`, `.yaml`, `.json`, or Python dict — whatever
  format the other 18 locales use) as the Greek skeleton
- All values start empty/English; fill them in over the following steps

---

## Step 3 — Translate UI strings (shared across all pages) (~2–3 hours)

These are short but numerous — every button, label, and message used in the game itself:

- **Game controls:** New Game, Pause, Restart, Quit, Flag, Reveal
- **Status messages:** You Win, Game Over, mines remaining, timer labels
- **Difficulty labels:** Beginner, Intermediate, Expert, Custom, Evil
- **Settings panel labels**, leaderboard column headers, account/profile strings
- **Navigation:** Play, How to Play, Strategy, About, Leaderboard, Log In, Sign Up
- **Error & validation messages**, notification toasts

---

## Step 4 — Translate long-form content pages (~1–2 days)

Each page is a discrete chunk that can be worked on independently or handed to a translator:

| Page | ~Word Count | Notes |
|---|---|---|
| Home | ~300 | Marketing copy, mode descriptions |
| How to Play | ~4,000 | Largest single piece; tutorial prose |
| Strategy | ~1,000–2,000 | Estimate; overlaps with How to Play |
| About | ~2,000 | Includes the landmine/Diana section — tone matters |
| Rush | ~500 | Mode description + instructions |
| Multiplayer (Duel/PvP) | ~500 | Mode descriptions |
| Tentaizu | ~500 | Rules + how-to |
| Mosaic | ~300 | Rules + how-to |
| CubeSweeper | ~300 | Rules + how-to |

---

## Step 5 — Decide on blog articles (~30 min decision)

The 13 blog articles are the one open question — check how other languages handle them. If
`/de/blog/...` exists, translate them; if blogs are English-only across all locales, skip.

---

## Step 6 — Wire up the sitemap & hreflang (~1 hour)

- Add `/el`, `/el/intermediate`, `/el/how-to-play`, etc. to the sitemap generator (likely a
  one-line change if it already loops over the language list)
- Confirm `<link rel="alternate" hreflang="el">` tags are emitted on all pages (likely automatic
  once `el` is in the supported language list)

---

## Step 7 — QA pass (~2–4 hours)

- Native Greek speaker plays through the full game flow and reads each page
- Check for text overflow/clipping — Greek words tend to run longer than English
- Verify the site font supports the Greek Unicode block (U+0370–U+03FF)
- Confirm `/el`, `/el/how-to-play`, etc. all resolve correctly and return `200`

---

## Step 8 — Deploy & monitor

- Ship behind a feature flag or deploy directly (consistent with how other languages were released)
- Watch for any untranslated string fallbacks appearing in the Greek UI after launch

---

## Effort Summary

| Work type | Estimated effort |
|---|---|
| Code / config changes | ~2–3 hours |
| UI string translation | ~2–3 hours |
| Long-form page translation | ~1–2 days |
| QA | ~half a day |

The dominant cost is the **~10,000 words of long-form content** — everything else is small because
the infrastructure is already in place for the other 18 languages.
