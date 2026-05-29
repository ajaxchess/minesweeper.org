# -*- coding: utf-8 -*-
"""15-Puzzle (fp_*) translations — framework + batch 1: eo, de, es, fr"""
import sys, io, re, ast, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANS_FILE = os.path.join(REPO, 'translations.py')
ANCHOR = "fp_lb_h1"


def esc(s):
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    return s


def build_block(keys, existing):
    lines = [f'        "{k}": "{esc(v)}",' for k, v in keys.items() if k not in existing]
    return ("\n".join(lines) + "\n") if lines else ""


LANGS = {}


def insert_lang(lang):
    keys = LANGS.get(lang)
    if not keys:
        print(f"[{lang}] no translations defined — skip")
        return True

    src = open(TRANS_FILE, encoding='utf-8').read()
    lines = src.splitlines(keepends=True)

    section_start = None
    for i, line in enumerate(lines):
        m = re.match(r'\s*"([a-z\-]+)"\s*:\s*\{', line)
        if m and m.group(1) == lang:
            section_start = i
            break

    if section_start is None:
        print(f"[{lang}] section not found!")
        return False

    existing = set()
    brace_depth = 0
    anchor_line = None
    for i in range(section_start, len(lines)):
        line = lines[i]
        brace_depth += line.count('{') - line.count('}')
        m = re.match(r'\s*"([^"]+)"\s*:', line)
        if m:
            k = m.group(1)
            existing.add(k)
            if k == ANCHOR and anchor_line is None:
                anchor_line = i
        if brace_depth <= 0 and i > section_start:
            break

    if anchor_line is None:
        print(f"[{lang}] anchor '{ANCHOR}' not found in section!")
        return False

    block = build_block(keys, existing)
    if not block:
        print(f"[{lang}] all keys already present — skip")
        return True

    insert_pos = anchor_line + 1
    new_lines = lines[:insert_pos] + [block] + lines[insert_pos:]
    new_src = "".join(new_lines)

    try:
        ast.parse(new_src)
    except SyntaxError as e:
        print(f"[{lang}] SYNTAX ERROR: {e}")
        return False

    with open(TRANS_FILE, 'w', encoding='utf-8') as f:
        f.write(new_src)

    count = len([k for k in keys if k not in existing])
    print(f"[{lang}] inserted {count} keys OK")
    return True


