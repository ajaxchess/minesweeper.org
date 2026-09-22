# Import Minesweeper.Online History & Bootcamp Enrollment

**Status:** idea
**Feature ID:** F-MOIMPORT
**Author:** Richard Cross
**Date:** 2026-09-21

---

## Problem / Motivation

Minesweeper.online (m.o.) is where most serious minesweeper players already have
their history. A player with 5,000 games there has a rich record of their own
improvement — and no way to learn anything from it. m.o. shows Time, 3BV, 3BV/s,
Clicks and Efficiency per game, and that is where it stops. It does not tell you
*why* your efficiency is 48%, which patterns you hesitate on, which chords you
miss, or what to practise next.

We have already built the machinery that answers those questions. `phase2_analyzer`
turns a timestamped move log into wasted-click detection, missed shortcuts,
stranded flags, opening/fishing analysis (DARD), pattern reaction times, guess
classification and a bootcamp level diagnosis. What we lack is *volume of games to
analyse* for a new visitor. A new user's first session on minesweeper.org produces
one game and therefore one data point; the coaching only becomes credible after
dozens.

Importing a player's m.o. history closes that gap in a single step. A player
arrives, connects their m.o. account, and within minutes sees a real diagnosis
built on their own several-hundred-game history — then enrols in the bootcamp with
a curriculum targeted at the weaknesses that diagnosis found. This is the
acquisition funnel for "minesweeper.org is the AI-powered site that makes you
better", and the import is the hook that makes the first impression substantive
rather than empty.

The second motivation is the player's own record. Right now a player's identity is
split across two sites, and the minesweeper.org half of it is the smaller half.
Importing makes `/u/{slug}` the complete picture of how someone plays — every game
they have played anywhere, in one history, clearly labelled by where it happened.

The third is portability, and it compounds with F-EMBED (Embeddable Game Replay).
m.o. offers no way to embed or export a game, so a player who wants to post their
best Expert run on r/Minesweeper or their own homepage has no good option today.
"Import it to minesweeper.org, then post it anywhere" is a concrete, self-interested
reason to connect an account — a better pitch than asking someone to migrate for its
own sake. The two features should be sequenced with that in mind: F-EMBED is useful
on its own and gives the import a payoff beyond analysis.

---

## Success Criteria

- [ ] A logged-in user can connect their minesweeper.online account and import their
      game history without manually copying anything game-by-game
- [ ] Imported games carry a full timestamped move log, so `phase2_analyzer` produces
      the same depth of analysis it produces for native minesweeper.org games
- [ ] Every imported game is reconciled against the stats m.o. reports for it
      (time, 3BV, click count, efficiency); mismatches are rejected, not silently stored
- [ ] Imported games appear in the user's game history on `/u/{slug}` and in their
      private profile, and are **excluded** from every leaderboard, all-time record
      and the Speff Championship
- [ ] Every game row on `/u/{slug}` is visibly marked with where it was played
      (minesweeper.org vs minesweeper.online), and the history can be filtered by source
- [ ] A user has two independent visibility controls — one for their minesweeper.org
      games and one for their imported games — and either can be published or kept
      private without affecting the other
- [ ] Visibility is enforced in the API, not just hidden in the UI, and applies to
      summary cards and trend charts as well as the history table
- [ ] The `/u/{slug}` game history matches or exceeds minesweeper.online's `/my-games`:
      mode and difficulty tabs, NF filter, time-range filter, sortable columns,
      3BV and 3BV/s, and pagination over the player's *entire* history
- [ ] After import the user lands on an evaluation report: skill radar, mistake
      heatmap, pattern fluency, assigned bootcamp level — built from their imported history
- [ ] From that report the user can enrol in the bootcamp in one click and receive a
      curriculum sequenced against their own weakest levels
- [ ] Re-running the import is incremental and idempotent — only new games are added

---

## Scope

**In this feature:**

- Browser extension ("Minesweeper.org Import Helper") that harvests the user's own
  m.o. games from their own logged-in session and uploads them to us
