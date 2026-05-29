# -*- coding: utf-8 -*-
"""Insert missing nn_* Nonosweeper keys into translations.py.
Anchor: nn_lb_h1 (present in all languages).
Usage: python scripts/insert_nn.py <lang>
"""
import ast, sys, re, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANS = os.path.join(REPO, "translations.py")
ANCHOR = "nav_numbers_match"

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
    "nn_bridge": "Minesweeper renkontas Nonogramon — uzu vicajn kaj kolumnajn indikojn por trovi la minojn.",
    "nn_btn_daily": "📅 Cxiutage",
    "nn_btn_new_random": "🎲 Nova Hazarda",
    "nn_btn_random": "🎲 Hazarda",
    "nn_btn_retry": "🔄 Reprovi",
    "nn_label_potd": "📅 Enigmo de la Tago",
    "nn_overlay_solved": "🎉 Solvita!",
    "nn_save_score": "Konservi Poentaron",
    "nn_lb_today": "🏆 Hodiauxaj Plej Bonaj Tempoj",
    "nn_instructions": "<strong>Maldekstra klako</strong> por malkovri — <em>klakado de mino finas la ludon!</em> &nbsp;|&nbsp; <strong>Dekstra klako</strong> por cikli: flago 💣 &rarr; necerta ? &rarr; kashxita. &nbsp;|&nbsp; <strong>Venku</strong> malkovrante cxiun sekuran celon.",
    "nn_what_h2": "Kio estas Nonosweeper?",
    "nn_what_p1": "Nonosweeper estas hibrida enigmo kiu fuzias du amatatajn enigmoformatojn: la mino-forigan tensiinon de <strong>Minesweeper</strong> kaj la krad-deduktadan logikon de <strong>Nonogramo</strong> (ankaux konata kiel Picross aux Griddler). Male al norma Minesweeper, vi neniam alklakos blinde por malkovri nombrojn — anstatauhe, la plena aro da vicaj kaj kolumnaj indikoj estas videbla de la komenco, ekzakte kiel en nonogramo. Via laboro estas uzi tiujn indikojn por ekscii ekzakte kiuj celoj kashxas minojn, poste alklaki la sekurajn celojn por malkovri ilin.",
    "nn_what_p2": "La Minesweeper-elemento tenas la altajn riskon: unu malghxusta klako sur mino kaj la enigmo finigxas tuj. Ne ekzistas sekura unua klako kaj neniu hazarda diveno estas permesita — cxiu movo devas esti deduktita el la indikoj.",
    "nn_clues_h2": "Kiel legi la indikojn",
    "nn_clues_p1": "Cxiu vico kaj kolumno havas indikon farita el unu aux pli da nombroj. Cxiu nombro reprezentas <strong>sinsekvajn minojn</strong> en tiu vico aux kolumno. La sinsekvo aperas en ordo (de maldekstre al dekstre por vicoj, de supre al malsupre por kolumnoj) kaj estas apartigita de almenauxu unu sekura celo.",
    "nn_clues_p2": 'Ekzemple, vica indiko de <strong>3 &nbsp;1 &nbsp;2</strong> signifas: tri minoj sinsekve, interspaco, unu mino, interspaco, poste du minoj sinsekve. Indiko de <strong>—</strong> signifas neniuj minoj ajn en tiu vico aux kolumno.',
    "nn_diff_h2": "Malfacilegniveloj",
    "nn_diff_beginner": "Komencanto (8x8)",
    "nn_diff_intermediate": "Meznivelo (10x10)",
    "nn_diff_expert": "Eksperto (15x15)",
    "nn_diff_li1": "<strong>Komencanto (8x8, 16 minoj):</strong> Kompakta krado kun mallongaj indikoj. Bona por lerni la mekanikon.",
    "nn_diff_li2": "<strong>Meznivelo (10x10, 35 minoj):</strong> Pli da celoj kaj pli densaj sinsekvo postulas zorgeman krucreferenci.",
    "nn_diff_li3": "<strong>Eksperto (15x15, 75 minoj):</strong> Granda krado kun kompleksaj multi-sinsekvo indikoj — serioza nonograma defio.",
    "nn_strat_h2": "Strategiaj konsiloj",
    "nn_strat_li1": "<strong>Komencu kun nul-indika vicoj/kolumnoj.</strong> Indiko '—' signifas cxiu celo en tiu linio estas sekura — malkovru ilin cxiujn senpage.",
    "nn_strat_li2": "<strong>Uzu superkovri-analizon.</strong> Se sinsekvo estas suficxe granda por ke gxi devas superkovri sin mem en cxiu valida loko, tiuj superkovrantaj celoj estas definitive minoj.",
    "nn_strat_li3": "<strong>Krucreferenci vicojn kaj kolumnojn.</strong> La vica indiko kaj kolumna indiko de celo kune ofte malvastigas ghxian staton tute.",
    "nn_strat_li4": "<strong>Flagu minojn antaux malkovrado.</strong> Kiam vi estas certa ke celo estas mino, flagu ghin antaux klakado de apudaj sekuraj celoj — gxi tenas la minokalkululon preciza kaj la tabelon legebla.",
    "nn_about_h2": "Pri Nonosweeper",
}

