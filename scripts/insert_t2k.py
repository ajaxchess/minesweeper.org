# -*- coding: utf-8 -*-
"""Insert missing t2k_* keys into translations.py.
Inserts only the keys not yet present, after the 't2k_lb_h1' anchor.
Usage: python scripts/insert_t2k.py <lang>
"""
import ast, sys, re, os, importlib.util

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANS = os.path.join(REPO, "translations.py")
ANCHOR = "t2k_lb_h1"

def esc(s):
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    return s

def build_block(keys, existing_keys):
    """Build insert block, skipping keys already present in the section."""
    lines = []
    for k, v in keys.items():
        if k not in existing_keys:
            lines.append(f'        "{k}": "{esc(v)}",')
    return ("\n".join(lines) + "\n") if lines else ""

LANGS = {}

# ── Esperanto ─────────────────────────────────────────────────────────────────
LANGS["eo"] = {
    "t2k_game_over": "😥 Ludo Finita",
    "t2k_htp_back": "← Ludi Hodiauan Enigmon",
    "t2k_htp_controls_desktop_li1": "<strong>Sagaj klavoj</strong> au <strong>W A S D</strong> — glitigu ciujn kahelojn en tiu direkto.",
    "t2k_htp_controls_desktop_li2": "Ciu klavo estas unu movo, ecx se nur unu kahelo movigxas.",
    "t2k_htp_controls_footer": "Uzu la butonon <strong>Nova Ludo</strong> por restarigi la tabelon kaj rekomenci iam ajn.",
    "t2k_htp_controls_h2": "Kontroloj",
    "t2k_htp_controls_mobile_li1": "<strong>Svipigi</strong> supren, malsupren, maldekstren, aux dekstren por glitigu ciujn kahelojn en tiu direkto.",
    "t2k_htp_controls_mobile_li2": "Cxiu svipo estas unu movo, ecx se nur unu kahelo movigxas.",
    "t2k_htp_daily_h2": "Cxiutaga Enigmo",
    "t2k_htp_daily_p1": "Cxiun tagon nova enigmo estas semita — la sama komenca tablo por cxiu ludanto tutmonde. La enigmo ricevas restarigon ce noktomezo UTC. Cxiuj ludantoj de la cxiutaga enigmo en difinita tago komencas de identika kahel-arangxo, igante gxin justa kapokonflikto.",
    "t2k_htp_daily_p2": 'Post plenumado de la cxiutaga enigmo vi povas sendi vian poentaron al la <a href="/other/2048/leaderboard">2048 rekordlisto</a>. Vi devas esti ensalutinta por sendi.',
    "t2k_htp_desc": "Lernu kiel ludi 2048 — la klasika kahel-kunsxovanta enigmo. Komprenu la regulojn, kontrolojn, poentadon kaj strategion por atingi la 2048-kahelon.",
    "t2k_htp_goal_h2": "La Celo",
    "t2k_htp_goal_p1": "Glitu kahelojn sur la krado por kunfandi identajn nombrojn. Kiam du kaheloj kun la sama valoro kolizias, ili kombinas en unu solan kahelon valoran duoble — 2 kaj 2 farigxas 4, du 4-oj farigxas 8, kaj tiel plu. La celo estas konstrui kahelon kiu atingas <strong>2048</strong>.",
    "t2k_htp_goal_p2": "Vi povas dauxri ludi post atingi 2048 por igi vian poentaron pli alta. La ludo finigxas kiam neniuj movoj restas — la krado estas plena kaj neniuj apudaj kaheloj havas la saman valoron.",
    "t2k_htp_intro": "2048 estas glitanta kahela enigmo ludata sur 4x4 krado. Kombinu kongruantajn numeritajn kahelojn glitante ilin en kvar direktoj. Cxiu movo aperas nova kahelo. Atingu la 2048-kahelon por venki — aux dauxrigu por pli alta poentaro.",
    "t2k_htp_scoring_h2": "Poentado",
    "t2k_htp_scoring_p1": "Cxiu kunfando aldonas la valoron de la nova kombinita kahelo al via poentaro. Kunfandi du 512-kahelojn en 1024-kahelon aldonas 1024 punktojn. Cxeni plurajn kunfandojn en unu movo aldonas ilin cxiujn kune.",
    "t2k_htp_scoring_p2": 'En la cxiutaga enigmo, via fina poentaro, mova kalkulo, kaj tempo estas registritaj kaj senditaj al la <a href="/other/2048/leaderboard">rekordlisto</a>. La rekordlisto rangordas unue laux poentaro (pli alta estas pli bone), poste laux tempo (malpli alta estas pli bone).',
    "t2k_htp_strategy_h2": "Baza Strategio",
    "t2k_htp_strategy_p1": "<strong>Elektu angulon kaj dediku al gxi.</strong> Elektu unu angulon — kutime malsupran angulon — kaj tenu vian plej valoran kahelon tie. Konstruu malpliigxantan cxenon de kaheloj laux la rando forigxanta de gxi tiel ke cxiu kunfando nature enmalsupreniras en la sekvan.",
    "t2k_htp_strategy_p2": "<strong>Neniam glitu for de via ankra angulo.</strong> Evitu movojn kiuj tiris vian plej grandan kahelon for de gxia angulo. Ekzemple, se via plej alta kahelo estas en la malsupra-maldekstra, evitu gliton supren krom se gxi estas absolute necesa. Perdi kontrolon de la angulo estas kiel plej multaj ludoj finigxas.",
    "t2k_htp_strategy_p3": "<strong>Tenu la supran vicon plenan.</strong> Unufoje vi havas cxenon transen la supran aux malsupran randon, provu teni tiun vicon plenan cxiam. Cxi tio devigas novajn kahelojn aperi aliloke kaj konservas vian cxenon.",
    "t2k_htp_strategy_p4": "<strong>Pensu anticipe.</strong> Antaux cxiu movo, konsideru kie la nova kahelo povus aperi kaj cxu gxi malordigos vian arangxon. Movoj kiuj lasas la tabelon en nerehavebla stato estas kutime signon ke vi movigxis sen penso.",
    "t2k_htp_tiles_h2": "Kahel-Valoroj",
    "t2k_htp_tiles_p1": "Kaheloj cxiam komencas kiel 2 aux 4 — estas 90% sxanco de 2 kaj 10% sxanco de 4. Novaj kaheloj aperas hazarde en malplena cxelo post cxiu movo. La sekvenco de valoroj duobligxas kun cxiu kunfando: 2 -> 4 -> 8 -> 16 -> 32 -> 64 -> 128 -> 256 -> 512 -> 1024 -> 2048 kaj preter.",
    "t2k_htp_tiles_p2": "Nur kaheloj kun la sama valoro povas kunfandi, kaj cxiu kahelo povas kunfandi maksimume unufoje per movo.",
    "t2k_htp_title": "Kiel Ludi 2048 | minesweeper.org",
    "t2k_keep_going": "Dauxrigi",
    "t2k_score": "Poentaro:",
    "t2k_solved": "Vi atingis 2048!",
}

