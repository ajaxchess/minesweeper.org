# Intent: Dependabot Auto-Merge for Security Patches

Status: **in-progress** — workflow added 2026-11-07, pending first live run

## Problem

Dependabot opens PRs daily (pip) and weekly (npm), but merging is manual.
Python dependency security patches (like joserfc CVE-2026-119283/119284) can
sit unmerged for days because someone has to regenerate `requirements.lock`
and click merge. The staging gate already validates every commit before
production, so the real bottleneck is the PR merge step.

## Solution

A GitHub Actions workflow (`.github/workflows/dependabot-auto-merge.yml`) that
runs on every Dependabot PR:

### What it does

1. **Fetch metadata** — uses `dependabot/fetch-metadata` to determine the
   update type (patch, minor, major) and ecosystem (pip, npm).

2. **Regenerate lock file** (pip PRs only) — runs `pip-compile --generate-hashes`
   on the PR branch and commits the updated `requirements.lock` back to the PR.
   This eliminates the manual lock regeneration step that previously blocked merges.

3. **Auto-merge patch bumps** — if the update is semver-patch AND all CI checks
   pass (tests, bandit, pip-audit, CodeQL), enables GitHub auto-merge. The PR
   merges as soon as all required checks go green.

4. **Label** — adds `auto-merged` label for audit trail.

### What it does NOT do

- **Minor/major bumps stay manual.** Minor bumps (1.6→1.7) occasionally introduce
  behavioral changes. Major bumps (1.x→2.x) expect breaking changes. Both require
  human review.
- **npm/mobile PRs are not auto-merged.** Mobile dependency bumps don't affect
  server security and need device testing before merge.
- **Does not bypass the staging gate.** After merge to main, the existing staging
  cron still validates the commit with smoke tests before production deploys.

## Risk analysis

| Update type | Risk | Auto-merge? | Rationale |
|---|---|---|---|
| Patch (x.y.Z) | Very low | Yes | Bug/security fixes only by semver convention. Staging gate catches regressions. |
| Minor (x.Y.0) | Low-medium | No | New features, occasionally behavioral changes. Lock regen runs but merge is manual. |
| Major (X.0.0) | High | No | Breaking changes expected. Always manual review. |
| npm (mobile) | Variable | No | Doesn't affect server. Needs device testing. |

### Safety layers for auto-merged patches

1. CI must pass: pytest, bandit, pip-audit, CodeQL
2. `requirements.lock` is regenerated with hashes — no hash mismatch on deploy
3. `tests/test_requirements_sync.py` ensures txt and lock versions match
4. Staging gate runs smoke tests against the deployed commit
5. Production only deploys commits that pass the staging gate
6. `staging-tested/<sha>` annotated tags provide audit trail

## Prerequisites

- GitHub repo setting "Allow auto-merge" must be enabled
- The `auto-merged` label must be created in the repo

## Original questions

> Can we automate deployment of Dependabot branches to staging?

Yes — but it's even simpler than that. Once the PR auto-merges to main, the
existing staging cron picks it up within 5 minutes and runs the full smoke test
suite. No separate staging deployment of the PR branch is needed.

> What are the risks of automatically promoting to production?

For patch versions: minimal, given the five safety layers above. The staging gate
is the critical control — it catches anything the unit tests miss (import errors,
missing columns, broken routes). For minor/major: too risky to automate, kept manual.
