#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# gcp_start_staging.sh — Start the staging instance on pgl-minesweeper-web (GCP)
#
# Environment : staging  (ENVIRONMENT=staging in .env)
# Port        : 8002
# URL         : https://staging-pgl.minesweeper.org
#
# Intended to be used as the ExecStart in a systemd service:
#
#   [Unit]
#   Description=Minesweeper Staging FastAPI App
#   After=network.target mysql.service
#
#   [Service]
#   User=ajaxchess_gmail_com
#   WorkingDirectory=/home/ajaxchess_gmail_com/git/staging.minesweeper.org
#   ExecStart=/home/ajaxchess_gmail_com/git/staging.minesweeper.org/scripts/gcp_start_staging.sh
#   Restart=always
#   RestartSec=5
#
#   [Install]
#   WantedBy=multi-user.target
#
# Save the above to /etc/systemd/system/minesweeper-staging.service, then:
#   sudo systemctl daemon-reload
#   sudo systemctl enable minesweeper-staging
#   sudo systemctl start  minesweeper-staging
#
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_DIR="/home/ajaxchess_gmail_com/git/staging.minesweeper.org"
VENV_DIR="${REPO_DIR}/venv"

cd "$REPO_DIR" || { echo "Error: REPO_DIR not found at ${REPO_DIR}"; exit 1; }

# Override ENVIRONMENT for this process (staging)
export ENVIRONMENT=staging

exec "${VENV_DIR}/bin/uvicorn" main:app \
    --host 127.0.0.1 \
    --port 8002 \
    --workers 2
