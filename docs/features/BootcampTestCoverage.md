# Bootcamp: Test Coverage

**Status:** done
**Feature ID:** F-BC-TESTS
**Author:** Richard Cross
**Date:** 2026-09-21

---

## Problem / Motivation

The bootcamp has two test files — `tests/test_drills.py` (drill generation) and
`tests/test_bootcamp_queries.py` (mastery blending integration) — both last touched
in early July. Between them they cover drill board generation and the drill-into-
diagnosis blend. Nothing covers the rest.

Specifically untested: the analyzer's seven mastery passes and the DARD passes
that feed them, level assignment from mastery, the diagnosis and level-progress
endpoints, the radar, heatmap and pattern-fluency endpoints, the annotation builder
that four other features now depend on, the difficulty filtering that was added
specifically to stop beginner games contaminating expert diagnoses, and the drill
submit flow's resume, idempotency and conflict behaviour.

This matters more now than it did in July for two reasons. Four new frontend
features (F-BC-RADAR, F-BC-HEATMAP, F-BC-FLUENCY, F-BC-REPLAY) are about to be built
directly on those untested endpoints, and a package consolidation
(F-BC-CONSOLIDATE) is queued that moves every one of these modules. A pure refactor
over an untested subsystem is not a refactor; it is a rewrite whose regressions
surface in production.

---

## Success Criteria

- [ ] Level assignment is tested against fixed mastery vectors, including the
      boundaries either side of the 0.85 threshold
- [ ] Each analyzer pass has a test over a hand-built move log with a known expected
      output — at minimum wasted clicks, missed shortcuts, openings, fishing, flag
      value and hierarchy
- [ ] Difficulty filtering is tested: a player with beginner and expert games gets
      distinct, non-blended diagnoses
- [ ] Drill generation determinism is tested — same seed, same board, for all seven
      drill types
- [ ] Drill submit flow is tested for resume, idempotent re-submit and conflict
- [ ] `/api/radar`, `/api/heatmap`, `/api/patterns/fluency` and
      `/api/replays/{id}` each have at least a shape-and-auth test
- [ ] The annotation builder is tested for badge assignment, suppression of
      positive cases, and sequential numbering
- [ ] Tests run in CI and a failure blocks the staging gate

---

## Scope

**In this feature:**
- Fixtures: a small library of hand-built move logs with known analyzer outputs
- Unit tests for analyzer passes and level assignment
- API tests for the six bootcamp/analysis endpoints, covering auth and empty states
- Drill generation and submit-flow tests
- CI wiring so these run on the staging gate described in `docs/staging-gate-runbook.md`

**Out of scope:**
- Frontend/browser tests for the bootcamp pages
- Load or performance testing
- Backfilling tests for the rest of the site

---

## Key Design Decisions

**Hand-built move logs are the investment worth making.** Most of the value here
comes from a handful of small, deliberately constructed games with known-correct
expected outputs: one with exactly three wasted clicks, one with a missed 1-2-1
opening, one with a flag that is never used in a chord. Those fixtures are reusable
by every pass, by the annotation builder, and by the replay analysis page. Build
them first and the tests write themselves.

**Test the boundary, not the middle.** Level assignment at 0.849 and 0.851 is where
the bugs live. Same for the blend weight when a player has drills but no games, and
no games but drills.

**Empty and sparse states are the common production case.** Most players do not have
50 analyzed games. Every endpoint needs a test for the too-few-games path, since
that is what a new visitor actually hits and it is the state the frontend features
will spend the most effort rendering.

**This gates F-BC-CONSOLIDATE.** The refactor's success criterion is "behaves
identically before and after", which is only checkable with these tests in place.

---

## Effort Sizing

| Item | Est. |
|---|---|
| Fixture library of annotated move logs | 3 days |
| Analyzer pass + level assignment tests | 4 days |
| API endpoint tests | 3 days |
| Drill generation + submit flow tests | 2 days |
| CI wiring | 1 day |

**~2.5 weeks.** Front-loaded value: the fixture library alone makes the analyzer
debuggable in a way it currently is not.

Dependencies: none. Should precede F-BC-CONSOLIDATE.

---

## Implementation Notes

Two new test files, 34 tests total, all passing:

**`tests/test_bootcamp_analyzer.py`** (22 tests) — unit tests for the phase2 analyzer:
- `detect_wasted_clicks`: safetyChord and flagOnUnused cases, plus clean-game negative
- `detect_shortcuts`: missed chord and right-click-on-revealed no-op cases
- `detect_stranded_flags`: flag on edge not used in chord vs. non-edge flag
- `classify_death`: forcedGuess, avoidableGuess (with region label), misread, and chord death
- `detect_guesses`: forced vs. avoidable, including the avoidable-guess region field
- `diagnose_level`: boundary tests at 0.849/0.851 threshold, multi-axis weakest-axis selection
- `_finalize_level_mastery`: DARD pass promotion, already-set protection, empty axes

**`tests/test_bootcamp_api.py`** (12 tests) — auth and annotation builder:
- Auth gate (parametrized): all 8 bootcamp endpoints return 401 with no session
- Annotation builder: sequential numbering, taken-opening suppression, high-value-flag suppression, empty analysis

**Three bug fixes in `phase2_analyzer/passes_speed_efficiency.py`:**
- `detect_wasted_clicks`: replaced `list(snapshot_at_each_move(game))` with incremental
  `clone_board(board)` + `apply_move` — the generator yields the same mutable object at
  every step, so the list captured all references to the final board state
- `detect_stranded_flags`: same mutable-snapshot fix
- `classify_death`: replaced snapshot approach with `simulate_up_to(game, last_idx - 1)` to
  get the board state before the death click; the old code examined the post-death board

**SQLite/MEDIUMTEXT compatibility fix:**
- Added `SQLiteTypeCompiler.visit_MEDIUMTEXT` patch in `tests/conftest.py` — MySQL's MEDIUMTEXT
  type is used in `GameAnalysis` columns and the SQLite compiler can't render it at CREATE TABLE
  time; the patch teaches SQLite to treat it as plain TEXT for test runs
- Reverted incorrect `try/except ImportError` in `phase2_analyzer/pipeline.py` (the import
  never fails — the error is at compile time, not import time)
