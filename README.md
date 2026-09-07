# minesweeper.org

Free online Minesweeper — classic, no-guess, real-time PvP duel, Rush, Tentaizu, Mosaic, and more.

**Live site:** https://minesweeper.org
**GitHub:** https://github.com/ajaxchess/minesweeper.org
**Author:** Richard Cross

---

## About

Minesweeper.org was originally launched in 1999 and dedicated to Diana, Princess of Wales, and the charity she supported — [The HALO Trust](https://www.halousa.org/).

The original site can be seen at the [Wayback Machine](https://web.archive.org/web/20040325004955/http://www.minesweeper.org/). One goal of this project is to bring back the original look, feel, and mission.

---

## Stack

- **Python 3** / **FastAPI** / **Uvicorn**
- **Jinja2** templates
- **MySQL** (via SQLAlchemy + PyMySQL)
- **Apache2** reverse proxy with WebSocket support (`mod_proxy_wstunnel`)
- Google OAuth 2.0 (sign-in), Google Analytics, Google AdSense

---

## Installation (Ubuntu 22.04+)

### 1. Clone the repository

```bash
git clone https://github.com/ajaxchess/minesweeper.org /home/ubuntu/minesweeper
cd /home/ubuntu/minesweeper
```

### 2. Configure environment variables

```bash
cp .env_example .env
nano .env   # fill in all required values (see .env_example for descriptions)
```

**Required values in `.env`:**

| Variable | Description |
|---|---|
| `DB_USER` | MySQL username |
| `DB_PASS` | MySQL password |
| `GOOGLE_CLIENT_ID` | From [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud Console |
| `SECRET_KEY` | Random string — generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `GA_TAG` | Google Analytics tag (optional, e.g. `G-XXXXXXXXXX`) |
| `ADMIN_EMAILS` | Comma-separated list of admin Google account emails |

### 3. Run the automated install script

```bash
sudo bash scripts/install_ubuntu.sh
```

This script:
- Installs system packages (Python 3, Node.js, MySQL, Apache2, Certbot)
- Creates the MySQL database and user
- Sets up the Python virtual environment and installs all dependencies
- Installs `terser` and `csso-cli` globally for JS/CSS minification
- Generates `database.py` from `database_template.py`
- Builds minified static assets
- Installs and starts the `minesweeper` systemd service
- Configures Apache2 as a reverse proxy with WebSocket support
- Installs the staging-gate deploy cron (every 5 minutes — see [Deployment](#deployment))

### 4. Get an SSL certificate

```bash
sudo certbot --apache -d minesweeper.org -d www.minesweeper.org
```

### 5. Verify

```bash
sudo systemctl status minesweeper
sudo journalctl -u minesweeper -f
```

---

## Files synced manually to the server

These are **gitignored** — manage and sync them independently:

| Path | Purpose |
|---|---|
| `.env` | Credentials and configuration |
| `database.py` | Generated from `database_template.py` with real credentials |
| `analysis/` | Markdown files displayed at `/admin/analysis` |
| `bots/` | PvP bot AI code (`minesweeper_bot.py`) |
| `screenshots/` | Local screenshots for development |

---

## Database

```sql
CREATE DATABASE minesweeper CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'minesweeper_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON minesweeper.* TO 'minesweeper_user'@'localhost';
FLUSH PRIVILEGES;
```

The `database_template.py` file contains placeholder credentials. The deploy script copies it to `database.py` and substitutes real credentials from `.env` whenever the template changes.

---

## Development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

---

## Testing

```bash
source venv/bin/activate
pytest                      # run the full test suite
pytest -x                   # stop on first failure
pytest tests/test_routes.py # run a specific file
```

Tests use an in-memory SQLite database (via SQLAlchemy `StaticPool`) and a full FastAPI test client — no external services required. Bandit SAST runs alongside pytest in CI.

---

## Deployment

Production never pulls directly from `origin/main`. Every push goes through a **staging gate** first:

```
commit → CI (pytest + Bandit) → staging cron → smoke tests → tag + write last-good SHA → production cron → git reset --hard $LAST_GOOD
```

**Staging cron** (`scripts/staging_minesweeper_service_update_and_restart.sh`, runs every 5 minutes):
1. `git fetch origin` and `git reset --hard origin/main` on the staging instance
2. Rebuilds assets, regenerates `database.py`, restarts the staging service
3. Runs smoke tests against the staging instance
4. On pass: creates an annotated tag `staging-tested/<short-sha>` and writes the SHA to `deploy_state/minesweeper_last_good_commit`
5. On fail: leaves `minesweeper_last_good_commit` unchanged — production is not updated

**Production cron** (`scripts/minesweeper_service_update_and_restart.sh`, runs every 5 minutes):
1. `git fetch origin`
2. Reads `$LAST_GOOD` from `deploy_state/minesweeper_last_good_commit`
3. `git reset --hard "$LAST_GOOD"` — hard-resets to the last staging-verified commit
4. Regenerates `database.py` from `database_template.py` + `.env`
5. Restarts the web service (uvicorn port 8000) and pvp service

See `docs/staging-gate-runbook.md` for the full flow and troubleshooting steps.

```bash
tail -f /var/log/minesweeper-deploy.log   # deploy logs
sudo systemctl restart minesweeper        # manual restart
sudo journalctl -u minesweeper -f         # app logs
```

---

## Observability

Minesweeper.org leverages **AWS Bedrock** to monitor the health of the infrastructure. Bedrock provides AI-powered analysis of application metrics, logs, and deployment events, enabling proactive detection of anomalies and degraded service conditions.

Key observability touchpoints:

| Signal | Source |
|---|---|
| Application health | `GET /health` — returns status, git commit, and environment |
| Uptime probe | `GET /iamatestfile.txt` — lightweight endpoint for load balancer and external monitors |
| Server metrics | CPU, memory, disk, and network stats recorded hourly to the `server_stats` table |
| Deploy gate | Staging smoke tests run after every deploy; failed commits are blocked from reaching production |
| App logs | `sudo journalctl -u minesweeper -f` |
| Deploy logs | `tail -f /var/log/minesweeper-deploy.log` |

### Operations — AWS X-Ray Performance Monitoring

The application is instrumented with **OpenTelemetry** (via `telemetry.py`). Traces are exported over OTLP HTTP to the **AWS Distro for OpenTelemetry (ADOT) Collector**, which forwards them to **AWS X-Ray** for performance analysis.

X-Ray provides a live trace map showing request flow from client to EC2 instance, latency distributions (p50/p99 response times), and per-route request counts — giving the team visibility into production performance without manual log analysis.

![AWS X-Ray Trace Map](docs/AWSXRayMonitoringExample.png)

**What is instrumented:**

| Instrumentation | What it captures |
|---|---|
| FastAPI routes | Every HTTP request as a trace span |
| SQLAlchemy | Every database query as a child span |
| Outbound HTTP | External API calls (httpx / requests) as child spans |
| Logging | `trace_id` and `span_id` injected into every log record |
| Score submissions | Custom metric — completions by game type and mode |
| Game duration | Custom histogram — time-to-complete in milliseconds |
| Scheduler jobs | Success/failure counter for `reset_scores`, `collect_server_stats`, `archive_guest_scores` |
| DB errors | Error counter tagged by operation |

**Configuration** (in `.env`):

```
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=minesweeper.org
OTEL_SERVICE_VERSION=1.0.0
```

Leave `OTEL_EXPORTER_OTLP_ENDPOINT` blank to disable tracing entirely (default in development).

---

## Software Development Gamification

Minesweeper.org uses gamification to keep the development team engaged and productive. The admin dashboard (accessible to team members at `/admin`) includes a **Git commit leaderboard** that tracks each contributor's weekly commit count — turning day-to-day development work into a friendly competition.

![Git Commit Leaderboard](docs/SoftwareDevelopmentGamification.png)

The leaderboard refreshes on every admin page load and shows:

- **Contributor** — git author name
- **Commits this week** — count of commits since Monday (UTC)
- **Latest commit SHA** — the current HEAD on the running server, compared against staging to confirm deployments are in sync

This lightweight approach to gamification encourages consistent contribution, surfaces who is actively shipping, and makes the weekly cadence of the team visible at a glance — without requiring any external tooling.

---

## AI-Native Development Workflow

Minesweeper.org is developed using the [AI-Native SDLC Playbook](https://claude.com/blog/the-ai-native-sdlc-playbook) published by Anthropic. All three developers work with **Claude Code** as a collaborative technical lead.

### How it works

**Features start as intent files.** Before writing any code, open an issue as a file in `intent/` using `intent/_template.md`. The file captures what to build and why — not how. Claude Code reads these at session start to understand what is planned and what is actively in flight.

**Status drives the Kanban board.** Each intent file has a `Status:` field (`idea` → `ready` → `in-progress` → `done`). The Kanban board at `/admin/kanban` is generated live from these files — no manual board maintenance needed.

**Completing a feature.** When work is done, add an Implementation Notes section to the intent file, set `Status: done`, and move it to `docs/features/` with `git mv`. Completed specs serve as architectural reference for future features.

```
intent/MyFeature.md  →  (build it)  →  docs/features/MyFeature.md
  Status: ready             ↓               Status: done
                      Status: in-progress
```

### Key files

| File / Directory | Purpose |
|---|---|
| `CLAUDE.md` | Instructions and conventions for Claude Code |
| `intent/` | Planned features not yet built |
| `intent/_template.md` | Starting template for new intent files |
| `docs/features/` | Completed feature specs — architectural reference |
| `/admin/kanban` | Kanban board driven by `intent/` file statuses |

---

## Blog

To add a post: drop a `.md` file in `blog/` and add one dict to `BLOG_POSTS` in `main.py`. No other changes needed.

---

## systemd service

```ini
[Unit]
Description=Minesweeper FastAPI App
After=network.target mysql.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/minesweeper
ExecStart=/home/ubuntu/minesweeper/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```
