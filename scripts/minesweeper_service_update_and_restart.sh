#!/bin/bash

# --- Configuration ---
STATE_DIR="/home/ubuntu/deploy_state"
REPO_DIR="/home/ubuntu/minesweeper"
VENV_DIR="/home/ubuntu/minesweeper/venv"
# Split across two services (see scripts/minesweeper-web.service and
# scripts/minesweeper-pvp.service): the multi-worker pool for general HTTP
# traffic, and a single-worker instance that owns duel.py's in-memory
# game/matchmaking state (routed /duel, /duelold, /pvp, /pvpbeta, /ws/ only —
# see scripts/minesweeper-split-example.conf). Both run the same codebase, so
# both must restart on every deploy or one keeps serving stale code.
SERVICE_NAMES=("minesweeper-web" "minesweeper-pvp")
source /home/ubuntu/minesweeper/.env

if [ "$(id -u)" -eq 0 ]; then
    echo "Error: This script must not be run as root. Run as the 'ubuntu' user."
    exit 1
fi

mkdir -p "$STATE_DIR"

# --- Navigate to repository and fetch changes ---
cd "$REPO_DIR" || { echo "Error: Missing REPO_DIR"; exit 1; }

git fetch origin > /dev/null 2>&1

LOCAL_COMMIT=$(git rev-parse HEAD)

# ── Determine deploy target ───────────────────────────────────────────────────
# Production only deploys commits that have been validated by staging smoke tests.
# The staging script writes the last passing commit SHA to minesweeper_last_good_commit.
LAST_GOOD=$(cat "$STATE_DIR/minesweeper_last_good_commit" 2>/dev/null || echo "")

if [ -z "$LAST_GOOD" ]; then
    # First run: no minesweeper_last_good_commit exists yet.
    # Assume the current prod state is good and record it.
    # Staging will overwrite this once it validates a new commit.
    echo "Initializing minesweeper_last_good_commit to current prod HEAD ($LOCAL_COMMIT)."
    echo "$LOCAL_COMMIT" > "$STATE_DIR/minesweeper_last_good_commit"
    LAST_GOOD="$LOCAL_COMMIT"
fi

if [ "$LOCAL_COMMIT" = "$LAST_GOOD" ]; then
    echo "Production is already on last good commit $LAST_GOOD. Nothing to deploy."
    exit 0
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') Deploy candidate available: $LAST_GOOD. Deploying to production..."

# ── Deploy ────────────────────────────────────────────────────────────────────
if [[ $(git status --porcelain) ]]; then
    echo "Warning: Uncommitted local changes found. Stashing before deploy."
    git stash
fi

git reset --hard "$LAST_GOOD"

echo "Installing/updating Python dependencies..."
"$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements.txt" --quiet || echo "Warning: pip install failed"

echo "Regenerating database.py from template..."
/usr/bin/cp database_template.py database.py
# Literal string replace via Python, not sed — sed's replacement string treats
# /, &, and \ specially, so a DB_PASS containing any of those silently
# corrupts database.py instead of erroring. Values are passed as env vars
# (not interpolated into the script text) so nothing in them can break the
# shell command either.
DB_USER="$DB_USER" DB_PASS="$DB_PASS" DB_NAME="$DB_NAME" python3 - database.py <<'PYEOF'
import os, sys
from pathlib import Path
p = Path(sys.argv[1])
s = p.read_text()
s = s.replace("the_minesweeper_user", os.environ["DB_USER"])
s = s.replace("the_password", os.environ["DB_PASS"])
s = s.replace("the_db_name", os.environ["DB_NAME"])
p.write_text(s)
PYEOF

for SERVICE_NAME in "${SERVICE_NAMES[@]}"; do
    echo "Restarting $SERVICE_NAME..."
    sudo systemctl restart "$SERVICE_NAME" || { echo "Error: Failed to restart $SERVICE_NAME"; exit 1; }
done
echo "Production deployed to commit $LAST_GOOD."