# ── Esperanto ──────────────────────────────────────────────────────────────────
LANGS["eo"] = {
    "fp_col_moves": "Movoj",
    "fp_gen_copy": "Kopii",
    "fp_gen_delete": "Forigi",
    "fp_gen_file_label": "JPG aŭ PNG, maks. 2MB",
    "fp_gen_limit_post": "-puzla limo. Forviŝu konservitan puzlon por liberigi spacon.",
    "fp_gen_limit_pre": "Vi atingis vian\xa0",
    "fp_gen_limit_reached": "Puzla limo atingita",
    "fp_gen_mode_h2": "2. Elektu Fotoreĝimon",
    "fp_gen_mode_hint": "<strong>Kaheloj:</strong> la foto estas tranĉita trans la kahelojn kaj miksite.<br><strong>Malkovru ĉe venko:</strong> kaheloj montras nombrojn; solvado malkovras la foton subĵetitan.",
    "fp_gen_mode_reveal": "Malkovru ĉe venko",
    "fp_gen_mode_tiles": "Kaheloj",
    "fp_gen_no_puzzles": "Ankaŭ neniuj konservitaj puze laĵoj. Kreu unu supre!",
    "fp_gen_refresh": "Refreŝigi",
    "fp_gen_refresh_hint": "por vidi ĝin en via konservita listo sube.",
    "fp_gen_save_btn": "Konservi &amp; Akiri Ligilon",
    "fp_gen_saved_title": "Puze laĵo konservita! Kunhavigu ĉi tiun ligilon:",
    "fp_gen_scramble": "↺ Miksi",
    "fp_gen_signin_btn": "Ensaluti",
    "fp_gen_signin_msg": """Vi devas <a href="/login?next=/other/15puzzle/generator" style="color:var(--accent2);font-weight:700;">Ensaluti</a> por alŝuti fotoĵojn kaj konservi puze laĵojn.""",
    "fp_gen_title_label": "Titolo de puze laĵo (nedeviga)",
    "fp_gen_title_ph": "Mia mirinda puze laĵo",
    "fp_gen_untitled": "Sennoma puze laĵo",
    "fp_gen_upload_h2": "1. Alŝutu Foton",
    "fp_gen_your_puzzles": "Viaj Konservitaj Puze laĵoj",
    "fp_htp_back": "← Ludi la Hodi aŭan Puzlon",
    "fp_htp_controls_desktop_li1": "<strong>Alklaku kahlon</strong> apudan al la malplena spaco por gliti ĝin en.",
    "fp_htp_controls_desktop_li2": "<strong>Alklaku kahlon pli malproksiman</strong> en la sama vico aŭ kolumno kaj la tuta linio da kaheloj inter ĝi kaj la malplena spaco glitas kune per unu movo — ekzakte kiel vera fizika puze laĵo.",
    "fp_htp_controls_desktop_li3": "<strong>Sagklavaĵoj</strong> movas kahlon en la malplenan spacon el la responda direkto.",
    "fp_htp_controls_footer": "Uzu la butonon <strong>Nova Ludo</strong> por rekomenci la tablon kaj rekomenci iam ajn.",
    "fp_htp_controls_h2": "Regiloj",
    "fp_htp_controls_mobile_li1": "<strong>Tuŝu kahlon</strong> apudan al la malplena spaco por gliti ĝin en.",
    "fp_htp_controls_mobile_li2": "<strong>Tuŝu kahlon pli malproksiman</strong> en la sama vico aŭ kolumno kaj la tuta vico aŭ kolumno glitas per unu movo.",
    "fp_htp_daily_h2": "Ĉiutaga Puzlo",
    "fp_htp_daily_p1": "Nova puzlo estas generata ĉiutage je noktomezo UTC — la sama miksita tabulo por ĉiu ludanto tutmonde. Solvu ĝin, sendu vian poentaron, kaj vidu vian rangon sur la gvidtabelo.",
    "fp_htp_daily_p2": """Vi ankaŭ povas krei vian propran fotopuzlon uzante la <a href="/other/15puzzle/generator">Puzlogeneratoron</a> — alŝutu ajnan bildon, elektu vian reĝimon, kaj kunhavigu la ligilon kun iu ajn.""",
    "fp_htp_desc": "Lernu kiel ludi la 15-Puzlon — la klasikan glitokahel an ludon. Komprenu la regulojn, regilojn, fotoreĝimojn kaj strategion por solvi ĝin rapide.",
    "fp_htp_ex_midgame": "En la mezo. La supraj vicoj estas ordiĝantaj. Koncentriĝu pri kompletigi unu vicon samtempe de supre malsupren.",
    "fp_htp_ex_nearlydone": "Preskau finita. Nur la malsupraj vicoj restas miksitaj. En ĉi tiu etapo necesas malgrandaj ĝustigoj — evitu malfari progreson en jam solvitaj vicoj.",
    "fp_htp_ex_scrambled": "La komenca pozicio. Kaheloj estas hazardigitaj sed ĉiam solvebla. La malplena spaco (malhela kvadrato) povas esti ie ajn sur la tabulo.",
    "fp_htp_ex_solved": "Solvita! Ĉiuj kaheloj estas en ordo kaj la plena bildo estas malkovrita. Via tempo kaj mova nombro estas registritaj por la gvidtabelo.",
    "fp_htp_example_h2": "Ekzemplo: Solvado Paŝon post Paŝo",
    "fp_htp_example_intro": "La ekrankopioj sube montras fotopuzlon solvatan uzante Lady Di's Mines kiel la bildon. Ĉiu kahelo portas nombron kaj fragmenton de la bildo — do vi povas uzi la bildon kiel vizan gvidon dum vi solvas.",
    "fp_htp_goal_h2": "La Celo",
    "fp_htp_goal_p1": "Aranĝu ĉiujn 15 kahelojn en kreskanta ordo — de maldekstre dekstren, de supre malsupren — kun la malplena spaco en la suba-dekstra angulo. La solvita pozicio aspektas tiel: 1, 2, 3, 4 tra la supra vico, poste 5, 6, 7, 8, poste 9, 10, 11, 12, poste 13, 14, 15 kaj la malplenaĵo.",
    "fp_htp_goal_p2": "Via poentaro estas kombinаĵo de kiom da movoj vi uzis kaj kiom rapide vi solvis ĝin. Malpli da movoj kaj malpli da tempo signifas pli bonan gvidtabelrangon.",
    "fp_htp_intro": "La 15-Puzlo estas klasika glitokahel a ludo ludita sur 4\xd74 krado. Dek kvin numeritaj kaheloj plenumas la tabulon, lasante unu malplenan spacon. Glitu kahelojn en la malplenan spacon por reordigi ilin ĝis ĉiu kahelo estas en ordo de 1 ĝis 15.",
    "fp_htp_photo_h2": "Fotopuzlaj Reĝimoj",
    "fp_htp_photo_p1": "La ĉiutaga puzlo kaj propraj fotopuzloj ofertas du malsamajn vidajn reĝimojn:",
    "fp_htp_photo_reveal": "<strong>Malkovru ĉe venko</strong> — kaheloj montras nur nombrojn dum vi solvas. Kiam vi metas la lastan kahelo ĝuste, la plena foto estas malkovrita subĵetitan. La bildo estas premio por finado, ne indiko.",
    "fp_htp_photo_tiles": "<strong>Kaheloreĝimo</strong> — ĉiu kahelo montras sian tranĉaĵon de la foto. La bildo donas al vi vizan kuntekston por gvidi vian solvadan — uzu la bildon kiel duan informtavolon aldone al la numeroj.",
    "fp_htp_strategy_h2": "Strategio",
    "fp_htp_strategy_p1": "<strong>Solvu vicon post vico de supre.</strong> Vicoj 1 kaj 2 povas ĉiu esti kompletigitaj kaj ŝlositaj sen ĝeni ion supran. La finaj du vicoj (kaheloj 9–15) estas solvitaj kune uzante rotacian teknikon.",
    "fp_htp_strategy_p2": "<strong>Metu kahelo 1 kaj kahelo 2 kune.</strong> Provi gliti kahelo 1 en pozicion sola ofte mallokas kahelo 2. Anstataŭe, manœuvru ambaŭ kahelojn 1 kaj 2 en ilian ĝustajn kolumnajn poziciojn samtempe, poste rotu ilin en la supran vicon samtempe.",
    "fp_htp_strategy_p3": "<strong>Uzu multikahel ajn glitigojn.</strong> Alklaki aŭ tuŝi kahelo kiu ne estas rekte apuda al la malplena spaco glitas la tutan intervenantan vicon aŭ kolumnon. Ĉi tio estas pli rapida ol movi kahelojn po unu kaj estas esenca por efika solvado.",
    "fp_htp_strategy_p4": "<strong>Nombru viajn movojn.</strong> Ĉiu glitigo kalkulas kiel unu movo, inkluzive multikahel ajn glitigojn. Unu bone planita multikahel a glitigo povas ŝpari plurajn unukahel ajn movojn — planu anticipe por minimumigi vian nombron.",
    "fp_htp_title": "Kiel Ludi la 15-Puzlon | minesweeper.org",
    "fp_moves": "Movoj:",
    "fp_name_label": "Nomo",
    "fp_new_game": "↺ Nova Ludo",
    "fp_photo_puzzle": "Fotopuzlo",
    "fp_same_for_all": "Sama puzlo por ĉiuj · Rekomenciĝas je noktomezo UTC",
    "fp_solved": "\U0001f389 Solvita!",
    "fp_submit_score": "Sendi vian poentaron",
    "fp_time": "Tempo:",
    "fp_today_heading": "Hodi aŭ — ",
}

