# Zero-Downtime Deploys — Runbook

Feature: F-ZERO-DOWNTIME. Design and decisions: `docs/features/ZeroDowntimeDeploy.md`.
Code: `scripts/zero_downtime/`. Tests: `tests/test_zero_downtime_*.py`.
**Live since 2026-11-16 00:50 UTC** (cutover notes at the end).

## How it works

```
                       ┌─ balancer://minesweeper_web ─┬─ 127.0.0.1:8010  minesweeper-web@blue   /home/ubuntu/minesweeper-blue
Apache (minesweeper.org)                              └─ 127.0.0.1:8011  minesweeper-web@green  /home/ubuntu/minesweeper-green
                       └─ /ws/ /duel /duelold /pvp /pvpbeta ─ 127.0.0.1:8050  minesweeper-pvp  /home/ubuntu/minesweeper-pvp

/home/ubuntu/minesweeper         → symlink to the live copy (cron jobs and /static go through it)
/home/ubuntu/minesweeper-shared  → .env, uploads/, hand-placed files, web-blue.env / web-green.env
/home/ubuntu/deploy_state        → last_good (from staging), prod_blocked, deploy_alert.json
```

- Normally one website copy runs. A deploy updates the idle copy, starts it,
  checks `/health` (must report the target commit) and the smoke-test pages,
  then stops the live copy. Apache health-checks both ports every 2 seconds and
  sends requests only to a copy that answers, so there is no gap and **Apache is
  never reloaded by a deploy**.
- PvP restarts only when the deploy changes something PvP uses
  (`scripts/zero_downtime/deploy_tools.py`, "restart unless clearly unrelated"),
  and nightly if it is behind (`pvp_catchup.sh`). Each PvP restart interrupts
  duels in progress for about 40 seconds.
- For 5 minutes after a switch the deploy reads the Apache log. At least 5
  website 5xx responses that are more than 2% of requests → automatic rollback,
  and the commit is blocked.
- Problems show as a banner on `/admin`.

## Everyday

| Task | Command (as `ubuntu`) |
|---|---|
| What is running | `/home/ubuntu/minesweeper/scripts/zero_downtime/deploy.sh --status` |
| Deploy log | `tail -f /tmp/minesweeper-deploy.log` |
| Roll back to the previous deploy | `deploy.sh --rollback` (blocks the current commit) |
| Deploy origin/main now, skipping staging and any block | `deploy.sh --force` |
| Bring PvP up to the website now | `scripts/zero_downtime/pvp_catchup.sh` |
| Unblock a commit without deploying it | `rm /home/ubuntu/deploy_state/minesweeper_prod_blocked_commit` |

A deploy takes about 1 minute plus the 5-minute watch. It holds
`/tmp/minesweeper_zd_deploy.lock` the whole time; cron ticks during it skip.

## When the /admin banner shows

| Banner | What happened | What to do |
|---|---|---|
| **health check failed** | The new commit didn't start, didn't report its commit, or a smoke-test page failed. It never took traffic; the commit is blocked. | Read the log in the banner. Fix and push; the next commit that passes staging deploys. |
| **rolled back** | Errors crossed the threshold after the switch. The previous copy is serving again; the commit is blocked. | Look at `/var/log/apache2/minesweeper.org-ssl-error.log` and `journalctl -u minesweeper-web@<color>` around the switch time. |
| **rollback failed** | The new commit produced errors **and** the previous copy did not come back. The bad commit is still serving. | **Act now.** `deploy.sh --status`; `journalctl -u minesweeper-web@<idle color> -n 100`. Fix the cause or `deploy.sh --force` a known-good commit. |
| **install failed** | `pip install` or the checkout failed in the idle copy. Nothing changed. Not blocked: retried every 5 minutes. | Usually network or PyPI. If it repeats, run the install by hand in the idle copy to see the error. |
| **pvp update failed** | The website deployed, but PvP didn't come back on the new commit. | `journalctl -u minesweeper-pvp -n 100`; `pvp_catchup.sh` to retry. |
| **manual rollback** | Someone ran `--rollback`. | Dismiss once the cause is known. |
| **watch unavailable** | Deployed, but the Apache log couldn't be read, so there was no automatic rollback. | Check `sudo -n test -r /var/log/apache2/minesweeper.org-ssl-access.log`. |

Dismissing the banner moves the record to `minesweeper_deploy_alert.dismissed.json`.

### Emergency: no website copy is running