# ── Spanish ───────────────────────────────────────────────────────────────────
LANGS["es"] = {
    "nn_bridge": "Buscaminas se encuentra con Nonograma — usa las pistas de filas y columnas para encontrar las minas.",
    "nn_btn_daily": "📅 Diario",
    "nn_btn_new_random": "🎲 Nuevo aleatorio",
    "nn_btn_random": "🎲 Aleatorio",
    "nn_btn_retry": "🔄 Reintentar",
    "nn_label_potd": "📅 Puzzle del día",
    "nn_overlay_solved": "🎉 ¡Resuelto!",
    "nn_save_score": "Guardar puntuación",
    "nn_lb_today": "🏆 Mejores tiempos de hoy",
    "nn_instructions": "<strong>Clic izquierdo</strong> para revelar — <em>¡hacer clic en una mina termina el juego!</em> &nbsp;|&nbsp; <strong>Clic derecho</strong> para ciclar: marcar 💣 &rarr; incierto ? &rarr; oculto. &nbsp;|&nbsp; <strong>Gana</strong> revelando cada celda segura.",
    "nn_what_h2": "¿Qué es Nonosweeper?",
    "nn_what_p1": "Nonosweeper es un puzzle híbrido que fusiona dos formatos de puzzle muy queridos: la tensión del despeje de minas de <strong>Buscaminas</strong> y la lógica de deducción de cuadrícula de un <strong>Nonograma</strong> (también conocido como Picross o Griddler). A diferencia del Buscaminas estándar, nunca haces clic a ciegas para revelar números — en cambio, el conjunto completo de pistas de filas y columnas es visible desde el principio, igual que en un nonograma. Tu trabajo es usar esas pistas para determinar exactamente qué celdas esconden minas y luego hacer clic en las celdas seguras para revelarlas.",
    "nn_what_p2": "El elemento Buscaminas mantiene las apuestas altas: un clic equivocado en una mina y el puzzle termina inmediatamente. No hay primer clic seguro ni adivinar al azar — cada movimiento debe deducirse de las pistas.",
    "nn_clues_h2": "Cómo leer las pistas",
    "nn_clues_p1": "Cada fila y columna tiene una pista compuesta de uno o más números. Cada número representa una <strong>serie consecutiva de minas</strong> en esa fila o columna. Las series aparecen en orden (de izquierda a derecha para filas, de arriba a abajo para columnas) y están separadas por al menos una celda segura.",
    "nn_clues_p2": 'Por ejemplo, una pista de fila de <strong>3 &nbsp;1 &nbsp;2</strong> significa: tres minas seguidas, un hueco, una mina, un hueco, luego dos minas seguidas. Una pista de <strong>—</strong> significa que no hay minas en esa fila o columna.',
    "nn_diff_h2": "Niveles de dificultad",
    "nn_diff_beginner": "Principiante (8×8)",
    "nn_diff_intermediate": "Intermedio (10×10)",
    "nn_diff_expert": "Experto (15×15)",
    "nn_diff_li1": "<strong>Principiante (8×8, 16 minas):</strong> Una cuadrícula compacta con pistas cortas. Bueno para aprender el mecánico.",
    "nn_diff_li2": "<strong>Intermedio (10×10, 35 minas):</strong> Más celdas y series más densas requieren una cuidadosa referencia cruzada.",
    "nn_diff_li3": "<strong>Experto (15×15, 75 minas):</strong> Una cuadrícula grande con pistas complejas de múltiples series — un serio desafío de nonograma.",
    "nn_strat_h2": "Consejos de estrategia",
    "nn_strat_li1": "<strong>Empieza con filas/columnas de pista cero.</strong> Una pista '—' significa que cada celda en esa línea es segura — revélalas todas gratis.",
    "nn_strat_li2": "<strong>Usa el análisis de superposición.</strong> Si una serie es lo suficientemente grande como para superponerse a sí misma en cada colocación válida, esas celdas superpuestas son definitivamente minas.",
    "nn_strat_li3": "<strong>Referencia cruzada entre filas y columnas.</strong> La pista de fila y la pista de columna de una celda juntas a menudo determinan completamente su estado.",
    "nn_strat_li4": "<strong>Marca las minas antes de revelar.</strong> Una vez que estás seguro de que una celda es una mina, márcala antes de hacer clic en las celdas seguras adyacentes — mantiene el contador de minas preciso y el tablero legible.",
    "nn_about_h2": "Sobre Nonosweeper",
}

