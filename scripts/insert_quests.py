# -*- coding: utf-8 -*-
"""Insert missing quest_* and quests_* keys into translations.py.
Anchor: quests_meta_title (present in all languages).
Usage: python scripts/insert_quests.py <lang>
"""
import ast, sys, re, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANS = os.path.join(REPO, "translations.py")
ANCHOR = "quests_meta_title"

def esc(s):
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    return s

def build_block(keys, existing):
    lines = [f'        "{k}": "{esc(v)}",' for k, v in keys.items() if k not in existing]
    return ("\n".join(lines) + "\n") if lines else ""

LANGS = {}

# ── Esperanto ─────────────────────────────────────────────────────────────────
LANGS["eo"] = {
    "quests_title": "Taskoj",
    "quests_subtitle": "Plenumu taskojn por gajni rekompencojn. Progreso estas konservita en via retumilo.",
    "quests_daily_title": "Cxiutaga Tasko",
    "quests_daily_note": "Unu tasko tage, rotacian cxiun 24 horojn.",
    "quests_seasonal_title": "Sezonaj Taskoj",
    "quests_seasonal_note": "Cxiuj tri estas aktivaj dum la tuta monato. Progreso transiras tagon post tago.",
    "quests_rewards_title": "Rekompencoj",
    "quests_rewards_note": "Gajnu ian ajn rekompencon por malaktivigi reklamojn sur cxi tiu aparato.",
    "quests_reward_active": "Rekompenco aktiva:",
    "quests_reward_active_desc": "Reklamoj estas malaktigitaj — dauxrigu!",
    "quests_streak_reward_title": "20-Taga Cxiutaga Tasko-Sinsekvo",
    "quests_streak_reward_desc": "Plenumu vian cxiutagan taskon 20 sinsekvajn tagojn.",
    "quests_season_reward_title": "10 Cxiutagaj Taskoj Cxi-Sezone",
    "quests_season_reward_desc": "Plenumu vian cxiutagan taskon ajnajn 10 tagojn cxi-monate.",
    "quests_og_title": "Minesweeper-Taskoj",
    "quests_og_desc": "Plenumu cxiutagajn kaj monatajn Minesweeper-taskojn. Gajnu 20-tagan sinsekvon aux finu 10 taskojn sezone por malaktivigi reklamojn.",
    "quest_complete": "Plenumita!",
    "quest_unlocked": "Malshlosita!",
    "quest_not_complete": "Ankoraux ne plenumita",
    "quest_play": "Ludi",
    "quest_days": "tagoj",
    "quest_daily_easy_win": "Venku Facilan Minesweeper",
    "quest_daily_rush_5": "Forigu 5 minojn en Rush-reghimo",
    "quest_daily_tentaizu": "Plenumu la cxiutagan Tentaizu-enigmon",
    "quest_season_intermediate_win": "Venku Meznivelan Minesweeper",
    "quest_season_rush_100": "Forigu 100 minojn en Rush-reghimo",
    "quest_season_tentaizu_10": "Plenumu 10 cxiutagajn Tentaizu-enigmojn",
    "quest_reward_reason_streak": "20-taga cxiutaga tasko-sinsekvo",
    "quest_reward_reason_season": "10 cxiutagaj taskoj cxi-sezone",
    "quest_toast_daily_easy": "Cxiutaga tasko plenumita! Facila Minesweeper venkita.",
    "quest_toast_daily_rush": "Cxiutaga tasko plenumita! 5 Rush-minoj forigitaj.",
    "quest_toast_daily_tentaizu": "Cxiutaga tasko plenumita! Tentaizu-enigmo plenumita.",
    "quest_toast_reward_unlocked": "Rekompenco malshlosita! Reklamoj malaktigitaj — {reason}.",
    "quest_toast_season_intermediate": "Sezona tasko plenumita! Meznivela Minesweeper venkita!",
    "quest_toast_season_rush": "Sezona tasko plenumita! 100 Rush-minoj forigitaj!",
    "quest_toast_season_tentaizu": "Sezona tasko plenumita! 10 Tentaizu-enigmoj plenumitaj!",
}

