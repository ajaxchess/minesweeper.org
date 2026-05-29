import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
with open('translations.py', encoding='utf-8') as f:
    lines = f.readlines()
targets = [346, 3026, 4426, 5737, 7021, 8225, 9453, 10766, 12074, 13461, 14714, 15929, 16852, 17143, 18371, 19623, 20904, 22251, 22721]
for t in targets:
    idx = t - 1
    for i in range(idx, max(0, idx-400), -1):
        line = lines[i]
        if 'TRANSLATIONS[' in line:
            print(f'Line {t}: {line.rstrip()}')
            break
