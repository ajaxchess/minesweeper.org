# Production cutover: web/pvp gunicorn split

Migrates the live EC2 host from a single `minesweeper` uvicorn process to two
gunicorn-managed services:

- **`minesweeper-web`** — 4 `UvicornWorker` processes on port 8000. All
  stateless HTTP traffic (games, scores, leaderboards, admin, etc.).
- **`minesweeper-pvp`** — 1 worker on port 8001. Only `/duel`, `/duelold`,
  `/pvp`, `/pvpbeta`, `/ws/`. These routes read/write `duel.py`'s in-memory
  `_games` dict and matchmaking queues directly — that only works if every
  request for a given game lands on the same OS process, so this stays
  single-worker until that state moves to something shared (e.g. Redis).

Why: with more than one worker, two players who queue up around the same
time can land on different processes with no way to see each other's
in-memory state — matchmaking silently fails to pair them, or a `DuelGame`'s
broadcast can't reach the other player's socket.

Commits: `8850967` (split + scheduler flock guard), `52add1c` (requirements.in).

**Expect a few minutes of reduced capacity while services swap over — do
this in a low-traffic window.** Steps 1–9 are non-destructive and reversible
at every point (see Rollback at the end). Do not skip the verification steps.

---

## 0. Before you start

SSH into the production host, then confirm the current state rather than
assuming it matches this doc:

```bash
systemctl list-units --type=service | grep -i minesweeper
cd /home/ubuntu/minesweeper && git status && git log --oneline -3
ls /etc/apache2/sites-enabled/
```

You're looking for: the currently-running service name (expected:
`minesweeper.service`), whether the repo has uncommitted local changes
(there shouldn't be any — if there are, stop and figure out why before
proceeding), and which Apache site file is actually enabled.

## 1. Pause the auto-deploy cron

The production cron (`/etc/cron.d/minesweeper-deploy`, every 5 minutes) runs
`minesweeper_service_update_and_restart.sh`, which now tries to restart
`minesweeper-web`/`minesweeper-pvp` — services that don't exist on this host
yet. Pause it so cron doesn't race you mid-migration:

```bash
sudo mv /etc/cron.d/minesweeper-deploy /etc/cron.d/minesweeper-deploy.paused
```

(You'll restore this in step 9. Until then, missing this file just means
"no auto-deploy," which is what we want.)

## 2. Pull the new code and install dependencies

```bash
cd /home/ubuntu/minesweeper
git fetch origin
git log --oneline HEAD..origin/main   # sanity check what you're about to pull
git reset --hard origin/main
venv/bin/pip install -r requirements.txt --quiet
venv/bin/pip show gunicorn            # confirm it installed (23.0.0)
```

## 3. Install the two systemd unit files

```bash
sudo cp scripts/minesweeper-web.service /etc/systemd/system/
sudo cp scripts/minesweeper-pvp.service /etc/systemd/system/
sudo systemctl daemon-reload
```

Both files hardcode `/home/ubuntu/minesweeper` and ports 8000/8001 — if your
host differs from that, edit before copying.

## 4. Cut over: stop the old service, start the two new ones

The old service and `minesweeper-web` both bind port 8000, so the old one
must be stopped first:

```bash
sudo systemctl stop minesweeper
sudo systemctl enable --now minesweeper-web
sudo systemctl enable --now minesweeper-pvp
sudo systemctl status minesweeper-web minesweeper-pvp --no-pager
```

Both should show `active (running)`. If either fails, check
`sudo journalctl -u minesweeper-web -n 50` /
`sudo journalctl -u minesweeper-pvp -n 50` before continuing — common causes
are the venv not having gunicorn yet (re-run step 2) or a port already in
use (confirm the old service actually stopped: `sudo ss -ltnp | grep -E ':8000|:8001'`).

