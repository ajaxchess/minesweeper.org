import ast, sys, io, importlib.util
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('translations.py', encoding='utf-8') as f:
    src = f.read()

try:
    ast.parse(src)
    print('PASS: ast.parse OK')
except SyntaxError as e:
    print(f'FAIL syntax: {e}')
    sys.exit(1)

count = src.count('"tmt_bridge"')
print(f'tmt_bridge occurrences: {count} (expect 18)')

spec = importlib.util.spec_from_file_location('t', 'translations.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
T = mod.TRANSLATIONS
langs = list(T.keys())
print(f'Total language sections: {len(langs)} -> {langs}')

missing = [l for l in langs if 'tmt_bridge' not in T[l]]
if missing:
    print(f'MISSING tmt_bridge in: {missing}')
else:
    print('All language sections have tmt_bridge - DONE')
