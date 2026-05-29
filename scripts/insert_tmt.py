"""Insert tmt_* translation keys into translations.py, one language at a time.
Run with: python scripts/insert_tmt.py <lang>
e.g.: python scripts/insert_tmt.py en
"""
import ast, sys, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANS = os.path.join(REPO, "translations.py")

def esc(s):
    """Escape for Python double-quoted string literal."""
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    return s

def build_block(keys):
    lines = []
    for k, v in keys.items():
        lines.append(f'        "{k}": "{esc(v)}",')
    return "\n".join(lines) + "\n"

# ── translations ─────────────────────────────────────────────────────────────

LANGS = {}

LANGS["en"] = {
    "tmt_bridge": "A daily logic puzzle — pick a difficulty and let the numbers guide you.",
    "tmt_my_history": "My History",
    "tmt_stat_mines": "Mines remaining",
    "tmt_stat_time": "Time elapsed",
    "tmt_overlay_solved": "🎉 Puzzle Solved!",
    "tmt_retry": "🔄 Retry",
    "tmt_new_random": "🎲 New Random",
    "tmt_start_hint": "Click any cell to start &middot; <strong>Left-click</strong> reveal &middot; <strong>Right-click</strong> flag",
    "tmt_play_hint": "Hover a number to highlight its region &middot; each number counts mines in its <strong>highlighted region</strong>",
    "tmt_lb_today": "🏆 Today's Leaderboard",
    "tmt_about_h2": "About Tametsi",
    "tmt_what_h2": "What Is Tametsi?",
    "tmt_what_p1": "Tametsi is a number-logic puzzle where you locate all hidden mines on a grid using regional number clues — not just adjacent-cell counts.",
    "tmt_what_p2": "Every revealed number tells you how many mines are hidden in a <strong>defined region</strong>. Regions can span the entire board, wrap around edges, or form irregular shapes.",
    "tmt_what_p3": "Every puzzle on this site is guaranteed solvable by pure logic — no guessing required.",
    "tmt_howto_h2": "How to Play Tametsi",
    "tmt_howto_li1": "<strong>Left-click</strong> a cell to reveal it and see its regional mine count.",
    "tmt_howto_li2": "<strong>Right-click</strong> a cell to plant a flag (🚩) on a suspected mine.",
    "tmt_howto_li3": "Hover over any revealed number to highlight the region it counts.",
    "tmt_howto_li4": "Use number clues to deduce which cells are safe and which hide mines.",
    "tmt_howto_li5": "Win by correctly flagging every mine and revealing every safe cell.",
    "tmt_vs_ms_h2": "Tametsi vs. Minesweeper",
    "tmt_vs_ms_li1": "<strong>Regional clues:</strong> Numbers count mines in a defined region, not just the 8 adjacent cells.",
    "tmt_vs_ms_li2": "<strong>No guessing:</strong> Every puzzle is fully logic-solvable — no 50/50 guesses.",
    "tmt_vs_ms_li3": "<strong>Irregular regions:</strong> Clue regions can be any shape, not a fixed 3×3 neighbourhood.",
    "tmt_vs_ms_li4": "<strong>Wrapping boards:</strong> Some grids have edges that connect, opening new deduction paths.",
    "tmt_vs_ms_li5": "<strong>Fresh daily puzzle:</strong> A new guaranteed-solvable challenge every day at midnight UTC.",
    "tmt_vs_tz_h2": "Tametsi vs. Tentaizu",
    "tmt_vs_tz_intro": 'Both Tametsi and <a href="/tentaizu">Tentaizu</a> are regional mine-finding puzzles, but differ in key ways:',
    "tmt_vs_tz_li1": "<strong>Grid size:</strong> Tametsi uses larger multi-row grids; Tentaizu uses a compact 7×7 grid.",
    "tmt_vs_tz_li2": "<strong>Mine count:</strong> Tametsi has many mines across a large board; Tentaizu hides exactly 10.",
    "tmt_vs_tz_li3": "<strong>Difficulty tiers:</strong> Tametsi offers Beginner, Intermediate, and Expert modes.",
    "tmt_vs_tz_li4": "<strong>Reveal vs. cycle:</strong> In Tametsi you reveal cells; in Tentaizu you cycle cells through states.",
    "tmt_strategy_h2": "Tametsi Strategy Tips",
    "tmt_strategy_li1": "<strong>Start with fully constrained regions.</strong> If a region's mine count equals its hidden-cell count, flag them all.",
    "tmt_strategy_li2": "<strong>Spot zero regions.</strong> A region showing 0 means every hidden cell in it is safe — reveal them all.",
    "tmt_strategy_li3": "<strong>Subtract overlapping regions.</strong> The difference in counts between overlapping regions constrains their unique cells.",
    "tmt_strategy_li4": "<strong>Hover to visualise.</strong> Hover any number to see its region and find overlaps with neighbours.",
    "tmt_strategy_li5": "<strong>Flag early.</strong> Confirmed mines flagged promptly shrink the unknowns in every overlapping region.",
    "tmt_strategy_li6": "<strong>Work inward.</strong> Smaller edge regions often yield the first sure deductions.",
}

# ── insertion logic ───────────────────────────────────────────────────────────

def insert_lang(lang):
    with open(TRANS, encoding="utf-8") as f:
        lines = f.readlines()

    # Find the language section boundaries
    section_starts = {}
    for i, line in enumerate(lines):
        import re
        m = re.match(r'\s*"([a-z\-]+)"\s*:\s*\{', line)
        if m:
            section_starts[m.group(1)] = i

    if lang not in section_starts:
        print(f"ERROR: language '{lang}' not found in {TRANS}")
        return False

    # Section range
    langs_list = list(section_starts.keys())
    lang_idx = langs_list.index(lang)
    section_start = section_starts[lang]
    section_end = section_starts[langs_list[lang_idx + 1]] if lang_idx + 1 < len(langs_list) else len(lines)

    # Find tametsi_history_h1 within this section (first occurrence)
    insert_after = None
    for i in range(section_start, section_end):
        if "tametsi_history_h1" in lines[i]:
            insert_after = i
            break

    if insert_after is None:
        print(f"ERROR: tametsi_history_h1 not found in '{lang}' section")
        return False

    # Check not already inserted
    if insert_after + 1 < len(lines) and "tmt_bridge" in lines[insert_after + 1]:
        print(f"SKIP: tmt_bridge already present after tametsi_history_h1 in '{lang}'")
        return True

    block = build_block(LANGS[lang])
    new_lines = lines[:insert_after + 1] + [block] + lines[insert_after + 1:]

    new_src = "".join(new_lines)
    try:
        ast.parse(new_src)
    except SyntaxError as e:
        print(f"SYNTAX ERROR after inserting '{lang}': {e}")
        return False

    with open(TRANS, "w", encoding="utf-8") as f:
        f.write(new_src)
    print(f"OK: inserted {len(LANGS[lang])} keys for '{lang}' after line {insert_after + 1}")
    return True

if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else "en"
    ok = insert_lang(lang)
    sys.exit(0 if ok else 1)