# ── German ─────────────────────────────────────────────────────────────────────
LANGS["de"] = {
    "fp_col_moves": "Z\xfcge",
    "fp_gen_copy": "Kopieren",
    "fp_gen_delete": "L\xf6schen",
    "fp_gen_file_label": "JPG oder PNG, max. 2 MB",
    "fp_gen_limit_post": "-R\xe4tsel-Limit. L\xf6sche ein gespeichertes R\xe4tsel, um Platz zu schaffen.",
    "fp_gen_limit_pre": "Du hast dein\xa0",
    "fp_gen_limit_reached": "R\xe4tsel-Limit erreicht",
    "fp_gen_mode_h2": "2. Fotomodus w\xe4hlen",
    "fp_gen_mode_hint": "<strong>Kacheln:</strong> Das Foto wird auf die Kacheln aufgeteilt und zusammen mit ihnen gemischt.<br><strong>Bei Sieg enth\xfcllen:</strong> Kacheln zeigen Zahlen; beim L\xf6sen wird das darunterliegende Foto enth\xfcllt.",
    "fp_gen_mode_reveal": "Bei Sieg enth\xfcllen",
    "fp_gen_mode_tiles": "Kacheln",
    "fp_gen_no_puzzles": "Noch keine gespeicherten R\xe4tsel. Erstelle oben eines!",
    "fp_gen_refresh": "Aktualisieren",
    "fp_gen_refresh_hint": "um es in deiner gespeicherten Liste unten zu sehen.",
    "fp_gen_save_btn": "Speichern &amp; Link erhalten",
    "fp_gen_saved_title": "R\xe4tsel gespeichert! Teile diesen Link:",
    "fp_gen_scramble": "↺ Mischen",
    "fp_gen_signin_btn": "Anmelden",
    "fp_gen_signin_msg": """Du musst dich <a href="/login?next=/other/15puzzle/generator" style="color:var(--accent2);font-weight:700;">Anmelden</a>, um Fotos hochzuladen und R\xe4tsel zu speichern.""",
    "fp_gen_title_label": "R\xe4tseltitel (optional)",
    "fp_gen_title_ph": "Mein tolles R\xe4tsel",
    "fp_gen_untitled": "Unbenanntes R\xe4tsel",
    "fp_gen_upload_h2": "1. Foto hochladen",
    "fp_gen_your_puzzles": "Deine gespeicherten R\xe4tsel",
    "fp_htp_back": "← Heutiges R\xe4tsel spielen",
    "fp_htp_controls_desktop_li1": "<strong>Klicke auf eine Kachel</strong> neben dem leeren Feld, um sie hineinzuschieben.",
    "fp_htp_controls_desktop_li2": "<strong>Klicke auf eine weiter entfernte Kachel</strong> in derselben Zeile oder Spalte, und die gesamte Reihe von Kacheln zwischen ihr und dem leeren Feld gleitet in einem Zug zusammen — genau wie bei einem echten physischen Puzzle.",
    "fp_htp_controls_desktop_li3": "<strong>Pfeiltasten</strong> bewegen eine Kachel aus der entsprechenden Richtung in das leere Feld.",
    "fp_htp_controls_footer": "Verwende die Schaltfl\xe4che <strong>Neues Spiel</strong>, um das Feld zur\xfcckzusetzen und jederzeit neu zu beginnen.",
    "fp_htp_controls_h2": "Steuerung",
    "fp_htp_controls_mobile_li1": "<strong>Tippe auf eine Kachel</strong> neben dem leeren Feld, um sie hineinzuschieben.",
    "fp_htp_controls_mobile_li2": "<strong>Tippe auf eine weiter entfernte Kachel</strong> in derselben Zeile oder Spalte und die gesamte Zeile oder Spalte gleitet in einem Zug.",
    "fp_htp_daily_h2": "Tagesr\xe4tsel",
    "fp_htp_daily_p1": "Jeden Tag um Mitternacht UTC wird ein neues R\xe4tsel erstellt — dasselbe gemischte Feld f\xfcr jeden Spieler weltweit. L\xf6se es, reiche deine Punktzahl ein und sieh, wie du auf der Bestenliste abschneidest.",
    "fp_htp_daily_p2": """Du kannst auch dein eigenes Foto-R\xe4tsel mit dem <a href="/other/15puzzle/generator">R\xe4tsel-Generator</a> erstellen — lade ein beliebiges Bild hoch, w\xe4hle deinen Modus und teile den Link mit jedem.""",
    "fp_htp_desc": "Lerne, wie man das 15-Puzzle spielt — das klassische Schiebepuzzle. Verstehe die Regeln, Steuerung, Fotomodi und Strategie, um es schnell zu l\xf6sen.",
    "fp_htp_ex_midgame": "Auf halbem Weg. Die oberen Zeilen ordnen sich ein. Konzentriere dich darauf, eine Zeile nach der anderen von oben nach unten zu vervollst\xe4ndigen.",
    "fp_htp_ex_nearlydone": "Fast fertig. Nur die unteren Zeilen sind noch gemischt. In dieser Phase sind kleine Anpassungen n\xf6tig — vermeide es, den Fortschritt in bereits gel\xf6sten Zeilen r\xfckg\xe4ngig zu machen.",
    "fp_htp_ex_scrambled": "Die Startposition. Kacheln sind zuf\xe4llig angeordnet, aber immer l\xf6sbar. Das leere Feld (dunkles Quadrat) kann sich \xfcberall auf dem Spielfeld befinden.",
    "fp_htp_ex_solved": "Gel\xf6st! Alle Kacheln sind in der richtigen Reihenfolge und das vollst\xe4ndige Bild wird enth\xfcllt. Deine Zeit und Zuganzahl werden f\xfcr die Bestenliste gespeichert.",
    "fp_htp_example_h2": "Beispiel: Schritt-f\xfcr-Schritt-L\xf6sung",
    "fp_htp_example_intro": "Die Screenshots unten zeigen ein Foto-R\xe4tsel, das mit Lady Di's Mines als Bild gel\xf6st wird. Jede Kachel tr\xe4gt eine Zahl und ein Fragment des Bildes — du kannst das Bild als visuellen Leitfaden beim L\xf6sen nutzen.",
    "fp_htp_goal_h2": "Das Ziel",
    "fp_htp_goal_p1": "Ordne alle 15 Kacheln in aufsteigender Reihenfolge an — von links nach rechts, von oben nach unten — mit dem leeren Feld in der unteren rechten Ecke. Die gel\xf6ste Position sieht so aus: 1, 2, 3, 4 in der obersten Zeile, dann 5, 6, 7, 8, dann 9, 10, 11, 12, dann 13, 14, 15 und das leere Feld.",
    "fp_htp_goal_p2": "Deine Punktzahl ist eine Kombination aus der Anzahl der verwendeten Z\xfcge und der L\xf6sungszeit. Weniger Z\xfcge und weniger Zeit bedeuten ein besseres Ranking auf der Bestenliste.",
    "fp_htp_intro": "Das 15-Puzzle ist ein klassisches Schiebepuzzle auf einem 4\xd74-Gitter. F\xfcnfzehn nummerierte Kacheln f\xfcllen das Feld und lassen ein leeres Feld frei. Schiebe Kacheln in das leere Feld, um sie neu anzuordnen, bis alle Kacheln von 1 bis 15 in der richtigen Reihenfolge sind.",
    "fp_htp_photo_h2": "Foto-Puzzle-Modi",
    "fp_htp_photo_p1": "Das Tagesr\xe4tsel und benutzerdefinierte Foto-R\xe4tsel bieten zwei verschiedene visuelle Modi:",
    "fp_htp_photo_reveal": "<strong>Bei Sieg enth\xfcllen</strong> — Kacheln zeigen nur Zahlen w\xe4hrend du l\xf6st. Wenn du die letzte Kachel richtig platzierst, wird das vollst\xe4ndige Foto darunter enth\xfcllt. Das Bild ist eine Belohnung f\xfcr das Abschlie\xdfen, kein Hinweis.",
    "fp_htp_photo_tiles": "<strong>Kachel-Modus</strong> — jede Kachel zeigt ihren Ausschnitt des Fotos. Das Bild gibt dir visuellen Kontext f\xfcr dein L\xf6sen — nutze das Bild als zweite Informationsebene zus\xe4tzlich zu den Zahlen.",
    "fp_htp_strategy_h2": "Strategie",
    "fp_htp_strategy_p1": "<strong>L\xf6se Zeile f\xfcr Zeile von oben.</strong> Zeilen 1 und 2 k\xf6nnen jeweils vervollst\xe4ndigt und fixiert werden, ohne irgendetwas dar\xfcber zu st\xf6ren. Die letzten zwei Zeilen (Kacheln 9–15) werden gemeinsam mit einer Rotationstechnik gel\xf6st.",
    "fp_htp_strategy_p2": "<strong>Platziere Kachel 1 und Kachel 2 zusammen.</strong> Der Versuch, Kachel 1 allein in die richtige Position zu schieben, verdr\xe4ngt oft Kachel 2. Man\xf6vriere stattdessen beide Kacheln 1 und 2 gleichzeitig in ihre richtigen Spaltenpositionen und rotiere sie dann gleichzeitig in die oberste Zeile.",
    "fp_htp_strategy_p3": "<strong>Verwende Mehrkachel-Sch\xfcbe.</strong> Das Klicken oder Tippen auf eine Kachel, die nicht direkt neben dem leeren Feld liegt, schiebt die gesamte dazwischenliegende Zeile oder Spalte. Das ist schneller als das Bewegen von Kacheln einzeln und ist f\xfcr effizientes L\xf6sen unerl\xe4sslich.",
    "fp_htp_strategy_p4": "<strong>Z\xe4hle deine Z\xfcge.</strong> Jeder Schub z\xe4hlt als ein Zug, einschlie\xdflich Mehrkachel-Sch\xfcbe. Ein einzelner gut geplanter Mehrkachel-Schub kann mehrere Einzelkachel-Z\xfcge einsparen — plane im Voraus, um deine Anzahl zu minimieren.",
    "fp_htp_title": "Wie man das 15-Puzzle spielt | minesweeper.org",
    "fp_moves": "Z\xfcge:",
    "fp_name_label": "Name",
    "fp_new_game": "↺ Neues Spiel",
    "fp_photo_puzzle": "Foto-R\xe4tsel",
    "fp_same_for_all": "Gleiches R\xe4tsel f\xfcr alle · Zur\xfcckgesetzt um Mitternacht UTC",
    "fp_solved": "\U0001f389 Gel\xf6st!",
    "fp_submit_score": "Punktzahl einreichen",
    "fp_time": "Zeit:",
    "fp_today_heading": "Heute — ",
}

