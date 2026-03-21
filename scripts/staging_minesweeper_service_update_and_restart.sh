#!/bin/bash

# --- Configuration ---
REPO_DIR="/home/ubuntu/git/staging.minesweeper.org"
VENV_DIR="$REPO_DIR/venv"
SERVICE_NAME="minesweeper-staging"
source "$REPO_DIR/.env"

# --- Navigate to repository and fetch changes ---
cd "$REPO_DIR" || { echo "Error: Missing REPO_DIR"; exit 1; }

# Fetch remote changes without merging
git fetch origin > /dev/null 2>&1

# Check if the local branch is behind the remote branch
LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main)

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    echo "Staging repository is up to date. No changes to pull."
else
    echo "Changes detected. Pulling updates..."
    if [[ $(git status --porcelain) ]]; then
        echo "Warning: Uncommitted local changes found. Stashing before pull."
        git stash
    fi

    git pull origin main

    # --- Minify static assets ---
    echo "Building static assets..."
    bash "$REPO_DIR/scripts/build_assets.sh" || echo "Warning: asset build failed (continuing)"

    # --- Sync Python dependencies ---
    echo "Installing/updating Python dependencies..."
    "$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements.txt" --quiet || { echo "Warning: pip install failed"; }

    # --- Copy database.py ---
    FILE_PATH="$REPO_DIR/database_template.py"
    MINUTES_AGO=5
    if [ -n "$(find "$FILE_PATH" -maxdepth 0 -mmin -"$MINUTES_AGO" 2>/dev/null)" ]; then
        echo "database_template.py changed — regenerating database.py"
        /usr/bin/cp database_template.py database.py
        /usr/bin/sed -i "s/the_minesweeper_user/$DB_USER/g" database.py
        /usr/bin/sed -i "s/the_password/$DB_PASS/g" database.py
        /usr/bin/sed -i "s/the_db_name/$DB_NAME/g" database.py
    else
        echo "database_template.py unchanged — skipping database.py regeneration."
    fi

    # --- Restart the service ---
    echo "Restarting service: $SERVICE_NAME..."
    sudo systemctl restart "$SERVICE_NAME" || { echo "Error: Failed to restart service"; exit 1; }
    echo "Service $SERVICE_NAME restarted successfully."
fi