- Pairing flow linking an extension install to a minesweeper.org account
- Import API: batch ingest, idempotency, rate limiting, quota
- Normalizer: m.o. game representation → our `game_replays.log_json` format
- Reconciliation gate: re-derive 3BV / clicks / efficiency from the move log and
  compare against m.o.'s own reported values before accepting a game
- Async analysis of the imported backlog via the existing `phase2_analyzer` pipeline
- `/import` — connect, scope selection, progress
- `/import/report` — the evaluation (reuses existing mockups)
- Bootcamp enrollment: baseline assessment, assigned level, sequenced curriculum,
  progress tracking, graduation criteria
- **Rebuild of the `/u/{slug}` game history** to m.o. parity, with source labelling
  and a server-side paginated/sorted/filtered endpoint
- Provenance model: `source`, `source_game_id` on every game row, and exclusion of
  imported games from all ranking surfaces

**Out of scope (future):**

- Importing from any source other than minesweeper.online (`source` column is
  designed for it; no second adapter is built here)
- Desktop replay file upload (.mvf / .rmv / .avf) — separate feature, see Open Questions
- Continuous background sync (import is user-initiated; no polling m.o. on a schedule)
- Importing other players' histories — a user may only import their own account
- Any form of imported-game leaderboard, including a separate "imported" board
- Paid or cohort-gated bootcamp tiers
- Email-driven coaching drip

---

## Key Design Decisions

### Decision 1 — Import mechanism: browser extension, not server-side scraping

**Decided: browser extension / userscript.**

Investigation on 2026-09-21 established the following about minesweeper.online:

- There is no public API, no documented export, and no mention of data access in
  their help pages.
- Game history lives at `/my-games`, behind a login, split by mode
  (Standard / No guessing / PvP) and difficulty (Beginner / Intermediate / Expert /
  Custom), with an "All games" toggle and a sort control. The list is rendered
  dynamically, not present in the static HTML.
- Per-game pages exist at `minesweeper.online/game/<id>` (e.g. `/game/6020808245`)
  and include a full replay player with play/pause and a scrub bar, plus a summary
  panel: Time, 3BV, 3BV/s, Clicks, Efficiency, date, player.
- The list view exposes Time, NF flag, 3BV, 3BV/s, Eff and Date per row — but not
  the click breakdown, and not the move log.

Server-side crawling was rejected. It would require us to hold or replay a user's
m.o. session, it depends on undocumented markup that can change without notice, it
is rate-limited from a single origin, and it is the interpretation of their terms
least likely to survive contact with their operator. An extension inverts all of
that: the data never leaves the user's own authenticated session until the user
chooses to send it to us, the traffic looks like the user's own browsing because it
is, and the failure mode when m.o. changes their markup is an extension update
rather than a broken production service.

### Decision 2 — Extracting the move log is an unresolved spike and gates everything

This is the single largest risk in the feature and must be resolved before any
other work starts.

We confirmed the replay data is **not** trivially reachable. On `/game/<id>`:

- it is not present in the page HTML (no long numeric runs, no base64 blob, no
  JSON island, no oversized `data-` attribute)
- it is not in a page-global JS variable
- pressing play fires **no** `fetch` and **no** `XMLHttpRequest`

So the move log is either delivered over the WebSocket connection the page opens at
load (the site maintains a `chic3.minesweeper.online` socket), or it is held inside
the closure scope of their bundled replay engine (`index-1033.js`).

Three candidate extraction strategies, in order of preference:

1. **WebSocket frame capture** — content script patches `WebSocket` before the page
   script runs and records the replay frame. Clean and cheap if this is where the
   data lives.
2. **Replay engine hook** — locate the replay state object in the bundle and read it
   directly. Fast, but couples us to their minified build and breaks on every
   rebuild.
3. **DOM-driven reconstruction** — drive the replay control programmatically and
   observe the board DOM frame by frame, reconstructing move order and timing from
   observed state transitions. This is the guaranteed fallback: it cannot fail
   for lack of access because it only uses what the user can already see. It is
   slow (roughly real-time per game unless the scrub control can be stepped), and
   the timing resolution it recovers is bounded by the replay player's own
   granularity — which may not be good enough for pattern reaction times.

