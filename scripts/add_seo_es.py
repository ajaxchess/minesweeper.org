#!/usr/bin/env python3
"""Insert seo_* keys for Spanish (es) locale into translations.py"""

ES = {
    "seo_beg_h2": "Jugar al Buscaminas Online — Gratis",
    "seo_beg_p1": 'Este es el tablero Principiante: una <strong>cuadrícula 9×9 con 10 minas ocultas</strong>. Es el punto de partida clásico — lo suficientemente pequeño para terminar en menos de un minuto cuando conoces las reglas, lo suficientemente grande para enseñar todas las técnicas fundamentales. Clic izquierdo para revelar una celda. Clic derecho para colocar una bandera en una mina sospechosa. Cuando todas las minas están marcadas y todas las celdas seguras están abiertas, ganas.',
    "seo_beg_p2": 'Cada número en el tablero indica cuántas minas están ocultas en las ocho celdas que lo rodean. ¿Un <em>1</em> junto a una celda esquinera con solo dos vecinos sin revelar? Una de esas dos es una mina. ¿Un <em>0</em>? No hay minas cerca — el tablero se expande automáticamente por todas las celdas vacías adyacentes. Todo el juego consiste en leer esos números y deducir dónde deben estar las minas.',
    "seo_about_h2": "Sobre Este Sitio",
    "seo_about_p1": 'minesweeper.org — apodado <strong>Las Minas de Lady Di</strong> — es una plataforma de Buscaminas gratuita en el navegador. Sin descarga, sin instalación, sin cuenta necesaria. Creado por un pequeño equipo de desarrolladores que querían una implementación rápida y limpia que respete las reglas clásicas añadiendo comodidades modernas: tablas de clasificación diarias, modo sin adivinanzas, tiempos con estadísticas 3BV y una colección creciente de variantes.',
    "seo_about_p2": 'La conexión con Diana es una broma interna convertida en marca: <em>Las Minas de Lady Di</em>. A medio camino entre un homenaje y un juego de palabras terrible. Lo abrazamos.',
    "seo_diff_h2": "Niveles de Dificultad",
    "seo_diff_li1": '<strong>Principiante (esta página) —</strong> Cuadrícula 9×9, 10 minas. ~12,3 % de densidad. Aprende las reglas, desarrolla memoria muscular, busca tiempos por debajo de 10 segundos.',
    "seo_diff_li2": '<strong><a href="/intermediate">Intermedio</a> —</strong> Cuadrícula 16×16, 40 minas. ~15,6 % de densidad. Cadenas más largas, deducciones más complejas, donde la mayoría de los jugadores se estancan.',
    "seo_diff_li3": '<strong><a href="/expert">Experto</a> —</strong> Cuadrícula 30×16, 99 minas. ~20,6 % de densidad. El referente. Aquí viven los récords mundiales. Peligroso en cada turno.',
    "seo_diff_li4": '<strong><a href="/custom">Personalizado</a> —</strong> Establece tus propias dimensiones de tablero y número de minas para un desafío a medida.',
    "seo_tips_h2": "Consejos para Empezar",
    "seo_tips_li1": '<strong>Haz clic cerca del centro primero.</strong> El primer clic siempre es seguro y tiende a abrir una mayor cascada desde una posición central.',
    "seo_tips_li2": '<strong>Encuentra los ceros.</strong> Una región vacía que se expande automáticamente te da información gratuita y revela muchos bordes numerados desde los que trabajar.',
    "seo_tips_li3": '<strong>¿Bandera o solo recordar?</strong> No tienes que marcar todas las minas — las banderas son solo marcadores. Muchos jugadores rápidos omiten las banderas y usan la memoria para mantener bajo el número de clics.',
    "seo_tips_li4": '<strong>Usa el modo sin adivinanzas</strong> si odias perder ante situaciones 50/50. Genera tableros siempre resolubles de forma lógica.',
    "seo_tips_li5": '<strong>Usa el acorde para ir más rápido.</strong> Hacer doble clic en un número revelado revela automáticamente todos sus vecinos si se ha colocado el número correcto de banderas. Es la forma más rápida de limpiar un tablero cuando tienes confianza.',
    "seo_beyond_h2": "Más Allá del Tablero Clásico",
    "seo_beyond_p": "Una vez que el nivel principiante te resulte fácil, hay mucho más por explorar aquí:",
    "seo_beyond_li1": '<strong><a href="/tentaizu">Tentaizu</a> —</strong> Un puzle japonés de cartas estelares. Todas las pistas están preplantadas, sin clics para revelar — lógica pura desde el primer movimiento. Un nuevo puzle cada día.',
    "seo_beyond_li2": '<strong><a href="/rush">Rush</a> —</strong> Buscaminas competitivo de 60 segundos. Limpia tantos tableros como sea posible antes de que se acabe el tiempo.',
    "seo_beyond_li3": '<strong><a href="/cylinder">Cilindro</a> —</strong> El tablero clásico pero los bordes izquierdo y derecho se conectan, creando un campo envolvente sin costuras.',
    "seo_beyond_li4": '<strong><a href="/hexsweeper">Hexsweeper</a> —</strong> Buscaminas en una cuadrícula hexagonal. Cada celda tiene seis vecinos en lugar de ocho.',
    "seo_beyond_li5": '<strong><a href="/mosaic">Mosaico</a> —</strong> Una variante estilo nonograma donde las pistas cuentan un área de 3×3 en lugar de la adyacencia directa.',
    "seo_int_h2": "Buscaminas Intermedio — 16×16, 40 Minas",
    "seo_int_p1": 'Intermedio es donde el Buscaminas deja de ser un tutorial y se convierte en un juego. El tablero crece a <strong>16×16 con 40 minas</strong> — más de cuatro veces el área del principiante, con una densidad de minas de aproximadamente el 15,6 %. Las cadenas de deducción se extienden por múltiples filas. Los patrones que funcionaban de forma aislada en una cuadrícula 9×9 ahora se superponen e interactúan. El salto de dificultad es real, y es aquí donde la mayoría de los jugadores se estancan.',
    "seo_int_changes_h2": "Qué Cambia en Intermedio",
    "seo_int_changes_li1": '<strong>Cadenas de deducción más largas.</strong> Una restricción en un borde del tablero puede propagarse por cinco o seis celdas antes de resolverse. Necesitas mantener más estados en la mente simultáneamente.',
    "seo_int_changes_li2": '<strong>Muros de números más densos.</strong> Con más minas por área, verás más 2, 3 y 4 juntos. Leer pistas superpuestas — averiguar qué minas se comparten entre dos restricciones — es la habilidad clave aquí.',
    "seo_int_changes_li3": '<strong>Las situaciones 50/50 aparecen con más frecuencia.</strong> Con mayor densidad, surgen ambigüedades de dos celdas aisladas más frecuentemente. El modo sin adivinanzas las elimina si quieres un desafío de lógica pura.',
    "seo_int_changes_li4": '<strong>Las cascadas de apertura son más pequeñas.</strong> La mayor densidad de minas significa que la región abierta segura es menor en promedio. Pasarás más tiempo en deducción restringida que en exploración libre.',
    "seo_int_strat_h2": "Estrategia para Intermedio",
    "seo_int_strat_li1": '<strong>Domina el patrón 1-2.</strong> Un <em>1</em> adyacente a un <em>2</em> que comparten un vecino desconocido significa que el otro vecino único del <em>2</em> es una mina. Este patrón aparece constantemente a densidad intermedia.',
    "seo_int_strat_li2": '<strong>Trabaja los bordes primero.</strong> Las celdas de los bordes tienen menos vecinos, haciendo sus restricciones más ajustadas y fáciles de resolver. Limpiar los bordes primero abre territorio interior seguro.',
    "seo_int_strat_li3": '<strong>Rastrea los conteos de minas globalmente.</strong> Cuarenta minas son muchas para rastrear, pero si has marcado 35, solo quedan 5. Esa restricción global puede resolver clústeres ambiguos que el razonamiento local no puede descifrar.',
    "seo_int_strat_li4": '<strong>Usa los clics de acorde agresivamente.</strong> La velocidad importa. Una vez que un número está satisfecho, haz doble clic para revelar automáticamente los vecinos en lugar de hacer clic en cada uno manualmente.',
    "seo_int_strat_li5": '<strong>No marques en exceso.</strong> Cada bandera es un clic derecho y potencialmente un clic izquierdo desperdiciado. Los jugadores rápidos en este nivel marcan solo cuando necesitan el indicador visual para completar una cadena de deducción.',
    "seo_int_compare_h2": "Principiante vs. Intermedio vs. Experto",
    "seo_int_compare_li1": '<strong><a href="/">Principiante</a> —</strong> 9×9, 10 minas (~12,3 % de densidad). Aprende los fundamentos, busca marcas personales por debajo de 10 segundos.',
    "seo_int_compare_li2": '<strong>Intermedio (esta página) —</strong> 16×16, 40 minas (~15,6 %). El punto de control de habilidad estándar. Sub-60 s es respetable; sub-30 s es fuerte.',
    "seo_int_compare_li3": '<strong><a href="/expert">Experto</a> —</strong> 30×16, 99 minas (~20,6 %). El referente definitivo. El territorio de récord mundial está por debajo de 40 segundos.',
    "seo_int_related_h2": "Modos Relacionados",
    "seo_int_related_li1": '<strong><a href="/cylinder/intermediate">Cilindro Intermedio</a> —</strong> 16×16, 40 minas, pero los bordes izquierdo y derecho se conectan. Misma densidad, diferente topología.',
    "seo_int_related_li2": '<strong><a href="/toroid/intermediate">Toroide Intermedio</a> —</strong> Los cuatro bordes se conectan. Sin bordes en absoluto.',
    "seo_int_related_li3": '<strong><a href="/hexsweeper/intermediate">Hexsweeper Intermedio</a> —</strong> El tablero intermedio en una cuadrícula hexagonal.',
    "seo_int_related_li4": '<strong><a href="/tentaizu">Tentaizu</a> —</strong> Un puzle de deducción japonés con todas las pistas preplantadas. Sin adivinanzas, nunca. Nuevo puzle diario.',
    "seo_exp_h2": "Buscaminas Experto — 30×16, 99 Minas",
    "seo_exp_p1": 'Experto es el referente definitivo del Buscaminas. El tablero tiene <strong>30×16 con 99 minas</strong> — una densidad de minas de aproximadamente el 20,6 %, casi el doble que en principiante. No hay cascadas de apertura fáciles, ni regiones vacías generosas para explorar. Cada área del tablero está restringida, cada número es una pista que requiere atención inmediata. Aquí es donde el juego se pone serio.',
    "seo_exp_p2": 'Los jugadores de clase mundial terminan Experto en menos de 40 segundos. Sub-100 segundos es un hito intermedio común. Si eres nuevo en Experto, espera que tus primeras victorias tarden varios minutos — y espera perder con frecuencia. Aprender a leer el tablero a densidad experta lleva tiempo, pero el reconocimiento de patrones que se desarrolla es lo que separa a los jugadores ocasionales de los serios.',
    "seo_exp_hard_h2": "Qué Hace Difícil al Experto",
    "seo_exp_hard_li1": '<strong>Alta densidad de minas en todas partes.</strong> Con el 20,6 %, hay muy pocas celdas cero. Casi cada revelación produce un número. El tablero nunca se abre como lo hace en dificultades menores.',
    "seo_exp_hard_li2": '<strong>Resolución de restricciones simultáneas.</strong> Los tableros experto presentan regularmente configuraciones donde tres, cuatro o cinco celdas numeradas comparten vecinos desconocidos. Leer estos patrones rápidamente — y correctamente — es la habilidad central.',
    "seo_exp_hard_li3": '<strong>Presión de velocidad.</strong> Experto recompensa los patrones de clic eficientes. Los jugadores que logran tiempos sub-60 s han interiorizado los patrones comunes tan a fondo que los procesan en fracciones de segundo.',
    "seo_exp_hard_li4": '<strong>Adivinanzas más frecuentes.</strong> Incluso en tableros sin adivinanzas, los diseños de densidad experta producen cadenas más restringidas. Sin el modo sin adivinanzas, algunos tableros contienen 50/50 inevitables.',
    "seo_exp_strat_h2": "Estrategia Experta",
    "seo_exp_strat_li1": '<strong>Empieza con cualquier apertura.</strong> Tu primer clic es seguro en cualquier lugar. Muchos jugadores expertos prefieren una esquina — cascada inicial pequeña pero entrada inmediata en territorio restringido donde puedes empezar a leer.',
    "seo_exp_strat_li2": '<strong>Reconoce los patrones al instante.</strong> El patrón 1-2, 1-2-1, 1-2-2-1, esquinas aisladas, restricciones completadas — a velocidad experta, el reconocimiento de patrones debe ser automático. Estúdialos explícitamente.',
    "seo_exp_strat_li3": '<strong>Minimiza banderas, maximiza acordes.</strong> Los mejores jugadores expertos suelen usar un enfoque de "bandera sobre la marcha" o incluso "sin bandera", acordando a través de restricciones reveladas sin detenerse a hacer clic derecho en cada mina.',
    "seo_exp_strat_li4": '<strong>Escanea, no leas.</strong> No analices una celda a la vez. Entrena tus ojos para escanear una región en busca de restricciones completadas para acordar a través de múltiples celdas en un solo barrido.',
    "seo_exp_strat_li5": '<strong>Acepta las adivinanzas.</strong> En tableros que no son sin adivinanzas, los 50/50 inevitables son parte del Experto. Un buen tiempo con una mala adivinanza no es un fracaso — es varianza. Busca una deducción consistente en todo el tablero y deja que las probabilidades actúen con el tiempo.',
    "seo_exp_stats_h2": "Estadísticas 3BV del Experto",
    "seo_exp_stats_p1": 'Los tableros experto típicamente tienen un 3BV (conteo mínimo de clics) entre 100 y 200. Tu 3BV/s (3BV por segundo) y eficiencia (3BV dividido por los clics reales) aparecen en la tabla de clasificación — miden la calidad de tu juego más allá del tiempo bruto. Un tiempo rápido con baja eficiencia significa muchos clics desperdiciados. Alta eficiencia con tiempo lento significa técnica limpia, aún no a la velocidad máxima.',
    "seo_exp_stats_p2": 'La tabla de clasificación anterior muestra los mejores tiempos experto del día. Los tiempos incluyen tanto el modo estándar como el modo sin adivinanzas — comprueba el interruptor sobre el tablero para cambiar.',
    "seo_exp_stats_p3": '<a href="/info/3bv">Aprende más sobre 3BV →</a>',
    "seo_exp_variants_h2": "Variantes Experto",
    "seo_exp_variants_li1": '<strong><a href="/cylinder/expert">Cilindro Experto</a> —</strong> 30×16, 99 minas, con los bordes izquierdo y derecho conectados. La unión crea cadenas de deducción que abarcan toda la anchura del tablero.',
    "seo_exp_variants_li2": '<strong><a href="/toroid/expert">Toroide Experto</a> —</strong> Los cuatro bordes se conectan. Sin esquinas, sin bordes — cada celda tiene exactamente ocho vecinos.',
    "seo_exp_variants_li3": '<strong><a href="/hexsweeper/expert">Hexsweeper Experto</a> —</strong> Juego a densidad experta en una cuadrícula hexagonal. Seis vecinos por celda en lugar de ocho cambia la matemática de forma fundamental.',
    "seo_exp_variants_li4": '<strong><a href="/worldsweeper/expert">Worldsweeper Experto</a> —</strong> Buscaminas en un globo terráqueo 3D. Densidad experta distribuida por la superficie de una esfera.',
}

with open('/Users/cross/git/minesweeper.org/translations.py', 'r', encoding='utf-8') as f:
    content = f.read()

anchor = '        "guest_banner_post": "o tus puntuaciones desaparecer\\u00e1n a medianoche UTC.",'
if anchor not in content:
    print("ERROR: anchor not found")
    exit(1)

insert = '\n'
for k, v in ES.items():
    # escape backslashes and double quotes for file storage as Python dict string
    safe = v.replace('\\', '\\\\').replace('"', '\\"')
    insert += f'        "{k}": "{safe}",\n'

new = content.replace(anchor, anchor + insert, 1)
if new == content:
    print("ERROR: replacement had no effect")
    exit(1)

with open('/Users/cross/git/minesweeper.org/translations.py', 'w', encoding='utf-8') as f:
    f.write(new)
print("Done - inserted", len(ES), "keys for es")