# ── Spanish ────────────────────────────────────────────────────────────────────
LANGS["es"] = {
    "fp_col_moves": "Movimientos",
    "fp_gen_copy": "Copiar",
    "fp_gen_delete": "Eliminar",
    "fp_gen_file_label": "JPG o PNG, m\xe1x. 2 MB",
    "fp_gen_limit_post": " de l\xedmite de rompecabezas. Elimina un rompecabezas guardado para hacer espacio.",
    "fp_gen_limit_pre": "Has alcanzado tu\xa0",
    "fp_gen_limit_reached": "L\xedmite de rompecabezas alcanzado",
    "fp_gen_mode_h2": "2. Elige el modo de foto",
    "fp_gen_mode_hint": "<strong>Fichas:</strong> la foto se divide entre las fichas y se mezcla con ellas.<br><strong>Revelar al ganar:</strong> las fichas muestran n\xfameros; al resolver se revela la foto debajo.",
    "fp_gen_mode_reveal": "Revelar al ganar",
    "fp_gen_mode_tiles": "Fichas",
    "fp_gen_no_puzzles": "A\xfan no hay rompecabezas guardados. \xa1Crea uno arriba!",
    "fp_gen_refresh": "Actualizar",
    "fp_gen_refresh_hint": "para verlo en tu lista guardada a continuaci\xf3n.",
    "fp_gen_save_btn": "Guardar &amp; Obtener enlace",
    "fp_gen_saved_title": "\xa1Rompecabezas guardado! Comparte este enlace:",
    "fp_gen_scramble": "↺ Mezclar",
    "fp_gen_signin_btn": "Iniciar sesi\xf3n",
    "fp_gen_signin_msg": """Debes <a href="/login?next=/other/15puzzle/generator" style="color:var(--accent2);font-weight:700;">Iniciar sesi\xf3n</a> para subir fotos y guardar rompecabezas.""",
    "fp_gen_title_label": "T\xedtulo del rompecabezas (opcional)",
    "fp_gen_title_ph": "Mi incre\xedble rompecabezas",
    "fp_gen_untitled": "Rompecabezas sin t\xedtulo",
    "fp_gen_upload_h2": "1. Sube una foto",
    "fp_gen_your_puzzles": "Tus rompecabezas guardados",
    "fp_htp_back": "← Jugar el rompecabezas de hoy",
    "fp_htp_controls_desktop_li1": "<strong>Haz clic en una ficha</strong> adyacente al espacio vac\xedo para deslizarla.",
    "fp_htp_controls_desktop_li2": "<strong>Haz clic en una ficha m\xe1s alejada</strong> en la misma fila o columna y toda la l\xednea de fichas entre ella y el espacio vac\xedo se desliza junta en un movimiento — igual que un rompecabezas f\xedsico real.",
    "fp_htp_controls_desktop_li3": "<strong>Las teclas de flecha</strong> mueven una ficha hacia el espacio vac\xedo desde la direcci\xf3n correspondiente.",
    "fp_htp_controls_footer": "Usa el bot\xf3n <strong>Nuevo juego</strong> para reiniciar el tablero y empezar de nuevo en cualquier momento.",
    "fp_htp_controls_h2": "Controles",
    "fp_htp_controls_mobile_li1": "<strong>Toca una ficha</strong> adyacente al espacio vac\xedo para deslizarla.",
    "fp_htp_controls_mobile_li2": "<strong>Toca una ficha m\xe1s alejada</strong> en la misma fila o columna y toda la fila o columna se desliza en un movimiento.",
    "fp_htp_daily_h2": "Rompecabezas diario",
    "fp_htp_daily_p1": "Cada d\xeda a medianoche UTC se genera un nuevo rompecabezas — el mismo tablero mezclado para todos los jugadores del mundo. Resuelve, env\xeda tu puntuaci\xf3n y mira tu posici\xf3n en el marcador.",
    "fp_htp_daily_p2": """Tambi\xe9n puedes crear tu propio rompecabezas de fotos usando el <a href="/other/15puzzle/generator">Generador de rompecabezas</a> — sube cualquier imagen, elige tu modo y comparte el enlace con cualquiera.""",
    "fp_htp_desc": "Aprende a jugar al rompecabezas de 15 piezas — el cl\xe1sico juego de fichas deslizantes. Comprende las reglas, controles, modos de foto y estrategia para resolverlo r\xe1pido.",
    "fp_htp_ex_midgame": "A mitad de camino. Las filas superiores van tomando su lugar. Conc\xe9ntrate en completar una fila a la vez de arriba hacia abajo.",
    "fp_htp_ex_nearlydone": "Casi terminado. Solo las filas inferiores siguen mezcladas. En esta etapa se necesitan peque\xf1os ajustes — evita deshacer el progreso en filas ya resueltas.",
    "fp_htp_ex_scrambled": "La posici\xf3n inicial. Las fichas est\xe1n desordenadas pero siempre son solucionables. El espacio vac\xedo (cuadrado oscuro) puede estar en cualquier lugar del tablero.",
    "fp_htp_ex_solved": "\xa1Resuelto! Todas las fichas est\xe1n en orden y la imagen completa queda revelada. Tu tiempo y n\xfamero de movimientos se registran para el marcador.",
    "fp_htp_example_h2": "Ejemplo: resoluci\xf3n paso a paso",
    "fp_htp_example_intro": "Las capturas de pantalla de abajo muestran un rompecabezas de fotos siendo resuelto usando Lady Di's Mines como imagen. Cada ficha lleva un n\xfamero y un fragmento de la imagen — as\xed puedes usar la imagen como gu\xeda visual mientras resuelves.",
    "fp_htp_goal_h2": "El objetivo",
    "fp_htp_goal_p1": "Coloca las 15 fichas en orden ascendente — de izquierda a derecha, de arriba a abajo — con el espacio vac\xedo en la esquina inferior derecha. La posici\xf3n resuelta tiene este aspecto: 1, 2, 3, 4 en la fila superior, luego 5, 6, 7, 8, luego 9, 10, 11, 12, luego 13, 14, 15 y el espacio en blanco.",
    "fp_htp_goal_p2": "Tu puntuaci\xf3n es una combinaci\xf3n de cu\xe1ntos movimientos usaste y qu\xe9 tan r\xe1pido lo resolviste. Menos movimientos y menos tiempo significa una mejor posici\xf3n en el marcador.",
    "fp_htp_intro": "El rompecabezas de 15 piezas es un cl\xe1sico juego de fichas deslizantes en una cuadr\xedcula de 4\xd74. Quince fichas numeradas llenan el tablero, dejando un espacio vac\xedo. Desliza las fichas hacia el espacio vac\xedo para reordenarlas hasta que todas est\xe9n en orden del 1 al 15.",
    "fp_htp_photo_h2": "Modos de rompecabezas de fotos",
    "fp_htp_photo_p1": "El rompecabezas diario y los rompecabezas de fotos personalizados ofrecen dos modos visuales diferentes:",
    "fp_htp_photo_reveal": "<strong>Revelar al ganar</strong> — las fichas muestran solo n\xfameros mientras resuelves. Cuando colocas la \xfaltima ficha correctamente, la foto completa se revela debajo. La imagen es una recompensa por terminar, no una pista.",
    "fp_htp_photo_tiles": "<strong>Modo fichas</strong> — cada ficha muestra su porci\xf3n de la foto. La imagen te da contexto visual para guiar tu resoluci\xf3n — usa la imagen como una segunda capa de informaci\xf3n adem\xe1s de los n\xfameros.",
    "fp_htp_strategy_h2": "Estrategia",
    "fp_htp_strategy_p1": "<strong>Resuelve fila por fila desde arriba.</strong> Las filas 1 y 2 pueden completarse y fijarse sin perturbar nada de arriba. Las dos \xfaltimas filas (fichas 9–15) se resuelven juntas usando una t\xe9cnica de rotaci\xf3n.",
    "fp_htp_strategy_p2": "<strong>Coloca la ficha 1 y la ficha 2 juntas.</strong> Intentar deslizar la ficha 1 a su posici\xf3n sola a menudo desplaza la ficha 2. En cambio, maniobra ambas fichas 1 y 2 a sus posiciones de columna correctas simult\xe1neamente, luego r\xf3talas a la fila superior al mismo tiempo.",
    "fp_htp_strategy_p3": "<strong>Usa deslizamientos de m\xfaltiples fichas.</strong> Hacer clic o tocar una ficha que no est\xe1 directamente adyacente al espacio vac\xedo desliza toda la fila o columna intermedia. Esto es m\xe1s r\xe1pido que mover fichas de una en una y es esencial para resolver eficientemente.",
    "fp_htp_strategy_p4": "<strong>Cuenta tus movimientos.</strong> Cada deslizamiento cuenta como un movimiento, incluidos los deslizamientos de m\xfaltiples fichas. Un \xfanico deslizamiento bien planificado puede ahorrar varios movimientos — planifica con anticipaci\xf3n para minimizar tu cuenta.",
    "fp_htp_title": "C\xf3mo jugar al rompecabezas de 15 piezas | minesweeper.org",
    "fp_moves": "Movimientos:",
    "fp_name_label": "Nombre",
    "fp_new_game": "↺ Nuevo juego",
    "fp_photo_puzzle": "Rompecabezas de fotos",
    "fp_same_for_all": "El mismo rompecabezas para todos · Se reinicia a medianoche UTC",
    "fp_solved": "\U0001f389 \xa1Resuelto!",
    "fp_submit_score": "Enviar tu puntuaci\xf3n",
    "fp_time": "Tiempo:",
    "fp_today_heading": "Hoy — ",
}

