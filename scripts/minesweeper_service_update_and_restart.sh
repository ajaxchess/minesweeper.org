#!/bin/bash

# --- Configuration ---
STATE_DIR="/home/ubuntu/deploy_state"
REPO_DIR="/home/ubuntu/minesweeper"
VENV_DIR="/home/ubuntu/minesweeper/venv"
SERVICE_NAME="minesweeper"
source /home/ubuntu/minesweeper/.env

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

echo "Deploy candidate available: $LAST_GOOD. Checking staging..."

# ── Staging health gate ───────────────────────────────────────────────────────
# Confirm staging is healthy and running the exact commit we are about to promote.
STAGING_RESPONSE=$(curl -s --max-time 10 \
    -w "\n__HTTP_STATUS__%{http_code}" \
    http://127.0.0.1:8002/health)
STAGING_HTTP=$(echo "$STAGING_RESPONSE" | grep '__HTTP_STATUS__' | sed 's/__HTTP_STATUS__//')
STAGING_BODY=$(echo "$STAGING_RESPONSE" | grep -v '__HTTP_STATUS__')

if [ "$STAGING_HTTP" != "200" ]; then
    echo "ERROR: Staging /health returned HTTP $STAGING_HTTP. Aborting prod deploy."
    exit 1
fi

STAGING_STATUS=$(echo "$STAGING_BODY" | python3 -c \
    "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
if [ "$STAGING_STATUS" != "ok" ]; then
    echo "ERROR: Staging health status is '$STAGING_STATUS' (expected 'ok'). Aborting prod deploy."
    exit 1
fi

STAGING_COMMIT=$(echo "$STAGING_BODY" | python3 -c \
    "import sys,json; print(json.load(sys.stdin).get('commit',''))" 2>/dev/null)
if [ "$STAGING_COMMIT" != "$LAST_GOOD" ]; then
    echo "ERROR: Staging is on commit $STAGING_COMMIT, expected last good commit $LAST_GOOD."
    echo "       Staging may still be reverting or restarting. Aborting prod deploy."
    exit 1
fi

echo "Staging OK — HTTP 200, status=ok, commit=$STAGING_COMMIT. Deploying to production..."

# ── Deploy ────────────────────────────────────────────────────────────────────
if [[ $(git status --porcelain) ]]; then
    echo "Warning: Uncommitted local changes found. Stashing before deploy."
    git stash
fi

git reset --hard "$LAST_GOOD"

echo "Building static assets..."
bash "$REPO_DIR/scripts/build_assets.sh" || echo "Warning: asset build failed (continuing)"

echo "Installing/updating Python dependencies..."
"$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements.txt" --quiet || echo "Warning: pip install failed"

FILE_PATH="/home/ubuntu/git/minesweeper.org/database_template.py"
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

sudo systemctl restart "$SERVICE_NAME" || { echo "Error: Failed to restart service"; exit 1; }
echo "Production deployed to commit $LAST_GOOD."
