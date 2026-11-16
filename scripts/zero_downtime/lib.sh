# shellcheck shell=bash
# lib.sh — shared by deploy.sh and pvp_catchup.sh (F-ZERO-DOWNTIME).
# Layout and reasoning: intent/ZeroDowntimeDeploy.md, docs/zero-downtime-deploy-runbook.md.

BASE="${MS_ZD_BASE:-/home/ubuntu}"
LIVE_LINK="$BASE/minesweeper"                  # symlink → minesweeper-blue | minesweeper-green
SHARED_DIR="$BASE/minesweeper-shared"          # .env, uploads, hand-placed files
PVP_DIR="$BASE/minesweeper-pvp"
STATE_DIR="$BASE/deploy_state"
LAST_GOOD_FILE="$STATE_DIR/minesweeper_last_good_commit"      # written by the staging gate
BLOCKED_FILE="$STATE_DIR/minesweeper_prod_blocked_commit"     # failed or rolled back in production
ALERT_FILE="$STATE_DIR/minesweeper_deploy_alert.json"         # the /admin banner
LOCK_FILE="${MS_ZD_LOCK:-/tmp/minesweeper_zd_deploy.lock}"                         # lock only
APACHE_LOG="${MS_ZD_APACHE_LOG:-/var/log/apache2/minesweeper.org-ssl-access.log}"
PVP_SERVICE="minesweeper-pvp"
PVP_PORT="${MS_ZD_PVP_PORT:-8050}"
HEALTH_TIMEOUT="${MS_ZD_HEALTH_TIMEOUT:-150}"   # seconds for a copy to load and answer (normally ~40)
WATCH_SECONDS="${MS_ZD_WATCH_SECONDS:-300}"     # automatic-rollback window after a switch
WATCH_INTERVAL="${MS_ZD_WATCH_INTERVAL:-30}"
# After the new copy passes its checks, both copies serve this long before the old
# one stops. Apache retries a member that refused connections only every 5 s
# (retry=5), so this lets it see the new copy as healthy first.
SETTLE_SECONDS="${MS_ZD_SETTLE_SECONDS:-6}"
# The MS_ZD_* overrides exist for tests/test_zero_downtime_deploy.py; production uses the defaults.
CPU_WEIGHT_LOADING=20     # while a new copy loads, live traffic keeps most of the CPU
CPU_WEIGHT_SERVING=100

TOOLS="$(dirname "${BASH_SOURCE[0]}")/deploy_tools.py"

log() { echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') $*"; }

port_for() {
    case "$1" in
        blue)  echo "${MS_ZD_BLUE_PORT:-8010}" ;;
        green) echo "${MS_ZD_GREEN_PORT:-8011}" ;;
        *)     return 1 ;;
    esac
}

other_color() { [ "$1" = blue ] && echo green || echo blue; }
color_dir()   { echo "$BASE/minesweeper-$1"; }
service_for() { echo "minesweeper-web@$1"; }

# The copy the live symlink points at: blue or green.
live_color() {
    local target
    target="$(readlink "$LIVE_LINK" 2>/dev/null)" || return 1
    case "$(basename "$target")" in
        minesweeper-blue)  echo blue ;;
        minesweeper-green) echo green ;;
        *) return 1 ;;
    esac
}

commit_of() { git -C "$1" rev-parse HEAD 2>/dev/null; }

# The commit a running copy reports on /health (localhost only), or nothing.
health_commit() {
    curl -s --max-time 3 "http://127.0.0.1:$1/health" 2>/dev/null \
        | python3 -c 'import json,sys; print(json.load(sys.stdin).get("commit",""))' 2>/dev/null
}

# Wait until the copy on PORT reports COMMIT, up to HEALTH_TIMEOUT seconds.
wait_healthy() {
    local port="$1" commit="$2" waited=0
    while [ "$waited" -lt "$HEALTH_TIMEOUT" ]; do
        [ "$(health_commit "$port")" = "$commit" ] && return 0
        sleep 3
        waited=$((waited + 3))
    done
    return 1
}

# Same checks as the staging gate's website smoke tests, against one port.
smoke_test() {
    local label="$1" path="$2" expect="$3" port="$4" body code result
    body="$(mktemp)"
    code="$(curl -s --max-time 15 --compressed -o "$body" -w '%{http_code}' "http://127.0.0.1:${port}${path}")"
    if [ "$code" != "200" ]; then
        log "  FAIL: $label ($path) — HTTP $code"
        rm -f "$body"
        return 1
    fi
    result="$(python3 - "$body" "$expect" <<'PYEOF'
import sys
body = open(sys.argv[1], 'rb').read().lower()
expect = sys.argv[2].lower().encode()
errors = [b'internal server error', b'traceback', b'templateassertionerror', b'jinja2.exceptions']
print('SERVER_ERROR' if any(e in body for e in errors) else 'EXPECT_FAIL' if expect not in body else 'PASS')
PYEOF
)"
    rm -f "$body"
    if [ "$result" != "PASS" ]; then
        log "  FAIL: $label ($path) — $result"
        return 1
    fi
    log "  PASS: $label ($path)"
}

website_smoke_tests() {
    local port="$1" failed=0
    smoke_test "Home"               "/"                                           "minesweeper"   "$port" || failed=1
    smoke_test "Tentaizu"           "/tentaizu"                                   "Tentaizu"      "$port" || failed=1
    smoke_test "Numbers Match page" "/numbers-match"                              "Numbers Match" "$port" || failed=1
    smoke_test "Numbers Match API"  "/api/numbers-match-board/$(date +%Y-%m-%d)" "board_data"    "$port" || failed=1
    return "$failed"
}