# ── German ────────────────────────────────────────────────────────────────────
LANGS["de"] = {
    "quests_title": "Aufgaben",
    "quests_subtitle": "Erledige Aufgaben, um Belohnungen zu verdienen. Der Fortschritt wird in deinem Browser gespeichert.",
    "quests_daily_title": "Tagliche Aufgabe",
    "quests_daily_note": "Eine Aufgabe pro Tag, wechselt alle 24 Stunden.",
    "quests_seasonal_title": "Saisonale Aufgaben",
    "quests_seasonal_note": "Alle drei sind den ganzen Monat uber aktiv. Der Fortschritt wird von Tag zu Tag ubertragen.",
    "quests_rewards_title": "Belohnungen",
    "quests_rewards_note": "Verdiene eine der Belohnungen, um Werbung auf diesem Gerat zu deaktivieren.",
    "quests_reward_active": "Belohnung aktiv:",
    "quests_reward_active_desc": "Werbung ist deaktiviert — weiter so!",
    "quests_streak_reward_title": "20-Tagige Tagliche Aufgaben-Serie",
    "quests_streak_reward_desc": "Erledige deine tagliche Aufgabe an 20 aufeinanderfolgenden Tagen.",
    "quests_season_reward_title": "10 Tagliche Aufgaben Diese Saison",
    "quests_season_reward_desc": "Erledige deine tagliche Aufgabe an beliebigen 10 Tagen in diesem Monat.",
    "quests_og_title": "Minesweeper-Aufgaben",
    "quests_og_desc": "Erledige tagliche und monatliche Minesweeper-Aufgaben. Verdiene eine 20-Tage-Serie oder schliesse 10 Aufgaben in einer Saison ab, um Werbung zu deaktivieren.",
    "quest_complete": "Erledigt!",
    "quest_unlocked": "Freigeschaltet!",
    "quest_not_complete": "Noch nicht erledigt",
    "quest_play": "Spielen",
    "quest_days": "Tage",
    "quest_daily_easy_win": "Einfaches Minesweeper gewinnen",
    "quest_daily_rush_5": "5 Minen im Rush-Modus rumen",
    "quest_daily_tentaizu": "Das tagliche Tentaizu-Ratsel losen",
    "quest_season_intermediate_win": "Mittleres Minesweeper gewinnen",
    "quest_season_rush_100": "100 Minen im Rush-Modus raumen",
    "quest_season_tentaizu_10": "10 tagliche Tentaizu-Ratsel losen",
    "quest_reward_reason_streak": "20-tagige tagliche Aufgaben-Serie",
    "quest_reward_reason_season": "10 tagliche Aufgaben diese Saison",
    "quest_toast_daily_easy": "Tagliche Aufgabe abgeschlossen! Einfaches Minesweeper gewonnen.",
    "quest_toast_daily_rush": "Tagliche Aufgabe abgeschlossen! 5 Rush-Minen geraumt.",
    "quest_toast_daily_tentaizu": "Tagliche Aufgabe abgeschlossen! Tentaizu-Ratsel gelost.",
    "quest_toast_reward_unlocked": "Belohnung freigeschaltet! Werbung deaktiviert — {reason}.",
    "quest_toast_season_intermediate": "Saisonale Aufgabe abgeschlossen! Mittleres Minesweeper gewonnen!",
    "quest_toast_season_rush": "Saisonale Aufgabe abgeschlossen! 100 Rush-Minen geraumt!",
    "quest_toast_season_tentaizu": "Saisonale Aufgabe abgeschlossen! 10 Tentaizu-Ratsel gelost!",
}

