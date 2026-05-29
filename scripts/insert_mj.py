"""Insert missing mj_* keys into translations.py.
Inserts after the existing 'mj_lb_h1' anchor in each language section.
Usage: python scripts/insert_mj.py <lang>
"""
import ast, sys, re, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANS = os.path.join(REPO, "translations.py")
ANCHOR = "mj_lb_h1"

def esc(s):
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    return s

def build_block(keys):
    return "\n".join(f'        "{k}": "{esc(v)}",' for k, v in keys.items()) + "\n"

LANGS = {}

# ── Esperanto ─────────────────────────────────────────────────────────────────
LANGS["eo"] = {
    "mj_hint_free": "Montri Liberajn Kahelojn",
    "mj_hint_match": "Montri Kongruojn",
    "mj_htp_back": "Ludi Hodiaŭan Enigmon",
    "mj_htp_controls_h2": "Kontroloj",
    "mj_htp_controls_li1": "<strong>Alklaku liberan kahelon</strong> por elekti ĝin (elstarigita en oro).",
    "mj_htp_controls_li2": "<strong>Alklaku duan liberan kahelon</strong> de la sama tipo por forigi la paron.",
    "mj_htp_controls_li3": "<strong>Alklaku la elektitan kahelon denove</strong> por malelekti ĝin.",
    "mj_htp_controls_li4": "<strong>Malfari</strong> repaŝas unu kongruigitan paron samtempe.",
    "mj_htp_daily_h2": "Ĉiutaga Enigmo",
    "mj_htp_daily_p": "Ĉiun tagon nova tablo estas generita el la hodiaŭa dato — la sama tablo por ĉiu ludanto tutmonde. La tempigilo ekiras kiam vi alklakos vian unuan kahelon. Plenumu la tabelon por sendi vian tempon al la rekordlisto.",
    "mj_htp_desc": "Lernu la regulojn de Mahŝongo Solitulo — kongruu liberajn kahelparojn, uzu konsilojn, kaj malplenigu la Testudtabelon.",
    "mj_htp_free_h2": "Kio estas Libera Kahelo?",
    "mj_htp_free_p": "Kahelo estas <strong>libera</strong> kiam du kondiĉoj estas plenumitaj: (1) neniu kahelo estas stakaĵita super ĝi, kaj (2) ĝi estas malferma sur ĝia maldekstra <em>aŭ</em> dekstra flanko — signifante neniu apuda kahelo sur la sama tavolo almenaŭ sur unu flanko.",
    "mj_htp_goal_h2": "La Celo",
    "mj_htp_goal_p": "Forigu ĉiujn 144 kahelojn de la tablo per elektado de kongruaj paroj. Ambaŭ kaheloj en paro devas esti <strong>liberaj</strong>. La ludo estas venkita kiam la tablo estas malplena.",
    "mj_htp_hints_h2": "Konsilbutonoj",
    "mj_htp_hints_p": "<strong>Montri Liberajn Kahelojn</strong> elstarigas ĉiujn nuntempe alireblajn kahelojn en bluo. <strong>Montri Kongruojn</strong> elstarigas liberajn kahelojn kiuj havas almenaŭ unu kongruantan liberan partneron en verdo.",
    "mj_htp_intro": "Mahŝongo Solitulo estas unupersona kahelo-kongruiga ludo. 144 kaheloj estas stakitaj en la klasika Testud-formo. Via celo estas forigi ĉiujn kahelojn per kongruado de identaj liberaj paroj.",
    "mj_htp_refs_h2": "Referencoj",
    "mj_htp_refs_p": 'Ĉi tiu implementado estas bazita sur la malfermitkoda projekto <a href="https://github.com/ffalt/mah" target="_blank" rel="noopener noreferrer">mah</a> de ffalt. Lernu pli pri la ludo en <a href="https://eo.wikipedia.org/wiki/Mahjong_solitulo" target="_blank" rel="noopener noreferrer">Vikipedio</a>.',
    "mj_htp_tiles_h2": "Tipoj de Kaheloj &amp; Kongruado",
    "mj_htp_tiles_p": "La plena aro uzas 144 kahelojn: naŭ Cirkloj (1–9), naŭ Bambuoj (1–9), naŭ Signoj (1–9), kvar Ventoj (Oriento, Sudo, Okcidento, Nordo), tri Drakoj (Ruĝa, Verda, Blanka), kvar Sezonoj, kaj kvar Floroj. Plej multaj kaheloj kongruas nur kun identaj paroj. <strong>Escepto:</strong> iuj ajn du Sezon-kaheloj kongruas unu kun la alia, kaj iuj ajn du Flor-kaheloj kongruas unu kun la alia.",
    "mj_htp_title": "Kiel Ludi Mahŝongon | minesweeper.org",
    "mj_lb_all_heading": "Ĉiam",
    "mj_lb_season_heading": "Ĉi-Monate",
    "mj_lb_tab_all": "Ĉiam",
    "mj_lb_tab_daily": "Hodiaŭ",
    "mj_lb_tab_season": "Ĉi-Monate",
    "mj_name_label": "Nomo",
    "mj_new_game": "Nova Ludo",
    "mj_play_today": "Ludi Hodiaŭ",
    "mj_removed_pairs": "Forigitaj Paroj",
    "mj_same_for_all": "Sama tablo por ĉiuj · Rekomenciĝas je noktomezo UTC",
    "mj_solved": "🎉 Solvita!",
    "mj_submit_btn": "Sendi Poentaron",
    "mj_submit_score": "Sendi vian poentaron",
    "mj_time": "Tempo:",
    "mj_today_heading": "Hodiaŭ — ",
    "mj_undo": "Malfari",
}