**Gate: if only strategy 3 is available and its timing resolution is too coarse for
`phase2_analyzer`'s pattern-timing passes, the fidelity decision must be revisited
before Phase 2 is funded.** A stats-only import is a much smaller feature and a much
smaller promise; we should not discover that after building an extension.

### Decision 3 — Full move log fidelity

**Decided: full move log.** Summary stats alone would give trend charts and a style
classification, but not the mistake heatmap, pattern fluency or DARD passes — which
are the parts of the product that are actually differentiated. The whole argument
for importing is that we can say something m.o. does not already say on its own
game page.

### Decision 4 — Imported games are history, not competition

**Decided: imported games are excluded from every leaderboard and all-time record,
and are included in the player's own history.**

This is the right split. The value of the import is diagnostic and biographical —
it gives us enough of a player's history to coach them, and it gives the player a
complete record of how they play. None of that requires ranking a game we did not
observe, and ranking games we did not observe is what would have cost us: a
contested record is far more expensive to walk back than to never publish.

Concretely:

- Imported games **do** appear in `/u/{slug}` game history, in the private profile,
  in personal trend charts, in the bootcamp baseline assessment, and in every
  analysis surface (heatmap, radar, pattern fluency, replay browser).
- Imported games **do not** appear in any leaderboard, any all-time record, the
  Speff Championship (F-SPEFF-2026), PvP Elo, quests, or any site-wide statistic
  that implies a ranking.
- Exclusion is enforced at the query layer, not the display layer. Every ranking
  query filters `source = 'native'`. This should be a shared helper rather than a
  predicate copy-pasted into each leaderboard, so a new leaderboard cannot leak
  imported games by omission.
- A reconciliation gate still applies, but now for **data quality** rather than
  competitive integrity: a game whose move log does not reproduce m.o.'s reported
  3BV, clicks and efficiency is rejected because it would poison the user's own
  analysis, not because it might steal a record. This means we can drop signed
  payloads, verification tiers, dispute handling and record-invalidation tooling
  from scope — a meaningful simplification bought by this decision.

### Decision 5 — `/u/{slug}` game history is rebuilt to m.o. parity

The profile history is currently much thinner than `/my-games`, and it will not
survive an import of several thousand games. Today `templates/profile_public.html`
renders a table with `#`, Time, Eff%, CPS, Date/Time, NG and Watch, behind tabs for
beginner / intermediate / expert / custom / rush / tentaizu and fixed row-count
buttons (10 / 50 / 100 / 1000). It is fed by `_build_stats()` in `main.py`, which
loads a user's **entire** `GameHistory` into memory on every profile view, groups it
in Python, and truncates `recent` at 1000 rows.

That approach is already generous and becomes untenable the moment a user imports
5,000 games. The rebuild is therefore not cosmetic — it is required by the import.

**Parity with `/my-games`** (what they have that we do not):

| m.o. feature | Our status |
|---|---|
| Standard / No guessing / PvP mode tabs | NG is a column, not a tab; no PvP in this table |
| Beginner / Intermediate / Expert / Custom tabs | Have it |
| "All games" toggle (wins only vs everything) | Missing — we show history without an outcome filter |
| "NF only" filter | Missing |
| Time-range filter ("All time") | Missing |
| Sort by column | Missing — fixed order |
| 3BV, 3BV/s columns | Missing (we show Eff% and CPS instead) |
| Rank numbering within the filtered set | Have it |
| Row links to the game replay | Have it ("Watch") |

**What we should add beyond parity**, since these are things m.o. structurally
cannot show:

- **Source column** — a badge on every row marking minesweeper.org vs
  minesweeper.online, with imported rows linking back to the source game page.
  Filterable: all / played here / imported.
- IOE and throughput from `game_analyses`
- Win / loss / abandoned outcome, with board completion % on losses
- Wasted clicks and avoidable guesses per game — the actionable columns
- A link from each row into the full analysis view, not just replay playback
- CSV export of the player's own history

