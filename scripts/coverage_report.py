"""Compare translation key coverage across all languages vs English baseline."""
import sys, io, importlib.util
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

spec = importlib.util.spec_from_file_location('t', 'translations.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
T = mod.TRANSLATIONS

en_keys = set(T['en'].keys())
langs = [l for l in T.keys() if l != 'en' and l != 'tlh']

# Group EN keys by prefix
def prefix(k):
    return k.split('_')[0]

all_prefixes = sorted(set(prefix(k) for k in en_keys))

print(f"English baseline: {len(en_keys)} keys\n")
print(f"{'Lang':<10} {'Keys':>6} {'Missing':>8} {'Coverage':>10}")
print("-" * 40)

lang_missing = {}
for lang in langs:
    lang_keys = set(T[lang].keys())
    missing = en_keys - lang_keys
    pct = 100 * len(lang_keys) / len(en_keys)
    print(f"{lang:<10} {len(lang_keys):>6} {len(missing):>8} {pct:>9.1f}%")
    lang_missing[lang] = missing

# Per-prefix breakdown: how many languages are missing each prefix
print("\n\n=== Missing keys by prefix (langs missing ≥1 key in that group) ===\n")
print(f"{'Prefix':<25} {'EN keys':>8} {'Langs missing any':>20}")
print("-" * 60)

prefix_report = []
for p in all_prefixes:
    p_keys = [k for k in en_keys if prefix(k) == p]
    langs_missing_any = [l for l in langs if any(k in lang_missing[l] for k in p_keys)]
    if langs_missing_any:
        prefix_report.append((p, len(p_keys), langs_missing_any))

for p, cnt, missing_langs in sorted(prefix_report, key=lambda x: -len(x[2])):
    print(f"{p:<25} {cnt:>8}    {', '.join(missing_langs)}")

# Detailed: keys missing in 2+ languages
print("\n\n=== Individual keys missing in 3+ languages ===\n")
from collections import Counter
key_miss_count = Counter()
for lang, missing in lang_missing.items():
    for k in missing:
        key_miss_count[k] += 1

for k, count in sorted(key_miss_count.items(), key=lambda x: -x[1]):
    if count >= 3:
        missing_in = [l for l in langs if k in lang_missing[l]]
        print(f"  [{count:>2} langs]  {k}")
