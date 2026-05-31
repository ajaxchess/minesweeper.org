#!/bin/bash

# --- Configuration ---
STATE_DIR="/home/ubuntu/deploy_state"
REPO_DIR="/home/ubuntu/minesweeper"
VENV_DIR="/home/ubuntu/minesweeper/venv"
SERVICE_NAME="minesweeper"
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
# The staging script writes the last passing commit SHA to last_good_commit.
LAST_GOOD=$(cat "$STATE_DIR/last_good_commit" 2>/dev/null || echo "")

if [ -z "$LAST_GOOD" ]; then
    # First run: no last_good_commit exists yet.
    # Assume the current prod state is good and record it.
    # Staging will overwrite this once it validates a new commit.
    echo "Initializing last_good_commit to current prod HEAD ($LOCAL_COMMIT)."
    echo "$LOCAL_COMMIT" > "$STATE_DIR/last_good_commit"
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

# Always rebuild static assets after git reset --hard, because the reset always
# restores the unminified source files from git regardless of whether JS/CSS changed.
echo "Building static assets..."
bash "$REPO_DIR/scripts/build_assets.sh" || echo "Warning: asset build failed (continuing)"

echo "Installing/updating Python dependencies..."
"$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements.txt" --quiet || echo "Warning: pip install failed"

echo "Regenerating database.py from template..."
/usr/bin/cp database_template.py database.py
/usr/bin/sed -i "s/the_minesweeper_user/$DB_USER/g" database.py
/usr/bin/sed -i "s/the_password/$DB_PASS/g" database.py
/usr/bin/sed -i "s/the_db_name/$DB_NAME/g" database.py

sudo systemctl restart "$SERVICE_NAME" || { echo "Error: Failed to restart service"; exit 1; }
echo "Production deployed to commit $LAST_GOOD."
