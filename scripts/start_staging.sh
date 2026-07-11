#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# start_staging.sh — Start the WEB half of the staging instance of minesweeper.org
#
# Superseded by scripts/minesweeper-staging-web.service +
# scripts/minesweeper-staging-pvp.service (see docs/pvp-gunicorn-split-runbook.md).
# Staging is now split the same way as production: this script/port only
# serves general HTTP traffic. /duel, /duelold, /pvp, /pvpbeta, /ws/ are
# served by a separate single-worker instance on port 8052 (see
# scripts/minesweeper-staging-pvp.service) — those routes read/write duel.py's
# in-memory game state directly, which breaks under more than one worker.
# Kept as a manual/local-testing helper for the web half only.
#
# Environment : staging  (ENVIRONMENT=staging in .env)
# Port        : 8002
# URL         : https://staging.minesweeper.org
#
# For the real systemd units, apply scripts/minesweeper-staging-web.service
# and scripts/minesweeper-staging-pvp.service directly — see the runbook.
#
# Apache vhost for staging.minesweeper.org: scripts/staging-minesweeper.conf
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_DIR="/home/ubuntu/staging-minesweeper"
VENV_DIR="${REPO_DIR}/venv"

cd "$REPO_DIR" || { echo "Error: REPO_DIR not found at ${REPO_DIR}"; exit 1; }

# Override ENVIRONMENT for this process (staging)
export ENVIRONMENT=staging

exec "${VENV_DIR}/bin/uvicorn" main:app \
    --host 127.0.0.1 \
    --port 8002 \
    --workers 2
