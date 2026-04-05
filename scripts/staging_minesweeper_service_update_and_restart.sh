#!/bin/bash

# --- Configuration ---
STATE_DIR="/home/ubuntu/deploy_state"
REPO_DIR="/home/ubuntu/git/staging.minesweeper.org"
PROD_REPO_DIR="/home/ubuntu/minesweeper"
VENV_DIR="$REPO_DIR/venv"
SERVICE_NAME="minesweeper-staging"
source "$REPO_DIR/.env"

if [ "$(id -u)" -eq 0 ]; then
    echo "Error: This script must not be run as root. Run as the 'ubuntu' user."
    exit 1
fi

mkdir -p "$STATE_DIR"

# --- Navigate to repository and fetch changes ---
cd "$REPO_DIR" || { echo "Error: Missing REPO_DIR"; exit 1; }

git fetch origin > /dev/null 2>&1

LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main)

# ── Blocked commit check ──────────────────────────────────────────────────────
# If the tip of origin/main is the same commit that failed smoke tests last time,
# skip deployment and wait for a new commit to arrive.
BLOCKED_COMMIT=$(cat "$STATE_DIR/blocked_commit" 2>/dev/null || echo "")
if [ "$REMOTE_COMMIT" = "$BLOCKED_COMMIT" ]; then
    echo "Commit $REMOTE_COMMIT is blocked (failed smoke tests). Waiting for a new commit."
    exit 0
fi

# ── Up-to-date check ─────────────────────────────────────────────────────────
if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    echo "Staging is up to date. No changes to deploy."
    exit 0
fi

echo "New commit detected: $REMOTE_COMMIT. Deploying to staging..."

# Clear any stale block now that a new commit has arrived
rm -f "$STATE_DIR/blocked_commit"

# ── Deploy new commit to staging ─────────────────────────────────────────────
if [[ $(git status --porcelain) ]]; then
    echo "Warning: Uncommitted local changes found. Stashing before deploy."
    git stash
fi

git reset --hard "$REMOTE_COMMIT"

# Only rebuild static assets if JS or CSS files changed between commits.
if git diff --name-only "$LOCAL_COMMIT" "$REMOTE_COMMIT" -- static/js/ static/css/ | grep -qE '\.(js|css)$'; then
    echo "Static assets changed — building..."
    bash "$REPO_DIR/scripts/build_assets.sh" || echo "Warning: asset build failed (continuing)"
else
    echo "Static assets unchanged — skipping build."
fi

echo "Installing/updating Python dependencies..."
"$VENV_DIR/bin/pip" install --require-hashes -r "$REPO_DIR/requirements.lock" \
    || { echo "ERROR: pip install failed — hash mismatch or missing package. Aborting."; exit 1; }

echo "Regenerating database.py from template..."
/usr/bin/cp database_template.py database.py
/usr/bin/sed -i "s/the_minesweeper_user/$DB_USER/g" database.py
/usr/bin/sed -i "s/the_password/$DB_PASS/g" database.py
/usr/bin/sed -i "s/the_db_name/$DB_NAME/g" database.py

echo "Restarting staging service..."
sudo systemctl restart "$SERVICE_NAME" || { echo "Error: Failed to restart staging service"; exit 1; }

# Wait for Uvicorn to be ready before running smoke tests (up to 60s)
READY=0
for i in $(seq 1 20); do
    if curl -s --max-time 3 http://127.0.0.1:8002/health | grep -q '"status"'; then
        READY=1
        break
    fi
    sleep 3
done
if [ "$READY" = "0" ]; then
    echo "ERROR: Staging did not become healthy within 60s after restart. Aborting smoke tests."
    exit 1
fi
echo "Staging service is up. Running smoke tests..."

# ── Smoke tests ───────────────────────────────────────────────────────────────
# Tests run against staging's Uvicorn port directly (bypasses Apache).
# smoke_test returns 1 on failure so the caller can collect results without
# aborting the whole script mid-run.
SMOKE_FAILED=0

smoke_test() {
    local label="$1"
    local path="$2"
    local expect="$3"   # optional string that must appear in body

    local RESP
    RESP=$(curl -s --max-time 15 \
        -w "\n__HTTP_STATUS__%{http_code}" \
        "http://127.0.0.1:8002${path}")
    local HTTP_CODE
    HTTP_CODE=$(echo "$RESP" | grep '__HTTP_STATUS__' | sed 's/__HTTP_STATUS__//')
    local BODY
    BODY=$(echo "$RESP" | grep -v '__HTTP_STATUS__')

    if [ "$HTTP_CODE" != "200" ]; then
        echo "  FAIL: $label ($path) — HTTP $HTTP_CODE"
        return 1
    fi
    if echo "$BODY" | grep -qi "internal server error\|traceback\|templateassertionerror\|jinja2.exceptions"; then
        echo "  FAIL: $label ($path) — server error in response body"
        return 1
    fi
    if [ -n "$expect" ] && ! echo "$BODY" | grep -qi "$expect"; then
        echo "  FAIL: $label ($path) — expected '$expect' not found in body"
        return 1
    fi
    echo "  PASS: $label ($path)"
    return 0
}

smoke_test "Home"     "/"         "minesweeper" || SMOKE_FAILED=1
smoke_test "PvP"      "/pvp"      "PvP Minesweeper" || SMOKE_FAILED=1
smoke_test "Duel"     "/duel"     "Minesweeper" || SMOKE_FAILED=1
smoke_test "Tentaizu" "/tentaizu" "Tentaizu" || SMOKE_FAILED=1

# ── Handle smoke test outcome ─────────────────────────────────────────────────
if [ "$SMOKE_FAILED" = "1" ]; then
    echo "Smoke tests FAILED for commit $REMOTE_COMMIT."

    # Record this commit as blocked so future cron runs skip it
    echo "$REMOTE_COMMIT" > "$STATE_DIR/blocked_commit"

    # Revert staging to the last commit that passed tests.
    # Fall back to prod's current HEAD if no last_good_commit file exists yet.
    REVERT_TO=$(cat "$STATE_DIR/last_good_commit" 2>/dev/null \
        || git -C "$PROD_REPO_DIR" rev-parse HEAD 2>/dev/null \
        || echo "")

    if [ -z "$REVERT_TO" ]; then
        echo "WARNING: No revert target found. Staging left on failed commit $REMOTE_COMMIT."
        exit 1
    fi

    echo "Reverting staging to last known good commit: $REVERT_TO..."
    git reset --hard "$REVERT_TO"
    bash "$REPO_DIR/scripts/build_assets.sh" || echo "Warning: asset build failed during revert"
    sudo systemctl restart "$SERVICE_NAME" \
        || echo "Warning: failed to restart staging service after revert"
    echo "Staging reverted to $REVERT_TO. Blocked commit: $REMOTE_COMMIT."
    echo "Deploy to production will not occur. Waiting for a new commit."
    exit 0
fi

# ── All tests passed ──────────────────────────────────────────────────────────
echo "$REMOTE_COMMIT" > "$STATE_DIR/last_good_commit"
echo "All smoke tests passed. Commit $REMOTE_COMMIT is the deploy candidate for production."
