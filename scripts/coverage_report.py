"""Compare translation key coverage across all languages vs English baseline.
Writes a markdown report to docs/translation-coverage.md.
"""
import sys, io, importlib.util, os
from collections import Counter
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

spec = importlib.util.spec_from_file_location('t', os.path.join(REPO, 'translations.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
T = mod.TRANSLATIONS

en_keys = set(T['en'].keys())
langs = [l for l in T.keys() if l != 'en' and l != 'tlh']

def prefix(k):
    return k.split('_')[0]

all_prefixes = sorted(set(prefix(k) for k in en_keys))

lang_missing = {}
for lang in langs:
    lang_missing[lang] = en_keys - set(T[lang].keys())

# ── console summary ────────────────────────────────────────────────────────────
print(f"English baseline: {len(en_keys)} keys\n")
print(f"{'Lang':<10} {'Keys':>6} {'Missing':>8} {'Coverage':>10}")
print("-" * 40)
for lang in langs:
    keys = len(T[lang])
    missing = len(lang_missing[lang])
    pct = 100 * keys / len(en_keys)
    print(f"{lang:<10} {keys:>6} {missing:>8} {pct:>9.1f}%")

# ── per-prefix breakdown ───────────────────────────────────────────────────────
prefix_report = []
for p in all_prefixes:
    p_keys = [k for k in en_keys if prefix(k) == p]
    missing_langs = [l for l in langs if any(k in lang_missing[l] for k in p_keys)]
    if missing_langs:
        prefix_report.append((p, len(p_keys), missing_langs))

# ── key-level detail ───────────────────────────────────────────────────────────
key_miss_count = Counter()
for lang, missing in lang_missing.items():
    for k in missing:
        key_miss_count[k] += 1

# ── build markdown ─────────────────────────────────────────────────────────────
FLAGS = {
    'eo': '', 'de': '🇩🇪', 'es': '🇪🇸', 'fr': '🇫🇷', 'pt': '🇧🇷',
    'it': '🇮🇹', 'pl': '🇵🇱', 'ru': '🇷🇺', 'uk': '🇺🇦',
    'zh': '🇨🇳', 'zh-hant': '🇹🇼', 'ja': '🇯🇵', 'ko': '🇰🇷',
    'th': '🇹🇭', 'tl': '🇵🇭', 'nl': '🇳🇱', 'pgl': '',
}

lines = []
lines.append(f"# Translation Coverage Report")
lines.append(f"")
lines.append(f"Generated: {date.today()}  ")
lines.append(f"English baseline: **{len(en_keys):,} keys**")
lines.append(f"")
lines.append(f"---")
lines.append(f"")
lines.append(f"## Coverage by Language")
lines.append(f"")
lines.append(f"| Language | Keys | Missing | Coverage |")
lines.append(f"|---|---|---|---|")

# Sort by coverage descending
sorted_langs = sorted(langs, key=lambda l: len(T[l]), reverse=True)
for lang in sorted_langs:
    keys = len(T[lang])
    missing = len(lang_missing[lang])
    pct = 100 * keys / len(en_keys)
    flag = FLAGS.get(lang, '')
    label = f"{flag} `{lang}`" if flag else f"`{lang}`"
    bar = "**" if missing == 0 else ""
    lines.append(f"| {label} | {keys:,} | {missing} | {bar}{pct:.1f}%{bar} |")

lines.append(f"")
lines.append(f"> `tlh` Klingon inherits from `en` automatically and is excluded from this report.")
lines.append(f"")
lines.append(f"---")
lines.append(f"")
lines.append(f"## Gaps by Feature Area")
lines.append(f"")

if prefix_report:
    lines.append(f"| Feature group | Key prefix | EN keys | Langs missing any |")
    lines.append(f"|---|---|---|---|")
    for p, cnt, missing_langs in sorted(prefix_report, key=lambda x: -len(x[2])):
        n = len(missing_langs)
        tag = f"**All {n}**" if n == len(langs) else f"{n} of {len(langs)}"
        lines.append(f"| `{p}_*` | `{p}_*` | {cnt} | {tag} |")
else:
    lines.append(f"_No gaps — all prefixes fully translated across all languages!_")

lines.append(f"")
lines.append(f"---")
lines.append(f"")
lines.append(f"## Individual Keys Missing in 3+ Languages")
lines.append(f"")

top_missing = [(k, c) for k, c in key_miss_count.most_common() if c >= 3]
if top_missing:
    lines.append(f"| Key | Missing from (langs) |")
    lines.append(f"|---|---|")
    for k, count in top_missing:
        missing_in = [l for l in langs if k in lang_missing[l]]
        lines.append(f"| `{k}` | {count} — {', '.join(missing_in)} |")
else:
    lines.append(f"_No keys missing from 3 or more languages._")

lines.append(f"")
lines.append(f"---")
lines.append(f"")
lines.append(f"## Notes")
lines.append(f"")
lines.append(f"- Re-run `scripts/coverage_report.py` after any translation batch to refresh this report.")
lines.append(f"- Use `python scripts/show_missing_prefix.py <prefix>` to see exactly which keys are missing for a given feature group.")
lines.append(f"- Use `python scripts/find_anchor.py` to find a suitable insertion anchor key for a new batch.")

md = "\n".join(lines) + "\n"

out_path = os.path.join(REPO, 'docs', 'translation-coverage.md')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(md)

print(f"\nReport written to {out_path}")