# ── German ────────────────────────────────────────────────────────────────────
LANGS["de"] = {
    "t2k_htp_back": "← Heutiges Tagespuzzle spielen",
    "t2k_htp_controls_desktop_li1": "<strong>Pfeiltasten</strong> oder <strong>W A S D</strong> — alle Kacheln in diese Richtung schieben.",
    "t2k_htp_controls_desktop_li2": "Jeder Tastendruck ist ein Zug, auch wenn sich nur eine Kachel bewegt.",
    "t2k_htp_controls_footer": "Benutze die Schaltflasche <strong>Neues Spiel</strong>, um das Feld zurueckzusetzen und jederzeit neu zu beginnen.",
    "t2k_htp_controls_h2": "Steuerung",
    "t2k_htp_controls_mobile_li1": "<strong>Wischen</strong> nach oben, unten, links oder rechts, um alle Kacheln in diese Richtung zu schieben.",
    "t2k_htp_controls_mobile_li2": "Jedes Wischen ist ein Zug, auch wenn sich nur eine Kachel bewegt.",
    "t2k_htp_daily_h2": "Tagliches Ratsel",
    "t2k_htp_daily_p1": "Jeden Tag wird ein neues Ratsel generiert — das gleiche Startfeld fur jeden Spieler weltweit. Das Ratsel setzt sich um Mitternacht UTC zuruck. Alle Spieler des taglichen Ratsels an einem bestimmten Tag beginnen mit dem gleichen Kachel-Layout, was einen fairen Direktvergleich ergibt.",
    "t2k_htp_daily_p2": 'Nach dem Abschliessen des Tagesratsels kannst du deinen Punktestand an die <a href="/other/2048/leaderboard">2048-Bestenliste</a> senden. Du musst angemeldet sein, um einsenden zu konnen.',
    "t2k_htp_desc": "Lerne, wie man 2048 spielt — das klassische Kachel-Zusammenfuhrungsratsel. Verstehe die Regeln, Steuerung, Punktewertung und Strategie, um die 2048-Kachel zu erreichen.",
    "t2k_htp_goal_h2": "Das Ziel",
    "t2k_htp_goal_p1": "Schiebe Kacheln auf dem Gitter, um gleiche Zahlen zusammenzufuhren. Wenn zwei Kacheln mit dem gleichen Wert zusammenstossen, verbinden sie sich zu einer einzigen Kachel mit doppeltem Wert — aus einer 2 und einer 2 wird eine 4, aus zwei 4en eine 8 usw. Das Ziel ist es, eine Kachel mit dem Wert <strong>2048</strong> zu bauen.",
    "t2k_htp_goal_p2": "Du kannst nach Erreichen von 2048 weiterspielen, um deinen Punktestand zu erhohen. Das Spiel endet, wenn keine Zuge mehr moglich sind — das Gitter ist voll und keine benachbarten Kacheln teilen den gleichen Wert.",
    "t2k_htp_intro": "2048 ist ein Schiebepuzzle auf einem 4x4-Gitter. Kombiniere gleichwertige Zahlenkacheln, indem du sie in vier Richtungen schiebst. Nach jedem Zug erscheint eine neue Kachel. Erreiche die 2048-Kachel, um zu gewinnen — oder spiele weiter fur einen hoheren Punktestand.",
    "t2k_htp_scoring_h2": "Punktewertung",
    "t2k_htp_scoring_p1": "Jede Zusammenfuhrung addiert den Wert der neuen kombinierten Kachel zu deinem Punktestand. Das Zusammenfuhren zweier 512er-Kacheln zu einer 1024er-Kachel gibt 1024 Punkte. Mehrere Zusammenfuhrungen in einem Zug werden alle addiert.",
    "t2k_htp_scoring_p2": 'Beim taglichen Ratsel werden dein Endergebnis, die Zuganzahl und die Zeit aufgezeichnet und an die <a href="/other/2048/leaderboard">Bestenliste</a> ubermittelt. Die Bestenliste sortiert zuerst nach Punktzahl (hoher ist besser), dann nach Zeit (niedriger ist besser).',
    "t2k_htp_strategy_h2": "Grundstrategie",
    "t2k_htp_strategy_p1": "<strong>Wahle eine Ecke und bleibe dabei.</strong> Wahle eine Ecke — normalerweise eine untere Ecke — und halte deine wertvollste Kachel dort. Baue eine absteigende Kette von Kacheln entlang des Randes, der davon wegfuhrt, damit jede Zusammenfuhrung naturlich in die nachste einfliesst.",
    "t2k_htp_strategy_p2": "<strong>Schiebe niemals von deiner Ankerecke weg.</strong> Vermeide Zuge, die deine grosste Kachel von ihrer Ecke wegziehen. Wenn deine hochste Kachel beispielsweise unten links ist, vermeide es nach oben zu schieben, sofern es nicht unbedingt notwendig ist. Die Kontrolle uber die Ecke zu verlieren ist der Grund, warum die meisten Spiele enden.",
    "t2k_htp_strategy_p3": "<strong>Halte die oberste Zeile voll.</strong> Sobald du eine Kette uber den oberen oder unteren Rand hast, versuche diese Zeile jederzeit voll zu halten. Dadurch mussen neue Kacheln woanders erscheinen und deine Kette bleibt erhalten.",
    "t2k_htp_strategy_p4": "<strong>Denke im Voraus.</strong> Uberlege vor jedem Zug, wo die neue Kachel erscheinen konnte und ob sie dein Layout storen wird. Zuge, die das Feld in einem nicht wiederherstellbaren Zustand zurucklassen, sind meist ein Zeichen dafur, dass du ohne Nachdenken gezogen hast.",
    "t2k_htp_tiles_h2": "Kachelwerte",
    "t2k_htp_tiles_p1": "Kacheln beginnen immer als 2 oder 4 — es gibt eine 90%ige Chance auf eine 2 und eine 10%ige Chance auf eine 4. Neue Kacheln erscheinen nach jedem Zug zufallig in einer leeren Zelle. Die Wertesequenz verdoppelt sich mit jeder Zusammenfuhrung: 2 -> 4 -> 8 -> 16 -> 32 -> 64 -> 128 -> 256 -> 512 -> 1024 -> 2048 und daruber hinaus.",
    "t2k_htp_tiles_p2": "Nur Kacheln mit dem gleichen Wert konnen zusammengefuhrt werden, und jede Kachel kann pro Zug maximal einmal zusammengefuhrt werden.",
    "t2k_htp_title": "Wie man 2048 spielt | minesweeper.org",
}

