#!/bin/bash
# build_assets.sh — Minify JS and CSS static assets after git pull.
# Run from the repo root, or called by the deploy script.

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
JS_DIR="$REPO_DIR/static/js"
CSS_DIR="$REPO_DIR/static/css"

echo "=== Building assets ==="

if ! command -v npx &>/dev/null; then
    echo "  [ERROR] npx not found — skipping asset minification"
    exit 1
fi

# Minify each JS file in place
JS_FILES=(minesweeper.js quests.js duel.js rush.js tentaizu.js tentaizu_easy.js cylinder.js toroid.js replay.js mosaic.js)
for f in "${JS_FILES[@]}"; do
    src="$JS_DIR/$f"
    if [ -f "$src" ]; then
        npx terser "$src" --compress --mangle --output "$src" 2>/dev/null \
            && echo "  Minified JS: $f" \
            || echo "  [WARN] Failed to minify: $f"
    fi
done

# Minify CSS in place
CSS_FILE="$CSS_DIR/style.css"
if [ -f "$CSS_FILE" ]; then
    npx csso-cli "$CSS_FILE" --output "$CSS_FILE" 2>/dev/null \
        && echo "  Minified CSS: style.css" \
        || echo "  [WARN] Failed to minify: style.css"
fi

echo "=== Build complete ==="
