# Bootcamp: Remove the Preview Backdoor from Production JS

**Status:** in-progress
**Feature ID:** F-BC-PREVIEW
**Author:** Richard Cross
**Date:** 2026-09-21

---

## Problem / Motivation

`static/js/bootcamp.js` ships a debug backdoor to every visitor. Loading
`/bootcamp?preview=all` writes `bc.preview.all` to `localStorage`, after which the
page rewrites every level's status to `current` — unlocking all seven levels of the
ladder, expanding every level card, and fetching level detail for levels the player
has not reached. A fixed yellow badge appears reading "Preview: all levels unlocked".
The flag persists across sessions until `?preview=off` is visited.

This was a development convenience and it was flagged in the July roadmap review. It
is still in the minified production bundle.

The harm is modest but real: it is not a security hole (the API still enforces what
it enforces, and the flag only changes client-side presentation), but it hands any
visitor a way to defeat the progression design that the entire bootcamp rests on. A
player who unlocks everything sees seven levels of drills with no sequencing and no
diagnosis behind them, which is precisely the experience the ladder exists to
prevent. It also makes support and bug reports harder to reason about, since a
player with the flag set sees a page that does not match their actual state.

---

## Success Criteria

- [ ] `?preview=all` has no effect for a non-admin visitor
- [ ] An existing `bc.preview.all` value in a visitor's `localStorage` is cleared on
      next page load rather than silently honoured
- [ ] Admins retain the capability, gated on a real server-side admin check
- [ ] The preview badge only ever appears for admins
- [ ] No behaviour change for ordinary players who never used the flag

---

## Scope

**In this feature:**
- Gate the preview path in `bootcamp.js` on an admin flag supplied server-side
  through the existing `BOOTCAMP_CONFIG` bootstrap
- Clear any stale `bc.preview.all` key for non-admins
- Audit the other bootcamp/drill bundles for equivalent flags before closing

**Out of scope:**
- Any change to level assignment or the diagnosis API
- A general-purpose admin impersonation or preview system

---

## Key Design Decisions

**The edit has to happen in minified code, and that is accepted deliberately.**
`static/js/bootcamp.js` is minified in place by CI and committed, so the preview
logic exists only as mangled code inside a single 14KB line. The readable copy at
`phase5_bootcamp/static/js/bootcamp.js` is **not** a usable substitute: it does not
contain the backdoor at all (zero occurrences of `bc.preview.all`), meaning the two
files diverged in commit `6b58f3a2` — the `static/` copy gained the preview feature
and the `phase5_bootcamp/` copy never did. Editing the readable copy and shipping it
would silently revert whatever else diverged in that commit.

So: a narrowly targeted edit to the minified bundle now, with the readable source
reconciled as part of F-ASSETS. Given this is a half-day change and F-ASSETS is a
week, that is the right trade — but the divergence must be recorded so F-ASSETS
reconciles rather than overwrites.

**Gate it, don't delete it.** The capability is genuinely useful for checking level
card rendering without grinding to level 7. The problem is that it is ungated, not
that it exists. `BOOTCAMP_CONFIG` is already bootstrapped server-side, so adding
`isAdmin` costs nothing and the check cannot be forged by editing localStorage —
the worst a non-admin can do is set a flag the JS no longer reads.

**Clear rather than ignore.** Anyone who found the flag has it set permanently.
Actively removing the key on load for non-admins means the population converges back
to correct behaviour instead of carrying a stale unlocked view indefinitely.

**Check the sibling bundles.** `drill.js` is likewise minified with no readable copy
anywhere in the working tree, and `admin_bootcamp` assets come from the same
development effort. Audit both for the same pattern in the same pass.

---

## Effort Sizing

**~half a day** as a targeted patch to the minified bundle, including the audit of
sibling bundles. Effectively free if folded into F-ASSETS instead, which has to
touch this file anyway.

This is the smallest item in the bootcamp backlog and the only one currently
affecting production behaviour, so it should be picked up early regardless of what
else is scheduled.

---

## Implementation Notes

**Implemented 2026-09-22. Not yet deployed — status moves to `done` after it ships.**

Three files changed:

- **`main.py`** — `bootcamp_page()` now resolves the current user once, computes
  `is_admin` against the existing `ADMIN_EMAILS` set (already imported at
  `main.py:45`), and passes it to the template. No new admin mechanism was
  introduced; this is the same check already used at `admin_routes.py:1554`.
- **`templates/bootcamp.html`** — `BOOTCAMP_CONFIG` gains
  `isAdmin: {{ (is_admin if is_admin is defined else false) | tojson }}`. The
  `is defined` guard means the template still renders correctly if reached from a
  route that does not supply the flag, defaulting closed. Script cache-buster bumped
  `?v=3` to `?v=4` so returning visitors pick up the change.
- **`static/js/bootcamp.js`** — the gate itself. `bcPreviewAllowed` is computed once
  at module scope as a strict comparison against `isAdmin`, so a spoofed `"true"`
  string fails. `c()` short-circuits to false for non-admins, and the URL-parsing
  IIFE clears any existing `bc.preview.all` key for non-admins before doing anything
  else — so visitors who previously set the flag converge back to correct behaviour
  on their next page load rather than carrying it indefinitely.

**Verification.** The patched gate expression was extracted from the shipped bundle
and exercised in node against a fake `localStorage` across seven cases: non-admin
with `?preview=all`, non-admin with a stale key already set, non-admin normal load,
admin with `?preview=all`, admin with the key already set, admin with `?preview=off`,
and a spoofed `isAdmin:"true"` string. All seven behave as specified. `node --check`
passes on the bundle, `py_compile` on `main.py`, and the Jinja template parses with
the config expression rendering `true` / `false` / `false` for admin / non-admin /
undefined respectively.

**Sibling audit (success criterion 6).** Clean. `static/js/drill.js` contains zero
`localStorage` and zero `URLSearchParams` references — no equivalent backdoor exists
there. There is no separate admin JS bundle. The four remaining `localStorage`
references in `bootcamp.js` are all the preview key itself (one get, one set, two
removes).

**Carried into F-ASSETS.** `phase5_bootcamp/static/js/bootcamp.js` does not contain
the backdoor and now also does not contain the gate; the two copies remain divergent
until F-ASSETS reconciles them. F-ASSETS must treat the minified `static/` copy as
authoritative for this file, not the readable one.

**Not done here:** the repo's test suite could not be run on this machine — the
checkout has no virtualenv and `fastapi`, `sqlalchemy` and `pytest` are absent, so
`tests/test_bootcamp_queries.py` and `tests/test_drills.py` were not executed against
this change. Neither covers the touched code paths, but standing up a working local
test environment is a prerequisite for F-BC-TESTS and should be its first task.
