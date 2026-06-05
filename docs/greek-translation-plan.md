# Greek (`el`) Translation Plan — minesweeper.org

**Language code:** `el`  
**Display name:** `Ελληνικά`  
**Picker label:** `EL`  
**Script:** Greek (Unicode block U+0370–U+03FF)  
**Reference languages already live:** nl, sv, id, ms, hi (most recently added)

---

## Overview

The site already supports 19 real languages via a uniform infrastructure (path-prefix routing `/el/…`, ChainMap fallback to English, automatic sitemap/hreflang). Adding Greek is:

1. **One large content task** — translating all 1,993 keys in `translations.py`
2. **Four small code changes** — registering the locale in `REAL_LANGS`, `LANGUAGE_OPTIONS`, `base.html` (two spots), and the `static/img/flags/` directory

No routing, middleware, database, or API changes are needed.

---

## Step 1 — Add the Greek flag image

**File:** `static/img/flags/el.png`

All other flags are 20 × 14 px PNG files in this directory. Source a Greek flag (blue and white horizontal stripes with a white cross in the upper-left canton) at the same dimensions, matching the existing files' style.

**Check:** Confirm the file exists and is referenced correctly by opening the language picker on any page after Step 3 is done.

---

## Step 2 — Register `el` in `REAL_LANGS`

**File:** `translations.py`, lines 37677–37681

```python
# BEFORE
REAL_LANGS: frozenset = frozenset({
    "de", "fr", "es", "ko", "ja", "zh", "zh-hant",
    "ru", "pt", "it", "pl", "uk", "th", "tl", "nl", "sv",
    "id", "ms", "hi",
})

# AFTER
REAL_LANGS: frozenset = frozenset({
    "de", "fr", "es", "ko", "ja", "zh", "zh-hant",
    "ru", "pt", "it", "pl", "uk", "th", "tl", "nl", "sv",
    "id", "ms", "hi", "el",
})
```

This single change automatically enables:
- Greek in the sitemap (`sitemap.xml` loops over `sitemap_langs` which reads `REAL_LANGS`)
- `<link rel="alternate" hreflang="el">` tags on all localized pages (once Step 4 is done)

---

## Step 3 — Register `el` in `game_catalog.py`

**File:** `game_catalog.py`, lines 16–39  
Insert after the `hi` entry (line 35):

```python
{"code": "el", "label": "EL", "name": "Ελληνικά", "flag": "el"},
```

This registers Greek in the backend language registry used by several app routes.

---

## Step 4 — Update `base.html` (two spots)

**File:** `templates/base.html`

### 4a. The `_ll` abbreviation dict (line 397)

```jinja2
{#- BEFORE -#}
{%- set _ll = {'en':'EN','de':'DE','fr':'FR','es':'ES','pt':'PT','it':'IT','pl':'PL','ru':'RU','uk':'UK','zh':'ZH','zh-hant':'繁體','ja':'JA','ko':'KO','th':'TH','tl':'TL','nl':'NL','sv':'SV','id':'ID','ms':'MS','hi':'HI','pgl':'PGL','eo':'EO'} -%}

{#- AFTER — add 'el':'EL' -#}
{%- set _ll = {'en':'EN','de':'DE','fr':'FR','es':'ES','pt':'PT','it':'IT','pl':'PL','ru':'RU','uk':'UK','zh':'ZH','zh-hant':'繁體','ja':'JA','ko':'KO','th':'TH','tl':'TL','nl':'NL','sv':'SV','id':'ID','ms':'MS','hi':'HI','el':'EL','pgl':'PGL','eo':'EO'} -%}
```

### 4b. The language picker loop (lines 412–434)

Insert after the `('hi', 'HI', 'हिन्दी')` entry and before `('pgl', ...)`:

```jinja2
('el',      'EL',   'Ελληνικά'),
```

### 4c. The hreflang alternates block (lines 23–41)

Insert after the `hi` line (line 41):

```jinja2
<link rel="alternate" hreflang="el"      href="https://minesweeper.org/el{{ _bp }}">
```

---

## Step 5 — Add the Greek translation section to `translations.py`

**File:** `translations.py`  
**Insert after:** Line ~30089 (the closing `},` of the Dutch `"nl"` section), or at the same position relative to the other new languages (`sv`, `id`, `ms`, `hi` are in the 30090–37676 range).

The section must be:

```python
    "el": {
        # ... 1,993 key-value pairs ...
    },
```

The Dutch section (lines 28170–30089) is the best structural reference: it was the most recently hand-crafted section and has the same key set.

### 5a. Bootstrapping the skeleton

The fastest way to produce the initial skeleton:

```python
# bootstrap_el.py  (run once, then delete)
from translations import TRANSLATIONS

en = TRANSLATIONS["en"]
lines = ['    "el": {']
for k, v in en.items():
    # Use English value as placeholder — replace with Greek during translation
    escaped = v.replace('\\', '\\\\').replace('"', '\\"')
    lines.append(f'        {k!r}: "{escaped}",')
lines.append('    },')
print('\n'.join(lines))
```

Run `python bootstrap_el.py >> translations_el_stub.py`, paste the output into `translations.py`, then replace values language by language.

### 5b. Translation order (recommended)

Translate in this order to unblock testing as early as possible:

