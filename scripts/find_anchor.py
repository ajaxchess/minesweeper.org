import importlib.util, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
spec = importlib.util.spec_from_file_location('t', 'translations.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
T = mod.TRANSLATIONS
langs = [l for l in T if l != 'tlh']
candidates = ['nav_numbers_match', 't2k_daily_h1', 'mj_daily_h1',
              'game_new_game', 'game_left_click', 'game_view_lb', 'game_over']
for c in candidates:
    missing = [l for l in langs if c not in T[l]]
    ok = "GOOD" if not missing else f"missing: {missing}"
    print(f'{c}: {ok}')
