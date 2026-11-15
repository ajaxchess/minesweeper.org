# Zero-Downtime Deploys for the Main Website

**Status:** in-progress
**Feature ID:** F-ZERO-DOWNTIME
**Author:** Richard Cross
**Date:** 2026-11-14

---

## Problem / Motivation

Every production deploy makes minesweeper.org hang for up to about 40 seconds.

`scripts/minesweeper_service_update_and_restart.sh` resets the live directory to
the new commit, then restarts `minesweeper-web`. The new gunicorn workers take
35–40 seconds to load the app (most of it importing `translations.py`). Apache
keeps the requests waiting rather than failing them: on the restart of
2026-11-13 06:24 UTC, requests hung for up to 31 seconds and none returned an
error. To a player the site is frozen, and a score submitted in that window can
time out in the browser.

The code also changes on disk before the old processes stop. Templates and
lazily loaded modules are read from disk, so for a short time old code runs with
new files. B63 was this kind of mismatch.

With deploys gated on staging and Dependabot patches merging automatically
(intent/DependabotTestAutomation.md), deploys will get more frequent, and each
one costs a freeze.

---

## Success Criteria

- [ ] During a production deploy, no request to the main website waits more than
      about 2 seconds longer than it would without a deploy, and none fails.
- [ ] A deploy whose new code does not start, or does not pass its health check,
      never takes traffic: the old version keeps serving and the deploy says why.
- [ ] A deploy that starts producing errors after the switch is rolled back
      automatically within about 5 minutes, and its commit is not deployed again.
- [ ] Rolling back by hand takes under a minute and does not reinstall anything.
- [ ] Deploys do not reload Apache, so the other sites on this shared server are
      never touched by a minesweeper.org deploy.
- [ ] Daily jobs (score reset, guest-score archive, daily puzzles) keep running
      after every deploy, always on the website's current code.
- [ ] Duels are interrupted only by deploys that change something PvP uses, and
      PvP is never more than a day behind the website.
- [ ] A failed deploy or an automatic rollback shows as a banner on `/admin`.

---

## Scope

**In this feature:**
- The main website: every route Apache sends to the web pool (today port 8000).
- Fewer PvP interruptions: the PvP service restarts only when a deploy affects it
  (decision 7).
- Production only.
- The deploy script, the systemd units, the Apache vhost, and the app changes the
  design needs (scheduler, deploy banner).
- A runbook for deploys, rollback and the one-time cutover.

**Out of scope:**
- Zero-downtime PvP. The PvP / duel service (`/ws/`, `/duel`, `/duelold`, `/pvp`,
  `/pvpbeta`) keeps its in-memory game state in one process, so when it does
  restart, duels in progress are interrupted for about 40 seconds. Fixing that
  means moving duel state out of the process (e.g. Redis) — a separate feature.
- Staging. It is started only to test a commit (on-demand staging), so a freeze
  there costs nothing.
- Making the app start faster. Worth doing on its own (lazy-loading
  `translations.py`), but this design does not depend on it.
- Deploy time windows. Production keeps deploying whenever staging approves a
  commit (decided 2026-11-14).

---

## Key Design Decisions

Decisions marked *(2026-11-14)* were settled in the design interview with Richard.

### 1. Two copies of the website, "blue" and "green"

- Two directories, `/home/ubuntu/minesweeper-blue` and `/home/ubuntu/minesweeper-green`,
  each a git worktree of the same repository with its own virtualenv.
- Two services from one systemd template, `minesweeper-web@blue` (port 8010) and
  `minesweeper-web@green` (port 8011). Both ports are free today.
- Normally only one copy runs. Both run only during the seconds of a switch.
- `/home/ubuntu/minesweeper` becomes a symlink to the copy that is live, so cron
  jobs and Apache's `/static` alias keep their current paths.
- PvP runs from its own third copy (decision 7).

### 2. Apache picks the copy that is up

- The vhost's catch-all `ProxyPass /` points at a balancer
  (`mod_proxy_balancer`) with both ports as members.
- When a port refuses connections, Apache retries the request on the other port.
  A stopped copy therefore costs nothing, and the switch happens by starting and
  stopping copies — **no Apache reload per deploy**.
- Connection reuse to the backends is turned off (`disablereuse=On`). Otherwise a
  POST can be sent on a connection the old copy has just closed and come back as
  a 502. Connections are to localhost, so this costs very little.
- **Mixed versions for a few seconds are accepted** *(2026-11-14)*. While both
  copies run, requests are split between the old and the new version. An exact
  switch would need an Apache reload per deploy, which touches every site on the
  server.

### 3. A deploy

The production cron still runs every 5 minutes. The deploy holds a lock for its
whole run, including the 5-minute watch, so the next tick waits.

1. Pick the idle copy; reset it to the commit staging approved; install from
   `requirements.lock`; generate `database.py`.
2. Start the idle copy (at lower CPU priority, decision 8).
3. Wait until `/health` on its port reports the target commit and the standard
   smoke-test pages return 200 (same checks as the staging gate). Give up after
   2 minutes: stop the idle copy, leave the live one serving, mark the commit
   blocked, raise the `/admin` banner.
4. Gracefully stop the live copy. gunicorn closes its listening socket first, so
   new requests fail over to the new copy, and in-flight requests get up to 30
   seconds to finish.
5. Point the `/home/ubuntu/minesweeper` symlink at the new copy.
6. If the deploy affects PvP (decision 7), update the PvP copy and restart PvP.
7. Watch for 5 minutes (decision 4).

### 4. Rollback

