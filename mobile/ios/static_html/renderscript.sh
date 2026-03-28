#!/bin/bash
# renderscript.sh
# Fetches the mobile-detected versions of the how-to-play and strategy pages,
# saves the full pages, then extracts just the <main>...</main> content section
# into standalone HTML files suitable for use in a React Native WebView.
#
# Output files:
#   howtoplay.html         — full page (for reference)
#   strategy.html          — full page (for reference)
#   howtoplay_content.html — standalone content only (use in app)
#   strategy_content.html  — standalone content only (use in app)

MOBILE_UA="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"

echo "Fetching how-to-play..."
/usr/bin/curl -A "$MOBILE_UA" https://minesweeper.org/how-to-play > howtoplay.html

echo "Fetching strategy..."
/usr/bin/curl -A "$MOBILE_UA" https://minesweeper.org/strategy > strategy.html

echo "Extracting content sections..."

# extract_content.py: reads a full rendered page, pulls out <main>...</main>,
# and writes a self-contained HTML file with inline mobile-detection CSS.
/usr/bin/python3 - howtoplay.html howtoplay_content.html <<'PYEOF'
import sys, re

src_path, dst_path = sys.argv[1], sys.argv[2]
html = open(src_path, encoding="utf-8").read()

# Extract the <main ...>...</main> block (non-greedy, dotall)
m = re.search(r'(<main\b[^>]*>.*?</main>)', html, re.DOTALL)
if not m:
    print(f"ERROR: no <main> found in {src_path}", file=sys.stderr)
    sys.exit(1)

main_content = m.group(1)

# Wrap in a minimal self-contained HTML document.
# - Sets is-mobile on <html> immediately so mobile-only content shows.
# - Uses system font stack appropriate for iOS.
# - Keeps the page readable without the site stylesheet.
output = f"""<!DOCTYPE html>
<html lang="en" class="is-mobile">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes" />
  <style>
    body {{
      font-family: -apple-system, Helvetica Neue, sans-serif;
      font-size: 16px;
      line-height: 1.6;
      margin: 0;
      padding: 16px;
      color: #111;
      background: #fff;
    }}
    h1, h2, h3 {{ line-height: 1.3; }}
    code, pre {{ font-family: Menlo, monospace; background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
    ul, ol {{ padding-left: 1.4em; }}
    .is-mobile .desktop-only {{ display: none !important; }}
    html:not(.is-mobile) .mobile-only {{ display: none !important; }}
  </style>
</head>
<body>
{main_content}
</body>
</html>"""

open(dst_path, "w", encoding="utf-8").write(output)
print(f"  wrote {dst_path}")
PYEOF

/usr/bin/python3 - strategy.html strategy_content.html <<'PYEOF'
import sys, re

src_path, dst_path = sys.argv[1], sys.argv[2]
html = open(src_path, encoding="utf-8").read()

m = re.search(r'(<main\b[^>]*>.*?</main>)', html, re.DOTALL)
if not m:
    print(f"ERROR: no <main> found in {src_path}", file=sys.stderr)
    sys.exit(1)

main_content = m.group(1)

output = f"""<!DOCTYPE html>
<html lang="en" class="is-mobile">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes" />
  <style>
    body {{
      font-family: -apple-system, Helvetica Neue, sans-serif;
      font-size: 16px;
      line-height: 1.6;
      margin: 0;
      padding: 16px;
      color: #111;
      background: #fff;
    }}
    h1, h2, h3 {{ line-height: 1.3; }}
    code, pre {{ font-family: Menlo, monospace; background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
    ul, ol {{ padding-left: 1.4em; }}
    .is-mobile .desktop-only {{ display: none !important; }}
    html:not(.is-mobile) .mobile-only {{ display: none !important; }}
  </style>
</head>
<body>
{main_content}
</body>
</html>"""

open(dst_path, "w", encoding="utf-8").write(output)
print(f"  wrote {dst_path}")
PYEOF

echo "Done. App-ready files: howtoplay_content.html, strategy_content.html"

