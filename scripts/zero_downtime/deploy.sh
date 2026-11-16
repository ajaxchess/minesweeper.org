#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh — zero-downtime production deploy of the minesweeper.org website
# (F-ZERO-DOWNTIME; design: docs/features/ZeroDowntimeDeploy.md;
#  operations: docs/zero-downtime-deploy-runbook.md)
#
# Two copies of the site, blue (port 8010) and green (8011), sit behind an Apache
# balancer. A deploy updates the idle copy, starts it, checks it, then stops the
# live copy; Apache sends each request to whichever copy is up. PvP (port 8050)
# runs from its own copy and restarts only when the deploy affects it.
#
# Run as ubuntu (cron every 5 minutes):
#   */5 * * * * /home/ubuntu/minesweeper/scripts/zero_downtime/deploy.sh >> /tmp/minesweeper-deploy.log 2>&1
#
#   deploy.sh             deploy the commit staging approved (minesweeper_last_good_commit)
#   deploy.sh --force     deploy origin/main now, skipping the staging gate and any block
#   deploy.sh --rollback  switch back to the previous deploy and block the current one
#   deploy.sh --status    show which copy serves which commit; changes nothing
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8

# Resolve our own directory first: this file lives in the live copy, which the
# deploy never modifies (only the idle copy is checked out).
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
# shellcheck source=lib.sh
source "$HERE/lib.sh"

MODE=deploy
for arg in "$@"; do
    case "$arg" in
        --force)    MODE=force ;;
        --rollback) MODE=rollback ;;
        --status)   MODE=status ;;
        *) echo "Usage: $0 [--force | --rollback | --status]"; exit 2 ;;
    esac
done

if [ "$(id -u)" -eq 0 ]; then
    echo "Error: run as ubuntu, not root."
    exit 1
fi

LIVE="$(live_color)" || { log "ERROR: $LIVE_LINK does not point at minesweeper-blue or minesweeper-green. See the runbook."; exit 1; }
IDLE="$(other_color "$LIVE")"
LIVE_DIR="$(color_dir "$LIVE")";  LIVE_PORT="$(port_for "$LIVE")"
IDLE_DIR="$(color_dir "$IDLE")";  IDLE_PORT="$(port_for "$IDLE")"
LIVE_COMMIT="$(commit_of "$LIVE_DIR")"

if [ "$MODE" = status ]; then
    echo "live copy:   $LIVE (port $LIVE_PORT)  checked out $LIVE_COMMIT  /health: $(health_commit "$LIVE_PORT" || true)"
    echo "idle copy:   $IDLE (port $IDLE_PORT)  checked out $(commit_of "$IDLE_DIR")  /health: $(health_commit "$IDLE_PORT" || echo stopped)"
    echo "pvp:         checked out $(commit_of "$PVP_DIR")  /health: $(health_commit "$PVP_PORT" || true)"
    echo "last good:   $(cat "$LAST_GOOD_FILE" 2>/dev/null || echo none)"
    echo "blocked:     $(cat "$BLOCKED_FILE" 2>/dev/null || echo none)"
    echo "alert:       $( [ -f "$ALERT_FILE" ] && echo "yes — $ALERT_FILE" || echo none)"
    exit 0
fi

# One deploy at a time, including the 5-minute watch; the next cron tick skips.
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    log "Another deploy is running. Skipping."
    exit 0
fi

# Keep this run's output for the /admin banner.
RUN_LOG="$(mktemp /tmp/minesweeper-deploy-run.XXXXXX)"
trap 'rm -f "$RUN_LOG"' EXIT
exec > >(tee -a "$RUN_LOG") 2>&1

# ── Rollback by hand ──────────────────────────────────────────────────────────
if [ "$MODE" = rollback ]; then
    PREVIOUS="$(commit_of "$IDLE_DIR")"
    # After a failed deploy or an automatic rollback the idle copy holds the bad commit.
    if [ "$PREVIOUS" = "$(cat "$BLOCKED_FILE" 2>/dev/null || true)" ]; then
        log "Refusing: the $IDLE copy holds $PREVIOUS, which is blocked (it failed or was rolled back)."
        log "$LIVE still serves $LIVE_COMMIT. To move to another commit, use deploy.sh --force or wait for staging."
        exit 1
    fi
    log "Rolling back: $LIVE ($LIVE_COMMIT) → $IDLE ($PREVIOUS)."
    cpu_weight "$IDLE" "$CPU_WEIGHT_SERVING"
    start_web "$IDLE"
    if ! wait_healthy "$IDLE_PORT" "$PREVIOUS"; then
        stop_web "$IDLE"
        log "ERROR: $IDLE did not come up on $PREVIOUS. Nothing changed; $LIVE still serves $LIVE_COMMIT."
        exit 1
    fi
    sleep "$SETTLE_SECONDS"
    stop_web "$LIVE"
    make_live "$IDLE"
    if [ "$PREVIOUS" = "$LIVE_COMMIT" ]; then
        # Both copies on the same commit: a plain switch (used to test the setup).
        log "Switched to $IDLE; both copies are on $PREVIOUS, so nothing is blocked."
        exit 0
    fi
    block_commit "$LIVE_COMMIT"
    if [ "$(commit_of "$PVP_DIR")" = "$LIVE_COMMIT" ]; then
        pvp_update "$PREVIOUS" || raise_alert pvp_update_failed "PvP could not be rolled back to $PREVIOUS." "$LIVE_COMMIT" "$PREVIOUS"
    fi
    raise_alert manual_rollback "Rolled back by hand from $LIVE_COMMIT. That commit is blocked until a newer one passes staging." "$LIVE_COMMIT" "$PREVIOUS"
    log "Rollback complete: $IDLE serves $PREVIOUS."
    exit 0