**By hand:** the copy that was just stopped still holds the previous commit and
its dependencies. `--rollback` on the deploy script starts it, waits for its
health check, stops the current one and flips the symlink. About a minute, most
of it the old copy loading.

**Automatically, for 5 minutes after a switch** *(2026-11-14)*:

- The deploy reads the main website's responses from the Apache access log
  (`minesweeper.org-ssl-access.log`) for the 5 minutes after the switch. PvP
  routes are not counted.
- It rolls back if **at least 5 responses are 5xx and they are more than 2% of
  website requests** in that window. The minimum count stops one stray error on a
  quiet night from triggering it. (Normal traffic is about 20–30 requests a
  minute, so 100–150 requests in the window.)
- **The rolled-back commit is blocked**, as staging does for a failed smoke test:
  production stays on the previous commit until a newer commit passes staging.
  `--force` still deploys it.
- If PvP was restarted with the bad commit, it is rolled back too.

### 5. The team sees problems as a banner on `/admin`

*(2026-11-14)*

- A failed health check or an automatic rollback writes a short record (time,
  commit, reason, the last log lines) to a file in `/home/ubuntu/deploy_state/`.
- `/admin` shows it as a warning banner until an admin dismisses it.
- The deploy log in `/tmp/minesweeper-deploy.log` stays as it is.
- No email: it would need SMTP set up for minesweeper. The banner is only seen
  when someone opens `/admin`.

### 6. Rules the code must follow from now on

- **Database changes must work with the previous release** *(2026-11-14; goes
  into CLAUDE.md)*. The old copy keeps serving for a few seconds after the new
  copy has run its startup migrations. Adding a column or table is fine; dropping
  or renaming one takes two deploys (stop using it, then remove it). Because PvP
  can run older code for longer, a deploy that removes or renames anything always
  restarts PvP.
- **The scheduler lock must be retried.** Only one process runs the daily jobs,
  and today it takes the lock (`_acquire_scheduler_lock`) only at startup. With
  the old copy still holding the lock while the new one starts, the new copy
  would never run the jobs. The new copy must keep retrying until it gets it.
- **The daily jobs run only in the website copies, never in PvP.** Today
  whichever process starts first takes the lock. A PvP process can now live
  through many deploys, so it could run the score reset with old code. The PvP
  service is started with the scheduler switched off.

### 7. PvP restarts only when it is affected

*(2026-11-14)*

- PvP gets its own copy, `/home/ubuntu/minesweeper-pvp`, with its own virtualenv.
  That copy changes only when PvP restarts, so a long-running PvP process never
  reads files from a newer commit.
- **Restart unless clearly unrelated.** The repository keeps a list of paths
  known *not* to affect PvP: other games' route modules, their templates and
  JavaScript, `docs/`, `intent/`, `tests/`, `mobile/`. If every file the deploy
  changed is on that list, PvP is left alone; any other change restarts it.
  `main.py`, `base.html`, `translations.py`, `requirements.lock` and the scripts
  `base.html` loads therefore always count. When unsure, restart.
- Static files are shared: Apache serves `/static` from the live website copy for
  every page, PvP's pages included. So JavaScript and CSS that PvP pages load
  count as PvP files.
- A deploy that removes or renames anything in the database always restarts PvP.
- **Nightly catch-up:** once a night in quiet hours (around 4 AM US Central), if
  PvP runs an older commit than the website, it is updated and restarted.

### 8. Capacity

- Memory: the four web workers use about 800 MB together and the server has
  about 3.3 GB available, so two copies fit.
- CPU is tighter: the server has 2 cores, and four workers loading the app take
  about 35 seconds of CPU each. While the new copy loads, live traffic is slower.
  The new copy starts at lower priority (`nice`).

### 9. Files that must not live in any copy

Shared in `/home/ubuntu/minesweeper-shared/`, symlinked into all three copies:

- `.env`
- `static/uploads/` — jigsaw photos uploaded by players
- Hand-placed, gitignored folders: `static/html`, `static/mvs`, `analysis`,
  `business`, `minesweeperbootcamp`
- Any other gitignored path found in the live directory at cutover time

### 10. One-time server cutover

*Richard with Claude, in a working session at a quiet hour, after the code is
reviewed and merged* *(2026-11-14)*.

- **Prerequisite:** production must first catch up with this week's commits. The
  staging gate has been blocked since 2026-11-11 by the old
  `minesweeper-staging.service` holding port 8002; Richard is handling it.
- Enable `proxy_balancer`, `lbmethod_byrequests` and `slotmem_shm` (installed,
  not enabled); edit the minesweeper.org vhost; one graceful Apache reload.
- Create the three worktrees, their virtualenvs and the shared folder.
- Install the `minesweeper-web@` template unit and the new PvP unit; retire
  `minesweeper-web`.
- Keep the old vhost and units on disk so the old setup can come back in minutes.

---

## Settled in the design interview (2026-11-14)

| Question | Answer |
|---|---|
| Accept a few seconds of mixed versions? | Yes — no Apache reload per deploy |
| Database changes compatible with the previous release? | Yes, as a team rule |
| Restart PvP on every deploy? | No — only when affected, decided by a "clearly unrelated" path list |
| Limit how far PvP falls behind? | Nightly catch-up |
| Limit production deploys to a time window? | No — deploy whenever staging approves |
| Roll back automatically? | Yes, for 5 minutes: ≥ 5 errors and > 2% of requests |
| What happens to a rolled-back commit? | Blocked until a newer commit passes staging |
| How does the team hear about it? | Banner on `/admin` |
| Who does the cutover? | Richard with Claude, after production catches up |

---

## Implementation Notes

*Filled in when work completes.*