# ── French ────────────────────────────────────────────────────────────────────
LANGS["fr"] = {
    "nn_bridge": "Le Démineur rencontre le Nonogramme — utilisez les indices de lignes et de colonnes pour trouver les mines.",
    "nn_btn_daily": "📅 Quotidien",
    "nn_btn_new_random": "🎲 Nouveau aléatoire",
    "nn_btn_random": "🎲 Aléatoire",
    "nn_btn_retry": "🔄 Réessayer",
    "nn_label_potd": "📅 Puzzle du jour",
    "nn_overlay_solved": "🎉 Résolu !",
    "nn_save_score": "Sauvegarder le score",
    "nn_lb_today": "🏆 Meilleurs temps du jour",
    "nn_instructions": "<strong>Clic gauche</strong> pour révéler — <em>cliquer sur une mine termine la partie !</em> &nbsp;|&nbsp; <strong>Clic droit</strong> pour cycler : drapeau 💣 &rarr; incertain ? &rarr; caché. &nbsp;|&nbsp; <strong>Gagnez</strong> en révélant chaque cellule sûre.",
    "nn_what_h2": "Qu'est-ce que Nonosweeper ?",
    "nn_what_p1": "Nonosweeper est un puzzle hybride qui fusionne deux formats de puzzle appréciés : la tension du démineur de <strong>Démineur</strong> et la logique de déduction de grille d'un <strong>Nonogramme</strong> (également connu sous le nom de Picross ou Griddler). Contrairement au Démineur standard, vous ne cliquez jamais aveuglément pour révéler des chiffres — au contraire, l'ensemble complet des indices de lignes et de colonnes est visible dès le départ, tout comme dans un nonogramme. Votre travail consiste à utiliser ces indices pour déterminer exactement quelles cellules cachent des mines, puis à cliquer sur les cellules sûres pour les révéler.",
    "nn_what_p2": "L'élément Démineur maintient les enjeux élevés : un mauvais clic sur une mine et le puzzle se termine immédiatement. Il n'y a pas de premier clic sûr et aucune supposition aléatoire n'est autorisée — chaque mouvement doit être déduit des indices.",
    "nn_clues_h2": "Comment lire les indices",
    "nn_clues_p1": "Chaque ligne et colonne a un indice composé d'un ou plusieurs chiffres. Chaque chiffre représente une <strong>séquence consécutive de mines</strong> dans cette ligne ou colonne. Les séquences apparaissent dans l'ordre (de gauche à droite pour les lignes, de haut en bas pour les colonnes) et sont séparées par au moins une cellule sûre.",
    "nn_clues_p2": 'Par exemple, un indice de ligne de <strong>3 &nbsp;1 &nbsp;2</strong> signifie : trois mines d\'affilée, un espace, une mine, un espace, puis deux mines d\'affilée. Un indice de <strong>—</strong> signifie qu\'il n\'y a aucune mine du tout dans cette ligne ou colonne.',
    "nn_diff_h2": "Niveaux de difficulté",
    "nn_diff_beginner": "Débutant (8×8)",
    "nn_diff_intermediate": "Intermédiaire (10×10)",
    "nn_diff_expert": "Expert (15×15)",
    "nn_diff_li1": "<strong>Débutant (8×8, 16 mines) :</strong> Une grille compacte avec des indices courts. Idéal pour apprendre le mécanisme.",
    "nn_diff_li2": "<strong>Intermédiaire (10×10, 35 mines) :</strong> Plus de cellules et des séquences plus denses nécessitent un croisement de références soigneux.",
    "nn_diff_li3": "<strong>Expert (15×15, 75 mines) :</strong> Une grande grille avec des indices complexes à plusieurs séquences — un sérieux défi de nonogramme.",
    "nn_strat_h2": "Conseils stratégiques",
    "nn_strat_li1": "<strong>Commencez par les lignes/colonnes à indice zéro.</strong> Un indice '—' signifie que chaque cellule de cette ligne est sûre — révélez-les toutes gratuitement.",
    "nn_strat_li2": "<strong>Utilisez l'analyse de chevauchement.</strong> Si une séquence est assez grande pour se chevaucher elle-même dans chaque placement valide, ces cellules chevauchées sont définitivement des mines.",
    "nn_strat_li3": "<strong>Faites des références croisées entre lignes et colonnes.</strong> L'indice de ligne et l'indice de colonne d'une cellule ensemble limitent souvent complètement son état.",
    "nn_strat_li4": "<strong>Marquez les mines avant de révéler.</strong> Une fois certain qu'une cellule est une mine, marquez-la avant de cliquer sur les cellules sûres adjacentes — cela maintient le compteur de mines précis et le plateau lisible.",
    "nn_about_h2": "À propos de Nonosweeper",
}

