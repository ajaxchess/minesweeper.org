# Static Assets Have No Source of Truth

**Status:** ready
**Feature ID:** F-ASSETS
**Author:** Richard Cross
**Date:** 2026-09-21

---

## Problem / Motivation

`.github/workflows/build-assets.yml` minifies every file matching `static/js/*.js`
and `static/css/*.css` **in place**, then commits the result back to the repository:

```
find static/js -maxdepth 1 -name "*.js" | sort | while read f; do
  terser "$f" --compress --mangle --output "$f"
done
...
git commit -m "chore: minify static assets [skip ci]"
git push
```

There is no separate source tree. The committed file is simultaneously the source
and the build output, and the build destroys the source. Once CI has run, the
readable version of a file exists only in git history — every developer who opens
`static/js/bootcamp.js` from that point on is reading mangled, single-line code.

This is not hypothetical. `static/js/bootcamp.js` is 14KB of minified output whose
last two commits are `6b58f3a2` (the real change) followed by `2827960a chore:
minify static assets [skip ci]`. The only readable copy of that file in the working
tree is `phase5_bootcamp/static/js/bootcamp.js`, which survives purely because it
sits outside `static/` and the minifier never globbed it. The same is true of
`bootcamp.css`. `drill.js` is minified with no readable copy anywhere.

Two consequences are already visible in the codebase. The preview backdoor
(F-BC-PREVIEW) now lives inside minified code, so fixing it means either editing
mangled source or reconstructing from `phase5_bootcamp/`. And the July roadmap
recommended deleting `phase5_bootcamp/` as an obsolete duplicate — which, acted on
literally, would have destroyed the last readable source of two live assets.

A third inconsistency compounds it: `scripts/build_assets.sh`, which the deploy
script calls, minifies only a hardcoded list of ten files that does not include
`bootcamp.js` or `drill.js`, while the CI workflow globs everything. The two build
paths disagree about what gets built.

---

## Success Criteria

- [ ] Readable source exists in the repository for every static asset, and it is the
      file developers edit
- [ ] Minified output is generated at build or deploy time and is not what a
      developer opens
- [ ] No workflow overwrites a source file with its own build output
- [ ] `scripts/build_assets.sh` and `.github/workflows/build-assets.yml` agree on
      which files are processed, or one of them is removed
- [ ] The readable sources currently surviving only in `phase5_bootcamp/` are
      recovered into the canonical location before anything deletes that directory
- [ ] No change to what the browser receives — same minified bytes served

---

## Scope

**In this feature:**
- Introduce a source location for static assets distinct from what is served
- Recover readable sources for `bootcamp.js`, `bootcamp.css` and any other asset
  already minified in place — from `phase5_bootcamp/` where it exists, from git
  history where it does not
- Rewrite the CI workflow to build from source to output rather than in place
- Reconcile or retire `scripts/build_assets.sh`
- Add `.gitignore` or equivalent so build output is not committed, if the chosen
  approach stops committing it

**Out of scope:**
- Content-hash filenames replacing the manual `?v=N` cache-busting query strings —
  a real improvement, recommended separately, but a larger change touching every
  template reference
- Introducing a bundler or any build step beyond minification
- Changing which assets exist or what they do

---

## Key Design Decisions

**The smallest fix that works: `static/src/` → `static/js/`.** Developers edit
`static/src/js/*.js` and `static/src/css/*.css`; the workflow minifies from there
into `static/js/` and `static/css/`, which remain the served paths so no template
reference changes. Output can stay committed (keeping the current deploy model
intact, which simply pulls the repo) or become build-time-only. Committed output is
the lower-risk choice given the deploy script hard-resets to a known commit.

**Recover before deleting, in that order.** `phase5_bootcamp/static/` holds the only
readable `bootcamp.js` and `bootcamp.css`. Those files must be moved into the new
source location and verified to compile to byte-equivalent minified output *before*
F-BC-CONSOLIDATE removes that directory. Getting this order wrong loses the source
permanently from HEAD.

**Verify byte-equivalence, not just "it loads".** For each recovered file, minify it
and diff against the currently committed output. A difference means the readable copy
is not simply the unminified form of what is deployed, and blindly promoting it would
silently revert live behaviour.

`bootcamp.js` is already known to be in exactly that state and must not be promoted
naively. The readable copy in `phase5_bootcamp/` contains **zero** occurrences of
`bc.preview.all`, while the deployed minified copy contains the full preview-unlock
feature — the two diverged in commit `6b58f3a2`, which added that feature to the
`static/` copy only. F-BC-PREVIEW has since added an admin gate to the minified copy
and not to the readable one, widening the gap further. **For this file the minified
`static/` copy is authoritative**; the readable source must be brought forward to
match it — preview feature, admin gate and all — and verified to rebuild to the same
behaviour before it replaces anything. Treat every other already-minified asset as
suspect until the same check is done.

**Do this before the four new bootcamp surfaces.** F-BC-RADAR, F-BC-HEATMAP,
F-BC-FLUENCY and F-BC-REPLAY each add a JS and a CSS file. Under the current
workflow, each of those becomes unreadable the first time CI runs after it lands.
Fixing the pipeline first means four new features are born with readable source;
fixing it after means four more recovery jobs.

---

## Effort Sizing

| Item | Est. |
|---|---|
| Source directory, workflow rewrite, `build_assets.sh` reconciliation | 2 days |
| Recovery and byte-equivalence verification of already-minified assets | 2 days |
| Verification pass — every page's assets load and behave identically | 1 day |

**~1 week.** No user-visible change. It is the prerequisite that stops the next
several features from inheriting the same problem.

---

## Implementation Notes

_To be filled in after shipping._
