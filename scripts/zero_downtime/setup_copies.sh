#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# setup_copies.sh — one-time preparation for zero-downtime deploys (F-ZERO-DOWNTIME).
#
# Creates the shared folder and the three copies (blue, green, pvp) as git
# worktrees of the current production checkout, each with its own virtualenv.
# Does NOT touch any running service, systemd unit, Apache or cron, so it is
# safe to run (and re-run) before the cutover. See docs/zero-downtime-deploy-runbook.md.
#
#   scripts/zero_downtime/setup_copies.sh [COMMIT]     (default: the live checkout's HEAD)
#   scripts/zero_downtime/setup_copies.sh --sync-uploads   (copy new uploads again; repeat at switch time)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
# shellcheck source=lib.sh
source "$HERE/lib.sh"

SOURCE_REPO="${SOURCE_REPO:-$BASE/git/minesweeper.org}"   # today's live checkout
[ -d "$SOURCE_REPO/.git" ] || { echo "Error: $SOURCE_REPO is not the production git checkout."; exit 1; }
if [ "$(id -u)" -eq 0 ]; then echo "Error: run as ubuntu, not root."; exit 1; fi

sync_uploads() {
    mkdir -p "$SHARED_DIR/uploads"
    # No --delete: the shared folder is the master copy once the switch is done.
    rsync -a "$SOURCE_REPO/static/uploads/" "$SHARED_DIR/uploads/"
    log "Uploads synced: $(find "$SHARED_DIR/uploads" -type f | wc -l) files in $SHARED_DIR/uploads."
}

if [ "${1:-}" = "--sync-uploads" ]; then
    sync_uploads
    exit 0
fi

COMMIT="${1:-$(git -C "$SOURCE_REPO" rev-parse HEAD)}"
PYTHON="${PYTHON:-$(readlink -f "$SOURCE_REPO/venv/bin/python3")}"
log "Setting up copies on $COMMIT with $PYTHON."

# ── Shared folder ─────────────────────────────────────────────────────────────
mkdir -p "$SHARED_DIR/files"
if [ ! -f "$SHARED_DIR/.env" ]; then
    cp -p "$SOURCE_REPO/.env" "$SHARED_DIR/.env"
    chmod 600 "$SHARED_DIR/.env"
fi
sync_uploads
printf 'MS_WEB_PORT=%s\n' "$(port_for blue)"  > "$SHARED_DIR/web-blue.env"
printf 'MS_WEB_PORT=%s\n' "$(port_for green)" > "$SHARED_DIR/web-green.env"

# Hand-placed, gitignored files (analysis/, static/html/, the résumé in business/, …).
# Generated or per-copy things are left out: each copy has its own.
git -C "$SOURCE_REPO" status --porcelain --ignored \
    | sed -n 's/^!! //p' \
    | grep -v -E '(^|/)(venv|__pycache__|\.pytest_cache|node_modules)(/|$)|\.pyc$|^database\.py$|^\.env$|^mobile/' \
    > "$SHARED_DIR/linked-paths.txt" || true
while IFS= read -r path; do
    path="${path%/}"
    mkdir -p "$(dirname "$SHARED_DIR/files/$path")"
    if [ -d "$SOURCE_REPO/$path" ]; then
        rsync -a "$SOURCE_REPO/$path/" "$SHARED_DIR/files/$path/"
    else
        rsync -a "$SOURCE_REPO/$path" "$SHARED_DIR/files/$path"
    fi
done < "$SHARED_DIR/linked-paths.txt"
log "Shared files: $(wc -l < "$SHARED_DIR/linked-paths.txt") paths (list in $SHARED_DIR/linked-paths.txt)."

# ── The three copies ──────────────────────────────────────────────────────────
for name in blue green pvp; do
    dir="$BASE/minesweeper-$name"
    if [ ! -e "$dir" ]; then
        git -C "$SOURCE_REPO" worktree add --detach "$dir" "$COMMIT"
    fi
    [ -x "$dir/venv/bin/python" ] || "$PYTHON" -m venv "$dir/venv"

    ln -sfn "$SHARED_DIR/.env" "$dir/.env"
    while IFS= read -r path; do
        path="${path%/}"
        if [ -e "$dir/$path" ] && [ ! -L "$dir/$path" ]; then
            log "Warning: $dir/$path exists and is not a link; left alone."
            continue
        fi
        mkdir -p "$(dirname "$dir/$path")"
        ln -sfn "$SHARED_DIR/files/$path" "$dir/$path"
    done < "$SHARED_DIR/linked-paths.txt"

    prepare_copy "$dir" "$COMMIT"
    log "Copy ready: $dir on $(commit_of "$dir")."
done

cat <<EOF

Copies are ready. Nothing is serving from them yet.
Next: the cutover steps in docs/zero-downtime-deploy-runbook.md (units, Apache, switch).
EOF