# ── Spanish ───────────────────────────────────────────────────────────────────
LANGS["es"] = {
    "quests_title": "Misiones",
    "quests_subtitle": "Completa misiones para ganar recompensas. El progreso se guarda en tu navegador.",
    "quests_daily_title": "Mision diaria",
    "quests_daily_note": "Una mision por dia, rota cada 24 horas.",
    "quests_seasonal_title": "Misiones de temporada",
    "quests_seasonal_note": "Las tres estan activas durante todo el mes. El progreso se acumula dia a dia.",
    "quests_rewards_title": "Recompensas",
    "quests_rewards_note": "Gana cualquiera de las recompensas para desactivar los anuncios en este dispositivo.",
    "quests_reward_active": "Recompensa activa:",
    "quests_reward_active_desc": "Los anuncios estan desactivados — ¡sigue asi!",
    "quests_streak_reward_title": "Racha de 20 dias de mision diaria",
    "quests_streak_reward_desc": "Completa tu mision diaria durante 20 dias consecutivos.",
    "quests_season_reward_title": "10 misiones diarias esta temporada",
    "quests_season_reward_desc": "Completa tu mision diaria cualquier 10 dias de este mes.",
    "quests_og_title": "Misiones de Buscaminas",
    "quests_og_desc": "Completa misiones diarias y mensuales de Buscaminas. Consigue una racha de 20 dias o termina 10 misiones en una temporada para desactivar los anuncios.",
    "quest_complete": "¡Completado!",
    "quest_unlocked": "¡Desbloqueado!",
    "quest_not_complete": "Aun no completado",
    "quest_play": "Jugar",
    "quest_days": "dias",
    "quest_daily_easy_win": "Ganar Buscaminas Facil",
    "quest_daily_rush_5": "Eliminar 5 minas en modo Rush",
    "quest_daily_tentaizu": "Completar el puzzle diario de Tentaizu",
    "quest_season_intermediate_win": "Ganar Buscaminas Intermedio",
    "quest_season_rush_100": "Eliminar 100 minas en modo Rush",
    "quest_season_tentaizu_10": "Completar 10 puzzles diarios de Tentaizu",
    "quest_reward_reason_streak": "Racha de 20 dias de mision diaria",
    "quest_reward_reason_season": "10 misiones diarias esta temporada",
    "quest_toast_daily_easy": "¡Mision diaria completada! Buscaminas Facil ganado.",
    "quest_toast_daily_rush": "¡Mision diaria completada! 5 minas Rush eliminadas.",
    "quest_toast_daily_tentaizu": "¡Mision diaria completada! Puzzle de Tentaizu completado.",
    "quest_toast_reward_unlocked": "¡Recompensa desbloqueada! Anuncios desactivados — {reason}.",
    "quest_toast_season_intermediate": "¡Mision de temporada completada! ¡Buscaminas Intermedio ganado!",
    "quest_toast_season_rush": "¡Mision de temporada completada! ¡100 minas Rush eliminadas!",
    "quest_toast_season_tentaizu": "¡Mision de temporada completada! ¡10 puzzles de Tentaizu completados!",
}

