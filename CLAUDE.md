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

## Key Conventions
- [any naming conventions, code style preferences]
- [how routes are organized]
- [how translations/i18n is handled]

## Deployment
- Cron-based auto-deploy every 5 minutes via git pull
- Runs as ubuntu user

## Known Issues / Notes