```
cd /home/ubuntu/minesweeper && scripts/zero_downtime/deploy.sh --status
sudo systemctl start minesweeper-web@$(basename "$(readlink /home/ubuntu/minesweeper)" | sed 's/minesweeper-//')
```

## Rules for code changes

- **Database changes must work with the previous release.** For a few seconds
  the old copy serves while the new copy has already run its startup migrations.
  Add columns and tables freely. To drop or rename, use two deploys: stop using
  it, then remove it. Such a deploy also restarts PvP (any `database_template.py`
  change does).
- **Uploads live in `/home/ubuntu/minesweeper-shared/uploads`** in production
  (`MINESWEEPER_UPLOADS_DIR`, served by Apache as `/static/uploads`). Files
  committed under `static/uploads/` are not served in production; always use
  `settings.upload_dir()`.
- **PvP restart list:** `scripts/zero_downtime/deploy_tools.py`. When you add a
  game module that PvP pages never use, add it to `UNRELATED_MODULES`; otherwise
  every change to it restarts PvP (safe, just more interruptions).

---

## One-time cutover

Richard and Claude, at a quiet hour (2026-11-14 interview). Allow two hours.

**Timing:** between steps 3 and 7 the old service and the blue copy both run the
daily scheduler (they use different lock files). Don't start within 15 minutes
of a full hour or of 23:59–00:00 UTC.

**Nothing below changes `/home/ubuntu/git/minesweeper.org`** (today's live
checkout). The back-out at the end returns to it.

### 0. Before

- The F-ZERO-DOWNTIME code is merged and deployed by the **old** pipeline.
  With no new environment variables set, it behaves exactly as before.
- Production is on the last good commit: `cat /home/ubuntu/deploy_state/minesweeper_last_good_commit`
  equals `git -C /home/ubuntu/git/minesweeper.org rev-parse HEAD`.
- **Turn the old deploy cron off** (`crontab -e`, comment out the
  `minesweeper_service_update_and_restart.sh` line). After step 6 it would run
  inside the blue copy and restart the old services.

### 1. Copies (no effect on the live site)

```
cd /home/ubuntu/git/minesweeper.org
scripts/zero_downtime/setup_copies.sh
ls -la /home/ubuntu/minesweeper-{blue,green,pvp} /home/ubuntu/minesweeper-shared
cat /home/ubuntu/minesweeper-shared/linked-paths.txt
```

### 2. Units

```
sudo cp 'scripts/zero_downtime/minesweeper-web@.service' /etc/systemd/system/
sudo systemctl daemon-reload
```

### 3. Start blue next to the old service

```
sudo systemctl start minesweeper-web@blue
curl -s 127.0.0.1:8010/health        # commit = the live commit
for p in / /tentaizu /numbers-match; do curl -s -o /dev/null -w "$p %{http_code}\n" 127.0.0.1:8010$p; done
journalctl -u minesweeper-web@blue -n 30 --no-pager | grep -i scheduler
```

### 4. Apache

```
sudo a2enmod proxy_balancer lbmethod_byrequests slotmem_shm proxy_hcheck
sudo cp /etc/apache2/sites-enabled/default-ssl.conf /home/ubuntu/minesweeper-shared/default-ssl.conf.pre-zd
sudoedit /etc/apache2/sites-enabled/default-ssl.conf     # apply scripts/zero_downtime/minesweeper.org-vhost.conf
sudo apachectl configtest
scripts/zero_downtime/setup_copies.sh --sync-uploads
sudo systemctl reload apache2                            # graceful
```

Keep the backup **outside** `sites-enabled`: Apache loads every `.conf` there.

Check: `curl -sI https://minesweeper.org/` is 200; an upload
(`curl -sI https://minesweeper.org/static/uploads/jigsaw/<file>`) is 200;
`journalctl -u minesweeper-web@blue -f` shows the traffic.

### 5. Retire the old website service

```
sudo systemctl stop minesweeper-web && sudo systemctl disable minesweeper-web
scripts/zero_downtime/setup_copies.sh --sync-uploads     # anything uploaded before step 4
```

### 6. Point the live symlink at blue

```
ln -sfn minesweeper-blue /home/ubuntu/minesweeper.new && mv -Tf /home/ubuntu/minesweeper.new /home/ubuntu/minesweeper
sudo systemctl enable minesweeper-web@blue
curl -sI https://minesweeper.org/static/css/style.css    # 200
```

### 7. PvP

