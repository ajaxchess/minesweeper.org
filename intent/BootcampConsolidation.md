# Bootcamp: Package Consolidation and Curriculum Single Source

**Status:** idea
**Feature ID:** F-BC-CONSOLIDATE
**Author:** Richard Cross
**Date:** 2026-09-21

---

## Problem / Motivation

The bootcamp was delivered in numbered phases and the numbering is still the
architecture. The repo root contains `phase2_analyzer/`, `phase4_routes/`,
`phase5_bootcamp/` and `phase7_drills/`, plus a `minesweeperbootcamp/` directory
holding a separate README, docs, scripts and transcripts. Those names describe the
order the work was done in, which is information of no value to anyone reading the
code now and actively misleading to anyone joining the project.

Three concrete problems follow from it.

**`phase5_bootcamp/` looks like dead weight and is not.** This was recorded as an
obsolete duplicate in the July roadmap, which recommended deleting it. That
recommendation is wrong and acting on it would destroy source code.

`.github/workflows/build-assets.yml` minifies every `static/js/*.js` and
`static/css/*.css` **in place** and commits the result. So `static/js/bootcamp.js`
(14KB, mangled, one line) is both the served asset and the only copy in `static/` —
its readable source was overwritten by its own build. The last readable versions of
`bootcamp.js` and `bootcamp.css` in the working tree are the ones in
`phase5_bootcamp/static/`, which survive only because the minifier's glob never
reached outside `static/`. Git confirms the relationship: both files were last
changed by the same commit `6b58f3a2`, after which only the `static/` copy received
`2827960a chore: minify static assets [skip ci]`.

This is a repo-wide problem rather than a bootcamp one, and it is specified
separately as **F-ASSETS**. It is a hard prerequisite for this feature: the readable
sources must be recovered into a proper source location, and verified to rebuild to
byte-equivalent output, *before* anything deletes `phase5_bootcamp/`.

**The curriculum has no single source of truth.** Level names, taglines, habits,
drill lists and the 0.85 mastery threshold are duplicated across
`phase4_routes/queries.py`, `phase2_analyzer/pipeline.py`, `phase7_drills/mastery.py`
and — as hardcoded abbreviation strings — `static/js/bootcamp.js`, which rewrites
"Cut Wasted Clicks" to "Cut Waste" and five other names by literal string
replacement. Renaming a level currently means finding four places, one of which is a
minified bundle. This is exactly the shape of duplication that produced the
drill-ID namespace mismatch already fixed once in July.

**Bootcamp routes are in `main.py`.** The file is 140KB. `/bootcamp`,
`_build_bootcamp` and the profile bootcamp endpoints sit in it, while
`phase4_routes` and `phase7_drills` already demonstrate the `include_router`
pattern the project has settled on.

Also worth folding in: `database.py` and `database_template.py` are byte-identical
in the working tree (86KB each), which makes the "never edit `database.py`" rule in
`CLAUDE.md` easy to violate by accident since nothing about the file announces that
it is generated.

---

## Success Criteria

- [ ] One `bootcamp/` package containing `analyzer/`, `api/`, `drills/` and `web/`
- [ ] `phase5_bootcamp/` is deleted, **after** F-ASSETS has recovered its readable
      sources into the canonical source location
- [ ] Stale READMEs are corrected or archived — `phase7_drills/README_Drills.md`
      contradicts itself, stating "all 7 levels shipped (drill_version 1.1)" in its
      catalog section while an earlier section still says "only L5 is wired today,
      other levels show a brief 'Drill coming soon'" 
- [ ] A single `curriculum.py` module defines level names, taglines, habits, drill
      mappings and the mastery threshold, consumed by the API, the pipeline, the
      mastery blend and the frontend via `BOOTCAMP_CONFIG`
- [ ] No level name or threshold literal appears in more than one place
- [ ] Bootcamp page routes move out of `main.py` into the bootcamp router
- [ ] `/bootcamp`, `/drill/{id}`, `/admin/bootcamp` and every bootcamp API behave
      identically before and after — verified by tests, not by inspection

---

## Scope

**In this feature:**
- Package reorganisation with import updates
- `curriculum.py` extraction and all four consumers rewired
- Frontend abbreviations served from config rather than string-replaced in JS
- Route relocation out of `main.py`
- Deletion of `phase5_bootcamp/` once F-ASSETS has rescued its sources, archival of `minesweeperbootcamp/` docs into
  `docs/` (the mockups there are referenced by F-BC-RADAR, F-BC-HEATMAP,
  F-BC-FLUENCY and F-BC-REPLAY — they must survive the move)
- README correction

**Out of scope:**
- Splitting `translations.py` (11MB, loaded at import) into lazy per-language files.
  Real problem, site-wide, deserves its own feature.
- Resolving the `database.py` / `database_template.py` duplication beyond making the
  generated-ness obvious — the deploy script depends on the current arrangement.
- Any behaviour change whatsoever.

---

## Key Design Decisions

**Do this after the analysis surfaces, not before.** F-BC-RADAR, F-BC-HEATMAP,
F-BC-FLUENCY and F-BC-REPLAY each add a template, CSS, JS and a route. Reorganising
the packages first means those four features are written against a layout that is
still settling; doing it after means one move instead of five. The exception is
`curriculum.py`, which the new surfaces will each want to read — that piece is worth
extracting first, on its own, as a small independent change.

**Land it behind tests or don't land it.** A pure refactor with no test coverage is
indistinguishable from a rewrite with unknown regressions. F-BC-TESTS should precede
the package move. This is the main argument for sequencing tests early.

**One commit per mechanical step.** Package move, then curriculum extraction, then
route relocation, then deletions — each independently revertable. A single large
"consolidation" commit is unreviewable and unbisectable.

**Preserve the mockups.** `minesweeperbootcamp/docs/` holds the design sources for
four unbuilt features. Archiving that directory without preserving those files would
delete work that four intent specs depend on.

---

## Effort Sizing

| Item | Est. |
|---|---|
| `curriculum.py` extraction + four consumers (do this one early, standalone) | 3 days |
| Package consolidation + import updates | 3 days |
| Route relocation out of `main.py` | 2 days |
| Deletions, README corrections, doc archival | 1 day |

**~2 weeks.** Zero user-visible change, which makes it the easiest thing to defer
forever and the thing that quietly taxes every bootcamp feature after it.

Dependencies: **F-ASSETS is a hard prerequisite** — deleting `phase5_bootcamp/`
before its sources are recovered loses them from HEAD. F-BC-TESTS first, ideally,
since "behaves identically before and after" is not checkable without it. The
analysis surfaces before the package move.

---

## Implementation Notes

_To be filled in after shipping._
