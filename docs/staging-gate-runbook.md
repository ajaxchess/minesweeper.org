# Staging Gate Runbook

Every commit to `main` must pass staging smoke tests before it reaches production.
This document covers how the gate works, what annotated tags mean, and how to
recover when something goes wrong.

---

## How the gate works

1. A cron job (every 5 minutes) runs
   `scripts/staging_minesweeper_service_update_and_restart.sh` on the staging server.
2. If `origin/main` has a new commit that hasn't been tested yet, staging:
   - Hard-resets to the new commit
   - Installs deps, regenerates `database.py`
   - Starts `minesweeper-staging-web` (port 8002) and `minesweeper-staging-pvp` (port 8052)
   - Runs smoke tests against both
   - Stops both services to free memory
3. **Pass**: writes the SHA to `/home/ubuntu/deploy_state/minesweeper_last_good_commit`
   and creates an annotated git tag (see below).
4. **Fail**: writes the SHA to `minesweeper_blocked_commit`; production deploy stays
   blocked until a new commit arrives.
5. A separate cron runs `scripts/minesweeper_service_update_and_restart.sh` on the
   production server, which only deploys if `minesweeper_last_good_commit` matches
   `origin/main`.

---

## Annotated tags

When a commit passes staging, the staging script creates and pushes:

```
staging-tested/<short-sha>
```

Example: `staging-tested/a0228754`

The annotation body contains:

```
Staging smoke tests passed 2026-09-07 02:15:43 UTC — commit a0228754...
```

**What this means**: every `staging-tested/*` tag in the GitHub tag list is a
commit that survived smoke tests. The annotation timestamp is when the tests ran,
not when the commit was made.

To inspect a tag locally:

```bash
git fetch --tags
git tag -v staging-tested/a0228754
```

---

## Troubleshooting

### A commit is stuck as "blocked"

The blocked SHA is in `/home/ubuntu/deploy_state/minesweeper_blocked_commit`.
Push a new commit to main — the cron will pick it up and run tests on the new SHA.
If you need to force-clear the block (e.g. transient network error caused the test):

```bash
# On the staging server
rm /home/ubuntu/deploy_state/minesweeper_blocked_commit
```

The next cron tick will re-test the current `origin/main`.

### Manually running the staging script

```bash
ssh staging-server
/home/ubuntu/git/staging.minesweeper.org/scripts/staging_minesweeper_service_update_and_restart.sh
```

The script is idempotent for a given SHA: if the commit is already validated or
blocked, it exits early without re-testing.

### Tag already exists (commit re-tested)

If staging is forced to re-test a commit that already has a tag, the script logs:

```
WARNING: Tag staging-tested/<sha> already exists — skipping (commit re-tested).
```

This is harmless. The state file and existing tag are both correct.

### Tag pushed but state file not updated (or vice versa)

The state file is authoritative for production gating. The tag is an audit trail.
If they diverge (e.g. the server lost the state file), you can recreate the state
file from the most recent tag:

```bash
# On the staging server
git fetch --tags
LAST=$(git tag -l 'staging-tested/*' | sort | tail -1)
git rev-list -n 1 "$LAST" > /home/ubuntu/deploy_state/minesweeper_last_good_commit
echo "Restored: $LAST -> $(cat /home/ubuntu/deploy_state/minesweeper_last_good_commit)"
```

---

## Smoke test coverage

Tests run against Uvicorn ports directly (bypasses Apache):

| Test | Route | Port |
|---|---|---|
| Home | `/` | web (8002) |
| Tentaizu | `/tentaizu` | web (8002) |
| Numbers Match page | `/numbers-match` | web (8002) |
| Numbers Match API | `/api/numbers-match-board/<date>` | web (8002) |
| PvP | `/pvp/bot` | pvp (8052) |
| Duel | `/duel` | pvp (8052) |

PvP/duel routes are tested against the pvp instance specifically because that is
the process that owns in-memory matchmaking state.
