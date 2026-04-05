#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# gcp_start_staging.sh — Start the staging instance on pgl-minesweeper-web (GCP)
#
# Environment : prod  (ENVIRONMENT=prod in .env)
# Port        : 8000
# URL         : https://pgl.minesweeper.org
#
# Intended to be used as the ExecStart in a systemd service:
#
#   [Unit]
#   Description=Minesweeper FastAPI App
#   After=network.target mysql.service
#
#   [Service]
#   User=ajaxchess_gmail_com
#   WorkingDirectory=/home/ajaxchess_gmail_com/git/minesweeper.org
#   ExecStart=/home/ajaxchess_gmail_com/git/minesweeper.org/scripts/gcp_start.sh
#   Restart=always
#   RestartSec=5
#
#   [Install]
#   WantedBy=multi-user.target
#
# Save the above to /etc/systemd/system/minesweeper.service, then:
#   sudo systemctl daemon-reload
#   sudo systemctl enable minesweeper
#   sudo systemctl start  minesweeper
#
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_DIR="/home/ajaxchess_gmail_com/git/minesweeper.org"
VENV_DIR="${REPO_DIR}/venv"

cd "$REPO_DIR" || { echo "Error: REPO_DIR not found at ${REPO_DIR}"; exit 1; }

# Override ENVIRONMENT for this process (prod)
export ENVIRONMENT=prod

exec "${VENV_DIR}/bin/uvicorn" main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 2
