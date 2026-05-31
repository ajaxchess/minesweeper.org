#!/bin/bash

# staging_minesweeper_service_update_and_restart.sh
#
# On-demand staging: only starts the service when there is a new, unvalidated
# commit.  Runs smoke tests, then STOPS the service to free memory.  Writes
# the validated commit SHA to a state file that the production deploy script reads.
#
# Flow:
#   1. Acquire a lock — exit immediately if another run is in progress.
#   2. Fetch origin/main — if no new commit, exit.
#   3. If the new commit is already in last_good_commit, exit (already validated).
#   4. If the new commit matches blocked_commit, exit (already failed).
#   5. Reset to new commit, build assets, install deps, regenerate database.py.
#   6. START the staging service (it is stopped when idle).
#   7. Wait for /health, run smoke tests.
#   8. STOP the service regardless of test outcome.
#   9. On pass: write validated SHA → production deploy will unblock.
#      On fail: write blocked SHA → exit 1.
#
# Recommended cron (runs every 5 minutes):
#   2-57/5 * * * * /home/ubuntu/git/staging.minesweeper.org/scripts/staging_minesweeper_service_update_and_restart.sh >> /tmp/minesweeper_staging_deploy.log 2>&1

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
STATE_DIR="/home/ubuntu/deploy_state"
REPO_DIR="/home/ubuntu/git/staging.minesweeper.org"
VENV_DIR="$REPO_DIR/venv"
SERVICE_NAME="minesweeper-staging"
PORT=8002
source "$REPO_DIR/.env"

# Prevent two cron ticks from running in parallel (tests can take >5 min).
LOCK_FILE="/tmp/minesweeper_staging_deploy.lock"

# ── Root check ────────────────────────────────────────────────────────────────
if [ "$(id -u)" -eq 0 ]; then
    echo "Error: This script must not be run as root. Run as the 'ubuntu' user."
    exit 1
fi

# ── Lock ──────────────────────────────────────────────────────────────────────
if [ -f "$LOCK_FILE" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') Another staging deploy is already running. Skipping."
    exit 0
fi
trap 'rm -f "$LOCK_FILE"' EXIT
touch "$LOCK_FILE"

mkdir -p "$STATE_DIR"

# ── Navigate to repo ──────────────────────────────────────────────────────────
cd "$REPO_DIR" || { echo "Error: REPO_DIR $REPO_DIR not found"; exit 1; }

git fetch origin > /dev/null 2>&1

LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main)

# ── Up-to-date check ─────────────────────────────────────────────────────────
if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') Up to date ($LOCAL_COMMIT). Nothing to do."
    exit 0
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') New commit detected: $LOCAL_COMMIT -> $REMOTE_COMMIT"