# ── French ─────────────────────────────────────────────────────────────────────
LANGS["fr"] = {
    "fp_col_moves": "Coups",
    "fp_gen_copy": "Copier",
    "fp_gen_delete": "Supprimer",
    "fp_gen_file_label": "JPG ou PNG, max. 2 Mo",
    "fp_gen_limit_post": " de limite de puzzles. Supprimez un puzzle enregistr\xe9 pour lib\xe9rer de la place.",
    "fp_gen_limit_pre": "Vous avez atteint votre\xa0",
    "fp_gen_limit_reached": "Limite de puzzles atteinte",
    "fp_gen_mode_h2": "2. Choisissez le mode photo",
    "fp_gen_mode_hint": "<strong>Tuiles :</strong> la photo est d\xe9coup\xe9e sur les tuiles et m\xe9lang\xe9e avec elles.<br><strong>R\xe9v\xe9ler \xe0 la victoire :</strong> les tuiles affichent des num\xe9ros ; la r\xe9solution r\xe9v\xe8le la photo en dessous.",
    "fp_gen_mode_reveal": "R\xe9v\xe9ler \xe0 la victoire",
    "fp_gen_mode_tiles": "Tuiles",
    "fp_gen_no_puzzles": "Aucun puzzle enregistr\xe9 pour l'instant. Cr\xe9ez-en un ci-dessus !",
    "fp_gen_refresh": "Actualiser",
    "fp_gen_refresh_hint": "pour le voir dans votre liste enregistr\xe9e ci-dessous.",
    "fp_gen_save_btn": "Enregistrer &amp; Obtenir le lien",
    "fp_gen_saved_title": "Puzzle enregistr\xe9 ! Partagez ce lien :",
    "fp_gen_scramble": "↺ M\xe9langer",
    "fp_gen_signin_btn": "Se connecter",
    "fp_gen_signin_msg": """Vous devez <a href="/login?next=/other/15puzzle/generator" style="color:var(--accent2);font-weight:700;">Vous connecter</a> pour t\xe9l\xe9charger des photos et enregistrer des puzzles.""",
    "fp_gen_title_label": "Titre du puzzle (facultatif)",
    "fp_gen_title_ph": "Mon super puzzle",
    "fp_gen_untitled": "Puzzle sans titre",
    "fp_gen_upload_h2": "1. T\xe9l\xe9charger une photo",
    "fp_gen_your_puzzles": "Vos puzzles enregistr\xe9s",
    "fp_htp_back": "← Jouer le puzzle du jour",
    "fp_htp_controls_desktop_li1": "<strong>Cliquez sur une tuile</strong> adjacente \xe0 l'espace vide pour la faire glisser.",
    "fp_htp_controls_desktop_li2": "<strong>Cliquez sur une tuile plus \xe9loign\xe9e</strong> dans la m\xeame ligne ou colonne et toute la rang\xe9e de tuiles entre elle et l'espace vide glisse ensemble en un seul coup — exactement comme un vrai puzzle physique.",
    "fp_htp_controls_desktop_li3": "<strong>Les touches fl\xe9ch\xe9es</strong> d\xe9placent une tuile dans l'espace vide depuis la direction correspondante.",
    "fp_htp_controls_footer": "Utilisez le bouton <strong>Nouvelle partie</strong> pour r\xe9initialiser le plateau et recommencer \xe0 tout moment.",
    "fp_htp_controls_h2": "Commandes",
    "fp_htp_controls_mobile_li1": "<strong>Appuyez sur une tuile</strong> adjacente \xe0 l'espace vide pour la faire glisser.",
    "fp_htp_controls_mobile_li2": "<strong>Appuyez sur une tuile plus \xe9loign\xe9e</strong> dans la m\xeame ligne ou colonne et toute la ligne ou colonne glisse en un seul coup.",
    "fp_htp_daily_h2": "Puzzle du jour",
    "fp_htp_daily_p1": "Un nouveau puzzle est g\xe9n\xe9r\xe9 chaque jour \xe0 minuit UTC — le m\xeame plateau m\xe9lang\xe9 pour chaque joueur dans le monde entier. R\xe9solvez-le, soumettez votre score et voyez votre classement sur le tableau des scores.",
    "fp_htp_daily_p2": """Vous pouvez \xe9galement cr\xe9er votre propre puzzle photo en utilisant le <a href="/other/15puzzle/generator">G\xe9n\xe9rateur de puzzles</a> — t\xe9l\xe9chargez n'importe quelle image, choisissez votre mode et partagez le lien avec n'importe qui.""",
    "fp_htp_desc": "Apprenez \xe0 jouer au puzzle de 15 — le jeu classique de tuiles coulissantes. Comprenez les r\xe8gles, les commandes, les modes photo et la strat\xe9gie pour le r\xe9soudre rapidement.",
    "fp_htp_ex_midgame": "\xc0 mi-chemin. Les rang\xe9es sup\xe9rieures se mettent en place. Concentrez-vous sur la compl\xe9tion d'une rang\xe9e \xe0 la fois de haut en bas.",
    "fp_htp_ex_nearlydone": "Presque termin\xe9. Seules les rang\xe9es inf\xe9rieures restent m\xe9lang\xe9es. \xc0 ce stade, de petits ajustements sont n\xe9cessaires — \xe9vitez d'annuler les progr\xe8s dans les rang\xe9es d\xe9j\xe0 r\xe9solues.",
    "fp_htp_ex_scrambled": "La position de d\xe9part. Les tuiles sont m\xe9lang\xe9es mais toujours solubles. L'espace vide (carr\xe9 sombre) peut se trouver n'importe o\xf9 sur le plateau.",
    "fp_htp_ex_solved": "R\xe9solu ! Toutes les tuiles sont en ordre et l'image compl\xe8te est r\xe9v\xe9l\xe9e. Votre temps et votre nombre de coups sont enregistr\xe9s pour le tableau des scores.",
    "fp_htp_example_h2": "Exemple : r\xe9solution \xe9tape par \xe9tape",
    "fp_htp_example_intro": "Les captures d'\xe9cran ci-dessous montrent un puzzle photo r\xe9solu en utilisant Lady Di's Mines comme image. Chaque tuile porte un num\xe9ro et un fragment de l'image — vous pouvez donc utiliser l'image comme guide visuel pendant la r\xe9solution.",
    "fp_htp_goal_h2": "L'objectif",
    "fp_htp_goal_p1": "Arrangez les 15 tuiles en ordre croissant — de gauche \xe0 droite, de haut en bas — avec l'espace vide dans le coin inf\xe9rieur droit. La position r\xe9solue ressemble \xe0 ceci : 1, 2, 3, 4 sur la rang\xe9e sup\xe9rieure, puis 5, 6, 7, 8, puis 9, 10, 11, 12, puis 13, 14, 15 et l'espace vide.",
    "fp_htp_goal_p2": "Votre score est une combinaison du nombre de coups utilis\xe9s et de la vitesse \xe0 laquelle vous l'avez r\xe9solu. Moins de coups et moins de temps signifient un meilleur classement sur le tableau des scores.",
    "fp_htp_intro": "Le puzzle de 15 est un jeu classique de tuiles coulissantes jou\xe9 sur une grille 4\xd74. Quinze tuiles num\xe9rot\xe9es remplissent le plateau, laissant un espace vide. Faites glisser les tuiles dans l'espace vide pour les r\xe9organiser jusqu'\xe0 ce que chaque tuile soit en ordre de 1 \xe0 15.",
    "fp_htp_photo_h2": "Modes de puzzle photo",
    "fp_htp_photo_p1": "Le puzzle du jour et les puzzles photo personnalis\xe9s proposent deux modes visuels diff\xe9rents :",
    "fp_htp_photo_reveal": "<strong>R\xe9v\xe9ler \xe0 la victoire</strong> — les tuiles n'affichent que des num\xe9ros pendant que vous r\xe9solvez. Lorsque vous placez la derni\xe8re tuile correctement, la photo compl\xe8te est r\xe9v\xe9l\xe9e en dessous. L'image est une r\xe9compense pour avoir termin\xe9, pas un indice.",
    "fp_htp_photo_tiles": "<strong>Mode tuiles</strong> — chaque tuile montre sa tranche de la photo. L'image vous donne un contexte visuel pour guider votre r\xe9solution — utilisez l'image comme une deuxi\xe8me couche d'information en plus des num\xe9ros.",
    "fp_htp_strategy_h2": "Strat\xe9gie",
    "fp_htp_strategy_p1": "<strong>R\xe9solvez rang\xe9e par rang\xe9e depuis le haut.</strong> Les rang\xe9es 1 et 2 peuvent chacune \xeatre compl\xe9t\xe9es et verrouill\xe9es sans perturber ce qui est au-dessus. Les deux derni\xe8res rang\xe9es (tuiles 9–15) sont r\xe9solues ensemble en utilisant une technique de rotation.",
    "fp_htp_strategy_p2": "<strong>Placez la tuile 1 et la tuile 2 ensemble.</strong> Essayer de faire glisser la tuile 1 en position seule d\xe9place souvent la tuile 2. Manœuvrez plut\xf4t les deux tuiles 1 et 2 simultan\xe9ment dans leurs positions de colonne correctes, puis faites-les pivoter dans la rang\xe9e sup\xe9rieure en m\xeame temps.",
    "fp_htp_strategy_p3": "<strong>Utilisez les glissements multi-tuiles.</strong> Cliquer ou appuyer sur une tuile qui n'est pas directement adjacente \xe0 l'espace vide fait glisser toute la rang\xe9e ou colonne interm\xe9diaire. C'est plus rapide que de d\xe9placer les tuiles une par une et est essentiel pour une r\xe9solution efficace.",
    "fp_htp_strategy_p4": "<strong>Comptez vos coups.</strong> Chaque glissement compte comme un coup, y compris les glissements multi-tuiles. Un seul glissement multi-tuiles bien planifi\xe9 peut \xe9conomiser plusieurs coups — planifiez \xe0 l'avance pour minimiser votre compte.",
    "fp_htp_title": "Comment jouer au puzzle de 15 | minesweeper.org",
    "fp_moves": "Coups :",
    "fp_name_label": "Nom",
    "fp_new_game": "↺ Nouvelle partie",
    "fp_photo_puzzle": "Puzzle photo",
    "fp_same_for_all": "M\xeame puzzle pour tous · R\xe9initialis\xe9 \xe0 minuit UTC",
    "fp_solved": "\U0001f389 R\xe9solu !",
    "fp_submit_score": "Soumettre votre score",
    "fp_time": "Temps :",
    "fp_today_heading": "Aujourd'hui — ",
}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        lang = sys.argv[1]
        sys.exit(0 if insert_lang(lang) else 1)
    else:
        for lang in LANGS:
            insert_lang(lang)