# ── German ────────────────────────────────────────────────────────────────────
LANGS["de"] = {
    "mj_hint_free": "Freie Steine anzeigen",
    "mj_hint_match": "Paare anzeigen",
    "mj_htp_back": "Heutiges Rätsel spielen",
    "mj_htp_controls_h2": "Steuerung",
    "mj_htp_controls_li1": "<strong>Klicke auf einen freien Stein</strong>, um ihn auszuwählen (golden hervorgehoben).",
    "mj_htp_controls_li2": "<strong>Klicke auf einen zweiten freien Stein</strong> des gleichen Typs, um das Paar zu entfernen.",
    "mj_htp_controls_li3": "<strong>Klicke erneut auf den ausgewählten Stein</strong>, um die Auswahl aufzuheben.",
    "mj_htp_controls_li4": "<strong>Rückgängig</strong> macht jeweils ein gematchtes Paar rückgängig.",
    "mj_htp_daily_h2": "Tägliches Rätsel",
    "mj_htp_daily_p": "Jeden Tag wird ein neues Spielfeld aus dem heutigen Datum generiert — dasselbe Feld für jeden Spieler weltweit. Der Timer startet, wenn du deinen ersten Stein anklickst. Schließe das Feld ab, um deine Zeit in die Bestenliste einzutragen.",
    "mj_htp_desc": "Lerne die Regeln von Mahjong Solitaire — matche freie Steinpaare, nutze Hinweise und leere das Schildkrötenbrett.",
    "mj_htp_free_h2": "Was ist ein freier Stein?",
    "mj_htp_free_p": "Ein Stein ist <strong>frei</strong>, wenn zwei Bedingungen erfüllt sind: (1) kein Stein liegt darauf gestapelt, und (2) er ist auf seiner linken <em>oder</em> rechten Seite offen — d.h. kein benachbarter Stein auf gleicher Ebene auf mindestens einer Seite.",
    "mj_htp_goal_h2": "Das Ziel",
    "mj_htp_goal_p": "Entferne alle 144 Steine vom Spielfeld, indem du passende Paare auswählst. Beide Steine eines Paares müssen <strong>frei</strong> sein. Das Spiel ist gewonnen, wenn das Feld leer ist.",
    "mj_htp_hints_h2": "Hinweis-Schaltflächen",
    "mj_htp_hints_p": "<strong>Freie Steine anzeigen</strong> hebt alle aktuell zugänglichen Steine blau hervor. <strong>Paare anzeigen</strong> hebt freie Steine, die mindestens einen passenden freien Partner haben, grün hervor.",
    "mj_htp_intro": "Mahjong Solitaire ist ein Einzelspieler-Steinmatch-Spiel. 144 Steine sind in der klassischen Schildkrötenformation gestapelt. Dein Ziel ist es, alle Steine durch das Zuordnen identischer freier Paare zu entfernen.",
    "mj_htp_refs_h2": "Quellen",
    "mj_htp_refs_p": 'Diese Implementierung basiert auf dem Open-Source-Projekt <a href="https://github.com/ffalt/mah" target="_blank" rel="noopener noreferrer">mah</a> von ffalt. Erfahre mehr über das Spiel auf <a href="https://de.wikipedia.org/wiki/Mahjong-Solitaire" target="_blank" rel="noopener noreferrer">Wikipedia</a>.',
    "mj_htp_tiles_h2": "Steintypen &amp; Paare",
    "mj_htp_tiles_p": "Der vollständige Satz umfasst 144 Steine: neun Kreise (1–9), neun Bambus (1–9), neun Zeichen (1–9), vier Winde (Ost, Süd, West, Nord), drei Drachen (Rot, Grün, Weiß), vier Jahreszeiten und vier Blumen. Die meisten Steine passen nur zu identischen Paaren. <strong>Ausnahme:</strong> Beliebige zwei Jahreszeitsteine passen zusammen, und beliebige zwei Blumensteine passen zusammen.",
    "mj_htp_title": "Wie man Mahjong Solitaire spielt | minesweeper.org",
    "mj_lb_all_heading": "Alle Zeit",
    "mj_lb_season_heading": "Diesen Monat",
    "mj_lb_tab_all": "Alle Zeit",
    "mj_lb_tab_daily": "Heute",
    "mj_lb_tab_season": "Diesen Monat",
    "mj_name_label": "Name",
    "mj_new_game": "Neues Spiel",
    "mj_play_today": "Heute spielen",
    "mj_removed_pairs": "Entfernte Paare",
    "mj_same_for_all": "Gleiches Feld für alle · Wird um Mitternacht UTC zurückgesetzt",
    "mj_solved": "🎉 Gelöst!",
    "mj_submit_btn": "Ergebnis einsenden",
    "mj_submit_score": "Dein Ergebnis einsenden",
    "mj_time": "Zeit:",
    "mj_today_heading": "Heute — ",
    "mj_undo": "Rückgängig",
}