# ── Skip if already validated ─────────────────────────────────────────────────
if [ -f "$STATE_DIR/last_good_commit" ] && [ "$(cat "$STATE_DIR/last_good_commit")" = "$REMOTE_COMMIT" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') Commit $REMOTE_COMMIT already validated. Nothing to do."
    exit 0
fi

# ── Skip if already blocked ───────────────────────────────────────────────────
BLOCKED_COMMIT=$(cat "$STATE_DIR/blocked_commit" 2>/dev/null || echo "")
if [ "$REMOTE_COMMIT" = "$BLOCKED_COMMIT" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') Commit $REMOTE_COMMIT is blocked (failed smoke tests). Waiting for a new commit."
    exit 0
fi

# ── Reset to new commit ───────────────────────────────────────────────────────
if [[ $(git status --porcelain) ]]; then
    echo "Warning: uncommitted local changes found — stashing."
    git stash
fi

git reset --hard "$REMOTE_COMMIT"
echo "Reset to $REMOTE_COMMIT complete."

# ── Build static assets ───────────────────────────────────────────────────────
echo "Building static assets..."
bash "$REPO_DIR/scripts/build_assets.sh" || echo "Warning: asset build failed (continuing)"

# ── Update Python dependencies ────────────────────────────────────────────────
echo "Installing/updating Python dependencies..."
"$VENV_DIR/bin/pip" install --require-hashes -r "$REPO_DIR/requirements.lock" \
    || { echo "ERROR: pip install failed — hash mismatch or missing package. Aborting."; exit 1; }

# ── Regenerate database.py from template ─────────────────────────────────────
echo "Regenerating database.py from template..."
/usr/bin/cp database_template.py database.py
/usr/bin/sed -i "s/the_minesweeper_user/$DB_USER/g" database.py
/usr/bin/sed -i "s/the_password/$DB_PASS/g" database.py
/usr/bin/sed -i "s/the_db_name/$DB_NAME/g" database.py

# ── Start the service (it is stopped when idle) ───────────────────────────────
# Use restart rather than start: if a previous run left the service running
# (e.g. on the first transition from always-on staging), restart ensures the
# new code is loaded; if it was already stopped, restart behaves like start.
echo "$(date '+%Y-%m-%d %H:%M:%S') Starting service: $SERVICE_NAME (port $PORT)..."
sudo systemctl restart "$SERVICE_NAME" \
    || { echo "Error: failed to start $SERVICE_NAME"; exit 1; }

# Wait for uvicorn to finish binding the port (up to 60s).
READY=0
for i in $(seq 1 20); do
    if curl -s --max-time 3 --compressed "http://127.0.0.1:${PORT}/health" | grep -aq '"status"'; then
        READY=1
        break
    fi
    sleep 3
done
if [ "$READY" = "0" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') ERROR: Staging did not become healthy within 60s. Stopping and aborting."
    sudo systemctl stop "$SERVICE_NAME"
    exit 1
fi
echo "$(date '+%Y-%m-%d %H:%M:%S') Staging service is up. Running smoke tests..."

# ── Smoke tests ───────────────────────────────────────────────────────────────
# Tests run against staging's Uvicorn port directly (bypasses Apache).
SMOKE_FAILED=0

smoke_test() {
    local label="$1"
    local path="$2"
    local expect="$3"

    local RESP
    RESP=$(curl -s --max-time 15 --compressed \
        -w "\n__HTTP_STATUS__%{http_code}" \
        "http://127.0.0.1:${PORT}${path}")
    local HTTP_CODE
    HTTP_CODE=$(echo "$RESP" | grep -a '__HTTP_STATUS__' | sed 's/__HTTP_STATUS__//')
    local BODY
    BODY=$(echo "$RESP" | grep -av '__HTTP_STATUS__')

    if [ "$HTTP_CODE" != "200" ]; then
        echo "  FAIL: $label ($path) — HTTP $HTTP_CODE"
        echo "        body(100): $(echo "$BODY" | head -c 100)"
        return 1
    fi
    if echo "$BODY" | grep -aqi "internal server error\|traceback\|templateassertionerror\|jinja2.exceptions"; then
        echo "  FAIL: $label ($path) — server error in response body"
        echo "        body(200): $(echo "$BODY" | grep -aim1 "error\|traceback\|exception")"
        return 1
    fi
    if [ -n "$expect" ] && ! echo "$BODY" | grep -aqi "$expect"; then
        echo "  FAIL: $label ($path) — expected '$expect' not found in body"
        echo "        body(300): $(echo "$BODY" | head -c 300)"
        return 1
    fi
    echo "  PASS: $label ($path)"
    return 0
}

smoke_test "Home"               "/"                                           "minesweeper" || SMOKE_FAILED=1
smoke_test "PvP"                "/pvp/bot"                                    "PvP Minesweeper" || SMOKE_FAILED=1
smoke_test "Duel"               "/duel"                                       "Minesweeper" || SMOKE_FAILED=1
smoke_test "Tentaizu"           "/tentaizu"                                   "Tentaizu" || SMOKE_FAILED=1
smoke_test "Numbers Match page" "/numbers-match"                              "Numbers Match" || SMOKE_FAILED=1
smoke_test "Numbers Match API"  "/api/numbers-match-board/$(date +%Y-%m-%d)" "board_data" || SMOKE_FAILED=1

# ── Stop the service to free memory ───────────────────────────────────────────
echo "$(date '+%Y-%m-%d %H:%M:%S') Stopping service: $SERVICE_NAME..."
sudo systemctl stop "$SERVICE_NAME"
echo "Service stopped."

# ── Record result ─────────────────────────────────────────────────────────────
if [ "$SMOKE_FAILED" -eq 0 ]; then
    echo "$REMOTE_COMMIT" > "$STATE_DIR/last_good_commit"
    rm -f "$STATE_DIR/blocked_commit"
    echo "$(date '+%Y-%m-%d %H:%M:%S') ✅ Smoke tests passed. Commit $REMOTE_COMMIT written to last_good_commit."
    echo "$(date '+%Y-%m-%d %H:%M:%S') Production deploy will proceed on its next cron tick."
else
    echo "$REMOTE_COMMIT" > "$STATE_DIR/blocked_commit"
    echo "$(date '+%Y-%m-%d %H:%M:%S') ❌ Smoke tests FAILED for $REMOTE_COMMIT. State file NOT updated."
    echo "$(date '+%Y-%m-%d %H:%M:%S') Production deploy remains blocked until tests pass."
    exit 1
fi