**Engineering:** replace the load-everything path with a server-side endpoint that
paginates, filters and sorts in SQL — `GET /api/profile/games/{public_id}` taking
mode, difficulty, source, outcome, nf, date range, sort, page. Keep the existing
summary cards on `_build_stats()`; move only the history table to the new endpoint.
This needs an index on `(user_email, mode, created_at)` and probably
`(user_email, source, created_at)`.

### Decision 6 — Two independent visibility toggles, one per source

**Decided: a user controls the public visibility of their minesweeper.org games and
their imported games separately.**

Today `UserProfile.games_public` is a single all-or-nothing flag. That is not
sufficient once history has two provenances. A player may reasonably want their m.o.
history imported and analysed privately while publishing only what they have played
here; another may want the opposite, showing off a long m.o. record while keeping
their early practice games here to themselves. Neither is served by one switch.

Replace `games_public` with two independent booleans — no master switch, because
"both off" already expresses it and a three-flag model invites the bug where a user
turns something on and nothing happens:

```
user_profiles  - games_public               (dropped)
               + games_public_native        BOOLEAN NOT NULL DEFAULT 1
               + games_public_imported      BOOLEAN NOT NULL DEFAULT 0
```

Migration sets `games_public_native = games_public` for every existing row.

`games_public_imported` defaults to **0 (private)** deliberately. Importing your
history from another site should never silently publish it — the user asked us to
analyse those games, which is not the same as asking us to broadcast them. Rather
than leave that as friction to discover later, the import flow asks the question
directly, pre-selected to match their existing `games_public` setting, so the user
makes one active decision at the moment it is meaningful.

**Behaviour:**

| native | imported | Public profile shows |
|---|---|---|
| on | on | Full history, both sources, source filter offers all three options |
| on | off | minesweeper.org games only; source filter hidden; imported games invisible |
| off | on | Imported games only; source filter hidden |
| off | off | History section hidden entirely |

**Enforcement is server-side and covers more than the table.** The visibility flags
must be applied in `/api/profile/games/{public_id}` and
`/api/profile/public-stats/{public_id}`, not in the template. The subtle leak to
avoid is the summary cards and trend charts: if imported games are hidden from the
history table but still feed the per-difficulty summary cards, a viewer sees a best
time that has no corresponding visible game — which both looks broken and discloses
exactly what the user chose to keep private. Every aggregate on the public profile
must be computed over the visible set only. Rank numbering in the history table is
likewise computed over the filtered set.

The owner always sees their own complete history on their private profile
regardless of either flag. Leaderboards are unaffected — they show native games
only by Decision 4 and are governed by `is_public`, not by these flags.

### Decision 7 — Bootcamp enrollment is a free structured curriculum

**Decided: free structured curriculum.** Today `/bootcamp` is a charts page —
`_build_bootcamp()` in `main.py` returns the last 100 wins per mode for plotting.
Enrollment turns it into a program:

1. **Baseline assessment** from the imported history — `phase2_analyzer` already
   emits `bootcamp_level` and `level_mastery_json` per game; aggregate across the
   import to assign a starting level and identify the weakest sub-skills.
2. **Curriculum** — an ordered sequence of `phase7_drills` drills plus target
   metrics per level.
3. **Progress tracking** — mastery per curriculum item, advancement when criteria
   are met, graduation from a level.
4. `/bootcamp` becomes the enrolled dashboard; the existing charts remain as a tab.

### Data model sketch

New tables:

```
external_accounts
  id, user_email, source ('minesweeper_online'), source_player_id,
  source_display_name, connected_at, last_import_at, status

import_jobs
  id, user_email, source, status (pending|running|done|failed|partial),
  games_discovered, games_imported, games_rejected, games_duplicate,
  error_json, started_at, finished_at

bootcamp_enrollments
  id, user_email, enrolled_at, baseline_level, baseline_analysis_json,
  current_level, status (active|paused|graduated), graduated_at

bootcamp_progress
  id, enrollment_id, curriculum_item_id, state, mastery_score,
  attempts, last_attempt_at, completed_at
```