```
sudo cp /etc/systemd/system/minesweeper-pvp.service /home/ubuntu/minesweeper-shared/minesweeper-pvp.service.pre-zd
sudo cp /home/ubuntu/minesweeper/scripts/zero_downtime/minesweeper-pvp.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl restart minesweeper-pvp
curl -s 127.0.0.1:8050/health
journalctl -u minesweeper-pvp -n 30 --no-pager | grep -i scheduler    # "Scheduler disabled"
```

Open `https://minesweeper.org/pvp/bot` and play a few moves (WebSocket).

### 8. Prove a switch under load

Terminal 1 — every request, and any that isn't a fast 200:

```
while true; do curl -s -o /dev/null -w '%{http_code} %{time_total}\n' https://minesweeper.org/; sleep 0.2; done \
  | awk '$1 != 200 || $2 > 2 {print "PROBLEM:", $0; fflush()} NR % 50 == 0 {print NR, "requests"; fflush()}'
```

Terminal 2:

```
/home/ubuntu/minesweeper/scripts/zero_downtime/deploy.sh --rollback   # both copies on the same commit: plain switch to green
/home/ubuntu/minesweeper/scripts/zero_downtime/deploy.sh --status
/home/ubuntu/minesweeper/scripts/zero_downtime/deploy.sh --rollback   # and back to blue
```

Expect no `PROBLEM` lines. Also try a POST during a switch (submit a score).

### 9. Cron

```
*/5 * * * * /home/ubuntu/minesweeper/scripts/zero_downtime/deploy.sh >> /tmp/minesweeper-deploy.log 2>&1
0 10 * * * /home/ubuntu/minesweeper/scripts/zero_downtime/pvp_catchup.sh >> /tmp/minesweeper-deploy.log 2>&1
```

Remove the old deploy line. `archive_anon_pvp.py` runs from
`/home/ubuntu/git/minesweeper.org`, which no longer receives deploys: change it
to `/home/ubuntu/minesweeper/scripts/archive_anon_pvp.py`.

### 10. First real deploy

Watch `/tmp/minesweeper-deploy.log` when the next commit passes staging. Then fill
in Implementation Notes in the intent file and set its Status to `done`.

### Cutover log (2026-11-16, Richard with Claude)

- 00:45 `36cdb8ca` deployed by the old pipeline; 00:46 old deploy cron off;
  `setup_copies.sh` took 1.5 minutes; 26 uploads copied.
- **Order changed:** PvP (step 7) went first. The old PvP service held the
  scheduler lock; restarting it with the scheduler off handed the lock to the old
  website service, so the overlap in steps 3–5 ran only blue's scheduler on its
  new lock file plus the old service — 00:49:15–00:49:51, clear of the hour.
- 00:49:32 Apache reloaded onto the balancer; 00:49:51 old `minesweeper-web`
  stopped and disabled; live symlink → `minesweeper-blue`.
- **Step 8, first run:** 753 requests, none failed, but 4 took 6–11 s, all while
  the incoming copy was loading: gunicorn opens its port before its workers are
  ready, and Apache sent requests to it. Fixed with Apache health checks
  (`proxy_hcheck`, `hcuri=/health`), reloaded 00:54:20.
- **Step 8, second run:** 1,175 requests (GET and POST) across two switches;
  none failed, none over 2 s (slowest 1.7 s, during the incoming copy's load).
- Cron switched to `deploy.sh` and `pvp_catchup.sh`; `archive_anon_pvp.py` now
  runs from `/home/ubuntu/minesweeper`. Old crontab: `/home/ubuntu/crontab.pre-zd.txt`.
- Apache backups: `/home/ubuntu/minesweeper-shared/default-ssl.conf.pre-zd`
  (before the cutover) and `default-ssl.conf.balancer-v1` (before health checks).

### Back-out (from any step)

```
sudo cp /home/ubuntu/minesweeper-shared/default-ssl.conf.pre-zd /etc/apache2/sites-enabled/default-ssl.conf
sudo apachectl configtest && sudo systemctl reload apache2
ln -sfn git/minesweeper.org /home/ubuntu/minesweeper.new && mv -Tf /home/ubuntu/minesweeper.new /home/ubuntu/minesweeper
sudo systemctl enable --now minesweeper-web
sudo cp /home/ubuntu/minesweeper-shared/minesweeper-pvp.service.pre-zd /etc/systemd/system/minesweeper-pvp.service
sudo systemctl daemon-reload && sudo systemctl restart minesweeper-pvp
sudo systemctl disable --now minesweeper-web@blue minesweeper-web@green
rsync -a /home/ubuntu/minesweeper-shared/uploads/ /home/ubuntu/git/minesweeper.org/static/uploads/
crontab /home/ubuntu/crontab.pre-zd.txt
```