# ── Spanish ───────────────────────────────────────────────────────────────────
LANGS["es"] = {
    "t2k_game_over": "😥 Fin del juego",
    "t2k_htp_back": "← Jugar el puzzle de hoy",
    "t2k_htp_controls_desktop_li1": "<strong>Teclas de flecha</strong> o <strong>W A S D</strong> — desliza todas las fichas en esa dirección.",
    "t2k_htp_controls_desktop_li2": "Cada tecla es un movimiento, incluso si solo una ficha se desplaza.",
    "t2k_htp_controls_footer": "Usa el botón <strong>Nuevo juego</strong> para reiniciar el tablero y comenzar de nuevo en cualquier momento.",
    "t2k_htp_controls_h2": "Controles",
    "t2k_htp_controls_mobile_li1": "<strong>Desliza</strong> hacia arriba, abajo, izquierda o derecha para mover todas las fichas en esa dirección.",
    "t2k_htp_controls_mobile_li2": "Cada deslizamiento es un movimiento, incluso si solo se desplaza una ficha.",
    "t2k_htp_daily_h2": "Puzzle diario",
    "t2k_htp_daily_p1": "Cada día se genera un nuevo puzzle — el mismo tablero inicial para cada jugador en el mundo. El puzzle se reinicia a medianoche UTC. Todos los que juegan el puzzle diario en un día dado comienzan desde un diseño de fichas idéntico, lo que lo convierte en una competencia justa.",
    "t2k_htp_daily_p2": 'Después de completar el puzzle diario puedes enviar tu puntuación a la <a href="/other/2048/leaderboard">tabla de clasificación de 2048</a>. Debes haber iniciado sesión para enviar.',
    "t2k_htp_desc": "Aprende a jugar 2048 — el clásico puzzle de combinar fichas. Comprende las reglas, controles, puntuación y estrategia para alcanzar la ficha 2048.",
    "t2k_htp_goal_h2": "El objetivo",
    "t2k_htp_goal_p1": "Desliza fichas en la cuadrícula para combinar números idénticos. Cuando dos fichas con el mismo valor colisionan, se combinan en una sola ficha que vale el doble — un 2 y un 2 se convierten en 4, dos 4s en 8, y así sucesivamente. El objetivo es construir una ficha que alcance <strong>2048</strong>.",
    "t2k_htp_goal_p2": "Puedes seguir jugando después de alcanzar 2048 para aumentar tu puntuación. El juego termina cuando no quedan movimientos — la cuadrícula está llena y ninguna ficha adyacente comparte el mismo valor.",
    "t2k_htp_intro": "2048 es un puzzle de fichas deslizantes jugado en una cuadrícula de 4×4. Combina fichas numéricas iguales deslizándolas en cuatro direcciones. Con cada movimiento aparece una nueva ficha. Alcanza la ficha 2048 para ganar — o sigue jugando para una puntuación más alta.",
    "t2k_htp_scoring_h2": "Puntuación",
    "t2k_htp_scoring_p1": "Cada combinación añade el valor de la nueva ficha combinada a tu puntuación. Combinar dos fichas de 512 en una ficha de 1024 añade 1024 puntos. Encadenar varias combinaciones en un movimiento las suma todas.",
    "t2k_htp_scoring_p2": 'En el puzzle diario, tu puntuación final, número de movimientos y tiempo se registran y envían a la <a href="/other/2048/leaderboard">tabla de clasificación</a>. La clasificación ordena primero por puntuación (más alta es mejor) y luego por tiempo (más bajo es mejor).',
    "t2k_htp_strategy_h2": "Estrategia básica",
    "t2k_htp_strategy_p1": "<strong>Elige una esquina y compórtate con ella.</strong> Elige una esquina — normalmente una esquina inferior — y mantén tu ficha de mayor valor allí. Construye una cadena descendente de fichas a lo largo del borde que se aleja de ella para que cada combinación alimente naturalmente a la siguiente.",
    "t2k_htp_strategy_p2": "<strong>Nunca deslices lejos de tu esquina de anclaje.</strong> Evita movimientos que alejen tu ficha más grande de su esquina. Por ejemplo, si tu ficha más alta está en la parte inferior izquierda, evita deslizar hacia arriba a menos que sea absolutamente necesario. Perder el control de la esquina es cómo terminan la mayoría de los juegos.",
    "t2k_htp_strategy_p3": "<strong>Mantén la fila superior llena.</strong> Una vez que tengas una cadena a lo largo del borde superior o inferior, intenta mantener esa fila siempre llena. Esto obliga a que aparezcan nuevas fichas en otro lugar y preserva tu cadena.",
    "t2k_htp_strategy_p4": "<strong>Piensa con anticipación.</strong> Antes de cada movimiento, considera dónde podría aparecer la nueva ficha y si interrumpirá tu disposición. Los movimientos que dejan el tablero en un estado irrecuperable suelen ser una señal de que te moviste sin pensar.",
    "t2k_htp_tiles_h2": "Valores de fichas",
    "t2k_htp_tiles_p1": "Las fichas siempre comienzan como 2 o 4 — hay un 90% de probabilidad de un 2 y un 10% de un 4. Las nuevas fichas aparecen aleatoriamente en una celda vacía después de cada movimiento. La secuencia de valores se duplica con cada combinación: 2 → 4 → 8 → 16 → 32 → 64 → 128 → 256 → 512 → 1024 → 2048 y más allá.",
    "t2k_htp_tiles_p2": "Solo las fichas con el mismo valor pueden combinarse, y cada ficha puede combinarse como máximo una vez por movimiento.",
    "t2k_htp_title": "Cómo jugar 2048 | minesweeper.org",
    "t2k_keep_going": "Seguir jugando",
    "t2k_score": "Puntuación:",
    "t2k_solved": "¡Llegaste a 2048!",
}