Extensions to existing tables:

```
game_replays   + source            VARCHAR(32)  NOT NULL DEFAULT 'native'
               + source_game_id    VARCHAR(64)  NULL
               + source_url        VARCHAR(255) NULL
               + imported_at       DATETIME     NULL
               UNIQUE (source, source_game_id)

game_history   + source            VARCHAR(32)  NOT NULL DEFAULT 'native'
               + outcome           VARCHAR(16)  NULL
               INDEX (user_email, source, created_at)
               INDEX (user_email, mode, created_at)

user_profiles  - games_public              (dropped; see Decision 6)
               + games_public_native       BOOLEAN NOT NULL DEFAULT 1
               + games_public_imported     BOOLEAN NOT NULL DEFAULT 0
```

Idempotency key is `(source, source_game_id)` — a re-import is a no-op for games
already held, which makes "import again later" incremental for free.

`source = 'native'` on existing rows means every current leaderboard query keeps
working unchanged until it is explicitly updated to filter — but the shared
`native_only()` helper should be applied to all of them in Phase 4 regardless, so
the filter is deliberate rather than incidental.

Note `database.py` is generated; schema changes go in `database_template.py`.

### API sketch

```
POST /api/import/pair            → issue single-use pairing token (logged-in user)
POST /api/import/jobs            → open an import job, return job id       (extension)
POST /api/import/jobs/{id}/games → batch of games, ≤50 per call            (extension)
POST /api/import/jobs/{id}/close → finalize, queue analysis                (extension)
GET  /api/import/jobs/{id}       → progress for the /import page UI
GET  /api/profile/games/{public_id} → paginated/filtered/sorted game history
POST /api/profile/settings       → now carries games_public_native +
                                   games_public_imported (replacing games_public)
GET  /import                     → connect + progress page
GET  /import/report              → evaluation report
POST /api/bootcamp/enroll        → create enrollment from latest analysis
GET  /api/bootcamp/curriculum    → assigned curriculum + progress
```

### Scale and cost

A serious m.o. player may have thousands of games. Analysis is not free —
`phase2_analyzer` replays each game through the solver. Import must be bounded
(proposal: most recent 500 games, or 12 months, user-selectable, with an explicit
"import everything" option), queued, throttled, and resumable, with visible
progress. `phase2_analyzer/backfill_with_progress.py` already does the batch-analysis
work and should be reused rather than reimplemented.

---

## Effort Sizing

One developer, calendar weeks. Phases 1–4 are largely parallelizable across the
three-person team; the serial critical path is Phase 0 → Phase 1 → Phase 2.

| Phase | Work | Size | Est. |
|---|---|---|---|
| **0** | **Spike: move-log extraction.** Determine whether the replay arrives over WebSocket, sits in bundle closure scope, or must be reconstructed from the DOM. Establish achievable timing resolution. Produce one real m.o. game as a valid `log_json`. **Gate — do not start Phase 1+ until this succeeds.** | M | **1 wk** |
| **1** | **Single-game import, end-to-end.** Paste a `/game/<id>` URL → normalize → reconcile → analyze → report. No extension. Proves the whole pipeline and ships user-visible value early. Includes normalizer, reconciliation gate, solver validity check, schema changes, `/import/report` v1 against the existing mockups. | L | **2 wks** |
| **2** | **Extension + bulk import.** MV3 extension, pairing flow, `/my-games` pagination across all mode × difficulty combinations, batch upload with retry/resume, popup progress UI, import API, job queue, quotas, `/import` page. Excludes store review latency. | XL | **4 wks** |
| **3** | **Bootcamp enrollment.** Enrollment tables, baseline assessment aggregation, curriculum model and content, progress and graduation, `/bootcamp` rebuild from charts page to enrolled dashboard, wiring to `phase7_drills`. | L | **3 wks** |
| **4** | **Profile history rebuild + provenance.** Server-side paginated/filtered/sorted `/api/profile/games`, replacing the load-everything path in `_build_stats()`. m.o. parity (mode tabs, NF filter, time range, sortable columns, 3BV/3BV/s) plus source badges, source filter, outcome, analysis links, CSV export. Split `games_public` into per-source visibility flags with migration, enforced across history, summary cards and trend charts. `native_only()` helper applied across every leaderboard and record query. Indexes. | M | **2 wks** |
| **5** | **Legal / ToS / privacy.** Review m.o. terms against an extension-based, user-initiated, own-data-only import. Privacy policy update, data deletion path, attribution, imported-games visibility toggle. Runs alongside Phase 0–1; needs a decision, not just drafting. | S | **3–5 days** |