# ── Spanish ───────────────────────────────────────────────────────────────────
LANGS["es"] = {
    "mj_hint_free": "Mostrar fichas libres",
    "mj_hint_match": "Mostrar coincidencias",
    "mj_htp_back": "Jugar el puzzle de hoy",
    "mj_htp_controls_h2": "Controles",
    "mj_htp_controls_li1": "<strong>Haz clic en una ficha libre</strong> para seleccionarla (resaltada en dorado).",
    "mj_htp_controls_li2": "<strong>Haz clic en una segunda ficha libre</strong> del mismo tipo para eliminar el par.",
    "mj_htp_controls_li3": "<strong>Haz clic de nuevo en la ficha seleccionada</strong> para deseleccionarla.",
    "mj_htp_controls_li4": "<strong>Deshacer</strong> retrocede un par emparejado a la vez.",
    "mj_htp_daily_h2": "Puzzle diario",
    "mj_htp_daily_p": "Cada día se genera un nuevo tablero a partir de la fecha de hoy — el mismo tablero para todos los jugadores del mundo. El temporizador comienza cuando haces clic en tu primera ficha. Completa el tablero para enviar tu tiempo a la tabla de clasificación.",
    "mj_htp_desc": "Aprende las reglas del Mahjong Solitaire — empareja fichas libres, usa pistas y vacía el tablero Tortuga.",
    "mj_htp_free_h2": "¿Qué es una ficha libre?",
    "mj_htp_free_p": "Una ficha está <strong>libre</strong> cuando se cumplen dos condiciones: (1) ninguna ficha está apilada encima de ella, y (2) está abierta en su lado izquierdo <em>o</em> derecho — es decir, no hay ficha adyacente en la misma capa en al menos un lado.",
    "mj_htp_goal_h2": "El objetivo",
    "mj_htp_goal_p": "Elimina todas las 144 fichas del tablero seleccionando pares coincidentes. Ambas fichas de un par deben estar <strong>libres</strong>. El juego se gana cuando el tablero está vacío.",
    "mj_htp_hints_h2": "Botones de pista",
    "mj_htp_hints_p": "<strong>Mostrar fichas libres</strong> resalta en azul todas las fichas actualmente accesibles. <strong>Mostrar coincidencias</strong> resalta en verde las fichas libres que tienen al menos un compañero libre coincidente.",
    "mj_htp_intro": "El Mahjong Solitaire es un juego de emparejamiento de fichas para un jugador. 144 fichas se apilan en la formación clásica de Tortuga. Tu objetivo es eliminar todas las fichas emparejando pares libres idénticos.",
    "mj_htp_refs_h2": "Referencias",
    "mj_htp_refs_p": 'Esta implementación está basada en el proyecto de código abierto <a href="https://github.com/ffalt/mah" target="_blank" rel="noopener noreferrer">mah</a> de ffalt. Aprende más sobre el juego en <a href="https://es.wikipedia.org/wiki/Mahjong_solitario" target="_blank" rel="noopener noreferrer">Wikipedia</a>.',
    "mj_htp_tiles_h2": "Tipos de fichas y emparejamiento",
    "mj_htp_tiles_p": "El conjunto completo usa 144 fichas: nueve Círculos (1–9), nueve Bambú (1–9), nueve Caracteres (1–9), cuatro Vientos (Este, Sur, Oeste, Norte), tres Dragones (Rojo, Verde, Blanco), cuatro Estaciones y cuatro Flores. La mayoría de las fichas solo coinciden con pares idénticos. <strong>Excepción:</strong> cualesquiera dos fichas de Estación coinciden entre sí, y cualesquiera dos fichas de Flor coinciden entre sí.",
    "mj_htp_title": "Cómo jugar Mahjong Solitaire | minesweeper.org",
    "mj_lb_all_heading": "Siempre",
    "mj_lb_season_heading": "Este mes",
    "mj_lb_tab_all": "Siempre",
    "mj_lb_tab_daily": "Hoy",
    "mj_lb_tab_season": "Este mes",
    "mj_name_label": "Nombre",
    "mj_new_game": "Nuevo juego",
    "mj_play_today": "Jugar hoy",
    "mj_removed_pairs": "Pares eliminados",
    "mj_same_for_all": "Mismo tablero para todos · Se reinicia a medianoche UTC",
    "mj_solved": "🎉 ¡Resuelto!",
    "mj_submit_btn": "Enviar puntuación",
    "mj_submit_score": "Envía tu puntuación",
    "mj_time": "Tiempo:",
    "mj_today_heading": "Hoy — ",
    "mj_undo": "Deshacer",
}

