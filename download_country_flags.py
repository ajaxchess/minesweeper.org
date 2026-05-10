"""
download_country_flags.py — Download 40px-wide flag PNGs for profile choices.

Run once from the repo root:
    python download_country_flags.py

Source:  https://flagcdn.com  (free, high quality, ISO 3166-1 alpha-2 codes
         plus supported region codes such as gb-eng, gb-sct, gb-wls, gb-nir)
Size:    w40  — 40 px wide, proportional height (~27 px for most flags)
Output:  static/img/country-flags/<code>.png

Skips any file that already exists, so safe to re-run after adding new countries.
"""

import os
import time
import requests
from countries import COUNTRIES

OUT = "static/img/country-flags"
os.makedirs(OUT, exist_ok=True)

BASE_URL = "https://flagcdn.com/w40/{code}.png"

ok, skipped, failed = [], [], []

for code, name in COUNTRIES:
    path = f"{OUT}/{code}.png"

    if os.path.exists(path):
        skipped.append(code)
        continue

    url = BASE_URL.format(code=code)
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"  ok     {code:6}  {name}")
            ok.append(code)
        else:
            print(f"  MISS   {code:6}  {name}  (HTTP {r.status_code})")
            failed.append((code, name, r.status_code))
    except Exception as exc:
        print(f"  ERR    {code:6}  {name}  ({exc})")
        failed.append((code, name, str(exc)))

    time.sleep(0.06)  # ~16 req/s — polite to CDN

print(f"\n{'='*50}")
print(f"Downloaded : {len(ok)}")
print(f"Skipped    : {len(skipped)}  (already existed)")
if failed:
    print(f"Failed     : {len(failed)}")
    for code, name, reason in failed:
        print(f"  {code:6}  {name}  — {reason}")
else:
    print("Failed     : 0")
print(f"Total flags: {len(os.listdir(OUT))}")
