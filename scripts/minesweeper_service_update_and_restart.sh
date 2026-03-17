#!/bin/bash


# --- Configuration ---
REPO_DIR="/home/ubuntu/minesweeper"
VENV_DIR="/home/ubuntu/minesweeper/venv"   # adjust if your venv lives elsewhere
SERVICE_NAME="minesweeper" # e.g., nginx, apache2, custom_app
source /home/ubuntu/minesweeper/.env

# --- Navigate to repository and fetch changes ---
cd "$REPO_DIR" || { echo "Error: Missing REPO_DIR"; exit 1; }

# Fetch remote changes without merging
git fetch origin > /dev/null 2>&1

# Check if the local branch is behind the remote branch
LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main) # Replace 'main' if your branch name is different

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    echo "Local repository is up to date. No changes to pull."
else
    echo "Changes detected. Pulling updates..."
    # Ensure a clean working directory before pulling
    if [[ $(git status --porcelain) ]]; then
        echo "Warning: Uncommitted local changes found. Stashing before pull."
        git stash
    fi

    # Pull the changes
    git pull origin main # Replace 'main' if your branch name is different

    # If changes were stashed, re-apply them
    if [ "$?" -eq 0 ] && [ -n "$STASH_NEEDED" ]; then
        echo "Applying stashed changes..."
        git stash pop
    fi

    # --- Sync Python dependencies ---
    echo "Installing/updating Python dependencies..."
    "$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements.txt" --quiet || { echo "Warning: pip install failed"; }

    # --- Copy database.py ---
    FILE_PATH="/home/ubuntu/git/minesweeper.org/database_template.py"
    MINUTES_AGO=5
    if [ -n "$(find "$FILE_PATH" -maxdepth 0 -mmin -"$MINUTES_AGO" 2>/dev/null)" ]; then
        echo "The file $FILE_PATH was changed in the past $MINUTES_AGO minutes."
        echo "copy database_template.py database.py"
        /usr/bin/cp database_template.py database.py
        /usr/bin/sed -i "s/the_minesweeper_user/$DB_USER/g" database.py
        /usr/bin/sed -i "s/the_password/$DB_PASS/g" database.py
    else
        echo "The file $FILE_PATH was NOT changed in the past $MINUTES_AGO minutes, or does not exist."
    fi
    # --- Restart the service ---
    echo "Restarting service: $SERVICE_NAME..."
    # Use 'sudo' if necessary, depending on your permissions
    sudo systemctl restart "$SERVICE_NAME" || { echo "Error: Failed to restart service"; exit 1; }
    echo "Service $SERVICE_NAME restarted successfully."
fi