# ── French ────────────────────────────────────────────────────────────────────
LANGS["fr"] = {
    "mj_hint_free": "Afficher les tuiles libres",
    "mj_hint_match": "Afficher les paires",
    "mj_htp_back": "Jouer le puzzle du jour",
    "mj_htp_controls_h2": "Contrôles",
    "mj_htp_controls_li1": "<strong>Cliquez sur une tuile libre</strong> pour la sélectionner (surlignée en or).",
    "mj_htp_controls_li2": "<strong>Cliquez sur une deuxième tuile libre</strong> du même type pour supprimer la paire.",
    "mj_htp_controls_li3": "<strong>Cliquez de nouveau sur la tuile sélectionnée</strong> pour la désélectionner.",
    "mj_htp_controls_li4": "<strong>Annuler</strong> revient une paire appariée à la fois.",
    "mj_htp_daily_h2": "Puzzle quotidien",
    "mj_htp_daily_p": "Chaque jour, un nouveau plateau est généré à partir de la date du jour — le même plateau pour chaque joueur dans le monde. Le chronomètre démarre lorsque vous cliquez sur votre première tuile. Terminez le plateau pour soumettre votre temps au classement.",
    "mj_htp_desc": "Apprenez les règles du Mahjong Solitaire — associez des paires de tuiles libres, utilisez les indices et videz le plateau Tortue.",
    "mj_htp_free_h2": "Qu'est-ce qu'une tuile libre ?",
    "mj_htp_free_p": "Une tuile est <strong>libre</strong> lorsque deux conditions sont remplies : (1) aucune tuile n'est empilée dessus, et (2) elle est ouverte sur son côté gauche <em>ou</em> droit — c'est-à-dire qu'il n'y a pas de tuile adjacente sur la même couche d'au moins un côté.",
    "mj_htp_goal_h2": "L'objectif",
    "mj_htp_goal_p": "Retirez les 144 tuiles du plateau en sélectionnant des paires correspondantes. Les deux tuiles d'une paire doivent être <strong>libres</strong>. Le jeu est gagné quand le plateau est vide.",
    "mj_htp_hints_h2": "Boutons d'indice",
    "mj_htp_hints_p": "<strong>Afficher les tuiles libres</strong> surligne en bleu toutes les tuiles actuellement accessibles. <strong>Afficher les paires</strong> surligne en vert les tuiles libres qui ont au moins un partenaire libre correspondant.",
    "mj_htp_intro": "Le Mahjong Solitaire est un jeu d'association de tuiles pour un seul joueur. 144 tuiles sont empilées dans la formation classique de la Tortue. Votre objectif est de retirer toutes les tuiles en faisant correspondre des paires libres identiques.",
    "mj_htp_refs_h2": "Références",
    "mj_htp_refs_p": 'Cette implémentation est basée sur le projet open-source <a href="https://github.com/ffalt/mah" target="_blank" rel="noopener noreferrer">mah</a> de ffalt. En savoir plus sur le jeu sur <a href="https://fr.wikipedia.org/wiki/Mahjong_solitaire" target="_blank" rel="noopener noreferrer">Wikipédia</a>.',
    "mj_htp_tiles_h2": "Types de tuiles &amp; correspondances",
    "mj_htp_tiles_p": "Le jeu complet utilise 144 tuiles : neuf Cercles (1–9), neuf Bambous (1–9), neuf Caractères (1–9), quatre Vents (Est, Sud, Ouest, Nord), trois Dragons (Rouge, Vert, Blanc), quatre Saisons et quatre Fleurs. La plupart des tuiles ne correspondent qu'à des paires identiques. <strong>Exception :</strong> deux tuiles Saison quelconques correspondent entre elles, et deux tuiles Fleur quelconques correspondent entre elles.",
    "mj_htp_title": "Comment jouer au Mahjong Solitaire | minesweeper.org",
    "mj_lb_all_heading": "Tout temps",
    "mj_lb_season_heading": "Ce mois-ci",
    "mj_lb_tab_all": "Tout temps",
    "mj_lb_tab_daily": "Aujourd'hui",
    "mj_lb_tab_season": "Ce mois-ci",
    "mj_name_label": "Nom",
    "mj_new_game": "Nouvelle partie",
    "mj_play_today": "Jouer aujourd'hui",
    "mj_removed_pairs": "Paires supprimées",
    "mj_same_for_all": "Même plateau pour tous · Réinitialisé à minuit UTC",
    "mj_solved": "🎉 Résolu !",
    "mj_submit_btn": "Soumettre le score",
    "mj_submit_score": "Soumettre votre score",
    "mj_time": "Temps :",
    "mj_today_heading": "Aujourd'hui — ",
    "mj_undo": "Annuler",
}

