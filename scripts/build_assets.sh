#!/bin/bash
# build_assets.sh — Build minified JS and CSS from static/src/ into the served
# static/js/ and static/css/ trees. Run from the repo root, or called by the
# deploy script.
#
# Sources live in static/src/. The served copies are BUILD OUTPUT and are
# overwritten here — never edit them directly.
# See intent/StaticAssetSourceOfTruth.md (F-ASSETS).

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC_JS="$REPO_DIR/static/src/js"
SRC_CSS="$REPO_DIR/static/src/css"
OUT_JS="$REPO_DIR/static/js"
OUT_CSS="$REPO_DIR/static/css"

echo "=== Building assets ==="

if ! command -v npx &>/dev/null; then
    echo "  [ERROR] npx not found — skipping asset minification"
    exit 1
fi

for src in "$SRC_JS"/*.js; do
    [ -e "$src" ] || continue
    out="$OUT_JS/$(basename "$src")"
    npx --yes terser "$src" --compress --mangle --output "$out" 2>/dev/null \
        && echo "  Minified JS: $(basename "$src")" \
        || echo "  [WARN] Failed to minify: $(basename "$src")"
done

for src in "$SRC_CSS"/*.css; do
    [ -e "$src" ] || continue
    out="$OUT_CSS/$(basename "$src")"
    npx --yes csso-cli "$src" --output "$out" 2>/dev/null \
        && echo "  Minified CSS: $(basename "$src")" \
        || echo "  [WARN] Failed to minify: $(basename "$src")"
done

# NOTE: static/js/goldberg_prebaked.js is generated prebake data with no
# readable source. It is not built here and must not be minified in place.

echo "=== Build complete ==="