# ── Ukrainian ─────────────────────────────────────────────────────────────────
LANGS["uk"] = {
    "nn_bridge": "Сапер зустрічає Нонограму — використовуйте підказки рядків і стовпців, щоб знайти міни.",
    "nn_btn_daily": "📅 Щоденне",
    "nn_btn_new_random": "🎲 Нове випадкове",
    "nn_btn_random": "🎲 Випадкове",
    "nn_btn_retry": "🔄 Повторити",
    "nn_label_potd": "📅 Задача дня",
    "nn_overlay_solved": "🎉 Вирішено!",
    "nn_save_score": "Зберегти рахунок",
    "nn_lb_today": "🏆 Найкращі часи сьогодні",
    "nn_instructions": "<strong>Лівий клік</strong> для відкриття — <em>клік на міну завершує гру!</em> &nbsp;|&nbsp; <strong>Правий клік</strong> для циклу: прапорець 💣 &rarr; невизначено ? &rarr; приховано. &nbsp;|&nbsp; <strong>Виграйте</strong>, відкривши кожну безпечну клітинку.",
    "nn_what_h2": "Що таке Nonosweeper?",
    "nn_what_p1": "Nonosweeper — це гібридна головоломка, що поєднує два улюблені формати: напругу очищення від мін у <strong>Сапері</strong> та логіку дедукції сітки <strong>Нонограми</strong> (також відомої як Picross або Griddler). На відміну від стандартного Сапера, ви ніколи не натискаєте навмання, щоб відкрити числа — натомість повний набір підказок рядків і стовпців видимий з самого початку, як і в нонограмі. Ваше завдання — використовувати ці підказки, щоб визначити, які клітинки приховують міни, а потім натискати на безпечні клітинки, щоб відкрити їх.",
    "nn_what_p2": "Елемент Сапера підтримує ставки на високому рівні: один неправильний клік на міну — і головоломка негайно закінчується. Немає безпечного першого кліку і не допускається випадкове вгадування — кожен хід має бути виведений з підказок.",
    "nn_clues_h2": "Як читати підказки",
    "nn_clues_p1": "Кожен рядок і стовпець має підказку, яка складається з одного або більше чисел. Кожне число представляє <strong>послідовний ряд мін</strong> у цьому рядку або стовпці. Ряди з'являються по порядку (зліва направо для рядків, зверху вниз для стовпців) і розділені принаймні однією безпечною клітинкою.",
    "nn_clues_p2": 'Наприклад, підказка рядка <strong>3 &nbsp;1 &nbsp;2</strong> означає: три міни підряд, проміжок, одна міна, проміжок, потім дві міни підряд. Підказка <strong>—</strong> означає, що в цьому рядку або стовпці немає мін.',
    "nn_diff_h2": "Рівні складності",
    "nn_diff_beginner": "Початківець (8×8)",
    "nn_diff_intermediate": "Середній (10×10)",
    "nn_diff_expert": "Експерт (15×15)",
    "nn_diff_li1": "<strong>Початківець (8×8, 16 мін):</strong> Компактна сітка з короткими підказками. Добре для вивчення механіки.",
    "nn_diff_li2": "<strong>Середній (10×10, 35 мін):</strong> Більше клітинок і щільніші ряди вимагають ретельного перехресного посилання.",
    "nn_diff_li3": "<strong>Експерт (15×15, 75 мін):</strong> Велика сітка зі складними підказками з кількома рядами — серйозний виклик нонограми.",
    "nn_strat_h2": "Стратегічні поради",
    "nn_strat_li1": "<strong>Починайте з рядків/стовпців з нульовою підказкою.</strong> Підказка '—' означає, що кожна клітинка в цьому рядку безпечна — відкрийте їх усі безкоштовно.",
    "nn_strat_li2": "<strong>Використовуйте аналіз перекриття.</strong> Якщо ряд досить великий, щоб перекриватися в кожному дійсному розміщенні, ці клітинки, що перекриваються, є однозначно мінами.",
    "nn_strat_li3": "<strong>Перехресно посилайтеся на рядки та стовпці.</strong> Підказки рядка та стовпця клітинки разом часто повністю звужують її стан.",
    "nn_strat_li4": "<strong>Позначайте міни перед відкриттям.</strong> Коли ви впевнені, що клітинка є міною, позначте її перед натисканням на сусідні безпечні клітинки — це підтримує точний лічильник мін і читабельну дошку.",
    "nn_about_h2": "Про Nonosweeper",
}

# ── insertion logic ───────────────────────────────────────────────────────────
def insert_lang(lang):
    with open(TRANS, encoding="utf-8") as f:
        lines = f.readlines()
    section_starts = {}
    for i, line in enumerate(lines):
        m = re.match(r'\s*"([a-z\-]+)"\s*:\s*\{', line)
        if m:
            section_starts[m.group(1)] = i
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
