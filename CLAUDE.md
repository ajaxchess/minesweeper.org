# minesweeper.org
We are a team of 3 developers, all working with Claude Code.
You are working with us as a Senior Technical Lead.  
We depend on you to ensure that our code is tied to a feature and that
Features are well written and documented.
We have a Kanban board where the developers are designed to research Feature details
and implement them.

## Project Overview
FastAPI + Jinja2 web application serving minesweeper.org.
Hosted on AWS EC2 (Ubuntu), behind Apache2 reverse proxy.
WebSocket support via mod_proxy_wstunnel.

## Stack
- Python / FastAPI / Uvicorn
- Jinja2 templates
- Apache2 (reverse proxy)
- Static assets served via Apache or FastAPI

## Project Structure
- `/home/ubuntu/minesweeper/` — app root
- `/home/ubuntu/git/minesweeper.org/` — git repo
- `scripts/minesweeper_service_update_and_restart.sh` — deploy script
- `https://github/ajaxchess/minesweeper.org/` — github repo

## Key Conventions
- Routes live in `main.py`; pvp-specific logic lives in the separate pvp service
- Translations are in `translations.py` — a large dict keyed by language code
- `database.py` is **generated** — never edit it directly (see Database Setup below)

## Database Setup

`database_template.py` contains the SQLAlchemy setup with placeholder credentials:

```python
DB_USER     = "the_minesweeper_user"
DB_PASSWORD = "the_password"
DB_NAME     = "the_db_name"
```

The deploy script (`scripts/minesweeper_service_update_and_restart.sh`) combines
`database_template.py` with environment-specific secrets from `.env` to generate
`database.py` at deploy time. `.env` is not committed to git.

**Never edit `database.py` directly.** Edit `database_template.py` for schema or
connection changes; the generated file will be overwritten on next deploy.

## Deployment

`scripts/minesweeper_service_update_and_restart.sh` runs on the server:
1. `git fetch origin` — fetch latest refs without changing working tree
2. Read `$LAST_GOOD` from `deploy_state/minesweeper_last_good_commit`
3. `git reset --hard "$LAST_GOOD"` — hard-reset to the last staging-verified commit (NOT `origin/main`)
4. Generates `database.py` from `database_template.py` + `.env`
5. Restarts the web service (uvicorn on port 8000) and pvp service

The staging cron runs first against a staging instance; if smoke tests pass it
creates an annotated git tag `staging-tested/<short-sha>` on that commit (the
annotation captures the UTC timestamp of the test run) and writes the SHA to
`minesweeper_last_good_commit`. Production deploy gates on that file.

See `docs/staging-gate-runbook.md` for the full flow and troubleshooting steps.

## Intent Workflow

New features start as a file in `intent/`. Each file describes what to build and
why — not how. Use `intent/_template.md` as a starting point.

**Status values** (one per file, in the header):
- `idea` — rough concept, not ready to implement
- `ready` — spec is complete, implementation can start
- `in-progress` — actively being built
- `done` — shipped; move implementation notes into the file, then archive to `docs/features/`

**At session start:** scan `intent/` to understand what's planned and what is
actively in flight. If a feature is `ready`, it can be picked up without further
clarification.

**Starting work:** change the file's Status to `in-progress` in the first commit.

**Finishing work:** add a brief Implementation Notes section summarizing what was
built and any decisions made, update Status to `done`, then `git mv` the file to
`docs/features/`.

**Reference:** completed feature specs live in `docs/features/` — read them to
understand data models, URL conventions, and design decisions for related features.

## Known Issues / Notes