# ── French ────────────────────────────────────────────────────────────────────
LANGS["fr"] = {
    "t2k_game_over": "😥 Partie terminée",
    "t2k_htp_back": "← Jouer le puzzle du jour",
    "t2k_htp_controls_desktop_li1": "<strong>Touches fléchées</strong> ou <strong>W A S D</strong> — faites glisser toutes les tuiles dans cette direction.",
    "t2k_htp_controls_desktop_li2": "Chaque appui de touche est un mouvement, même si une seule tuile se déplace.",
    "t2k_htp_controls_footer": "Utilisez le bouton <strong>Nouvelle partie</strong> pour réinitialiser le plateau et recommencer à tout moment.",
    "t2k_htp_controls_h2": "Contrôles",
    "t2k_htp_controls_mobile_li1": "<strong>Glissez</strong> vers le haut, le bas, la gauche ou la droite pour faire glisser toutes les tuiles dans cette direction.",
    "t2k_htp_controls_mobile_li2": "Chaque glissement est un mouvement, même si une seule tuile se déplace.",
    "t2k_htp_daily_h2": "Puzzle quotidien",
    "t2k_htp_daily_p1": "Chaque jour, un nouveau puzzle est généré — le même plateau de départ pour chaque joueur dans le monde. Le puzzle se réinitialise à minuit UTC. Tous ceux qui jouent le puzzle quotidien un jour donné partent d'une disposition de tuiles identique, en faisant une compétition équitable.",
    "t2k_htp_daily_p2": 'Après avoir complété le puzzle quotidien, vous pouvez soumettre votre score au <a href="/other/2048/leaderboard">classement 2048</a>. Vous devez être connecté pour soumettre.',
    "t2k_htp_desc": "Apprenez à jouer à 2048 — le puzzle classique de fusion de tuiles. Comprenez les règles, les contrôles, le système de points et la stratégie pour atteindre la tuile 2048.",
    "t2k_htp_goal_h2": "L'objectif",
    "t2k_htp_goal_p1": "Faites glisser des tuiles sur la grille pour fusionner des nombres identiques. Quand deux tuiles de même valeur entrent en collision, elles se combinent en une seule tuile valant le double — un 2 et un 2 deviennent 4, deux 4 deviennent 8, etc. L'objectif est de construire une tuile qui atteint <strong>2048</strong>.",
    "t2k_htp_goal_p2": "Vous pouvez continuer à jouer après avoir atteint 2048 pour augmenter votre score. Le jeu se termine quand il ne reste plus de coups — la grille est pleine et aucune tuile adjacente ne partage la même valeur.",
    "t2k_htp_intro": "2048 est un puzzle à tuiles coulissantes joué sur une grille 4×4. Combinez des tuiles numérotées identiques en les faisant glisser dans quatre directions. À chaque mouvement, une nouvelle tuile apparaît. Atteignez la tuile 2048 pour gagner — ou continuez pour un score plus élevé.",
    "t2k_htp_scoring_h2": "Système de points",
    "t2k_htp_scoring_p1": "Chaque fusion ajoute la valeur de la nouvelle tuile combinée à votre score. Fusionner deux tuiles de 512 en une tuile de 1024 ajoute 1024 points. Enchâner plusieurs fusions en un seul mouvement les additionne toutes.",
    "t2k_htp_scoring_p2": 'Pour le puzzle quotidien, votre score final, le nombre de coups et le temps sont enregistrés et soumis au <a href="/other/2048/leaderboard">classement</a>. Le classement trie d\'abord par score (plus élevé est mieux), puis par temps (plus bas est mieux).',
    "t2k_htp_strategy_h2": "Stratégie de base",
    "t2k_htp_strategy_p1": "<strong>Choisissez un coin et engagez-vous.</strong> Choisissez un coin — généralement un coin inférieur — et gardez votre tuile de plus grande valeur là. Construisez une chaîne descendante de tuiles le long du bord s'éloignant de lui pour que chaque fusion alimente naturellement la suivante.",
    "t2k_htp_strategy_p2": "<strong>Ne glissez jamais loin de votre coin d'ancrage.</strong> Évitez les mouvements qui éloignent votre plus grande tuile de son coin. Par exemple, si votre tuile la plus haute est en bas à gauche, évitez de glisser vers le haut sauf si c'est absolument nécessaire. Perdre le contrôle du coin, c'est ainsi que la plupart des parties se terminent.",
    "t2k_htp_strategy_p3": "<strong>Gardez la rangée du haut pleine.</strong> Une fois que vous avez une chaîne sur le bord supérieur ou inférieur, essayez de garder cette rangée pleine en permanence. Cela force les nouvelles tuiles à apparaître ailleurs et préserve votre chaîne.",
    "t2k_htp_strategy_p4": "<strong>Pensez à l'avance.</strong> Avant chaque mouvement, considérez où la nouvelle tuile pourrait apparaître et si elle perturbera votre disposition. Les mouvements qui laissent le plateau dans un état irrécupérable sont généralement le signe que vous avez bougé sans réfléchir.",
    "t2k_htp_tiles_h2": "Valeurs des tuiles",
    "t2k_htp_tiles_p1": "Les tuiles commencent toujours par 2 ou 4 — il y a 90% de chance d'avoir un 2 et 10% d'avoir un 4. De nouvelles tuiles apparaissent aléatoirement dans une cellule vide après chaque mouvement. La séquence de valeurs double à chaque fusion : 2 → 4 → 8 → 16 → 32 → 64 → 128 → 256 → 512 → 1024 → 2048 et au-delà.",
    "t2k_htp_tiles_p2": "Seules les tuiles de même valeur peuvent fusionner, et chaque tuile ne peut fusionner qu'une seule fois par mouvement.",
    "t2k_htp_title": "Comment jouer à 2048 | minesweeper.org",
    "t2k_keep_going": "Continuer",
    "t2k_score": "Score :",
    "t2k_solved": "Vous avez atteint 2048 !",
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
        print(f"ERROR: language '{lang}' not found")
        return False

    langs_list = list(section_starts.keys())
    lang_idx = langs_list.index(lang)
    section_start = section_starts[lang]
    section_end = section_starts[langs_list[lang_idx + 1]] if lang_idx + 1 < len(langs_list) else len(lines)

    # Collect existing keys in this section
    existing_keys = set()
    for i in range(section_start, section_end):
        m = re.match(r'\s*"([^"]+)"\s*:', lines[i])
        if m:
            existing_keys.add(m.group(1))

    # Find anchor
    insert_after = None
    for i in range(section_start, section_end):
        if f'"{ANCHOR}"' in lines[i]:
            insert_after = i
            break

    if insert_after is None:
        print(f"ERROR: anchor '{ANCHOR}' not found in '{lang}'")
        return False

    block = build_block(LANGS[lang], existing_keys)
    if not block.strip():
        print(f"SKIP: all keys already present in '{lang}'")
        return True

    new_lines = lines[:insert_after + 1] + [block] + lines[insert_after + 1:]
    new_src = "".join(new_lines)

    try:
        ast.parse(new_src)
    except SyntaxError as e:
        print(f"SYNTAX ERROR in '{lang}': {e}")
        return False

    with open(TRANS, "w", encoding="utf-8") as f:
        f.write(new_src)
    added = len([k for k in LANGS[lang] if k not in existing_keys])
    print(f"OK: {added} keys inserted for '{lang}' after line {insert_after + 1}")
    return True

if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else "eo"
    ok = insert_lang(lang)
    sys.exit(0 if ok else 1)