**Total: ~12 weeks of single-developer effort.** With three developers and the
parallelism above, roughly **6–7 calendar weeks to full scope**, plus Chrome Web
Store review latency (assume 1–2 weeks, not on the critical path if submitted early
with a stub).

Phase 4 is smaller than it would have been under a "imported games rank" policy —
signed payloads, verification tiers, dispute handling and record-invalidation
tooling all fall out of scope — but that saving is spent on the profile history
rebuild, which the import forces regardless.

**Recommended first commitment: Phases 0 and 1 only — about 3 weeks.** That lands a
shippable "paste any minesweeper.online game and get it analyzed" feature, proves
the normalizer, reconciliation and report, and resolves the extraction risk before
anyone builds an extension against an unknown.

### Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| Move log not extractable at usable timing resolution | Guts the feature's value; forces fallback to stats-only | Phase 0 gate before any further spend |
| m.o. changes markup / bundle / socket protocol | Import breaks in the field | Extension versioning, server-side schema tolerance, fast update path, clear failure messaging |
| m.o. terms prohibit automated interaction | Feature cannot ship as designed | Phase 5 review early; user-initiated own-data-only posture is the most defensible; consider contacting them directly |
| Imported games leak into a leaderboard by omission | Erodes the integrity guarantee we are making | Single shared `native_only()` helper; audit every ranking query in Phase 4; test asserting no ranking surface returns a non-native row |
| Private imported games leak through summary cards or trend charts | Discloses exactly what the user chose to hide | Compute every public aggregate over the visible set only; API-level enforcement; test asserting public-stats matches the visible history |
| Profile history performance under large imports | Slow or broken profile pages | Server-side pagination in Phase 4, indexes, no load-everything queries |
| Analysis cost on large backlogs | Cost, latency, degraded site performance | Bounded import, queue, throttle, off-peak processing |
| Chrome Web Store review rejection or delay | Slips Phase 2 delivery | Submit a minimal stub early to establish the listing |

---

## Open Questions

1. **Should we contact minesweeper.online directly?** A sanctioned export — even a
   plain CSV or a "download my games" button — would eliminate the extension, the
   spike, most of the risk register and roughly six weeks of work. Worth an email
   before Phase 2 is funded. Low probability, very high payoff.
2. **Import scope default.** 500 most recent games, or 12 months, or everything?
   Affects analysis cost materially.
3. **Should desktop replay files (.mvf / .rmv / .avf) be a parallel import path?**
   Arbiter, Viennasweeper and Metasweeper all produce high-fidelity local replay
   files, and open parsers exist (`sweeping-view`, `minesweeper-rawvf`). This is a
   much cheaper import path serving the most competitive users, with no ToS
   exposure. It shares the entire normalizer, reconciliation, analysis and report
   pipeline built in Phase 1 — likely 1 additional week on top. Recommend as a
   fast-follow.
4. **PvP games.** m.o. has a PvP tab in `/my-games`. Import them into history, and
   if so do they show in the profile PvP card? They must not touch our PvP Elo.
   Recommend: import as history only, excluded from Elo, v2.
5. **Custom boards.** m.o. supports custom dimensions. Our analyzer handles custom;
   import and analyze them, and they are excluded from ranking anyway by Decision 4.
6. **What happens on disconnect?** If a user unlinks their m.o. account, do imported
   games remain in their history? Recommend: remain, but stop updating; deletion is
   a separate explicit action.

---

## Implementation Notes

_To be filled in after shipping._
