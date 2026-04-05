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

echo "Deploy candidate available: $LAST_GOOD. Checking staging..."

# ── Staging health gate (3 attempts, 15s apart) ───────────────────────────────
# Confirm staging is healthy and running the exact commit we are about to promote.
# Retries handle the case where staging is still coming up after a restart.
STAGING_OK=0
for attempt in 1 2 3; do
    STAGING_RESPONSE=$(curl -s --max-time 10 \
        -w "\n__HTTP_STATUS__%{http_code}" \
        http://127.0.0.1:8002/health)
    STAGING_HTTP=$(echo "$STAGING_RESPONSE" | grep '__HTTP_STATUS__' | sed 's/__HTTP_STATUS__//')
    STAGING_BODY=$(echo "$STAGING_RESPONSE" | grep -v '__HTTP_STATUS__')

    STAGING_STATUS=$(echo "$STAGING_BODY" | python3 -c \
        "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
    STAGING_COMMIT=$(echo "$STAGING_BODY" | python3 -c \
        "import sys,json; print(json.load(sys.stdin).get('commit',''))" 2>/dev/null)

    if [ "$STAGING_HTTP" = "200" ] && [ "$STAGING_STATUS" = "ok" ] && [ "$STAGING_COMMIT" = "$LAST_GOOD" ]; then
        STAGING_OK=1
        break
    fi

    if [ $attempt -lt 3 ]; then
        echo "Staging check attempt $attempt failed (HTTP=$STAGING_HTTP, status=$STAGING_STATUS, commit=$STAGING_COMMIT). Retrying in 15s..."
        sleep 15
    else
        echo "ERROR: Staging health gate failed after 3 attempts."
        echo "       Last response: HTTP=$STAGING_HTTP, status=$STAGING_STATUS, commit=$STAGING_COMMIT (expected $LAST_GOOD)."
        echo "       Aborting prod deploy."
    fi
done

if [ "$STAGING_OK" = "0" ]; then
    exit 1
fi

echo "Staging OK — HTTP 200, status=ok, commit=$STAGING_COMMIT. Deploying to production..."

# ── Deploy ────────────────────────────────────────────────────────────────────
if [[ $(git status --porcelain) ]]; then
    echo "Warning: Uncommitted local changes found. Stashing before deploy."
    git stash
fi

git reset --hard "$LAST_GOOD"

# Only rebuild static assets if JS or CSS files changed between commits.
if git diff --name-only "$LOCAL_COMMIT" "$LAST_GOOD" -- static/js/ static/css/ | grep -qE '\.(js|css)$'; then
    echo "Static assets changed — building..."
    bash "$REPO_DIR/scripts/build_assets.sh" || echo "Warning: asset build failed (continuing)"
else
    echo "Static assets unchanged — skipping build."
fi

echo "Installing/updating Python dependencies..."
"$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements.txt" --quiet || echo "Warning: pip install failed"

echo "Regenerating database.py from template..."
/usr/bin/cp database_template.py database.py
/usr/bin/sed -i "s/the_minesweeper_user/$DB_USER/g" database.py
/usr/bin/sed -i "s/the_password/$DB_PASS/g" database.py
/usr/bin/sed -i "s/the_db_name/$DB_NAME/g" database.py

sudo systemctl restart "$SERVICE_NAME" || { echo "Error: Failed to restart service"; exit 1; }
echo "Production deployed to commit $LAST_GOOD."