# Check out COMMIT in a copy, install its dependencies and generate database.py.
# Untracked files (the shared symlinks, uploads) are left alone.
prepare_copy() {
    local dir="$1" commit="$2"
    git -C "$dir" fetch --quiet origin || log "Warning: git fetch failed in $dir; using local objects."
    git -C "$dir" checkout --quiet --force --detach "$commit" || { log "ERROR: cannot check out $commit in $dir"; return 1; }
    log "Installing dependencies in $dir (requirements.lock, hash-checked)..."
    "$dir/venv/bin/pip" install --quiet --require-hashes -r "$dir/requirements.lock" \
        || { log "ERROR: pip install failed in $dir"; return 1; }
    generate_database_py "$dir"
}

# database.py = database_template.py + credentials from the shared .env.
# Literal replacement in Python, not sed: a password containing / & or \ would
# silently corrupt a sed replacement.
generate_database_py() {
    local dir="$1"
    (
        set -a
        # shellcheck disable=SC1091
        source "$SHARED_DIR/.env"
        set +a
        cp "$dir/database_template.py" "$dir/database.py"
        DB_USER="$DB_USER" DB_PASS="$DB_PASS" DB_NAME="$DB_NAME" python3 - "$dir/database.py" <<'PYEOF'
import os, sys
from pathlib import Path
p = Path(sys.argv[1])
s = p.read_text()
for placeholder, var in (("the_minesweeper_user", "DB_USER"), ("the_password", "DB_PASS"), ("the_db_name", "DB_NAME")):
    s = s.replace(placeholder, os.environ[var])
p.write_text(s)
PYEOF
    ) || { log "ERROR: could not generate database.py in $dir"; return 1; }
}

start_web()  { sudo -n systemctl start "$(service_for "$1")"; }
# Graceful: gunicorn closes its socket first (Apache fails over at once), then gives
# in-flight requests up to 30 s.
stop_web()   { sudo -n systemctl stop "$(service_for "$1")"; }
cpu_weight() { sudo -n systemctl set-property --runtime "$(service_for "$1")" "CPUWeight=$2" >/dev/null 2>&1 || true; }

# Point the live symlink at COLOR (atomic rename), and make COLOR the copy that
# starts at boot. Cron jobs and Apache's /static alias go through the symlink.
make_live() {
    local color="$1" other
    other="$(other_color "$color")"
    ln -sfn "minesweeper-$color" "$LIVE_LINK.new" && mv -Tf "$LIVE_LINK.new" "$LIVE_LINK" \
        || { log "ERROR: could not repoint $LIVE_LINK"; return 1; }
    sudo -n systemctl enable --quiet "$(service_for "$color")" 2>/dev/null || true
    sudo -n systemctl disable --quiet "$(service_for "$other")" 2>/dev/null || true
}

# Restart PvP on COMMIT. PvP is stopped before its copy changes, so a running PvP
# process never reads files from another commit.
pvp_update() {
    local commit="$1"
    log "Updating PvP to $commit (duels in progress are interrupted)..."
    sudo -n systemctl stop "$PVP_SERVICE"
    if ! prepare_copy "$PVP_DIR" "$commit"; then
        log "ERROR: PvP copy update failed; starting PvP on whatever is checked out."
        sudo -n systemctl start "$PVP_SERVICE"
        return 1
    fi
    sudo -n systemctl start "$PVP_SERVICE" || return 1
    wait_healthy "$PVP_PORT" "$commit" || { log "ERROR: PvP did not report $commit on /health"; return 1; }
    log "PvP is on $commit."
}

block_commit() { echo "$1" > "$BLOCKED_FILE"; log "Blocked $1 for production (deploy.sh --force overrides)."; }

# Raise the /admin banner. RUN_LOG is this run's output.
raise_alert() {
    local kind="$1" reason="$2" commit="${3:-}" serving="${4:-}"
    python3 "$TOOLS" write-alert --path "$ALERT_FILE" --kind "$kind" --reason "$reason" \
        --commit "$commit" --serving "$serving" ${RUN_LOG:+--log-file "$RUN_LOG"} \
        || log "Warning: could not write the /admin alert."
}

# The last lines of the access log, including the rotated file in case the log
# rotated during the watch. Each file is read on its own: one missing file must not
# hide the other.
recent_access_log() {
    sudo -n tail -q -n 5000 "$APACHE_LOG.1" 2>/dev/null || true
    sudo -n tail -q -n 5000 "$APACHE_LOG" 2>/dev/null || true
}

# 0 = no rollback needed after WATCH_SECONDS; 1 = errors crossed the threshold.
watch_after_switch() {
    local since="$1" elapsed=0 result
    if ! sudo -n test -r "$APACHE_LOG"; then
        log "Warning: cannot read $APACHE_LOG — automatic rollback is not available for this deploy."
        raise_alert watch_unavailable "Deployed, but the Apache log could not be read, so errors after the switch were not watched." "" ""
        return 0
    fi
    while [ "$elapsed" -lt "$WATCH_SECONDS" ]; do
        sleep "$WATCH_INTERVAL"
        elapsed=$((elapsed + WATCH_INTERVAL))
        if ! result="$(recent_access_log | python3 "$TOOLS" watch-verdict --since "$since")"; then
            log "Warning: could not judge the Apache log at ${elapsed}s."
            continue
        fi
        log "Watch ${elapsed}s: $result"
        case "$result" in
            *'"rollback": true'*) return 1 ;;
        esac
    done
    return 0
}