fi

# ── What to deploy ────────────────────────────────────────────────────────────
git -C "$IDLE_DIR" fetch --quiet origin || log "Warning: git fetch failed."
if [ "$MODE" = force ]; then
    TARGET="$(git -C "$IDLE_DIR" rev-parse origin/main)"
    log "--force: deploying origin/main ($TARGET), skipping the staging gate."
    echo "$TARGET" > "$LAST_GOOD_FILE"
else
    TARGET="$(cat "$LAST_GOOD_FILE" 2>/dev/null || true)"
    [ -n "$TARGET" ] || { log "No staging-approved commit yet ($LAST_GOOD_FILE). Nothing to deploy."; exit 0; }
fi

if [ "$TARGET" = "$LIVE_COMMIT" ]; then
    echo "Production is already on last good commit $TARGET. Nothing to deploy."
    exit 0
fi
if [ "$MODE" != force ] && [ "$TARGET" = "$(cat "$BLOCKED_FILE" 2>/dev/null || true)" ]; then
    echo "Commit $TARGET is blocked in production (failed or rolled back). Waiting for a newer commit."
    exit 0
fi

log "Deploying $TARGET to $IDLE (port $IDLE_PORT). Live: $LIVE (port $LIVE_PORT) on $LIVE_COMMIT."

# ── 1. Prepare the idle copy ──────────────────────────────────────────────────
if ! prepare_copy "$IDLE_DIR" "$TARGET"; then
    # Not blocked: install failures are often transient (network). Retried next tick.
    raise_alert install_failed "Could not prepare $TARGET in the $IDLE copy. Production is unchanged." "$TARGET" "$LIVE_COMMIT"
    exit 1
fi

# ── 2. Start it and check it before it takes traffic ──────────────────────────
cpu_weight "$IDLE" "$CPU_WEIGHT_LOADING"
start_web "$IDLE" || log "Warning: systemctl start reported an error; checking health anyway."
if ! wait_healthy "$IDLE_PORT" "$TARGET" || ! website_smoke_tests "$IDLE_PORT"; then
    stop_web "$IDLE"
    block_commit "$TARGET"
    raise_alert health_check_failed "$TARGET did not pass its health check or smoke tests in the $IDLE copy. It never took traffic." "$TARGET" "$LIVE_COMMIT"
    log "Deploy aborted. $LIVE still serves $LIVE_COMMIT."
    exit 1
fi
cpu_weight "$IDLE" "$CPU_WEIGHT_SERVING"

# ── 3. Switch ─────────────────────────────────────────────────────────────────
# For a few seconds both copies serve (accepted, decision 2). Stopping the live
# copy closes its port first, so Apache sends everything to the new one.
sleep "$SETTLE_SECONDS"
SWITCHED_AT="$(date +%s)"
stop_web "$LIVE"
make_live "$IDLE"
log "Switched: $IDLE now serves $TARGET."

# ── 4. PvP, only if this deploy affects it ────────────────────────────────────
PVP_COMMIT="$(commit_of "$PVP_DIR")"
PVP_RESTARTED=0
if [ "$PVP_COMMIT" != "$TARGET" ]; then
    if CHANGED="$(git -C "$IDLE_DIR" diff --name-only --no-renames "$PVP_COMMIT" "$TARGET")"; then
        printf '%s\n' "$CHANGED" | python3 "$TOOLS" pvp-affected --old-tree "$PVP_DIR" --new-tree "$IDLE_DIR"
        PVP_CHECK=$?
    else
        log "Could not list the changes since PvP's commit; restarting PvP to be safe."
        PVP_CHECK=1
    fi
    case $PVP_CHECK in
        10) log "PvP left on $PVP_COMMIT." ;;
        *)  if pvp_update "$TARGET"; then
                PVP_RESTARTED=1
            else
                raise_alert pvp_update_failed "PvP could not be updated to $TARGET. The website deploy went ahead." "$TARGET" "$TARGET"
            fi ;;
    esac
fi

# ── 5. Watch, and roll back on errors ─────────────────────────────────────────
if watch_after_switch "$SWITCHED_AT"; then
    log "Deploy of $TARGET complete."
    exit 0
fi

log "Errors crossed the threshold after the switch. Rolling back to $LIVE_COMMIT."
start_web "$LIVE"
if ! wait_healthy "$LIVE_PORT" "$LIVE_COMMIT"; then
    stop_web "$LIVE"
    raise_alert rollback_failed "$TARGET produced errors after the switch, and the previous copy ($LIVE_COMMIT) did not come back. $TARGET is still serving. Act now: see the runbook." "$TARGET" "$TARGET"
    exit 1
fi
stop_web "$IDLE"
make_live "$LIVE"
if [ "$PVP_RESTARTED" = 1 ]; then
    pvp_update "$PVP_COMMIT" || log "ERROR: PvP could not be rolled back to $PVP_COMMIT."
fi
block_commit "$TARGET"
raise_alert rolled_back "$TARGET produced errors after the switch and was rolled back automatically. It is blocked until a newer commit passes staging." "$TARGET" "$LIVE_COMMIT"
log "Rolled back: $LIVE serves $LIVE_COMMIT."
exit 1