| Priority | Key group | Count | Why first |
|---|---|---|---|
| 1 | `nav_*` | ~40 | Navigation renders on every page |
| 2 | `common_*`, `game_*`, `auth_*` | ~120 | Game controls, auth messages, shared UI |
| 3 | `meta_title_*`, `meta_desc_*` | ~130 | SEO; affects every page's `<title>` |
| 4 | `htp_*`, `about_*`, `hex_info_*`, `cyl_*`, `tor_*` | ~300 | How-to-play and about pages |
| 5 | `lb_*`, `pvp_*`, `duel_*` | ~80 | Leaderboard + multiplayer UI |
| 6 | `jig_*`, `other_*`, `jig_*`, `mahjong_*`, `nm_*`, `schulte_*` | ~250 | Puzzle game pages |
| 7 | `seo_*`, `seo_exp_*`, `seo_how_*`, `seo_diff_*` | ~200 | SEO content blocks |
| 8 | `tz_strategy_*`, `links_*`, `blog_*` | ~90 | Strategy guide, links page |
| 9 | Remaining long-form prose keys | ~780 | Fill remaining gaps |

A ChainMap fallback to English means untranslated keys display in English — the site is functional from the moment `"el": {}` exists, and you can fill in translations incrementally.

### 5c. Greek-specific translation notes

**Font support:** Verify that the site font (`style.css`) includes or falls back to a system font covering U+0370–U+03FF. Greek shares the Latin-Extended and Basic blocks, so most web fonts cover it, but confirm with a visual check.

**Capitalization:** Greek does not use title case for headings the way English does. Use sentence case throughout (only capitalize the first word and proper nouns).

**Game terminology:** Minesweeper community terms have established Greek equivalents:
- "mine" → μεταλλευτής / νάρκη (use **νάρκη** — consistent with how other Greek software uses it)
- "flag" → σημαία
- "reveal" → αποκάλυψη
- "Beginner / Intermediate / Expert" → Αρχάριος / Μέσος / Ειδικός

**HTML in values:** Keys containing `<strong>`, `<em>`, `<a>`, etc. must preserve the HTML tags exactly — only the visible text around them changes. Use `| safe` filter in templates (already done for Dutch equivalents).

**Ampersands in values:** Some keys use `&amp;` (already HTML-escaped). Keep these as-is.

**Number formatting:** Greek uses a period as thousands separator and comma as decimal separator (e.g., `1.000` not `1,000`). Update any hardcoded number examples in translated prose.

---

## Step 6 — Completeness verification

After the section is written, run the same Python check used for Dutch:

```python
from translations import TRANSLATIONS
en = TRANSLATIONS["en"]
el = TRANSLATIONS.get("el", {})
missing = [k for k in en if k not in el]
print(f"EN: {len(en)} | EL: {len(el)} | Missing: {len(missing)}")
```

Target: **0 missing keys** before merging.

Also confirm syntax:
```python
import ast
ast.parse(open("translations.py", encoding="utf-8").read())
```

---

## Step 7 — Template audit

Once `"el"` is live, run the Dutch-equivalent template audit:

```bash
# Scan for hardcoded English in templates (same pattern used for Dutch audit)
grep -rn '"[A-Z][a-z]\+' templates/ | grep -v '{{ t\.' | grep -v '{#'
```

The Dutch work already fixed most structural hardcodes. Greek-specific follow-up is unlikely to reveal new issues — but confirm by loading a sample of pages at `/el/…` and visually checking for English fallthrough.

---

## Step 8 — QA checklist

Work through these URLs with Greek active (`/el/…`):

| URL | Check |
|---|---|
| `/el` | Home page renders in Greek; nav, hero, and difficulty labels all translated |
| `/el/intermediate` | Game UI (mine counter, timer, reset button) in Greek |
| `/el/how-to-play` | Full HTP page rendered in Greek; no English fragments |
| `/el/leaderboard` | Column headers, period tabs, date label in Greek |
| `/el/variants` | Variant card text in Greek |
| `/el/other/jigsaw/daily` | Jigsaw UI (difficulty buttons, controls, win modal) in Greek |
| `/el/pvp` | PvP lobby and chat strings in Greek |
| `/el/hexsweeper` | Hexsweeper page in Greek; mode badge shows Greek name |
| Language picker → EL | Flag shows correctly; switching navigates to `/el/…` |
| View page source | `<title>` and `<meta name="description">` contain Greek text |
| View page source | `<link rel="alternate" hreflang="el">` present on localized pages |
| `/sitemap.xml` | Greek URLs (`/el/…`) present |

**Text overflow check:** Greek words average ~20% longer than English. Check the nav bar, difficulty tabs, leaderboard headers, and game control buttons on a 375 px wide viewport.

---

## File change summary

| File | Change | Size |
|---|---|---|
| `translations.py` | Add `"el": { 1,993 pairs }` section | ~2,200 lines |
| `translations.py` | Add `"el"` to `REAL_LANGS` | 1 line |
| `game_catalog.py` | Add `el` entry to `LANGUAGE_OPTIONS` | 1 line |
| `templates/base.html` | Add `el` to `_ll` dict | 1 token |
| `templates/base.html` | Add `('el','EL','Ελληνικά')` to picker loop | 1 line |
| `templates/base.html` | Add hreflang `el` alternate | 1 line |
| `static/img/flags/el.png` | Greek flag 20×14 px PNG | 1 file |

No routes, middleware, database schemas, JS, or CSS changes required.

---

## Effort estimate

| Task | Effort |
|---|---|
| Steps 1–4 (code wiring) | ~30 min |
| Step 5 priority 1–3 (nav + common + meta, ~290 keys) | ~2–3 hours |
| Step 5 priority 4–6 (game pages, ~630 keys) | ~1 day |
| Step 5 priority 7–9 (SEO prose + strategy + remainder, ~1,073 keys) | ~1–2 days |
| Steps 6–8 (verification + QA) | ~2–3 hours |
| **Total** | **~2.5–3.5 days** |

The translation work can be done incrementally — the ChainMap fallback means partial translations deploy safely without breaking the site.
