#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# start_staging.sh — Start the staging instance of minesweeper.org
#
# Environment : staging  (ENVIRONMENT=staging in .env)
# Port        : 8002
# URL         : https://staging.minesweeper.org
#
# Intended to be used as the ExecStart in a systemd service:
#
#   [Unit]
#   Description=Minesweeper Staging FastAPI App
#   After=network.target mysql.service
#
#   [Service]
#   User=ubuntu
#   WorkingDirectory=/home/ubuntu/minesweeper
#   ExecStart=/home/ubuntu/minesweeper/scripts/start_staging.sh
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
# Apache vhost for staging.minesweeper.org (port 443 via certbot):
#
#   <VirtualHost *:80>
#       ServerName staging.minesweeper.org
#       ProxyPreserveHost On
#       ProxyPass        /static/ !
#       Alias /static /home/ubuntu/minesweeper/static
#       <Directory /home/ubuntu/minesweeper/static>
#           Require all granted
#       </Directory>
#       ProxyPass        /ws/ ws://127.0.0.1:8002/ws/
#       ProxyPassReverse /ws/ ws://127.0.0.1:8002/ws/
#       ProxyPass        / http://127.0.0.1:8002/
#       ProxyPassReverse / http://127.0.0.1:8002/
#   </VirtualHost>
#
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