# ── French ────────────────────────────────────────────────────────────────────
LANGS["fr"] = {
    "quests_title": "Quetes",
    "quests_subtitle": "Completez des quetes pour gagner des recompenses. La progression est sauvegardee dans votre navigateur.",
    "quests_daily_title": "Quete quotidienne",
    "quests_daily_note": "Une quete par jour, change toutes les 24 heures.",
    "quests_seasonal_title": "Quetes saisonnieres",
    "quests_seasonal_note": "Les trois sont actives tout le mois. La progression se cumule jour apres jour.",
    "quests_rewards_title": "Recompenses",
    "quests_rewards_note": "Gagnez l'une ou l'autre des recompenses pour desactiver les publicites sur cet appareil.",
    "quests_reward_active": "Recompense active :",
    "quests_reward_active_desc": "Les publicites sont desactivees — continuez comme ca !",
    "quests_streak_reward_title": "Serie de 20 jours de quete quotidienne",
    "quests_streak_reward_desc": "Completez votre quete quotidienne pendant 20 jours consecutifs.",
    "quests_season_reward_title": "10 quetes quotidiennes cette saison",
    "quests_season_reward_desc": "Completez votre quete quotidienne n'importe quels 10 jours ce mois-ci.",
    "quests_og_title": "Quetes Demineur",
    "quests_og_desc": "Completez des quetes quotidiennes et mensuelles de Demineur. Gagnez une serie de 20 jours ou finissez 10 quetes en une saison pour desactiver les publicites.",
    "quest_complete": "Complete !",
    "quest_unlocked": "Debloque !",
    "quest_not_complete": "Pas encore complete",
    "quest_play": "Jouer",
    "quest_days": "jours",
    "quest_daily_easy_win": "Gagner le Demineur Facile",
    "quest_daily_rush_5": "Eliminer 5 mines en mode Rush",
    "quest_daily_tentaizu": "Completer le puzzle Tentaizu quotidien",
    "quest_season_intermediate_win": "Gagner le Demineur Intermediaire",
    "quest_season_rush_100": "Eliminer 100 mines en mode Rush",
    "quest_season_tentaizu_10": "Completer 10 puzzles Tentaizu quotidiens",
    "quest_reward_reason_streak": "Serie de 20 jours de quete quotidienne",
    "quest_reward_reason_season": "10 quetes quotidiennes cette saison",
    "quest_toast_daily_easy": "Quete quotidienne terminee ! Demineur Facile gagne.",
    "quest_toast_daily_rush": "Quete quotidienne terminee ! 5 mines Rush eliminees.",
    "quest_toast_daily_tentaizu": "Quete quotidienne terminee ! Puzzle Tentaizu complete.",
    "quest_toast_reward_unlocked": "Recompense debloquee ! Publicites desactivees — {reason}.",
    "quest_toast_season_intermediate": "Quete saisonniere terminee ! Demineur Intermediaire gagne !",
    "quest_toast_season_rush": "Quete saisonniere terminee ! 100 mines Rush eliminees !",
    "quest_toast_season_tentaizu": "Quete saisonniere terminee ! 10 puzzles Tentaizu completes !",
}

# ── insertion logic ───────────────────────────────────────────────────────────
def insert_lang(lang):
    with open(TRANS, encoding="utf-8") as f:
        lines = f.readlines()
    section_starts = {}
    for i, line in enumerate(lines):
        m = re.match(r'\s*"([a-z\-]+)"\s*:\s*\{', line)
        if m: section_starts[m.group(1)] = i
    if lang not in section_starts:
        print(f"ERROR: language '{lang}' not found"); return False
    langs_list = list(section_starts.keys())
    lang_idx = langs_list.index(lang)
    section_start = section_starts[lang]
    section_end = section_starts[langs_list[lang_idx+1]] if lang_idx+1 < len(langs_list) else len(lines)
    existing = set()
    for i in range(section_start, section_end):
        m = re.match(r'\s*"([^"]+)"\s*:', lines[i])
        if m: existing.add(m.group(1))
    insert_after = None
    for i in range(section_start, section_end):
        if f'"{ANCHOR}"' in lines[i]:
            insert_after = i; break
    if insert_after is None:
        print(f"ERROR: anchor '{ANCHOR}' not found in '{lang}'"); return False
    block = build_block(LANGS[lang], existing)
    if not block.strip():
        print(f"SKIP: all keys already present in '{lang}'"); return True
    new_lines = lines[:insert_after+1] + [block] + lines[insert_after+1:]
    new_src = "".join(new_lines)
    try:
        ast.parse(new_src)
    except SyntaxError as e:
        print(f"SYNTAX ERROR in '{lang}': {e}"); return False
    with open(TRANS, "w", encoding="utf-8") as f:
        f.write(new_src)
    added = len([k for k in LANGS[lang] if k not in existing])
    print(f"OK: {added} keys inserted for '{lang}' after line {insert_after+1}")
    return True

if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else "eo"
    sys.exit(0 if insert_lang(lang) else 1)
