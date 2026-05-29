"""Show missing keys for a given prefix across all languages."""
import sys, io, importlib.util
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

prefix = sys.argv[1] if len(sys.argv) > 1 else "mj"

spec = importlib.util.spec_from_file_location('t', 'translations.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
T = mod.TRANSLATIONS

en = T['en']
prefix_keys = sorted(k for k in en if k.startswith(prefix + '_') or k == prefix)
langs = [l for l in T if l not in ('en', 'tlh')]

print(f"=== English '{prefix}_*' keys ({len(prefix_keys)} total) ===\n")
for k in prefix_keys:
    print(f"  {k}: {en[k]!r}")

print(f"\n=== Missing by language ===\n")
for lang in langs:
    missing = [k for k in prefix_keys if k not in T[lang]]
    if missing:
        print(f"  {lang}: missing {len(missing)} -> {missing}")
    else:
        print(f"  {lang}: COMPLETE")