## 5. Verify both services directly (bypass Apache)

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/           # web pool — expect 200
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/duel       # pvp instance — expect 200
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/pvp/bot    # pvp instance — expect 200
```

If any of these fail, fix it now — don't proceed to touch Apache with a
broken backend.

## 6. Update the Apache vhost

Find the live config first (there may be a plain :80 file and a
certbot-generated `-le-ssl.conf` — you want the one with the actual
`ProxyPass` rules, usually the SSL one):

```bash
grep -l "ProxyPass" /etc/apache2/sites-enabled/*
```

Back it up, then apply the split from `scripts/minesweeper-split-example.conf`
(adjust `ServerName`/`SSLCertificateFile`/log paths to match your existing
file — that example is a bare-HTTP template, your real file likely has the
Let's Encrypt block from `staging-minesweeper.conf` as a reference):

```bash
sudo cp /etc/apache2/sites-enabled/<your-file>.conf /etc/apache2/sites-enabled/<your-file>.conf.bak-$(date +%Y%m%d)
sudo vi /etc/apache2/sites-enabled/<your-file>.conf
```

The parts that need to change — replace the existing `/ws/` and `/` blocks
with (order matters, most specific first):

```apache
ProxyPass        /ws/       ws://127.0.0.1:8001/ws/      upgrade=websocket retry=0
ProxyPassReverse /ws/       ws://127.0.0.1:8001/ws/

ProxyPass        /duel      http://127.0.0.1:8001/duel    retry=0
ProxyPassReverse /duel      http://127.0.0.1:8001/duel

ProxyPass        /duelold   http://127.0.0.1:8001/duelold retry=0
ProxyPassReverse /duelold   http://127.0.0.1:8001/duelold

ProxyPass        /pvp       http://127.0.0.1:8001/pvp     retry=0
ProxyPassReverse /pvp       http://127.0.0.1:8001/pvp

ProxyPass        /pvpbeta   http://127.0.0.1:8001/pvpbeta retry=0
ProxyPassReverse /pvpbeta   http://127.0.0.1:8001/pvpbeta

ProxyPass        / http://127.0.0.1:8000/
ProxyPassReverse / http://127.0.0.1:8000/
```

Everything else in the file (SSL cert directives, static asset caching,
compression, error/access logs) stays as-is.

## 7. Test and reload Apache

```bash
sudo apache2ctl configtest     # must print "Syntax OK" — do not reload if not
sudo systemctl reload apache2
```

## 8. End-to-end verification through the real domain

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://minesweeper.org/
curl -s -o /dev/null -w "%{http_code}\n" https://minesweeper.org/duel
curl -s -o /dev/null -w "%{http_code}\n" https://minesweeper.org/pvp/bot
```

Then the test that actually matters — **confirm two independent players can
still be matched and play against each other**, since that's the exact bug
this migration fixes:

1. Open `https://minesweeper.org/pvp` in one browser and a separate
   incognito/private window (or a second device).
2. Queue up for a match in both.
3. Confirm they pair up, both boards load, and moves/flags relay between
   them in real time.

Repeat this a few times — a single pass could luck into landing on the same
process even if something's misconfigured (there's only one pvp process
right now, so in practice it always will; this check is really about
confirming Apache is routing `/ws/`, `/pvp`, `/duel` correctly at all, not
about proving multi-process correctness, which is guaranteed by
`minesweeper-pvp` being single-worker).

Also spot-check something on the web pool that isn't pvp-related (e.g. play
a regular game, check `/leaderboard`) to confirm general traffic is fine on
`minesweeper-web`.

## 9. Clean up and re-enable auto-deploy

Once you're confident things are stable (give it a bit — maybe an hour of
normal traffic):

```bash
sudo systemctl disable minesweeper      # leave it stopped, don't delete yet
sudo mv /etc/cron.d/minesweeper-deploy.paused /etc/cron.d/minesweeper-deploy
```

Keep the old `minesweeper.service` unit file around (don't delete it) for a
few days in case you need to roll back. Once you're comfortable it's no
longer needed:

```bash
sudo rm /etc/systemd/system/minesweeper.service
sudo systemctl daemon-reload
```

---

## Rollback

If something goes wrong at any point after step 4:

```bash
sudo systemctl stop minesweeper-web minesweeper-pvp
sudo cp /etc/apache2/sites-enabled/<your-file>.conf.bak-<date> /etc/apache2/sites-enabled/<your-file>.conf
sudo apache2ctl configtest && sudo systemctl reload apache2
sudo systemctl start minesweeper
```

That restores the exact pre-migration state (old code was never touched —
only the new services and Apache config changed). If you'd already
progressed to step 2 (code pulled) before something broke, the old
`minesweeper.service` will run the new code too — that's fine, it's the same
codebase, just without the process split; nothing in this change alters
application behavior on a single process.

## What to watch afterward

- `sudo journalctl -u minesweeper-web -f` / `-u minesweeper-pvp -f` for the
  first day or two.
- The scheduler flock guard (`main.py`) logs which process won the lock at
  startup — `"Scheduler started ... (this process holds the scheduler
  lock)"` should appear exactly once across `minesweeper-web`'s 4 workers
  plus `minesweeper-pvp`'s 1 worker (5 total), not five times. Check after
  the next deploy-triggered restart:
  `sudo journalctl -u minesweeper-web -u minesweeper-pvp | grep "scheduler lock"`.
- If `minesweeper-pvp` traffic ever grows enough that a single process can't
  keep up, the fix is moving `duel.py`'s state into Redis (pub/sub for
  cross-process broadcast) — not raising `--workers` on that service, which
  would reintroduce the original bug.
