#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# pvp_catchup.sh — nightly: bring PvP up to the website's commit (F-ZERO-DOWNTIME,
# docs/features/ZeroDowntimeDeploy.md decision 7). PvP skips deploys that don't affect
# it, so without this it could fall behind indefinitely.
#
# Cron, 4 AM US Central in winter (5 AM in summer; the server runs on UTC):
#   0 10 * * * /home/ubuntu/minesweeper/scripts/zero_downtime/pvp_catchup.sh >> /tmp/minesweeper-deploy.log 2>&1
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
# shellcheck source=lib.sh
source "$HERE/lib.sh"

if [ "$(id -u)" -eq 0 ]; then
    echo "Error: run as ubuntu, not root."
    exit 1
fi

# Never at the same time as a deploy.
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    log "PvP catch-up: a deploy is running. Skipping tonight."
    exit 0
fi

RUN_LOG="$(mktemp /tmp/minesweeper-deploy-run.XXXXXX)"
trap 'rm -f "$RUN_LOG"' EXIT
exec > >(tee -a "$RUN_LOG") 2>&1

LIVE="$(live_color)" || { log "ERROR: $LIVE_LINK does not point at a website copy."; exit 1; }
WEBSITE_COMMIT="$(commit_of "$(color_dir "$LIVE")")"
PVP_COMMIT="$(commit_of "$PVP_DIR")"

if [ "$PVP_COMMIT" = "$WEBSITE_COMMIT" ]; then
    log "PvP catch-up: PvP is already on $WEBSITE_COMMIT."
    exit 0
fi

log "PvP catch-up: PvP is on $PVP_COMMIT, the website on $WEBSITE_COMMIT."
if ! pvp_update "$WEBSITE_COMMIT"; then
    raise_alert pvp_update_failed "The nightly PvP catch-up to $WEBSITE_COMMIT failed. PvP may be down." "$WEBSITE_COMMIT" "$WEBSITE_COMMIT"
    exit 1
fi