# ── insertion logic ───────────────────────────────────────────────────────────

def insert_lang(lang):
    import importlib.util
    with open(TRANS, encoding="utf-8") as f:
        lines = f.readlines()

    # Find language section boundaries
    section_starts = {}
    for i, line in enumerate(lines):
        m = re.match(r'\s*"([a-z\-]+)"\s*:\s*\{', line)
        if m:
            section_starts[m.group(1)] = i

    if lang not in section_starts:
        print(f"ERROR: language '{lang}' not found")
        return False

    langs_list = list(section_starts.keys())
    lang_idx = langs_list.index(lang)
    section_start = section_starts[lang]
    section_end = section_starts[langs_list[lang_idx + 1]] if lang_idx + 1 < len(langs_list) else len(lines)

    # Find anchor within section
    insert_after = None
    for i in range(section_start, section_end):
        if f'"{ANCHOR}"' in lines[i]:
            insert_after = i
            break

    if insert_after is None:
        print(f"ERROR: anchor '{ANCHOR}' not found in '{lang}' section")
        return False

    # Check already done
    if insert_after + 1 < len(lines) and '"mj_hint_free"' in lines[insert_after + 1]:
        print(f"SKIP: already present in '{lang}'")
        return True

    block = build_block(LANGS[lang])
    new_lines = lines[:insert_after + 1] + [block] + lines[insert_after + 1:]
    new_src = "".join(new_lines)

    try:
        ast.parse(new_src)
    except SyntaxError as e:
        print(f"SYNTAX ERROR in '{lang}': {e}")
        return False

    with open(TRANS, "w", encoding="utf-8") as f:
        f.write(new_src)
    print(f"OK: {len(LANGS[lang])} keys inserted for '{lang}' after line {insert_after + 1}")
    return True

if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else "eo"
    ok = insert_lang(lang)
    sys.exit(0 if ok else 1)
